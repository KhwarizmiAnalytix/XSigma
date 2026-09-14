# =============================================================================
# XSigma Bazel Helper Functions — Project-level
# =============================================================================
# Shared compiler flags, linker options, and project-wide compile definitions.
#
# Module-specific defines live in the corresponding module bzl files:
#   bazel/core.bzl, bazel/memory.bzl, bazel/parallel.bzl,
#   bazel/logging.bzl, bazel/profiler.bzl, bazel/vectorization.bzl,
#   bazel/models.bzl
# =============================================================================

def xsigma_copts(cxx_std = "c++20", cstdlib_include = True):
    """Returns common compiler options for XSigma targets.

    Args:
        cxx_std: C++ standard to use (default: c++20, matches CMake default).
                 Each module passes its own standard so targets are self-contained
                 and do not rely on --cxxopt in .bazelrc.
        cstdlib_include: Whether to force-include <cstdlib> on non-Windows (mirrors
                 CMake's `target_compile_options(<Lib> PRIVATE -include cstdlib)`,
                 applied identically across Core/Logging/Parallel/Profiler/Vectorization/Models
                 CMakeLists.txt). Memory's memory_copts() passes False: CMake skips this
                 specifically for Clang there (compiler-instability workaround, see
                 Library/Memory/CMakeLists.txt) — Bazel has no compiler-id config_setting
                 to key off, so Memory omits it unconditionally rather than only for
                 Clang (documented simplification, not a full match).
    """
    return select({
        "@platforms//os:windows": [
            "/std:" + cxx_std,
            "/Zc:__cplusplus",  # expose correct __cplusplus value (mirrors CMake /Zc:__cplusplus)
            "/EHsc",            # structured exception handling
            "/bigobj",          # large object files (mirrors CMake /bigobj)
            "/utf-8",           # UTF-8 source/output encoding (mirrors CMake /utf-8)
            "/wd4244",          # narrowing conversion (mirrors CMake /wd4244)
            "/wd4267",          # size_t → int conversion (mirrors CMake /wd4267)
            "/wd4715",          # not all control paths return (mirrors CMake /wd4715)
            "/wd4018",          # signed/unsigned comparison (mirrors CMake /wd4018)
            "/WX",              # warnings as errors (mirrors CMake /WX)
        ],
        "//conditions:default": [
            "-std=" + cxx_std,
            "-Wall",
            "-Wextra",
            "-Wpedantic",
        ] + (["-include", "cstdlib"] if cstdlib_include else []),
    })

def xsigma_defines():
    """Returns project-wide preprocessor defines.

    All module-specific HAS_* flags are owned by their respective module bzl
    files (core.bzl, memory.bzl, etc.) and are NOT included here.
    """
    return select({
        # Mirrors CMake add_definitions(-D_CRT_SECURE_NO_DEPRECATE ...) in compiler_checks.cmake
        "@platforms//os:windows": [
            "_CRT_SECURE_NO_DEPRECATE",
            "_CRT_NONSTDC_NO_DEPRECATE",
            "_CRT_SECURE_NO_WARNINGS",
            "_SCL_SECURE_NO_DEPRECATE",
            "_SCL_SECURE_NO_WARNINGS",
            "NOMINMAX",
        ],
        "//conditions:default": [],
    })

def xsigma_linkopts():
    """Returns common linker options for XSigma targets."""
    return select({
        "@platforms//os:windows": [],
        "@platforms//os:macos": [
            "-undefined",
            "dynamic_lookup",
        ],
        "//conditions:default": [
            "-lpthread",
            "-ldl",
        ],
    })

def xsigma_enzyme_copts():
    """Returns Enzyme AD compile options.

    The -fpass-plugin=<path> flag is Clang-only; supply it via .bazelrc.user:
      build:enzyme --per_file_copt=Library/.*@-fpass-plugin=/path/to/LLDEnzyme-XX.so
    """
    return select({
        "//bazel:enable_enzyme": [],  # Plugin path supplied via .bazelrc.user --per_file_copt
        "//conditions:default": [],
    })

def xsigma_enzyme_linkopts():
    """Returns Enzyme AD link options.

    For LTO builds add to .bazelrc.user:
      build:enzyme --linkopt=-fpass-plugin=/path/to/LLDEnzyme-XX.so
    """
    return select({
        "//bazel:enable_enzyme": [],  # Non-LTO: symbols resolved at compile time
        "//conditions:default": [],
    })

def xsigma_test_copts():
    """Returns compiler options for XSigma test targets."""
    return xsigma_copts()

def xsigma_test_linkopts():
    """Returns linker options for XSigma test targets."""
    return xsigma_linkopts()
