# Cmake/flags — Module Reference

This directory contains five CMake modules that together establish the build configuration, validate the environment, map feature flags to preprocessor definitions, and apply platform/compiler-specific compiler and linker flags.

---

## build_type.cmake

**Purpose:** Ensures `CMAKE_BUILD_TYPE` is always set before any other module runs.

- Uses `include_guard(GLOBAL)` so it is processed only once per CMake run.
- If `CMAKE_BUILD_TYPE` is not already defined, it defaults to `"Release"` and caches that choice so subsequent `cmake --build` invocations do not reset it.
- Registers the four standard values (`Debug`, `Release`, `MinSizeRel`, `RelWithDebInfo`) as the allowed property strings, which enables IDE drop-down menus.

**Flags / Variables set:**

| Variable | Default | Notes |
|---|---|---|
| `CMAKE_BUILD_TYPE` | `Release` | Cached `STRING`. Controls optimization level for all targets. |

---

## compiler_checks.cmake

**Purpose:** Hard-fails the configure step when the detected compiler is too old, before any source is compiled.

- Uses `include_guard(GLOBAL)` for single-pass execution.
- Checks `CMAKE_CXX_COMPILER_ID` and `CMAKE_CXX_COMPILER_VERSION` against strict minimums:

| Compiler | Minimum version | Rationale |
|---|---|---|
| GCC (`GNU`) | 8.0 | Full C++17 + reliable `if constexpr` |
| LLVM Clang | 7.0 | C++17 standard library headers |
| Apple Clang | 11.0 (Xcode 11.3.1) | macOS SDK alignment |
| MSVC | 19.10 (VS 2017) | `/std:c++17` switch |
| Intel ICC | 19.0 | C++17 conformance |

Issues `FATAL_ERROR` on version mismatch, stopping the build immediately.

> **Relationship to checks.cmake:** `compiler_checks.cmake` enforces *stricter* minimums (e.g. GCC 8 vs GCC 7, Apple Clang 11 vs 9) and is a lightweight gate applied early. `checks.cmake` repeats a similar check with slightly lower thresholds alongside broader system validation.

---

## checks.cmake

**Purpose:** Comprehensive system and compiler validation with aggressive result caching to keep re-configure times fast.

Uses a manual guard (`TEMP_CHECKS_CONFIGURED`) and a cache-key composed of compiler id + version + OS name + OS version. If the key matches a previous run, the entire module exits early with `"Using cached validation results"`.

### Platform detection

Detects and caches one of `Windows`, `macOS`, `Linux` (or `Unknown`) into:

| Cache variable | Type | Meaning |
|---|---|---|
| `TEMP_PLATFORM` | INTERNAL | Human-readable platform name |
| `TEMP_PLATFORM_WINDOWS` | INTERNAL | `TRUE` on Windows |
| `TEMP_PLATFORM_MACOS` | INTERNAL | `TRUE` on macOS |
| `TEMP_PLATFORM_LINUX` | INTERNAL | `TRUE` on Linux |

### Compiler version validation (cached)

Same compiler matrix as `compiler_checks.cmake` but with slightly more permissive minimums (GCC 7.0, Clang 5.0, Apple Clang 9.0, MSVC 19.14, Intel 18.0). Sets:

| Cache variable | Meaning |
|---|---|
| `TEMP_COMPILER_GCC` | GCC detected |
| `TEMP_COMPILER_CLANG` | Clang detected |
| `TEMP_COMPILER_APPLE_CLANG` | Apple Clang detected |
| `TEMP_COMPILER_MSVC` | MSVC detected |
| `TEMP_COMPILER_INTEL` | Intel ICC detected |
| `TEMP_COMPILER_ID` | Normalised id string (`gcc`, `clang`, `msvc`, `intel`) |

### Essential dependency checks (cached)

| Check | CMake module used | Failure behaviour |
|---|---|---|
| Threading (`Threads`) | `find_package` | `FATAL_ERROR` |
| Math library `libm` (non-Windows) | `check_library_exists` | `FATAL_ERROR` |

### C++17 feature probes (cached via `TEMP_CXX17_FEATURES_VALIDATED`)

