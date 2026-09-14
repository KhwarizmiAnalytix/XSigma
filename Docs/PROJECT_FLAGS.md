# XSigma CMake Options

This reference describes the public CMake cache variables in the current
source tree. XSigma intentionally keeps most configuration at library scope:
replace `<MODULE>` below with `CORE`, `LOGGING`, `MEMORY`, `PARALLEL`,
`PROFILER`, `VECTORIZATION`, `MODELS`, or `GRAPH` where that module provides
the option.

`Scripts/setup.py` is the preferred interface when configuring the whole
project because it fans supported choices out to the loaded modules. See
[readme/setup.md](readme/setup.md).

## Root options

| Variable | Default | Description |
|---|---:|---|
| `BUILD_SHARED_LIBS` | `ON` | Build shared libraries. The `static` helper token toggles this to `OFF`. |
| `XSIGMA_ENABLE_EXTERNAL` | `ON` | Prefer discoverable external third-party packages when supported. |
| `XSIGMA_LIBRARY_PROJECT` | empty | Build one library module and the dependencies selected by the root CMake file. Valid names: `Logging`, `Memory`, `Vectorization`, `Core`, `Parallel`, `Models`, `Graph`. |

CTest is always enabled by the root configuration. XSigma disables tests and
examples owned by third-party projects, while library test subtrees are
controlled by their own `*_ENABLE_TESTING` option.

## Per-module option families

Most C++ library modules expose these cache variables:

| Variable | Typical default | Values / effect |
|---|---:|---|
| `<MODULE>_CXX_STANDARD` | `20` | `11`, `14`, `17`, `20`, `23`. |
| `<MODULE>_LTO_MODE` | depends on build type | `off`, `thin`, `full`, `ipo`, `auto`. A non-Debug build defaults to `auto` for performance-profiled modules; Debug defaults to `off`. |
| `<MODULE>_LINKER_CHOICE` | `default` | `default`, `lld`, `mold`, `gold`, `lld-link`. |
| `<MODULE>_ENABLE_TESTING` | `ON` | Include that library's CMake test subtree. |
| `<MODULE>_ENABLE_EXAMPLES` | `OFF` | Build examples owned by that library. |
| `<MODULE>_ENABLE_GTEST` | `ON` | Enable GoogleTest support for that library. |
| `<MODULE>_ENABLE_BENCHMARK` | usually `ON` | Enable Google Benchmark targets. `GRAPH` defaults to `OFF`. |
| `<MODULE>_ENABLE_COVERAGE` | `OFF` | Enable coverage instrumentation for that module. |
| `<MODULE>_ENABLE_SANITIZER` | `OFF` | Enable a compiler sanitizer for that module. Requires Clang or GCC. |
| `<MODULE>_SANITIZER_TYPE` | `address` | `address`, `undefined`, `thread`, `memory`, `leak`. |
| `<MODULE>_ENABLE_CACHE` | `ON` | Enable the module's compiler-cache launcher. |
| `<MODULE>_CACHE_BACKEND` | `none` | `none`, `ccache`, `sccache`, `buildcache`. |
| `<MODULE>_ENABLE_CLANGTIDY` | `OFF` | Enable clang-tidy for that module. |
| `<MODULE>_ENABLE_IWYU` | `OFF` | Enable include-what-you-use for that module. |
| `<MODULE>_ENABLE_VALGRIND` | `OFF` | Run that module's tests through Valgrind where supported. |
| `<MODULE>_ENABLE_SPELL` | `OFF` | Enable check-only spell checking. |
| `<MODULE>_ENABLE_ICECC` | `OFF` | Use Icecream distributed compilation. |

Accepted C++ standard values are configuration choices, not a guarantee that
every module supports each language version. Graph currently requires C++17
or newer despite accepting `11` and `14`; see the
[Graph guide](graph/README.md) for its current build constraints.

Coverage and sanitizer options suppress LTO for the affected target. Do not set
the obsolete aggregate names `PROJECT_ENABLE_LTO`, `PROJECT_ENABLE_COVERAGE`,
`PROJECT_ENABLE_SANITIZER`, `PROJECT_SANITIZER_TYPE`, or
`PROJECT_CXX_STANDARD`: the current CMake files do not consume them.

## Primary selectors

