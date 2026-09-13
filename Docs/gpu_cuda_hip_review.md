# GPU Backend Review — CUDA / HIP

Scope: the CUDA and HIP paths across `Library/Memory`, `Library/Vectorization`,
and Profiler (now `ThirdParty/Profiler`), reviewed 2026-09-07. This document records **where the
GPU implementation stands today**, the measured performance of the CUDA path,
and the open gaps ranked by impact.

Companion documents: [`memory_design.md`](memory_design.md) §4 for the caching
allocator design, [`vectorization_backends.md`](vectorization_backends.md) for
the evaluator contracts, and
[`CUDA_HIP_REMEDIATION_PLAN.md`](CUDA_HIP_REMEDIATION_PLAN.md) for the
(superseded) July 2026 defect log. This review does not repeat those; it covers
current state and performance only.

---

## 1. Measurement environment

Every number in §3 was measured on a single machine. **Read the caveats before
generalizing any of them.**

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Ti (Ada, sm_89) |
| Peak DRAM bandwidth | 288 GB/s (128-bit GDDR6 @ 18 Gbps) |
| L2 cache | 32 MiB |
| Host | WSL2 (Linux 6.6.87.2-microsoft-standard-WSL2), 32 logical CPUs |
| CUDA | 12.x via `/usr/local/cuda/bin/nvcc` |
| Build | `build_ninja`, `MEMORY_GPU_BACKEND=cuda`, `VECTORIZATION_GPU_BACKEND=cuda` |
| Benchmark | `build_ninja/bin/benchmark_tensorgpu`, `--benchmark_min_time=0.2s` |

Caveats that matter:

- **WSL2 inflates kernel-launch latency.** An empty kernel plus
  `cudaDeviceSynchronize` costs 18.3 µs here; native Linux is typically
  5–8 µs. Every latency figure below is WSL2-inflated.
- **WSL2 also narrows the pinned-vs-pageable transfer gap** to ~5% (§3.4).
  On native Linux/Windows with PCIe 4.0 this gap is normally much larger.
- Single machine, single run, no run-to-run variance captured. Treat these as
  order-of-magnitude findings, not a regression baseline.
- HIP was **not** measured — no AMD hardware was available (§4, gap 10).

---

## 2. Current state

### 2.1 What is implemented

**Backend portability is real.** CUDA and HIP share one code path rather than
forking:

- `Library/Memory/gpu/gpu_runtime.h` — call sites keep CUDA API spellings;
  HIP builds macro-map them to `hip*`. One translation unit serves both.
- `Library/Vectorization/backend/gpu/gpu_stream_compat.h` — backend-neutral
  `gpu*` aliases so callers avoid their own `#if` ladders.
- `Library/Memory/gpu/caching_allocator.h` — single `memory::gpu::caching_allocator`
  alias and one `caching_allocator_for_device()` registry name, so
  `allocator<T>` never forks on backend-specific symbols.
- Backends are compile-time exclusive, selected by `MEMORY_GPU_BACKEND` /
  `VECTORIZATION_GPU_BACKEND` (`none|cuda|hip|metal`).

**The caching allocator is a genuine PyTorch port**, not a thin wrapper
(`Library/Memory/gpu/cuda_caching_allocator.cpp`, 1362 lines). It implements:

- 512-byte request rounding; 2 MiB segments for ≤1 MiB requests, 20 MiB for
  1–10 MiB, 2 MiB-rounded above that (`caching_allocator_config.h`)
- split-on-reuse with free-neighbour coalescing via intrusive `prev`/`next`
- stream-scoped free pools — a block is never reused on a foreign stream
- `record_stream()` (PyTorch `recordStream` semantics) with event-deferred
  reclamation, per-stream event queues drained independently
- the upstream OOM chain: free-memory callbacks → retry cache → flush entire
  cache → retry driver malloc once → `std::bad_alloc`
- `set_memory_fraction`, `reset_peak_stats`, `empty_cache` — the
  `torch.cuda.*` process-wide surface