Three compile-time probes using `check_cxx_source_compiles`:

| Probe | Variable set | Tested feature |
|---|---|---|
| Structured bindings | `TEMP_HAS_STRUCTURED_BINDINGS` | `auto [a, b] = ...` |
| `if constexpr` | `TEMP_HAS_IF_CONSTEXPR` | `if constexpr (true)` |
| `std::optional` | `TEMP_HAS_STD_OPTIONAL` | `<optional>` header + `.value_or()` |

All three must succeed; otherwise a `WARNING` is emitted (not fatal, to allow partial C++17 environments).

### Exception handling probe (cached via `TEMP_EXCEPTION_HANDLING_VALIDATED`)

Compiles a `try/catch` block. Failure emits a `WARNING` only — the build continues.

### Platform-specific header checks

| Platform | Headers required | Failure |
|---|---|---|
| Windows | `windows.h` | `FATAL_ERROR` |
| Linux / macOS | `unistd.h`, `pthread.h` | `FATAL_ERROR` |

---

## compile_definitions.cmake

**Purpose:** Provides a single reusable CMake function that converts `ENABLE_*` option variables into `HAS_*=0/1` compile definitions appended to a named list.

```cmake
compile_definition(<list_variable> <ENABLE_FLAG>)
```

**How it works:**

1. Derives the definition name by replacing `ENABLE` with `HAS` in the flag name (e.g. `LOGGING_ENABLE_SANITIZER` → `LOGGING_HAS_SANITIZER`).
2. Reads the current value of `<ENABLE_FLAG>`; treats undefined as `OFF`.
3. Appends `HAS_FOO=1` or `HAS_FOO=0` to the caller-supplied list variable in `PARENT_SCOPE`.

Each library's own `CMakeLists.txt` calls this function to build its private `*_COMPILE_DEFINITIONS` list before passing it to `target_compile_definitions`. This ensures every `ENABLE_*` option has a corresponding preprocessor constant available at compile time regardless of whether it is on or off.

---

## platform.cmake

**Purpose:** Applies platform-specific, compiler-specific, and architecture-specific compiler and linker flags globally.

Uses `include_guard(GLOBAL)`.

### SunOS / Sun C++ (non-GCC)

Links `Crun` and `Cstd` from `/opt/SUNWspro/lib` when building with the Sun C++ compiler — required for Java interop and certain standard library features that are not linked by default in shared-library builds.

### Emscripten (WebAssembly)

All flags below are set on **C, C++, EXE linker, shared linker, and module linker** flags, and propagated via `target_link_options`/`target_compile_options` on the `XSigmaPlatform` interface target so consumers inherit them automatically.

| Flag | Applied to | Purpose |
|---|---|---|
| `-fwasm-exceptions` | compiler + linker | Enable C++ exception support in Wasm (off by default due to overhead) |
| `-sEXCEPTION_STACK_TRACES=1` | linker | Generate helper functions for uncaught-exception stack traces |
| `-pthread` | compiler + linker | POSIX threads in Wasm (only when `PROJECT_WEBASSEMBLY_THREADS=ON`) |
| `-Wno-pthreads-mem-growth` | compiler | Suppress pthreads memory-growth warning (open LLVM issue) |
| `-sMEMORY64=1` | compiler + linker | 64-bit Wasm memory (only when `PROJECT_WEBASSEMBLY_64_BIT=ON`) |

### GCC on Windows / Cygwin

| Flag | Purpose |
|---|---|
| `-mwin32` | Expose Win32 API defines under GCC/Cygwin |
| `-lgdi32` | Link GDI32 for graphics primitives |

### GCC on MinGW

| Flag | Purpose |
|---|---|
| `-mthreads` | MinGW thread-safe exception handling (compiler + all linker flags) |

### GCC on SunOS (with DART/testing)

| Flag | Purpose |
|---|---|
| `-Wno-unknown-pragmas` | Suppress spurious warnings from X11 headers |

### OSF1 (Tru64 UNIX) — non-GCC

| Flag | Purpose |
|---|---|
| `-timplicit_local` | Local template instantiation |
| `-no_implicit_include` | Disable implicit `.cc` inclusion |