| Variable | Default | Supported values |
|---|---|---|
| `LOGGING_BACKEND` | `LOGURU` | `NATIVE`, `LOGURU`, `GLOG`, `SPDLOG`. Consumed by the third-party `ThirdParty/Logging` build. |
| `MEMORY_GPU_BACKEND` | `none` | `none`, `cuda`, `hip`, `metal`. Metal requires Apple platforms. HIP is not supported on Windows in this project. |
| `VECTORIZATION_GPU_BACKEND` | `none` | `none`, `cuda`, `hip`, `metal`. Keep it equal to `MEMORY_GPU_BACKEND` for GPU Vectorization. |
| `VECTORIZATION_CPU_BACKEND` | host-dependent | `no`, `sse`, `avx`, `avx2`, `avx512`, `neon`, `sve`. Defaults to AVX2 on recognised x86, NEON on AArch64, otherwise `no`. |
| `VECTORIZATION_PACKET_SIZE` | `4` | Positive SIMD lane count selected by the expression layer. |
| `PARALLEL_BACKEND` | `std` | `std`, `openmp`, `tbb`; the modes are exclusive. Consumed by the third-party `ThirdParty/Parallel` build. |

> Logging, Parallel, and Profiler are pure third-party dependencies
> (`ThirdParty/Logging`, `ThirdParty/Parallel`, `ThirdParty/Profiler`
> submodules). XSigma per-module fan-out flags do not reach them: the only
> selectors that cross the boundary are `LOGGING_BACKEND`, `PARALLEL_BACKEND`,
> and the global `BUILD_SHARED_LIBS` / `BUILD_TESTING` /
> `XSIGMA_ENABLE_EXTERNAL`. Flags such as `LOGGING_ENABLE_SANITIZER`,
> `PARALLEL_ENABLE_TBB`, or `LOGGING_ENABLE_BENCHMARK` are no longer consumed
> by the XSigma build (TBB selection is `PARALLEL_BACKEND=tbb`, which also
> turns on `PARALLEL_ENABLE_TBB` inside the Parallel subproject).

## Optional feature selectors

| Variable | Default | Description |
|---|---:|---|
| `CORE_ENABLE_MAGICENUM` | `ON` | Enable `magic_enum` in Core. |
| `MEMORY_ENABLE_MIMALLOC` | `ON` | Use mimalloc for the Memory CPU allocator. |
| `MEMORY_ENABLE_MIMALLOC_STATS` | `OFF` | Build mimalloc statistics support. |
| `MEMORY_ENABLE_TBB` | `OFF` | Use the TBB memory allocator. This is separate from the Parallel TBB backend. |
| `MEMORY_ENABLE_NUMA` | `OFF` | Enable NUMA support where available. |
| `MEMORY_ENABLE_MEMKIND` | `OFF` | Enable memkind; the CMake implementation limits it to Linux. |
| `PARALLEL_ENABLE_OPENMP` | `OFF` | Enable OpenMP in the third-party Parallel build. Prefer `PARALLEL_BACKEND=openmp` to select the complete backend. |
| `CORE_ENABLE_MKL` | `OFF` | Enable Core MKL integration. |
| `VECTORIZATION_ENABLE_MKL` | `OFF` | Enable Vectorization MKL VML support. |
| `VECTORIZATION_ENABLE_SLEEF` | `OFF` | Enable SLEEF SIMD math. |
| `VECTORIZATION_ENABLE_SVML` | `OFF` | Enable Intel SVML support when appropriate for the compiler and architecture. |
| `VECTORIZATION_ENABLE_ACCELERATE` | `OFF` | Enable Apple Accelerate vForce on AArch64 NEON. |
| `CORE_ENABLE_ENZYME` | `OFF` | Enable Enzyme automatic differentiation support. |

## Direct-CMake examples

```bash
# A complete Release configuration using explicit selectors.
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLOGGING_BACKEND=SPDLOG \
  -DVECTORIZATION_CPU_BACKEND=avx2 \
  -DMEMORY_GPU_BACKEND=none \
  -DVECTORIZATION_GPU_BACKEND=none

# Vectorization-only CUDA configuration.
cmake -S . -B build-cuda -G Ninja \
  -DXSIGMA_LIBRARY_PROJECT=Vectorization \
  -DMEMORY_GPU_BACKEND=cuda \
  -DVECTORIZATION_GPU_BACKEND=cuda

# AddressSanitizer for all loaded modules (Logging/Parallel are third-party
# and build with their own defaults — sanitizers do not fan into them).
cmake -S . -B build-asan -G Ninja \
  -DCORE_ENABLE_SANITIZER=ON -DCORE_SANITIZER_TYPE=address \
  -DMEMORY_ENABLE_SANITIZER=ON -DMEMORY_SANITIZER_TYPE=address \
  -DVECTORIZATION_ENABLE_SANITIZER=ON -DVECTORIZATION_SANITIZER_TYPE=address \
  -DMODELS_ENABLE_SANITIZER=ON -DMODELS_SANITIZER_TYPE=address \
  -DGRAPH_ENABLE_SANITIZER=ON -DGRAPH_SANITIZER_TYPE=address
```

For whole-project fan-out and correct single-library scoping, prefer:

```bash
python Scripts/setup.py config.build.test.ninja.clang.debug --sanitizer.address
```
