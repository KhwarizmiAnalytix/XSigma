# Memory Library Design

Scope: `Library/Memory` after the allocator consolidation and the GPU-cache /
ownership work (August 2026). This document describes the design **as it
exists now**, what landed in that pass, and what is still open.

Do not reintroduce the deleted machinery — the `Allocator` virtual interface,
`process_state`, BFC / pool / retry / tracking backends, `gpu_memory_*`
helpers, or the visualization dashboard — without a measured need (see
`Library/Memory/CLAUDE.md`).

---

## 1. Design goals

1. **Simple and fast CPU allocation.** Direct call into the best available
   system allocator (mimalloc by default). No virtual dispatch, no pooling
   layer, no always-on mutex or bookkeeping on the hot path. When
   `MEMORY_HAS_PROFILER=1`, a predicted-false `memory_profiling_active()`
   check is the only added cost unless a session actually wants memory events.
2. **Cached GPU allocation.** CUDA, HIP, and Metal allocations go through a
   PyTorch-style caching allocator so tensor alloc/free churn amortizes into
   cached segment reuse instead of driver malloc/free round-trips.
3. **One ownership story.** Owning storage is `memory::data_ptr<T>` (unique,
   copy always clones). Non-owning windows are `memory::data_view<T>`
   (constructed from a `data_ptr`, or `borrow()` for foreign memory).
   Allocation is `memory::allocator<T>` (static, policy-free).
4. **Compile-time backend selection.** CPU allocator backend, GPU backend
   (none/CUDA/HIP/Metal), NUMA, memkind, and TBB are CMake/Bazel-time
   decisions expressed as `MEMORY_HAS_*`. One GPU backend per binary.
5. **PyTorch-shaped client cache API.** Process-wide
   `empty_cache` / `memory_allocated` / `memory_reserved` /
   `set_memory_fraction` / `reset_peak_memory_stats` so a finance engine can
   drive the cache the same way it would `torch.cuda.*`.

---

## 2. Architecture at a glance

```
client code (Vectorization tensors, expressions, …)
        │
        ├─ owner ──► memory::data_ptr<T>          common/data_ptr.h   — unique RAII
        │                 │  view()
        └─ window ─► memory::data_view<T>         common/data_view.h  — non-owning
                          │  allocates/frees/copies via
                          ▼
memory::allocator<T, alignment>       allocator.h          — static dispatch by device_enum
        │
        ├─ device_enum::CPU ────► memory::cpu::memory_allocator
        │                          helper/memory_allocator.{h,cpp}
        │
        ├─ device_enum::CUDA ───► memory::gpu::caching_allocator_for_device(i)
        │   device_enum::HIP      gpu/caching_allocator.h → cuda_caching_allocator
        │                         (HIP via gpu/gpu_runtime.h)
        │
        └─ device_enum::METAL ──► memory::gpu::caching_allocator_for_device(i)
                                  gpu/caching_allocator.h → metal_caching_allocator
```

Vectorization `tensor<T>` holds both: `data_ptr` when this tensor owns
storage, `data_view` for the addressable buffer. Copy always deep-clones
via `data_ptr` (same contract as `data_ptr` itself). Wrap constructors and
`t()` / `view()` / `slice()` borrow; the source must outlive those views.

### File map

