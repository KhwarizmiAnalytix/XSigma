# Bazel Build Reference

The canonical Bazel guide is [../BAZEL_USER_GUIDE.md](../BAZEL_USER_GUIDE.md).
This short reference exists for readers navigating the `Docs/readme` guides.

## Quick start

```bash
python Scripts/setup_bazel.py config.release
python Scripts/setup_bazel.py build.test
python Scripts/setup_bazel.py build.test.release.avx2.cxx20
bazel test --config=release //Library/Core/Testing/Cxx:CoreCxxTests
```

Use Bazelisk. The pinned version is `8.4.2` in `.bazelversion`.

## Current defaults

- C++ standard: C++20.
- Parallel backend: standard threads.
- mimalloc, GoogleTest, and Google Benchmark defines: enabled by the helper.

The helper's `gtest` token disables GoogleTest defines. It is not required to
run the test suite.

## Frequently used configurations

```bash
# AddressSanitizer.
python Scripts/setup_bazel.py build.test.debug.asan

# Parallel backend.
python Scripts/setup_bazel.py build.test.release --parallel.tbb

# Limit the top-level target pattern to one library.
python Scripts/setup_bazel.py build.test.release --project.memory
```

`.bazelrc` defines `debug`, `release`, `relwithdebinfo`, `cxx17`, `cxx20`,
`cxx23`, the supported SIMD tiers, `lto`, sanitizer configurations, and
`logging_*`. Profiler instrumentation backends are not XSigma Bazel configs —
they live inside `ThirdParty/Profiler`. See the canonical guide for raw Bazel
commands, CMake differences, and current GPU limitations.
