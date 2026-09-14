# XSigma

[![CI Status](https://github.com/KhwarizmiAnalytix/XSigma/actions/workflows/ci.yml/badge.svg)](https://github.com/KhwarizmiAnalytix/XSigma/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/KhwarizmiAnalytix/XSigma/branch/main/graph/badge.svg)](https://codecov.io/gh/KhwarizmiAnalytix/XSigma)
[![License: GPL-3.0 or Commercial](https://img.shields.io/badge/License-GPL--3.0%20or%20Commercial-blue.svg)](LICENSE)

XSigma is a C++ quantitative-computing library. It provides CPU SIMD
vectorization, optional CUDA/HIP/Metal execution, memory allocation utilities,
parallel execution, logging, and profiling. The project supports CMake and
Bazel; CMake is the reference path for the full feature set.

## Build at a glance

Clone with submodules:

```bash
git clone https://github.com/KhwarizmiAnalytix/XSigma.git
cd XSigma
git submodule update --init --recursive
```

Requirements:

- CMake 3.16 or newer for the CMake build.
- A compiler that supports the chosen C++ standard. Library modules default to
  C++20. Accepted configuration values do not guarantee source compatibility:
  Graph requires at least C++17 despite accepting older CMake values.
- Python 3.9 or newer for `Scripts/setup.py` and `Scripts/setup_bazel.py`.
- Bazelisk for the Bazel build. It reads the pinned version, currently `8.4.2`,
  from `.bazelversion`.

### CMake

`Scripts/setup.py` is the recommended CMake entry point. It applies consistent
module-scoped options and produces a configuration summary.

```bash
# Configure, build, and run the default Debug test suite.
python Scripts/setup.py config.build.test.ninja.clang.debug

# Optimized C++20 build with AVX2.
python Scripts/setup.py config.build.test.ninja.clang.release.cxx20.avx2

# AddressSanitizer build.
python Scripts/setup.py config.build.test.ninja.clang.debug --sanitizer.address

# Build a single library and its required CMake dependencies.
python Scripts/setup.py config.build.test.ninja.clang.release --project.vectorization
```

The helper accepts dotted tokens and long options. Run
`python Scripts/setup.py --help` for the generated, current command reference.
The complete guide is [Docs/readme/setup.md](Docs/readme/setup.md).

For direct CMake use:

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

Library options are intentionally module-scoped. For example, use
`-DLOGGING_BACKEND=GLOG`, `-DMEMORY_GPU_BACKEND=cuda`, or
`-DVECTORIZATION_CPU_BACKEND=avx2`; do not rely on removed global
`PROJECT_ENABLE_*` switches. See [Docs/PROJECT_FLAGS.md](Docs/PROJECT_FLAGS.md)
for the authoritative option reference.

### Bazel

Use Bazelisk so the repository-selected version is used:

```bash
# Build and test the default Debug configuration.
python Scripts/setup_bazel.py build.test

# Release build with AVX2.
python Scripts/setup_bazel.py build.test.release.avx2

# Run a single test target directly.
bazel test --config=release //Library/Core/Testing/Cxx:CoreCxxTests
```

Bazel defaults to the LOGURU logging backend and the Kineto instrumentation
backend. The native TraceMe/XPlane profiler pipeline is compiled independently
of that choice. GPU configuration flags exist in Bazel, but CMake remains the
recommended path for CUDA/HIP device-language development and tests.

See [Docs/BAZEL_USER_GUIDE.md](Docs/BAZEL_USER_GUIDE.md) for supported
configurations and known limitations.

## Build behavior

- CMake library tests and GoogleTest are enabled per module by default.
  `setup.py` runs tests when its `test` action is present.
- Google Benchmark is enabled by most modules' CMake defaults; Graph defaults
  to off. `setup.py` disables it unless the `benchmark` token is present.
- A Release CMake configuration selects per-module `*_LTO_MODE=auto`; Debug,
  coverage, and sanitizer configurations do not apply LTO. The `lto` token
  explicitly requests `auto` mode.
- The default CMake logging backend is `LOGURU`. Profiler instrumentation
  (Kineto/ITT) is configured inside `ThirdParty/Profiler` — XSigma does not
  expose `PROFILER_BACKEND` or `--profiler.*` setup flags.
- CPU SIMD defaults are host-dependent: AVX2 on recognised x86 hosts, NEON on
  AArch64, and `no` elsewhere. Choose a tier explicitly for portable binaries.
- CUDA, HIP, and Metal are compile-time-exclusive GPU backends. When enabling
  one for Vectorization, configure matching `MEMORY_GPU_BACKEND` and
  `VECTORIZATION_GPU_BACKEND` values.

## Libraries

| Library | Purpose |
|---|---|
| `Library/Core` | Core utilities, algorithms, and optional MKL/Enzyme integrations. |
| `Library/Memory` | CPU allocators plus CUDA/HIP/Metal caching allocators. |
| `Library/Vectorization` | CPU SIMD expressions and CUDA/HIP/Metal evaluators. |
| `Library/Models` | SABR/ZABR smile routines, calibration, and MLP inference. |
| `Library/Graph` | Dependency DAG construction, parallel execution, target pruning, and caller-managed incremental caching. |
| `ThirdParty/Logging` | [KhwarizmiAnalytix/Logging](https://github.com/KhwarizmiAnalytix/Logging) third-party submodule. CMake `Logging::Logging`, Bazel `@logging//:Logging`. |
| `ThirdParty/Parallel` | [KhwarizmiAnalytix/Parallel](https://github.com/KhwarizmiAnalytix/Parallel) third-party submodule. CMake `Parallel::Parallel`, Bazel `@parallel//:Parallel`. |
| `ThirdParty/Profiler` | [KhwarizmiAnalytix/Profiler](https://github.com/KhwarizmiAnalytix/Profiler) third-party submodule. CMake `Profiler::Profiler`, Bazel `@profiler//:Profiler`. |

## Documentation

- [Documentation index](Docs/README.md)
- [CMake setup and helper reference](Docs/readme/setup.md)
- [Build configurations](Docs/readme/build/build-configuration.md)
- [Practical build examples](Docs/readme/usage-examples.md)
- [Bazel guide](Docs/BAZEL_USER_GUIDE.md)
- [CMake option reference](Docs/PROJECT_FLAGS.md)
- [Graph guide and portfolio pricing direction](Docs/graph/README.md)
- [Memory design](Docs/memory_design.md)
- [Vectorization backends](Docs/vectorization_backends.md)
- [Profiler guide](Docs/profiler/profiler.md)

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the repository's CMake and
Bazel conventions when adding code or dependencies. Changes to user-visible
build options should update the corresponding guide above in the same change.

## License

XSigma is available under GPL-3.0 or a commercial license. See [LICENSE](LICENSE).