| Path | Role |
|---|---|
| `allocator.h` / `allocator.cpp` | `allocator<T>` allocate/free/copy/record_stream + process-wide cache helpers |
| `common/data_ptr.h` | Unique owning typed buffer; copy always clones; stores device index + stream |
| `common/data_view.h` | Non-owning window over a `data_ptr` (or `borrow()` for foreign memory) |
| `common/device.{h,cpp}` | `device_enum` (CPU/CUDA/HIP/PrivateUse1/METAL), `device_option` |
| `common/memory_macros.h` | `MEMORY_ALIGNMENT` (64, 16 on `MEMORY_MOBILE`), force-inline/likely/export |
| `common/memory_containers.h` | `memory_map`/`memory_set` aliases (flat-hash optional) |
| `common/numa.{h,cpp}` | `NUMAMove` / `GetCurrentNUMANode` (Linux, `MEMORY_HAS_NUMA`) |
| `helper/memory_allocator.{h,cpp}` | Raw CPU allocation backend |
| `gpu/caching_allocator.h` | Unified registry + process-wide `torch.cuda.memory` analogues |
| `gpu/caching_allocator_config.h` | Shared size-class constants (512 B / 2–20 MiB segments) |
| `gpu/gpu_runtime.h` | CUDA↔HIP portability (`cuda*` spellings → `hip*` under HIP) |
| `gpu/cuda_caching_allocator.{h,cpp}` | CUDA/HIP segment cache + per-device registry |
| `gpu/metal/metal_caching_allocator.{h,mm}` | Metal segment cache (same size classes; MTLHeap-backed) |
| `gpu/metal/metal_buffer_allocator.{h,mm}` | Metal bind helpers (`mtl_buffer_handle` / `offset`) |
| `profiler/unified_memory_stats.{h,cpp}` | `unified_cache_stats` — GPU cache metrics |
| `profiler/gpu_memory_snapshot.h` | GPU segment snapshot + history ring (`_snapshot` / `_record_memory_history`) |
| `profiler/profiled_cpu_memory_reporter.{h,cpp}` | CPU alloc/free/OOM → profiler (gated) |

---

## 3. CPU path — `cpu::memory_allocator`

The whole CPU implementation is ~200 lines in `helper/memory_allocator.cpp`.
`allocator<T>::allocate(n, CPU)` is one force-inline hop into:

```cpp
void* allocate(std::size_t nbytes,
               std::size_t alignment = default_alignment(),   // MEMORY_ALIGNMENT
               init_policy_enum init = UNINITIALIZED);
void  free(void* ptr, std::size_t nbytes = 0) noexcept;
std::size_t usable_size(const void* ptr) noexcept;
```

### Backend selection (compile time, first match wins)

| Order | Guard | allocate | free | usable_size |
|---|---|---|---|---|
| 1 | `MEMORY_HAS_MIMALLOC` (default ON) | `mi_aligned_alloc` | `mi_free` | `mi_usable_size` |
| 2 | `MEMORY_HAS_TBB` | `scalable_aligned_malloc` | `scalable_aligned_free` | `scalable_msize` |
| 3 | `__ANDROID__` | `memalign` | `free` | `malloc_usable_size` |
| 4 | MSVC / MinGW | `_aligned_malloc` | `_aligned_free` | **0** (needs original alignment) |
| 5 | Apple | `posix_memalign`/`malloc` | `free` | `malloc_size` |
| 6 | other POSIX | `posix_memalign`/`malloc` | `free` | `malloc_usable_size` |

`usable_size` returns the backend-reported block size (≥ requested), or 0
where the backend cannot report (MSVC) — callers must treat 0 as "unknown",
not "empty".

### Behavior notes

- **Validation**: `LOGGING_CHECK` rejects `nbytes == 0`; debug builds also
  assert power-of-two alignment ≥ `sizeof(void*)`.
- **NUMA** (`MEMORY_HAS_NUMA`, Linux only): after allocation, `NUMAMove(ptr,
  nbytes, GetCurrentNUMANode())` applies first-touch policy. Free needs no
  NUMA handling.
- **Init policies**: `UNINITIALIZED` (fastest), `ZERO` (`memset 0` — also
  exposed as `allocate_zero`), `PATTERN` (`memset 0xCC`, debug builds only).
- **Escape hatches**: `allocate_tbb`/`free_tbb` and `allocate_mi`/`free_mi`
  call a specific backend directly (return nullptr when that backend is not
  compiled in) — used by the CPU benchmark to compare backends.
- **Threading**: everything is delegated to the backend. mimalloc gives
  per-thread free lists, so the multithreaded hot path is effectively
  contention-free without any project-level locking. With `MEMORY_HAS_PROFILER`,
  the profiler reporter is compiled in but takes a mutex only after
  `memory_profiling_active()` (predicted-false); without Profiler the
  allocate/free path does not call it.

### CPU profiler reporter (`profiled_cpu_memory_reporter`)