### AIX — non-GCC (xlC)

| Flag | Purpose |
|---|---|
| `-qrtti=all` | Enable `typeid` and `dynamic_cast` (off by default on xlC) |
| `-bhalt:5` | Silence duplicate-symbol linker warnings (EXE, shared, module linkers) |

### HP-UX — non-GCC

| Flag | Purpose |
|---|---|
| `+W2111 +W2236 +W4276` | Suppress specific aCC warnings that fire on standard headers |

### Intel ICC (UNIX)

Tests whether `-i_dynamic` is needed via `TestNO_ICC_IDYNAMIC_NEEDED.cmake`. If the test says the flag *is* needed, `-i_dynamic` is appended to `CMAKE_CXX_FLAGS` to enable dynamic linking of Intel runtime libraries.

### PGI (NVIDIA HPC SDK)

| Flag | Purpose |
|---|---|
| `--diag_suppress=236` | Suppress constant-value assert warnings used in error-handling macros |
| `--diag_suppress=381` | Suppress redundant-semicolon warnings from macro expansion |

### MSVC

| Flag / Definition | Scope | Purpose |
|---|---|---|
| `/Zc:__cplusplus` | C++ | Make `__cplusplus` report the actual standard (e.g. `201703L`) |
| `/wd4244 /wd4267` | C + C++ | Disable implicit narrowing-conversion warnings |
| `/wd4715` | C + C++ | Disable "not all control paths return a value" warning |
| `/wd4018` | C + C++ | Disable signed/unsigned mismatch warning |
| `-D_CRT_SECURE_NO_DEPRECATE` | preprocessor | Suppress MSVC CRT deprecation warnings |
| `-D_CRT_NONSTDC_NO_DEPRECATE` | preprocessor | Suppress POSIX-name deprecation warnings |
| `-D_CRT_SECURE_NO_WARNINGS` | preprocessor | Alias for the above (belt-and-suspenders) |
| `-D_SCL_SECURE_NO_DEPRECATE` | preprocessor | Suppress STL checked-iterator deprecation warnings |
| `-D_SCL_SECURE_NO_WARNINGS` | preprocessor | Alias for the above |
| `/MP<N>` | C + C++ | Parallel compilation using all `NUMBER_OF_PROCESSORS` cores |
| `/bigobj` | C + C++ | Increase COFF symbol-table limit for large translation units |
| `/Zi` | C + C++ | Produce a separate PDB file for fast incremental linking |
| `/DEBUG:FASTLINK` (default) | EXE + shared linker | Fast PDB generation during development builds |
| `/DEBUG:FULL /INCREMENTAL:NO` | EXE + shared linker | Full PDB when any of `CORE_ENABLE_COVERAGE`, `LOGGING_ENABLE_COVERAGE`, `MEMORY_ENABLE_COVERAGE`, or `PARALLEL_ENABLE_COVERAGE` is `ON` (coverage tools need complete symbols) |
| `/utf-8` | C + C++ | Treat source and object files as UTF-8 |
| `/EHsc` | C + C++ | Standard C++ synchronous exception handling (catch C++ exceptions only, extern "C" functions do not throw) |

### Apple / macOS LLVM linker

Adds LLVM library search paths and RPATHs so that binaries find the Homebrew- or custom-installed LLVM `libc++` at runtime rather than the system one.

Prefix resolution order:
1. `PROJECT_LLVM_INSTALL_PREFIX` (user override)
2. `/opt/homebrew/opt/llvm` (Apple Silicon Homebrew)
3. `/usr/local/opt/llvm` (Intel Homebrew)
4. Fallback: `/opt/homebrew/opt/llvm`

| Link option added | Purpose |
|---|---|
| `-L<prefix>/lib/c++` | Search LLVM `libc++` first |
| `-L<prefix>/lib` | Search LLVM runtime libs |
| `-Wl,-rpath,<prefix>/lib/c++` | Embed RPATH so installed binaries find `libc++` |
| `-Wl,-rpath,<prefix>/lib` | Embed RPATH for other LLVM runtime libs |

Each flag is added only once (guarded by `string(FIND ...)`) to avoid duplicates when the module is transitively pulled in.
