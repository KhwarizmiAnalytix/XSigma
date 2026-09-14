# Build Examples

These examples use the current CMake helper and option names. Run them from the
repository root. `Scripts/setup.py --help` remains the executable reference for
available helper tokens.

## Daily development

```bash
# Debug configuration, build, and run the test suite.
python Scripts/setup.py config.build.test.ninja.clang.debug

# Debug configuration for one module and its CMake dependencies.
python Scripts/setup.py config.build.test.ninja.clang.debug --project.core
```

Library tests and GoogleTest support are enabled by default. The `test` action
runs the CTest suite after building.

## Release CPU build

```bash
# Portable, explicit AVX2 binary.
python Scripts/setup.py config.build.test.ninja.clang.release.cxx20.avx2

# Request uniform automatic LTO and build benchmark targets.
python Scripts/setup.py config.build.ninja.clang.release.avx2.lto.benchmark

# Tune generated code for the local CPU only.
python Scripts/setup.py config.build.ninja.clang.release.native
```

On CMake Release and RelWithDebInfo configurations, modules use
`*_LTO_MODE=auto` by default. `lto` makes that request explicit; Debug,
sanitizer, and coverage configurations do not apply LTO.

## Diagnostics

```bash
# AddressSanitizer (Clang or GCC).
python Scripts/setup.py config.build.test.ninja.clang.debug --sanitizer.address

# UndefinedBehaviorSanitizer.
python Scripts/setup.py config.build.test.ninja.clang.debug --sanitizer.undefined

# Coverage instrumentation and coverage workflow.
python Scripts/setup.py config.build.test.ninja.clang.debug.coverage

# Static-analysis integrations.
python Scripts/setup.py config.build.ninja.clang.debug.clangtidy.iwyu.cppcheck
```

The helper fans sanitizer, coverage, clang-tidy, and IWYU choices out to the
loaded CMake modules. `cppcheck` is a post-build helper action, not a CMake
cache variable.

## Parallelism and allocation

```bash
# Select the OpenMP execution backend.
python Scripts/setup.py config.build.test.ninja.clang.release --parallel.openmp

# Select the TBB execution backend and enable the Memory TBB allocator.
python Scripts/setup.py config.build.test.ninja.clang.release --parallel.tbb

# Use a compiler cache backend.
python Scripts/setup.py config.build.ninja.clang.release.ccache
```

`parallel.std`, `parallel.openmp`, and `parallel.tbb` are exclusive choices.
The `cache` token disables compiler-cache launchers because they are enabled by
default; use `none`, `ccache`, `sccache`, or `buildcache` to choose a backend.

## Logging

```bash
python Scripts/setup.py config.build.test.ninja.clang.release
```

## GPU Vectorization

```bash
# CUDA backend for Memory and Vectorization.
python Scripts/setup.py config.build.test.ninja.clang.release.cuda --project.vectorization

# HIP backend. Use Linux or another supported Unix environment.
python Scripts/setup.py config.build.test.ninja.clang.release.hip --project.vectorization

# Metal backend on Apple platforms.
python Scripts/setup.py config.build.test.ninja.clang.release.metal --project.vectorization
```

The helper forwards a matching GPU backend to Memory and Vectorization. CUDA,
HIP, and Metal are compile-time exclusive. HIP is not supported on Windows, and
Metal requires an Apple platform.

## Direct CMake

```bash
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DVECTORIZATION_CPU_BACKEND=avx2 \
  -DMEMORY_GPU_BACKEND=none \
  -DVECTORIZATION_GPU_BACKEND=none
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

For direct instrumentation, use module-scoped variables such as
`CORE_ENABLE_SANITIZER`, `CORE_SANITIZER_TYPE`, or
`VECTORIZATION_ENABLE_COVERAGE`. Do not use removed `PROJECT_ENABLE_*`,
`ENABLE_GTEST`, `ENABLE_BENCHMARK`, or `XSIGMA_GOOGLE_TEST` variables.

## Bazel

```bash
python Scripts/setup_bazel.py build.test
python Scripts/setup_bazel.py build.test.release.avx2
python Scripts/setup_bazel.py build.test.debug.asan
bazel test --config=release //Library/Core/Testing/Cxx:CoreCxxTests
```

See [the Bazel guide](../BAZEL_USER_GUIDE.md) for Bazel-specific configuration
names and feature limitations.

## Related documentation

- [CMake setup](setup.md)
- [Build configuration](build/build-configuration.md)
- [Project option reference](../PROJECT_FLAGS.md)
- [Profiler](../profiler/profiler.md)