Equivalent of PyTorch `c10::ProfiledCPUMemoryReporter`. Compiled into
`allocate` / `free` only when `MEMORY_HAS_PROFILER=1`, and then only after a
predicted-false `profiler::memory_profiling_active()` check (same pattern as
the GPU caching allocators). Failed mallocs become `[OutOfMemory]` when a
session has `profile_memory=true`. `total_reserved` is 0 — no CPU caching
pool. `allocate_mi` / `allocate_tbb` bypass the reporter.

### mimalloc statistics (opt-in)

mimalloc release builds compile statistics **out** (`MI_STAT=0` in
`ThirdParty/mimalloc`); `MEMORY_ENABLE_MIMALLOC_STATS=ON` (setup.py
`--mimalloc_stats` — a `--` flag, not a dotted token, since `_` is a token
delimiter there) rebuilds the vendored `mimalloc-static` with `MI_STAT=1` and
sets `MEMORY_HAS_MIMALLOC_STATS=1`. Two consumption routes:

- **Env vars**: `MIMALLOC_SHOW_STATS=1` dumps full stats at process exit;
  `MIMALLOC_VERBOSE=1` prints init messages.
- **API** (`helper/memory_allocator.h`): `has_stats()` (compile-time
  availability), `stats_print()` (`mi_stats_merge` + line dump via
  `LOGGING_LOG_INFO`), `process_info(process_memory_info&)` (RSS / commit /
  page faults).

Because mimalloc is linked with `MI_OVERRIDE=OFF`, the stats cover only
allocations that went through this path — not the process's `malloc`.

`unified_cache_stats` remains the GPU cache metrics surface. Always-on CPU
allocation counters stay off the hot path; the gated profiler reporter and
mimalloc's opt-in stats are the CPU exceptions.

---

## 4. CUDA / HIP path — `cuda_caching_allocator`

Behavioral port of PyTorch's `c10/cuda/CUDACachingAllocator`, in
`gpu/cuda_caching_allocator.{h,cpp}` (PIMPL). Under `MEMORY_HAS_HIP` the same
translation unit runs on `hipMalloc` / `hipEvent*` via `gpu/gpu_runtime.h`
(call sites keep CUDA API spellings). On Metal builds the TU compiles to a
throwing stub so the header surface stays available.

### Size classes and segments

One driver malloc per **segment**; many blocks per segment.

| Request (after rounding) | Segment size |
|---|---|
| < 512 B → rounded up to 512 B multiples | — |
| ≤ 1 MiB ("small") | 2 MiB |
| 1–10 MiB | 20 MiB |
| ≥ 10 MiB | rounded up to 2 MiB multiples |

Two free pools: `small_blocks_` (≤ 1 MiB requests) and `large_blocks_`.
A request is only ever served from its own pool.

### Expandable segments

`malloc_segment` uses `cudaMalloc` / `hipMalloc` by default. An optional
virtual-memory mapping (`cuMemCreate` + `cuMemMap` / HIP `hipMem*`, ROCm ≥ 5.6)
is available via `set_expandable_segments(true)` but is **off by default**:
the previous always-on path reserved a VA range sized exactly to the segment
and never expanded it, paying 1.25–1.66× vs `cudaMalloc` with none of
PyTorch's fragmentation win. Failure of the opt-in VM path is still silent;
the next attempt is a plain driver malloc.

### Block lifecycle

- **Reuse lookup**: pools are ordered sets keyed by `(stream, size,
  registration_counter, ptr)`. Lookup is `lower_bound(size, stream)` →
  smallest sufficient block **on the same stream**; equal-size segments
  recycle FIFO. Blocks are never reused on a different stream than the
  allocation stream.
- **Split**: remainder ≥ 512 B (small pool) or > 1 MiB (large pool).
- **Coalesce**: on free, merge with `prev`/`next` only if the neighbor is
  free, has no pending events, and no recorded cross-stream uses.
- **Release to driver**: only *whole* (never-split) segments can be freed —
  split remainders share a segment with live neighbors.

### Cross-stream safety

