# Build Configuration

This guide describes the current CMake configuration model. XSigma does not
have a project-wide C++ standard, LTO, sanitizer, coverage, or test framework
switch. Those choices belong to the library modules and are named with a
module prefix, such as `CORE_LTO_MODE` or `MEMORY_ENABLE_SANITIZER`.

For whole-project builds, use [the setup helper](../setup.md). It fans a single
intent across the loaded modules and avoids stale cache-variable combinations.

## Build types

| CMake build type | Intended use | LTO default |
|---|---|---|
| `Debug` | Debugging and development | `off` |
| `Release` | Optimized builds | `auto` for performance-profiled modules |
| `RelWithDebInfo` | Optimized builds with debug information | `auto` for performance-profiled modules |

```bash
cmake -S . -B build-debug -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake -S . -B build-release -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake -S . -B build-relwithdebinfo -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build-release --parallel
```

With Visual Studio or another multi-config generator, select the configuration
at build time:

```powershell
cmake -S . -B build-vs -G "Visual Studio 17 2022"
cmake --build build-vs --config Release --parallel
ctest --test-dir build-vs -C Release --output-on-failure
```

## C++ standard

Library CMake options default to C++20 and accept `11`, `14`, `17`, `20`, or
`23` in `<MODULE>_CXX_STANDARD`. Source compatibility is module-dependent:
Graph requires at least C++17 despite accepting older values. See the
[Graph guide](../../graph/README.md). The helper applies `cxx17`, `cxx20`, or
`cxx23` to every loaded module.

```bash
python Scripts/setup.py config.build.test.ninja.clang.release.cxx20

# Direct CMake for a single library.
cmake -S . -B build-core -G Ninja \
  -DXSIGMA_LIBRARY_PROJECT=Core \
  -DCORE_CXX_STANDARD=23
```

## LTO and linkers

LTO is controlled by `<MODULE>_LTO_MODE`, not `PROJECT_ENABLE_LTO`. Supported
modes are `off`, `thin`, `full`, `ipo`, and `auto`.

- `auto` picks ThinLTO for a Clang GNU-style driver and IPO for GCC or the
  MSVC link model.
- CMake selects `auto` for a non-Debug performance build and `off` for Debug.
- Coverage and sanitizer configurations prevent LTO from being applied to the
  affected target.
- `<MODULE>_LINKER_CHOICE` accepts `default`, `lld`, `mold`, `gold`, and
  `lld-link`.

```bash
python Scripts/setup.py config.build.ninja.clang.release.lto
python Scripts/setup.py config.build.ninja.clang.release --lto.thin

cmake -S . -B build-vectorization -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DXSIGMA_LIBRARY_PROJECT=Vectorization \
  -DVECTORIZATION_LTO_MODE=thin \
  -DVECTORIZATION_LINKER_CHOICE=lld
```

## Testing, benchmarks, and instrumentation

Library test subtrees and GoogleTest support are on by default. Configure only
the modules that need a different policy:

```bash
cmake -S . -B build-minimal -G Ninja \
  -DCORE_ENABLE_TESTING=OFF \
  -DLOGGING_ENABLE_TESTING=OFF \
  -DMEMORY_ENABLE_TESTING=OFF \
  -DPARALLEL_ENABLE_TESTING=OFF \
  -DVECTORIZATION_ENABLE_TESTING=OFF
```

`ThirdParty/Profiler` is consumed as a pure third-party dependency: its
tests, examples, and benchmarks are always disabled from XSigma (they build
only from the standalone Profiler repo), and XSigma feature flags
(coverage, sanitizers, clang-tidy, IWYU, spell, C++ standard) do not fan
into it.

For sanitizers and coverage, the helper is clearer because it applies the
matching per-module pair:

```bash
python Scripts/setup.py config.build.test.ninja.clang.debug --sanitizer.address
python Scripts/setup.py config.build.test.ninja.clang.debug.coverage
python Scripts/setup.py config.build.ninja.clang.release.benchmark
```

Direct CMake uses the module prefix:

```bash
cmake -S . -B build-memory-asan -G Ninja \
  -DXSIGMA_LIBRARY_PROJECT=Memory \
  -DMEMORY_ENABLE_SANITIZER=ON \
  -DMEMORY_SANITIZER_TYPE=address
```

Sanitizers require Clang or GCC. Google Benchmark defaults to `ON` in most
modules, but `setup.py` only enables it when the `benchmark` token is present.

## Hardware and runtime backends

```bash
# Explicit CPU SIMD tier.
cmake -S . -B build-avx2 -G Ninja -DVECTORIZATION_CPU_BACKEND=avx2

# CUDA or HIP requires matching Memory and Vectorization backend values.
cmake -S . -B build-cuda -G Ninja \
  -DMEMORY_GPU_BACKEND=cuda \
  -DVECTORIZATION_GPU_BACKEND=cuda

# Select the complete parallel execution backend.
cmake -S . -B build-tbb -G Ninja -DPARALLEL_BACKEND=tbb
cmake -S . -B build-openmp -G Ninja -DPARALLEL_BACKEND=openmp
```

`VECTORIZATION_CPU_BACKEND` defaults according to the host architecture. CUDA,
HIP, and Metal are exclusive GPU selections; Metal requires Apple platforms and
HIP is not supported on Windows in this project.

## Related documentation

- [Setup helper reference](../setup.md)
- [Project CMake options](../../PROJECT_FLAGS.md)
- [Usage examples](../usage-examples.md)
- [Cross-platform building](../cross-platform-building.md)
