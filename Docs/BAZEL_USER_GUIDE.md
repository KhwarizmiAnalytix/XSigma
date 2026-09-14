# XSigma Bazel Guide

This guide covers the current Bazel build. The repository pins Bazel `8.4.2`
in `.bazelversion`; use Bazelisk to select it automatically. CMake remains the
reference build path for the complete feature set, particularly CUDA/HIP
device-language compilation and tests.

## Prerequisites

- Bazelisk or Bazel `8.4.2`.
- An available C++ toolchain. `Scripts/setup_bazel.py` defaults to Clang and
  accepts GCC, MSVC, Xcode, and Visual Studio selection tokens where supported.
- Initialised submodules: `git submodule update --init --recursive`.

The Bazel workspace currently uses both `MODULE.bazel` and `WORKSPACE.bazel`.
`.bazelrc` enables the workspace compatibility path required by its vendored
third-party configuration.

## Quick start

Run commands from the repository root:

```bash
# Show the resolved configuration only.
python Scripts/setup_bazel.py config.release

# Build and run the default Debug test configuration.
python Scripts/setup_bazel.py build.test

# Release test build with explicit AVX2 and C++20.
python Scripts/setup_bazel.py build.test.release.avx2.cxx20

# Run a single current test target directly.
bazel test --config=release //Library/Core/Testing/Cxx:CoreCxxTests
```

`Scripts/setup_bazel.py --help` is the current command reference. Its dotted
tokens resemble `setup.py`, but the two systems do not have feature parity.

## Defaults

The helper adds these configurations unless a different one is selected:

| Area | Default |
|---|---|
| Build type | `debug` when no build-type token is supplied |
| C++ standard | C++20 through platform and library settings |
| Parallel backend | `std` |
| mimalloc | Enabled through root `.bazelrc` and `memory.bzl` |
| GoogleTest and benchmark defines | Enabled by the helper's `gtest` and `benchmark` configs |

The `gtest` helper token is an inverse toggle: it emits
`--define=enable_gtest=false`. Do not add it to a normal test build.

## Supported helper selections

| Area | Examples | Bazel mapping |
|---|---|---|
| Build type | `debug`, `release`, `relwithdebinfo` | Matching `--config` |
| Compiler | `clang`, `gcc`, `msvc` | Matching `--config` |
| Build tool | `xcode`, `vs17`, `vs19`, `vs22`, `vs26` | Xcode configuration or platform/toolchain selection where available |
| C++ standard | `cxx17`, `cxx20`, `cxx23` | C++ standard options and `.bazelrc` configs |
| SIMD | `sse`, `avx`, `avx2`, `avx512`, `neon`, `sve` | `vectorization_type` define |
| LTO | `lto`, `--lto.thin`, `--lto.full`, `--lto.ipo` | `--config=lto` (ThinLTO flags) |
| Sanitizer | `asan`, `tsan`, `ubsan`, `msan`, `lsan`; `--sanitizer.address` etc. | Matching sanitizer `--config` |
| Parallel | `--parallel.std`, `.openmp`, `.tbb` | `parallel_backend` define; OpenMP/TBB config as needed |
| Memory and optional features | `mimalloc`, `numa`, `memkind`, `enzyme`, `sleef` | Matching `.bazelrc` config or define |
| Library scope | `--project.core`, `.memory`, `.vectorization`, etc. | Limits top-level target patterns to `//Library/<Name>/...` |

Examples:

```bash
python Scripts/setup_bazel.py build.test.debug.asan
python Scripts/setup_bazel.py build.test.release.avx2
python Scripts/setup_bazel.py build.test.release --parallel.tbb
python Scripts/setup_bazel.py build.test.release --project.vectorization
```

Only one parallel backend should be selected.

## Raw Bazel commands

The helper is optional. Use the named configurations defined in `.bazelrc`:

```bash
# Whole project, optimized C++20 with AVX2.
bazel build --config=clang --config=release --config=cxx20 --config=avx2 //...

# Run one test with visible output.
bazel test --config=release --test_output=all \
  //Library/Vectorization/Testing/Cxx:VectorizationCxxTests

# Sanitizer configurations.
bazel test --config=debug --config=asan //...
```

Current named configurations include `debug`, `release`, `relwithdebinfo`,
`cxx17`, `cxx20`, `cxx23`, `sse`, `avx`, `avx2`, `avx512`, `neon`, `sve`,
`lto`, `asan`, `tsan`, `ubsan`, `msan`, `lsan`, `openmp`, `tbb`, `numa`,
`memkind`, `mimalloc`, `gtest`, and `benchmark`.

## GPU status

The `cuda`, `hip`, and `metal` helper tokens select matching Memory and
Vectorization feature defines. The helper does not add the CUDA crosstool
configuration required for Bazel device-language compilation; use raw
`--config=cuda` only after the local CUDA toolchain is configured. CUDA/HIP
device-language coverage in the Bazel graph remains incomplete.

Use the CMake build for supported CUDA/HIP/Metal development and tests:

```bash
python Scripts/setup.py config.build.test.ninja.clang.release.cuda --project.vectorization
```

Metal is Apple-only. HIP is not supported on Windows by the CMake project.

## Known CMake differences

- CMake supports per-module cache, linker, clang-tidy, IWYU, Valgrind, spell,
  coverage, and sanitizer settings. Bazel does not model all of those options
  at library scope.
- CMake's `external` third-party dependency selection has no Bazel equivalent.
- CMake exposes `*_LTO_MODE` and can choose IPO; Bazel maps non-off LTO helper
  modes to its ThinLTO configuration.
- Use CMake's module-scoped options when a setting is absent from `.bazelrc`.

## Useful targets

```bash
bazel test //Library/Core/Testing/Cxx:CoreCxxTests
bazel test //Library/Vectorization/Testing/Cxx:VectorizationCxxTests
bazel test //Library/Graph/Testing/Cxx:GraphCxxTests
bazel query 'kind(cc_test, //Library/...)'
```

Target availability can depend on the selected backend and platform. Query the
checked-out graph rather than relying on historical target names such as
`core_tests`.

## See also

- [Compact Bazel reference](readme/bazel.md)
- [CMake setup guide](readme/setup.md)
- [CMake option reference](PROJECT_FLAGS.md)
- [Profiler guide](profiler/profiler.md)
- [Graph guide](graph/README.md)