- `record_stream(ptr, stream)` (or a deallocate stream hint) marks a live
  block as used on another stream (uses on the allocation stream are ignored).
- On free, a block with recorded uses is not pooled immediately: one CUDA/HIP
  event per recorded stream is queued, and the block is reclaimed lazily by
  `process_events_locked()` at the top of every `allocate`/`deallocate`.
- `insert_events_locked` is exception-safe (sanctioned `try/catch` around
  the driver).

### OOM and cache-pressure handling

`allocate` failure chain, mirroring upstream:

1. `get_free_block` from the pool.
2. Run registered **free-memory callbacks**; if any freed memory, retry the
   pool. The lock is recursive so a callback may `deallocate` / `empty_cache`.
3. If `set_memory_fraction` would be exceeded by a new segment, flush cached
   whole segments first; still over → `std::bad_alloc`.
4. Driver segment alloc with the allocator **mutex dropped** across
   `cudaMalloc` / `hipMalloc` (PyTorch ~2.7+). Non-OOM driver errors throw;
   the CUDA error state is cleared either way.
5. On `cudaErrorMemoryAllocation`: flush cache (synchronize pending events,
   `num_sync_all_streams++`) and retry the driver **once**.
6. Still failing → `num_ooms++`, `[OutOfMemory]` if a profiler session has
   `profile_memory`, a history-ring `oom` entry if recording, then
   `std::bad_alloc`.

Independently, `set_max_cached_bytes(bytes)` (default: unlimited) trims the
cache largest-first among releasable whole segments after every allocate and
deallocate. `empty_cache()` force-releases everything.

### GPU memory profiler (PyTorch `profile_memory` + `_snapshot`)

When `MEMORY_HAS_PROFILER=1`, CUDA/HIP and Metal `allocate` / `deallocate`
report the **known block size** (not a pool scan) after a predicted-false
`memory_profiling_active()` check — the same `report_memory_usage` contract
as Memory's CPU reporter. OOM calls `report_out_of_memory`.

Separately, `record_memory_history` / `snapshot` (and process-wide
`gpu::record_memory_history` / `gpu::memory_snapshot`) port
`torch.cuda.memory._record_memory_history` / `_snapshot`: a segment/block
map plus a bounded action ring. C++/Python stacks are not captured.

### Process-wide client API (PyTorch `torch.cuda.memory`)

Declared in `gpu/caching_allocator.h`, also as `allocator<T>` statics.
Operates on `caching_allocator_for_device(device_index)`:

| PyTorch | XSigma |
|---|---|
| `torch.cuda.empty_cache()` | `gpu::empty_cache(i)` |
| `memory_allocated` / `max_memory_allocated` | `gpu::memory_allocated` / `max_memory_allocated` |
| `memory_reserved` / `max_memory_reserved` | `gpu::memory_reserved` / `max_memory_reserved` |
| `memory_stats()` | `gpu::memory_stats()` → `unified_cache_stats` |
| `reset_peak_memory_stats()` | `gpu::reset_peak_memory_stats(i)` |
| `set_per_process_memory_fraction(f)` | `gpu::set_memory_fraction(f, i)` — cap reserved at `f * device_total_memory()` |
| `_record_memory_history` / `_snapshot` | `gpu::record_memory_history` / `gpu::memory_snapshot` — no stack frames |

`unified_cache_stats` also tracks `peak_bytes_allocated` /
`peak_bytes_reserved`, `inactive_split_bytes`, `num_alloc_retries`,
`num_ooms`, `num_sync_all_streams`.

### Device discipline

Driver-facing entry points hold a `DeviceGuard(device_)` (RAII
`cudaSetDevice`). `allocator<T>::copy` uses the same idea: it sets the
destination (or source) device from `to_index` / `from_index`, and uses
`cudaMemcpyPeer` / `cudaMemcpyPeerAsync` when both sides are GPU and the
indices differ.

### Threading model

One `std::recursive_mutex` per allocator instance. The mutex is **released**
around the driver malloc (other threads can hit the cache meanwhile) and
re-acquired afterwards. Stats counters are atomics, mutated under the lock
except where noted.