- `record_memory_history` / `snapshot` — the
  `torch.cuda.memory._record_memory_history` / `_snapshot` equivalent

**Stream infrastructure exists and is correct.** `terminals/stream_guard.h`
provides a thread-local ambient current stream per device (PyTorch
`CUDAStreamGuard` shape), and `tensor::assign_async` / `copy_from_host(..., stream)`
give explicit async entry points that thread through to `record_stream`.

**Profiler** routes CUDA GPU activity through the vendored Kineto fork
(CUPTI on CUDA, roctracer on HIP), wired in `ThirdParty/Profiler/CMakeLists.txt`.

### 2.2 Test status (verified 2026-09-07)

| Suite | Filter | Result |
|---|---|---|
| `MemoryCxxTests` | `*Cuda*:*Gpu*:*GPU*` | 38 passed |
| `VectorizationCxxTests` | `*Gpu*:*GPU*:*Cuda*:*Stream*` | 22 passed, 1 skipped (Metal-only) |

---

## 3. Performance

### 3.1 Kernel shape is at the roofline — do not optimize it

`Library/Vectorization/expressions/expressions_evaluator_gpu.h` uses a naive
one-thread-per-element kernel with a fixed block size of 256, no grid-stride
loop and no vectorized loads. That turns out to be the right choice.

4M-element `c = a + b` (float), 3 arrays × 4M × 4 B = 50.3 MB moved:

| Implementation | Time | Effective bandwidth |
|---|---|---|
| XSigma `c = a + b` | 205 µs | 245 GB/s |
| Hand-written naive CUDA equivalent | 209 µs | 240 GB/s |
| Hand-written `float4` + grid-stride | 223 µs | 225 GB/s |

**245 GB/s is 85% of this card's 288 GB/s peak.** The vectorized/grid-stride
rewrite is *slower*. The kernel is memory-bandwidth-bound and already near the
roofline; there is no headroom to recover by changing kernel shape.

Note the L2 effect when reading the size sweep: at 1M elements the working set
(12.6 MB) fits in the 32 MiB L2, so the reported 552 GB/s exceeds DRAM peak.
Only the 4M row (50 MB, exceeds L2) reflects true DRAM bandwidth.

### 3.2 Every op has a fixed ~16 µs floor — and it is not framework overhead

| `GPU_Add<float>` | Time | Throughput |
|---|---|---|
| 1 K elements | 16.1 µs | 63.0 M items/s |
| 64 K elements | 16.0 µs | 4.06 G items/s |
| 1 M elements | 22.8 µs | 45.7 G items/s |
| 4 M elements | 205 µs | 20.3 G items/s |

1 K and 64 K cost the same — both are pure latency. Measured against the raw
driver on the same box:

- empty kernel + `cudaDeviceSynchronize`: **18.3 µs**
- bare `cudaDeviceSynchronize` (nothing pending): 0.12 µs

XSigma's 16 µs is **at or below** the raw launch-plus-sync round-trip. The
framework adds essentially nothing; the floor is the WSL2 driver round-trip
(§1). The consequence still stands regardless of platform: **below roughly 1M
elements the CUDA path is entirely latency-bound**, and 64 K elements runs at
4 G items/s against the 128 G/s the hardware reaches at 4M. The fix is not a
faster kernel — it is not synchronizing (the existing `assign_async` API) or
batching launches under CUDA graphs (§4, gap 7).

### 3.3 Host↔device transfer dominates end-to-end by 30×

`GPU_Add_Transfer<float>` (upload both operands, add, download result):

| Elements | Total | Of which compute |
|---|---|---|
| 1 K | 95.5 µs | ~16 µs |
| 64 K | 245 µs | ~16 µs |
| 1 M | 1601 µs | ~23 µs |
| 4 M | 6710 µs | 205 µs |

At 4M, **97% of wall time is transfer and host buffer management**, not
compute. Decomposing the 6710 µs against measured raw copy costs on this box
(16 MB pageable H2D = 1427 µs, D2H = 1391 µs):

