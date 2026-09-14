# CMake Setup Guide

`Scripts/setup.py` is XSigma's CMake configuration helper. It accepts dotted
arguments such as `config.build.test.release.avx2` and selected long options.
It translates those choices into the module-scoped CMake cache variables used
by the current `Library/*/CMakeLists.txt` files.

Run `python Scripts/setup.py --help` to inspect the command surface supplied by
the checked-out version of the helper.

## Quick start

Run commands from the repository root:

```bash
# Configure, build, and run tests in a Debug configuration.
python Scripts/setup.py config.build.test.ninja.clang.debug

# Configure a Release build and run the test suite.
python Scripts/setup.py config.build.test.ninja.clang.release

# Build one library and its CMake dependencies.
python Scripts/setup.py config.build.test.ninja.clang.release --project.memory

# Print the resolved configuration without building.
python Scripts/setup.py config.release.avx2
```

`config`, `build`, and `test` are actions. `test` runs the configured CTest
suite after the build. The library test and GoogleTest options are enabled by
default; the action controls whether tests are executed by this invocation.

## Common selections

| Intent | Helper form | CMake effect |
|---|---|---|
| Build type | `debug`, `release`, `relwithdebinfo` | `CMAKE_BUILD_TYPE` |
| C++ standard | `cxx17`, `cxx20`, `cxx23` | Fans `*_CXX_STANDARD` to loaded modules |
| CPU SIMD | `no`, `sse`, `avx`, `avx2`, `avx512`, `neon`, `sve` | `VECTORIZATION_CPU_BACKEND` |
| GPU backend | `cuda`, `hip`, `metal`, or `--gpu_backend.<name>` | Matching `MEMORY_GPU_BACKEND` and `VECTORIZATION_GPU_BACKEND` |
| Logging | `--logging=SPDLOG|LOGURU|GLOG|NATIVE` | `LOGGING_BACKEND` |
| Parallel backend | `--parallel.std`, `--parallel.openmp`, `--parallel.tbb` | `PARALLEL_BACKEND`; TBB also enables the Memory TBB allocator |
| LTO | `lto`, `--lto.auto`, `--lto.thin`, `--lto.full`, `--lto.ipo`, `--lto.off` | Fans `*_LTO_MODE` to loaded modules |
| Sanitizer | `--sanitizer.address`, `.undefined`, `.thread`, `.memory`, `.leak` | Fans `*_ENABLE_SANITIZER` and `*_SANITIZER_TYPE` |
| Coverage | `coverage` | Fans `*_ENABLE_COVERAGE=ON` |
| Benchmark targets | `benchmark` | Fans `*_ENABLE_BENCHMARK=ON` |
| Compiler cache | `none`, `ccache`, `sccache`, `buildcache` | Fans `*_CACHE_BACKEND` |
| Host CPU tuning | `native` | `USE_NATIVE_ARCH=ON` for Vectorization on Clang/GCC |

`gtest`, `magic_enum`, `mimalloc`, and `cache` are inverse toggles because
their corresponding CMake defaults are `ON`: adding one disables the feature.
In particular, do not add `gtest` to a normal test build. `benchmark` is not an
inverse toggle: most modules default it to `ON` in CMake, while Graph defaults
to `OFF`. `setup.py` sets it `OFF` unless the `benchmark` token is supplied.

For `--project.graph`, CMake configures Graph plus the third-party Parallel
submodule (via `xsigma_add_parallel()`). See the
[Graph guide](../graph/README.md) for execution APIs, build targets and current
limitations.

## Examples

### Development and tests

```bash
python Scripts/setup.py config.build.test.ninja.clang.debug
python Scripts/setup.py config.build.test.ninja.clang.debug --sanitizer.address
python Scripts/setup.py config.build.test.ninja.clang.debug --parallel.tbb
```

Sanitizers require Clang or GCC. A sanitizer or coverage build suppresses LTO
for the affected targets.

### Release and performance

```bash
# Release uses each module's automatic LTO policy unless overridden.
python Scripts/setup.py config.build.test.ninja.clang.release.avx2

# Request a uniform auto LTO mode explicitly and enable benchmarks.
python Scripts/setup.py config.build.test.ninja.clang.release.avx2.lto.benchmark

# Tune for this build machine only; the binary may not run on older CPUs.
python Scripts/setup.py config.build.ninja.clang.release.native
```

For CMake, an explicit non-Debug build makes the per-module LTO default `auto`.
`auto` resolves to ThinLTO for a Clang GNU-style driver and IPO for GCC or the
MSVC link model. Debug builds default to `off`.

### GPU backends

```bash
# CUDA evaluator and matching Memory backend.
python Scripts/setup.py config.build.test.ninja.clang.release.cuda --project.vectorization

# Metal is supported only on Apple platforms.
python Scripts/setup.py config.build.test.ninja.clang.release.metal --project.vectorization

# HIP is unsupported on Windows in this project.
python Scripts/setup.py config.build.test.ninja.clang.release.hip --project.vectorization
```

CUDA, HIP, and Metal are mutually exclusive in one binary. The helper keeps the
Memory and Vectorization selectors aligned; use the same values when invoking
CMake directly.

### Backends and analysis

```bash
python Scripts/setup.py config.build.test.ninja.clang.release --logging=GLOG
python Scripts/setup.py config.build.test.ninja.clang.debug.coverage
python Scripts/setup.py config.build.ninja.clang.release.ccache
```

Profiler instrumentation (Kineto/ITT) is configured inside
`ThirdParty/Profiler`, not via XSigma setup flags.

## Direct CMake

The helper is not required. Use the real cache variables from the owning
module, for example:

```bash
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLOGGING_BACKEND=LOGURU \
  -DVECTORIZATION_CPU_BACKEND=avx2 \
  -DMEMORY_GPU_BACKEND=none \
  -DVECTORIZATION_GPU_BACKEND=none
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

For a single module, use `-DXSIGMA_LIBRARY_PROJECT=Memory` (or `Core`,
`Vectorization`, `Models`, or `Graph`). `Logging`, `Parallel`, and `Profiler`
are pure third-party submodules (`ThirdParty/`) and have no
`XSIGMA_LIBRARY_PROJECT` scope — they are configured on demand by the modules
that consume them.

The option families are deliberately module-scoped:

```bash
# AddressSanitizer for a Core-only configuration.
cmake -S . -B build-core -G Ninja \
  -DXSIGMA_LIBRARY_PROJECT=Core \
  -DCORE_ENABLE_SANITIZER=ON \
  -DCORE_SANITIZER_TYPE=address

# Explicit LTO policy for a Vectorization-only Release configuration.
cmake -S . -B build-vectorization -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DXSIGMA_LIBRARY_PROJECT=Vectorization \
  -DVECTORIZATION_LTO_MODE=thin
```

There are no project-wide `PROJECT_ENABLE_LTO`, `PROJECT_ENABLE_SANITIZER`,
`PROJECT_CXX_STANDARD`, `ENABLE_GTEST`, or `ENABLE_BENCHMARK` settings in the
current configuration. See [PROJECT_FLAGS.md](../PROJECT_FLAGS.md) for the
complete supported cache-variable families.

## Troubleshooting

- Initialise submodules before configuring: `git submodule update --init --recursive`.
- Use a fresh, differently named build directory when changing a generator,
  compiler, or GPU backend.
- Run `python Scripts/setup.py --help` after updating the repository; it is the
  authoritative list of helper tokens.
- Use `cmake --build <dir> --parallel` instead of shell-specific `-j` forms for
  portable commands.