### Per-device registry

```cpp
MEMORY_API cuda_caching_allocator& caching_allocator_for_device(int device_index);
```

Defined in the `.cpp` (mutex + `unordered_map`, lazy creation, index
validated against `cudaGetDeviceCount`). One registry process-wide even when
multiple shared libraries link Memory.

---

## 5. Metal path — `metal_caching_allocator`

`gpu/metal/metal_caching_allocator.{h,mm}` — same size classes, split/coalesce,
trim, OOM flush+retry, `unified_cache_stats`, free-memory callbacks, and the
process-wide API as CUDA. Segments are shared-storage `MTLBuffer`s, preferably
suballocated from an `MTLHeap`. Host pointers are `buffer.contents + offset`.

- Registry: `caching_allocator_for_device(i)` (device index **0 only** —
  `MTLCreateSystemDefaultDevice`).
- Streams: `stream_type` is `void*`; single default-stream pool.
  `record_stream` is a documented no-op (Vectorization Metal dispatch is
  `waitUntilCompleted`).
- Bind helpers: `mtl_buffer_handle` / `mtl_buffer_offset`.
- No fp64: `allocator<T>` throws `std::invalid_argument` for `double` on
  METAL (`if constexpr`).
- `set_memory_fraction` uses `recommendedMaxWorkingSetSize` as device
  capacity.

---

## 6. Ownership: `data_ptr<T>` and `data_view<T>`

`clone` is no longer a template parameter on `data_ptr`. Unique ownership and
aliasing are two types.

### `data_ptr<T>` — unique owner (`common/data_ptr.h`)

| Aspect | Design |
|---|---|
| Sized ctor | `data_ptr(size, device, device_index=0, stream=nullptr)` allocates |
| Raw-pointer ctor | **Always clones** into owned storage (does not adopt) |
| `explicit data_ptr(data_view)` | Clones the view's buffer |
| Copy | Always deep-clones (`data_ptr(rhs.view())`) |
| Move | Transfers ownership; moved-from handle is zeroed |
| Destructor | `allocator<T>::free` on the stored device index and stream |
| Members | `device_index_` and `stream_` are stored |
| `view()` / `view(offset, count)` | Returns a `data_view` over the owned buffer |

### `data_view<T>` — non-owning window (`common/data_view.h`)

| Aspect | Design |
|---|---|
| From owner | `data_view(data_ptr const&)` / `data_view(owner, offset, count)` |
| Foreign memory | `data_view<T>::borrow(ptr, size, device, index, stream)` — raw ctor is private |
| Copy | Aliases the pointer; destructor does not free |
| Lifetime | Does **not** keep the `data_ptr` alive. Destroying the owner while a view exists dangles |

Vectorization wrap constructors and `t()` / `view()` / `slice()` use
`borrow()`. Copy of a tensor always clones into a new `data_ptr`. Sized
ctors take optional `device_index` and `gpu_stream_t` (defaults: 0 /
`nullptr`) and pass them through to `data_ptr`.

`assign_async` records `record_stream` on the destination **and** walks
expression sources (unary / binary / trinary / tensor leaves) so the cache
does not reuse a source buffer still in flight on another stream.

### Cross-device copy matrix (`allocator<T>::copy`)

| from → to | Mechanism |
|---|---|
| CPU → CPU | `memcpy` |
| CPU ↔ CUDA/HIP, same-device GPU → GPU | `cudaMemcpy` / `cudaMemcpyAsync` under a `DeviceGuard` on the GPU index |
| CUDA/HIP peer (`from_index != to_index`) | `cudaMemcpyPeer` / `cudaMemcpyPeerAsync` |
| CPU ↔ METAL, METAL ↔ METAL | `memcpy` (shared storage); indices unused |
| anything else | `std::invalid_argument` |

---

## 7. Error-handling contract

- **Allocate paths throw**: `std::bad_alloc` on exhaustion (CPU null return,
  GPU after the fraction check / flush-and-retry chain),
  `std::invalid_argument` for unsupported device/type combinations
  (including Metal `double`).