- 2 × H2D + 1 × D2H ≈ 4250 µs
- compute ≈ 205 µs
- **remaining ≈ 2260 µs is `to_host_vector()`** allocating and
  value-initializing a fresh 16 MB `std::vector` on every call
  (`terminals/tensor.h:811`)

That allocation costs more than the kernel by an order of magnitude, and there
is no non-allocating download overload (§4, gap 3).

### 3.4 Pinned memory: small raw win here, but it gates overlap

16 MB transfers, measured:

| Host buffer | H2D | D2H |
|---|---|---|
| pageable | 1427 µs (11.76 GB/s) | 1391 µs (12.06 GB/s) |
| pinned (`cudaMallocHost`) | 1359 µs (12.35 GB/s) | 1322 µs (12.69 GB/s) |

Only ~5% apart **on this WSL2 host** — do not quote this as the general case.
The reason pinned memory matters is not raw bandwidth: it is the precondition
for chunked copy/compute overlap, which is the only mechanism that addresses
the 97% transfer share in §3.3. There is no pinned host allocator anywhere in
the tree (§4, gap 1).

### 3.5 Streams currently buy nothing for elementwise work

| Elements | `GPU_SingleStream_Add<float>` | `GPU_MultiStream_Add<float>` |
|---|---|---|
| 1 K | 49.5 µs | 28.6 µs |
| 64 K | 50.2 µs | 28.3 µs |
| 1 M | 204 µs | 202 µs |
| 4 M | 819 µs | 826 µs |

At 1M and 4M multi-stream is indistinguishable from single-stream, because the
work is already bandwidth-saturated — there is nothing left to overlap. The
stream machinery is correct and the benchmark confirms it costs nothing; it
simply has no throughput win to deliver until copy/compute pipelining exists.

### 3.6 The always-on VM segment path is a net loss

`malloc_segment()` in `cuda_caching_allocator.cpp` tries `try_cu_vm_alloc`
(`cuMemAddressReserve` + `cuMemCreate` + `cuMemMap` + `cuMemSetAccess`) before
falling back to `cudaMalloc`, on every segment, with no way to opt out.
Measured cost of one allocate+free cycle:

| Segment size | `cudaMalloc` + `cudaFree` | `cuMem` map + unmap | Penalty |
|---|---|---|---|
| 2 MiB | 266 µs | 442 µs | **1.66×** |
| 20 MiB | 727 µs | 911 µs | **1.25×** |

(VM minimum granularity on this device is 2 MiB, so the 2 MiB small-segment
class maps exactly one granule.)

The source comment describes this as "expandable", but **nothing is ever
expanded**: each call performs its own `cuMemAddressReserve` sized exactly to
the segment. PyTorch's `expandable_segments` win comes from reserving one large
virtual address range up front and mapping physical pages into it incrementally
— that is what reduces fragmentation. Here the cost is paid on every cache miss
and none of the benefit is realized.

---

## 4. Gaps, ranked by impact

### Blocking real GPU throughput

1. **No pinned host allocator anywhere.** Without it, chunked copy/compute
   overlap is impossible — and that is the only thing that addresses the 97%
   transfer share in §3.3. (Raw-bandwidth benefit is only ~5% on this host;
   the win is overlap.)
2. **No GPU reductions at all** — no `sum`, `dot`, `norm`, `min`/`max`. The GPU
   path is elementwise-only. For a quantitative library this is the largest
   functional hole.
3. **`to_host_vector()` allocates on every call**, costing ~2.3 ms at 4M
   elements — more than ten times the kernel. **Addressed 2026-09-07:** public
   `copy_to_host(ptr)` / `copy_to_host(ptr, count)` reuse the private gather
   path without allocating. `to_host_vector()` remains the allocating convenience.

### Usability and distribution

