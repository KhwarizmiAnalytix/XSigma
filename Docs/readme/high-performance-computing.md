# High-Performance Computing

XSigma's performance model combines a compile-time CPU SIMD choice, an optional
compile-time GPU backend, and an exclusive parallel-execution backend. Measure
the target workload before selecting an aggressive configuration.

## CPU SIMD

Vectorization compiles one CPU ISA per binary through
`VECTORIZATION_CPU_BACKEND`:

| Backend | Use case |
|---|---|
| `no` | Maximum portability or scalar debugging. |
| `sse` | Older x86 targets. |
| `avx`, `avx2`, `avx512` | Compatible x86 targets only. |
| `neon`, `sve` | Compatible AArch64 targets only. |

The default is host-dependent: AVX2 on recognised x86, NEON on AArch64, and
`no` otherwise. There is no runtime ISA dispatcher; an incompatible binary can
fail with an illegal instruction.

```bash
python Scripts/setup.py config.build.test.ninja.clang.release.avx2
python Scripts/setup.py config.build.test.ninja.clang.release.neon
python Scripts/setup.py config.build.test.ninja.clang.release.avx512
```

## GPU execution

Memory and Vectorization choose one of `none`, `cuda`, `hip`, or `metal` at
configure time. Keep the two selectors equal when using GPU Vectorization:

```bash
python Scripts/setup.py config.build.test.ninja.clang.release.cuda --project.vectorization

cmake -S . -B build-metal -G Ninja \
  -DMEMORY_GPU_BACKEND=metal \
  -DVECTORIZATION_GPU_BACKEND=metal
```

CUDA, HIP, and Metal are mutually exclusive in one binary. Metal requires
Apple platforms. HIP is unsupported on Windows in this project. The GPU
evaluator contract and remaining backend differences are documented in
[vectorization_backends.md](../vectorization_backends.md).

## Parallel execution

`PARALLEL_BACKEND` has three exclusive values: `std`, `openmp`, and `tbb`.
Select them through the helper:

```bash
python Scripts/setup.py config.build.test.ninja.clang.release --parallel.std
python Scripts/setup.py config.build.test.ninja.clang.release --parallel.openmp
python Scripts/setup.py config.build.test.ninja.clang.release --parallel.tbb
```

The TBB parallel backend also enables the separate Memory TBB allocator when
configured through `setup.py`. `MEMORY_ENABLE_TBB` by itself only concerns the
Memory allocator.

## Release configuration

```bash
# Explicit CPU tier and Release defaults.
python Scripts/setup.py config.build.test.ninja.clang.release.avx2

# Explicit automatic LTO plus benchmarks.
python Scripts/setup.py config.build.ninja.clang.release.avx2.lto.benchmark

# Compiler cache for iterative builds.
python Scripts/setup.py config.build.ninja.clang.release.avx2.ccache
```

Release and RelWithDebInfo CMake configurations choose per-module
`*_LTO_MODE=auto`; Debug defaults to `off`. Coverage and sanitizer builds skip
LTO. Do not use a removed project-wide `PROJECT_ENABLE_LTO` variable.

## Profiling

XSigma links `Profiler::Profiler` and uses `profiler::session` /
`PROFILER_SCOPE`. Work on Profiler itself in the standalone Profiler repository.

```bash
python Scripts/setup.py config.build.test.ninja.clang.release --project.memory
```

## Practical guidance

- Build with the lowest SIMD tier required by every deployment target.
- Use `native` only for binaries that stay on the build machine or homogeneous
  fleet.
- Treat GPU, CPU SIMD, allocator, and parallel choices as workload-specific;
  benchmark the target use case instead of relying on generic speedup claims.
- Keep sanitizer and coverage builds separate from performance measurements.
