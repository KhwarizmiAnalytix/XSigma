# Core (`Library/Core`)

Shared **Core** library: utilities, ownership helpers, compile-time traits, numeric algorithms, **Snappy** compression wrappers, and optional **Intel MKL**, **ROCm**, **Enzyme** AD, and **experimental** APIs.

## Layout

- `CMakeLists.txt` — options `CORE_ENABLE_*`, `CORE_CXX_STANDARD`, optional deps.
- `BUILD.bazel` — `//Library/Core:Core` and related targets.
- `Cmake/` — module-local CMake includes (compression, MKL, etc.).
- `Testing/Cxx/` — unit tests; benchmarks when `CORE_ENABLE_BENCHMARK=ON`.

---

## CMake options

### Feature and toolchain (`option()` / main `CACHE`)

| CMake variable | Default | Summary |
|----------------|---------|---------|
| `CORE_LTO_MODE` | Build-type dependent | `off`, `thin`, `full`, `ipo`, or `auto`; non-Debug performance builds default to `auto` |
| `CORE_ENABLE_COVERAGE` | OFF | Coverage instrumentation |
| `CORE_ENABLE_TESTING` | ON | `add_subdirectory(Testing/Cxx)` |
| `CORE_ENABLE_EXAMPLES` | OFF | Examples subtree |
| `CORE_ENABLE_GTEST` | ON | GoogleTest for Core tests |
| `CORE_ENABLE_BENCHMARK` | ON | Google Benchmark targets in tests |
| `CORE_ENABLE_MKL` | OFF | Intel MKL |
| `CORE_ENABLE_ROCM` | OFF | AMD ROCm |
| `CORE_ENABLE_EXPERIMENTAL` | OFF | Experimental API (advanced) |
| `CORE_ENABLE_ENZYME` | — | Declared in `Cmake/tools/enzyme.cmake` (root includes before Core) |
| `CORE_ENABLE_ICECC` / `CORE_ENABLE_CACHE` / `CORE_ENABLE_CLANGTIDY` / `CORE_ENABLE_FIX` / `CORE_ENABLE_IWYU` / `CORE_ENABLE_SANITIZER` / `CORE_ENABLE_SPELL` / `CORE_ENABLE_VALGRIND` | mostly OFF / cache ON | Tooling; see `CMakeLists.txt` |

### `CACHE STRING` selectors

| CMake variable | Default | Values / notes |
|----------------|---------|----------------|
| `CORE_CXX_STANDARD` | 20 | `11`, `14`, `17`, `20`, `23` |
| `CORE_SANITIZER_TYPE` | address | `address`, `undefined`, `thread`, `memory`, `leak` (if sanitizer ON) |
| `CORE_LINKER_CHOICE` | default | `default`, `lld`, `mold`, `gold`, `lld-link` |
| `CORE_CACHE_BACKEND` | none | `none`, `ccache`, `sccache`, `buildcache` |

### From other CMake modules / includes

| CMake variable | Summary |
|----------------|---------|
| `CORE_ENABLE_COMPRESSION` | Set by `include(compression)` — Snappy and related |
| `CORE_COMPRESSION_TYPE_SNAPPY` | Compression type when compression enabled |
| `CORE_SOBOL_1111` | Optional; defines `CORE_SOBOL_1111=1` when set |
| `CORE_LU_PIVOTING` | Optional; defines `CORE_LU_PIVOTING=1` when set |

SIMD capability macros (`CORE_SSE`, `CORE_AVX`, …) come from root `platform.cmake` / Vectorization probes (`PROJECT_*`). Intel SVML for SIMD math is configured on the **Vectorization** module (`VECTORIZATION_ENABLE_SVML` / Bazel `vectorization_enable_svml`), not on Core.

---

## Bazel flags

Starlark helpers: [`bazel/core.bzl`](../../bazel/core.bzl). `config_setting` names are under [`bazel/BUILD.bazel`](../../bazel/BUILD.bazel).

### `--define` keys → compile defines

| Define | When true / matched | Effect (macros) |
|--------|---------------------|-------------------|
| `core_enable_mkl` | `//bazel:enable_mkl` | `CORE_HAS_MKL=1` |
| `core_enable_rocm` | `//bazel:enable_rocm` | `CORE_HAS_ROCM=1` |
| `core_enable_experimental` | `//bazel:enable_experimental` | `CORE_HAS_EXPERIMENTAL=1` |
| `enable_gtest` | default ON; **`enable_gtest=false`** → `//bazel:disable_gtest` | `CORE_HAS_GTEST=0` when disabled |
| `core_lu_pivoting` | `//bazel:lu_pivoting` (`=true`) | `CORE_LU_PIVOTING=1` |
| `core_sobol_1111` | default effective ON; **`core_sobol_1111=false`** → `//bazel:disable_sobol_1111` | Omits `CORE_SOBOL_1111` when disabled |
| `core_enable_enzyme` | `//bazel:enable_enzyme` | `CORE_HAS_ENZYME=1` |
| `core_enable_compression` + `core_compression_type` | `//bazel:enable_compression_snappy` or `enable_compression` | `CORE_HAS_COMPRESSION`, `CORE_COMPRESSION_TYPE_SNAPPY` — see `core.bzl` |

### Convenience configs (`.bazelrc`)

Examples: `--config=mkl`, `--config=enzyme`, `--config=lu_pivoting`, `--config=sobol_1111`, `--config=gtest`, `--config=benchmark`. Defaults for `core_enable_benchmark` and `enable_benchmark` are in the root `.bazelrc` “CMake-equivalent defaults” block.

### CMake-only (no Starlark equivalent)

`CORE_CXX_STANDARD` is fixed as `c++20` in `core.bzl` (`CORE_CXX_STD`). LTO, coverage, sanitizers, clang-tidy, IWYU, linker/cache backend choice, spell, Valgrind, Icecream — **CMake only**.
