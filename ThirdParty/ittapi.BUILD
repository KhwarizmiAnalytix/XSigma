# =============================================================================
# Intel ITT API (ittnotify) BUILD Configuration
# =============================================================================
# VTune instrumentation/tracing API — private Profiler backend template.
# Staged into @profiler//third_party/ittapi by bazel/profiler_repository.bzl
# when needed; XSigma does not expose ITT as a setup/Bazel flag.
# Mirrors ittapi's `ittnotify` target (ittnotify_static.c only).
# =============================================================================

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "ittnotify",
    srcs = [
        "src/ittnotify/ittnotify_static.c",
    ],
    hdrs = [
        "include/ittnotify.h",
        "include/legacy/ittnotify.h",
        "include/libittnotify.h",
    ],
    # ittnotify_static.c's own #include "ittnotify_config.h" / "disable_warnings.h" /
    # "ittnotify_static.h" resolve via same-directory quoted-include lookup (standard
    # C/C++ behavior), independent of `includes` below -- listed as textual_hdrs so
    # Bazel's sandbox exposes them as inputs without treating them as public headers.
    textual_hdrs = [
        "src/ittnotify/disable_warnings.h",
        "src/ittnotify/ittnotify_config.h",
        "src/ittnotify/ittnotify_static.h",
        "src/ittnotify/ittnotify_types.h",
    ],
    copts = select({
        "@platforms//os:windows": [],
        "//conditions:default": ["-w"],  # upstream ships its own warning suppression pragmas
    }),
    includes = ["include"],
    linkopts = select({
        "@platforms//os:windows": [],
        "//conditions:default": ["-ldl"],  # mirrors CMAKE_DL_LIBS in ittapi/CMakeLists.txt
    }),
    linkstatic = True,
)