- **Free paths**: CPU frees are non-throwing. GPU caching `deallocate`
  throws on a foreign pointer / double free. Because `~data_ptr()` is
  implicitly `noexcept`, that bug terminates rather than corrupting
  silently.
- `LOGGING_CHECK` backs internal invariants with formatted messages.

---

## 8. Configuration matrix

| Knob | CMake | Bazel | Effect |
|---|---|---|---|
| GPU backend | `MEMORY_GPU_BACKEND=none\|cuda\|hip\|metal` | `//bazel:enable_cuda` / `enable_hip` / `enable_metal` | Sets `MEMORY_HAS_CUDA/HIP/METAL`; gates `gpu/*.cpp` (`.mm` only under metal) |
| mimalloc | `MEMORY_ENABLE_MIMALLOC` (ON) | default on; `//bazel:disable_mimalloc` | Backend #1 for CPU path |
| TBB malloc | `MEMORY_ENABLE_TBB` | `memory_enable_tbb` | Backend #2 |
| NUMA | `MEMORY_ENABLE_NUMA` (Linux) | `memory_enable_numa` | First-touch in CPU allocate |
| memkind | `MEMORY_ENABLE_MEMKIND` (Linux, OFF) | `memory_enable_memkind` | Extended-memory support |
| Logging | always linked | — | `LOGGING_LOG_*` / `LOGGING_CHECK` used directly |

The old `MEMORY_GPU_ALLOC` strategy knob and `MEMORY_HAS_ALLOCATION_STATS`
were removed with the machinery that consumed them.

Per-permutation compile coverage: `none` and `metal` are built and tested on
macOS. `cuda` / `hip` share the caching-allocator TU and compile; **runtime**
verification needs a CUDA or ROCm host (this Mac is Metal-only).

---

## 9. Testing surface

| File | Covers |
|---|---|
| `Testing/Cxx/TestCPUMemory.cpp` | Raw CPU backend |
| `Testing/Cxx/TestProfiledCPUMemoryReporter.cpp` | CPU profiler reporter (New/Delete/OOM + allocate wiring) |
| `Testing/Cxx/TestAllocator.cpp` | `allocator<T>` CPU path; `data_ptr` copy-clone / clone-from-view |
| `Testing/Cxx/TestDataView.cpp` | `data_view` from `data_ptr`, slice, `borrow()`, destructor does not free |
| `Testing/Cxx/TestGpuMemoryProfiler.cpp` | GPU snapshot / history / fraction OOM (CUDA, HIP, Metal) |
| `Testing/Cxx/TestCudaCachingAllocator.cpp` | CUDA/HIP caching allocator (those backends only) |
| `Testing/Cxx/TestMetalBufferAllocator.cpp` | Metal allocate/copy via `allocator<T>` |
| `Testing/Cxx/TestMetalCachingAllocator.cpp` | Metal segment cache + process-wide API |
| `Testing/Cxx/TestCachingAllocatorStub.cpp` | CUDA allocator stub on Metal builds |
| `Testing/Cxx/TestUnifiedMemoryStats.cpp` | `unified_cache_stats` rates / copy / `reset_peaks` |
| `Testing/Cxx/BenchmarkCPUMemoryAllocators.cpp` | CPU backend comparison |
| `Testing/Cxx/BenchmarkPyTorchComparisonCpu.cpp` | LibTorch CPU comparison (when LibTorch is on) |
| `Testing/Cxx/BenchmarkPyTorchComparisonGpu.cpp` | LibTorch GPU comparison (when LibTorch + GPU) |

Test files are globbed per-backend (`TestGpu*`/`TestCuda*`/`TestHip*`/
`TestMetal*` filtered by `MEMORY_GPU_BACKEND`). There is no `TestHip*.cpp`;
HIP runtime coverage is the CUDA test file compiled against `hip*`.

---

## 10. Status — done vs still open

### Done (August 2026)

- PyTorch-style 512 B / 2 MiB / 20 MiB segment cache on **CUDA, HIP, and
  Metal**; HIP is the CUDA TU via `gpu/gpu_runtime.h`.