4. **GPU dispatch requires the *calling* translation unit to be compiled by
   nvcc/hipcc.** `expressions_evaluator.h:127` gates dispatch on
   `defined(__CUDACC__)` / `defined(__HIPCC__)`; a plain `.cpp` assigning to a
   CUDA tensor falls through to `check_cpu_reachable` and throws at runtime.
   The in-tree workaround is to tag `.cpp` files `LANGUAGE CUDA` in CMake
   (`vectorization_tag_gpu_expression_sources()`) — which is precisely what
   produced the Windows `RuntimeLibrary` mismatch fixed in `1b907891`. Any
   downstream consumer needs the same trick.
5. **`run_gpu` / `fill_gpu` never check launch errors.** No `cudaGetLastError()`
   after the launch, so an invalid launch configuration silently yields wrong
   results instead of failing. **Addressed 2026-09-07:** both launchers check
   `cudaGetLastError` / `hipGetLastError` and reject a wrapped 32-bit grid.

### Allocator maturity vs. the PyTorch semantics it targets

6. **No environment-variable configuration** (`PYTORCH_CUDA_ALLOC_CONF`
   analogue): no `max_split_size`, no `garbage_collection_threshold`.
   **Addressed 2026-09-07 (VM path only):** `set_expandable_segments` defaults
   off so cache misses use `cudaMalloc`. Remaining AllocConf knobs are still
   unported.
7. **No CUDA graph capture support** (no private pools for captured graphs) and
   **no `cudaMallocAsync` / mempool backend option**.
8. **`trim_cache_locked` is O(blocks) per eviction** — it rescans both pools in
   full to pick each largest-first victim, under the lock, making a large trim
   quadratic. Latent only because `max_cached_bytes` defaults to unlimited.
9. **`memory_fraction` can be overshot under concurrency.**
   `reserved_would_exceed_locked` is evaluated before `alloc_segment_unlocked`
   drops the lock for the driver call, so concurrent allocators can both pass
   the check and both allocate.

### Verification

10. **No CI job runs GPU device tests for CUDA or HIP.** In
    `cmake-gpu-backend-tests`, Linux CUDA and HIP compile and then `GTEST_SKIP`
    (hosted runners have no GPU); Windows CUDA is build-only (no driver-less
    `nvcuda.dll` stub). Only Metal runs on real hardware. **HIP has never been
    executed anywhere** — it is compile-tested only, and every HIP claim in this
    document rests on source symmetry with CUDA, not observed behavior.
11. **No CUDA/HIP allocator benchmark exists.**
    `BenchmarkPyTorchComparisonGpu.cpp` is Metal-only and
    `benchmark_memory_cpumemoryallocators` is CPU-only. The caching allocator's
    entire justification is performance and it is unmeasured on CUDA/HIP.

### Lower priority

12. **No native CUPTI path in the Profiler.** `run_gpu_kernel_probe` returns
    false on CUDA (real kernel only under `PROFILER_HAS_METAL`); GPU activity
    depends entirely on the vendored Kineto fork.
13. **No multi-GPU collectives** — no NCCL/RCCL. Peer-to-peer `cudaMemcpyPeer`
    in `allocator.h` is the whole story.
14. **HIP `all` architecture list includes `gfx803`**, dropped in ROCm 6
    (`Library/Memory/Cmake/hip.cmake`). **Addressed 2026-09-07:** `gfx803`
    removed from `STRINGS` and from `all`.

---

## 5. Recommended order of work

Ranked by measured payoff per unit of effort. None of it requires kernel work —
§3.1 shows the kernels are already at the roofline.

**Phase 0 (2026-09-07):** VM path default-off, `copy_to_host(ptr)`, launch-error
checks, `gfx803` dropped, `device_guard` on `allocator<T>::copy`, allocator
churn hardening (identity pool erase, skip event poll when idle). Remaining:

1. **Add a pinned host allocator plus chunked `copy_from_host` /
   `copy_to_host` pipelining** (gap 1). This is where the 30× in §3.3 lives.
2. **Get one self-hosted GPU runner into CI** (gap 10), or the CUDA and HIP
   paths remain verified by nothing but a developer workstation.

Beyond that, GPU reductions (gap 2) are the largest *functional* addition and
should be sequenced against actual model requirements rather than treated as
allocator/perf work.
