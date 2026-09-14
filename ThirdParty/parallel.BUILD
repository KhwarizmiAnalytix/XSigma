# =============================================================================
# Parallel Parallel Library BUILD Configuration
# =============================================================================
# Standalone parallel computing library. No dependency on //Library/Core.
# Include root is the repo root (ThirdParty/Parallel); sources live under a nested
# Parallel/ subdirectory, so:
#   "Parallel/common/parallel_export.h"     -> ThirdParty/Parallel/Parallel/common/parallel_export.h
#   "Parallel/tools/parallel_tools.h"       -> ThirdParty/Parallel/Parallel/tools/parallel_tools.h
# XSigma clients include <parallel.h> (Parallel/parallel.h) via the extra
# "Parallel" entry in includes.
# =============================================================================

load("@bazel_skylib//lib:selects.bzl", "selects")
load("@xsigma//bazel:parallel.bzl", "parallel_copts", "parallel_defines", "parallel_linkopts")

package(default_visibility = ["//visibility:public"])

# =============================================================================
# Source File Groups
# =============================================================================

filegroup(
    name = "parallel_hdrs",
    srcs = glob(
        [
            "Parallel/*.h",
            "Parallel/tools/*.h",
            "Parallel/common/*.h",
        ],
        allow_empty = True,
    ),
)

filegroup(
    name = "parallel_srcs",
    srcs = glob(
        [
            "Parallel/tools/*.cpp",
            "Parallel/common/*.cpp",
        ],
        allow_empty = True,
    ),
)

# =============================================================================
# Parallel implementation library
# =============================================================================

cc_library(
    name = "parallel_lib",
    # Parallel backend: TBB > OpenMP > std_thread (matches CMake PARALLEL_BACKEND + legacy
    # flags). A single flat selects.with_or() -- a select() cannot be nested as another
    # select()'s branch value, so this intentionally does not special-case the discouraged
    # "both parallel_backend_tbb and enable_openmp set at once" combination: Bazel now reports
    # that as an explicit "multiple matching conditions" analysis error instead.
    srcs = [
        ":parallel_srcs",
    ] + selects.with_or({
        (
            "@xsigma//bazel:parallel_backend_tbb",
            "@xsigma//bazel:parallel_enable_tbb",
        ): glob(["Parallel/tbb/*.cpp"], allow_empty = True),
        (
            "@xsigma//bazel:parallel_backend_openmp",
            "@xsigma//bazel:enable_openmp",
        ): glob(["Parallel/openmp/*.cpp"], allow_empty = True),
        "//conditions:default": glob(["Parallel/std_thread/*.cpp"], allow_empty = True),
    }),
    hdrs = [
        ":parallel_hdrs",
    ] + selects.with_or({
        (
            "@xsigma//bazel:parallel_backend_tbb",
            "@xsigma//bazel:parallel_enable_tbb",
        ): glob(["Parallel/tbb/*.h", "Parallel/tbb/*.hxx"], allow_empty = True),
        (
            "@xsigma//bazel:parallel_backend_openmp",
            "@xsigma//bazel:enable_openmp",
        ): glob(["Parallel/openmp/*.h", "Parallel/openmp/*.hxx"], allow_empty = True),
        "//conditions:default": glob(["Parallel/std_thread/*.h", "Parallel/std_thread/*.hxx"], allow_empty = True),
    }),
    copts = parallel_copts(),
    defines = parallel_defines() + select({
        "@xsigma//bazel:shared_libs": ["PARALLEL_SHARED_DEFINE"],
        "//conditions:default": ["PARALLEL_STATIC_DEFINE"],
    }),
    local_defines = select({
        "@xsigma//bazel:shared_libs": ["PARALLEL_BUILDING_DLL"],
        "//conditions:default": [],
    }),
    includes = [
        ".",
        "Parallel",
        "Testing",
    ],
    linkopts = parallel_linkopts(),
    linkstatic = select({
        "@xsigma//bazel:shared_libs": False,
        "//conditions:default": True,
    }),
    deps = selects.with_or({
        (
            "@xsigma//bazel:parallel_backend_tbb",
            "@xsigma//bazel:parallel_enable_tbb",
        ): [
            "@tbb//:tbb",
            "@tbb//:tbbmalloc",
        ],
        "//conditions:default": [],
    }) + selects.with_or({
        (
            "@xsigma//bazel:parallel_backend_openmp",
            "@xsigma//bazel:enable_openmp",
        ): ["@parallel_openmp//:openmp_check"],
        "//conditions:default": [],
    }),
    alwayslink = False,
)

# =============================================================================
# Public Parallel target
# =============================================================================

cc_library(
    name = "Parallel",
    deps = [
        ":parallel_lib",
    ],
    visibility = ["//visibility:public"],
)
