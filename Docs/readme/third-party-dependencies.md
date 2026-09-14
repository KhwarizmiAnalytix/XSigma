# Third-Party Dependencies

XSigma vendors third-party source through Git submodules and can prefer
discoverable system packages where a module supports them. Initialise submodules
before configuring:

```bash
git submodule sync
git submodule update --init
```

## Host submodules (`ThirdParty/` on XSigma)

These are the only third-party checkouts registered in XSigma's `.gitmodules`.

| Path | Role |
|---|---|
| `ThirdParty/fmt` | Formatting (shared with Logging / Profiler) |
| `ThirdParty/cpuinfo` | CPU feature detection |
| `ThirdParty/googletest` | Unit tests |
| `ThirdParty/mimalloc` | Optional Memory allocator |
| `ThirdParty/benchmark` | Microbenchmarks |
| `ThirdParty/sleef` | Optional SIMD math |
| `ThirdParty/Logging` | Logging product ([KhwarizmiAnalytix/Logging](https://github.com/KhwarizmiAnalytix/Logging)) |
| `ThirdParty/Parallel` | Parallel product ([KhwarizmiAnalytix/Parallel](https://github.com/KhwarizmiAnalytix/Parallel)) |
| `ThirdParty/Profiler` | Profiler product ([KhwarizmiAnalytix/Profiler](https://github.com/KhwarizmiAnalytix/Profiler)) |

`ThirdParty/svml` is vendored binaries, not a git submodule. TBB is fetched by
the build (CMake/Bazel), not stored as an XSigma submodule.

XSigma host overlays compile Logging and Profiler product sources only.

## Dependency selection

Dependency policy is owned by the consuming library, not by a generic
`XSIGMA_ENABLE_XXX` switch. Common controls are:

| Dependency or area | Current option |
|---|---|
| External package preference | `XSIGMA_ENABLE_EXTERNAL=ON|OFF` |
| CPU allocator | `MEMORY_ENABLE_MIMALLOC=ON|OFF` |
| TBB Memory allocator | `MEMORY_ENABLE_TBB=ON|OFF` |
| OpenMP execution | `PARALLEL_BACKEND=openmp` |
| TBB execution | `PARALLEL_BACKEND=tbb` |
| Core MKL | `CORE_ENABLE_MKL=ON|OFF` |
| Vectorization MKL VML | `VECTORIZATION_ENABLE_MKL=ON|OFF` |
| Vector math libraries | `VECTORIZATION_ENABLE_SLEEF`, `VECTORIZATION_ENABLE_SVML`, or `VECTORIZATION_ENABLE_ACCELERATE` |
| Test and benchmark dependencies | `<MODULE>_ENABLE_GTEST`, `<MODULE>_ENABLE_BENCHMARK` |

GoogleTest defaults to `ON` per library. Google Benchmark also defaults to `ON`
in most modules, although `Scripts/setup.py` disables benchmark targets until
its `benchmark` token is supplied.

## External packages

```bash
cmake -S . -B build -G Ninja -DXSIGMA_ENABLE_EXTERNAL=ON
cmake --build build --parallel
```

External packages must be discoverable by the active toolchain. Set the normal
CMake package-search variables, such as `CMAKE_PREFIX_PATH`, when necessary.
The project may continue to use a vendored component when no supported external
substitution exists.

## Direct CMake examples

```bash
# TBB parallel execution and Memory allocator.
cmake -S . -B build-tbb -G Ninja \
  -DPARALLEL_BACKEND=tbb \
  -DMEMORY_ENABLE_TBB=ON

# Disable test and benchmark targets for a Core-only build.
cmake -S . -B build-core -G Ninja \
  -DXSIGMA_LIBRARY_PROJECT=Core \
  -DCORE_ENABLE_TESTING=OFF \
  -DCORE_ENABLE_GTEST=OFF \
  -DCORE_ENABLE_BENCHMARK=OFF
```

Avoid obsolete `ENABLE_GTEST` and `ENABLE_BENCHMARK` variables; current module
files consume only their module-prefixed forms.

## CMake targets

Library target names and third-party aliases are defined by the checked-out
CMake files and can vary with Parallel backend selection. Prefer linking XSigma's public
library targets (for example `Logging::Logging`, `Memory::Memory`, or
`Vectorization::Vectorization`) rather than depending directly on an internal
third-party target.

## Bazel

Bazel uses `MODULE.bazel`, `WORKSPACE.bazel`, `.bazelrc`, and hand-written
BUILD glue for selected vendored dependencies. Its `external` dependency
selection does not mirror CMake's `XSIGMA_ENABLE_EXTERNAL` option. See
[the Bazel guide](bazel.md) for the current Bazel dependency model.