- Expandable VM segments (`cuMemMap` / HIP ≥ 5.6) **opt-in** via
  `set_expandable_segments` (default off); silent fallback to
  `cudaMalloc` / `hipMalloc`.
- Allocator mutex **released** around the driver malloc.
- OOM: free-memory callbacks → fraction flush → driver alloc → full cache
  flush + one retry → `std::bad_alloc`.
- `set_max_cached_bytes` largest-first trim; Metal `MTLHeap` packing.
- `data_ptr` unique owner (copy clones); `data_view` window on `data_ptr`;
  `borrow()` for foreign wrap. Device index and stream stored on both.
- Vectorization tensor: `owner_` + `view_`; copy always clones; wrap / `t()` /
  `slice()` borrow; `size()` is logical numel; `at`/`[]` use strides; `clone()`
  copies via the allocator on the source device; expression converting
  constructors infer device from tensor leaves; sized ctors take
  `device_index` + `stream`; `assign_async` records dest **and** expression
  sources; host copies pass the tensor's device index.
- Process-wide cache API matching `torch.cuda.memory` (`empty_cache`,
  allocated/reserved + peaks, `set_memory_fraction`,
  `reset_peak_memory_stats`, `device_total_memory`).
- `allocator<T>::copy` honors `from_index` / `to_index` (DeviceGuard + peer
  copy on CUDA/HIP).
- Metal + CMake/Bazel Memory and Vectorization tests green on macOS.

### Still to do

Client / product gaps vs PyTorch (not missing size classes):

1. **CUDA / HIP runtime verification** on a GPU host. Metal is the only
   caching path exercised on this Mac. HIP has no dedicated `TestHip*.cpp`.
2. **CUDA graphs / capture-safe pools / `MemPool`.** No graph capture, no
   private pool, no capture-aware `record_stream` reuse. PDE time-stepping
   cannot replay a captured graph through this allocator.
3. **Pinned host caching allocator.** H2D of market data and MC gather still
   uses caller-managed host buffers (`cudaHostAlloc` / pageable).
4. **`PYTORCH_CUDA_ALLOC_CONF` knobs.** `expandable_segments` is now a
   runtime toggle (`set_expandable_segments`, default off). `max_split_size_mb`,
   `roundup_power2_divisions`, and `garbage_collection_threshold` are not
   ported. Mixed-tenor MC books must bucket sizes in the engine. Watch
   `inactive_split_bytes`.
5. **OOM forensics stacks.** Segment snapshot and the allocation-history
   ring are ported (`gpu::memory_snapshot` / `record_memory_history`).
   GatheredContext / Python-C++ stack capture is not. Overnight debugging
   can dump the segment map; attributing a block to a call site still
   needs an external tracer.
6. **`cudaMallocAsync` / `hipMallocAsync` backend.** Native stream-ordered
   pools are not an alternate path.
7. **View lifetime.** `data_view` does not refcount the owner. Destroying a
   `data_ptr` / owning tensor while a view (`t()` / wrap / `slice`) exists
   is a dangling GPU pointer. Tensor **copy** now clones, so an aliased copy
   is no longer the default. PyTorch `Storage` is refcounted.
8. **Metal async.** `record_stream` is a no-op; single pool; device 0 only;
   no fp64. Fine for fp32 PDE prototypes, not a production MC path.
9. **Tensor defaults.** Public `tensor(n, CUDA)` still allocates on device 0
   / default stream unless the caller passes index and stream. Expression
   converting constructors (`tensor r = ga + gb`) now inherit device/index
   from the leaves. Multi-GPU books must still pass them on sized ctors.
10. **`empty_cache` is not on the Vectorization public surface** — include
    Memory headers (`allocator.h` or `gpu/caching_allocator.h`). Do not call
    it on the hot path (per-trade); call it between heterogeneous books.

Operational habits that matter more than further allocator ports: preallocate
path/grid buffers, bucket MC sizes, `empty_cache` between mixed books (not
per trade), `record_stream` every buffer a non-default stream reads or
writes, keep views shorter-lived than owners, log `bytes_allocated` /
`bytes_reserved` / `inactive_split_bytes` per job.
