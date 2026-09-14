# =============================================================================
# Kineto Library BUILD Configuration
# =============================================================================
# Kineto profiling library with conditional CUPTI support — private Profiler
# backend. Staged into @profiler//third_party/kineto by
# bazel/profiler_repository.bzl (not a top-level XSigma WORKSPACE repo).
# =============================================================================

package(default_visibility = ["//visibility:public"])

# Kineto compiler flags
KINETO_COPTS = [
    "-DKINETO_NAMESPACE=libkineto",
    "-DLIBKINETO_NOROCTRACER",
    # Disable consteval to avoid C++20 compatibility issues with fmt library
    # The FMT_STRING macro uses consteval functions that have stricter requirements
    # in C++20, causing compilation errors in kineto's usage of fmt
    "-DFMT_USE_CONSTEVAL=0",
] + select({
    "@xsigma//bazel:enable_cuda": ["-DHAS_CUPTI"],
    "//conditions:default": ["-DLIBKINETO_NOCUPTI"],
}) + select({
    "@platforms//os:windows": [
        "/utf-8",  # MSVC: Treat source files as UTF-8
    ],
    "//conditions:default": [
        "-fexceptions",
        "-Wno-deprecated-declarations",
        "-Wno-unused-function",
        "-Wno-unused-private-field",
        "-Wno-unused-variable",
        "-Wno-unused-parameter",
        "-w",  # Suppress warnings for third-party code
    ],
})

cc_library(
    name = "kineto",
    srcs = glob(
        [
            "libkineto/src/*.cpp",
        ],
        exclude = [
            # Always exclude ROCm specific files
            "libkineto/src/RocprofActivityApi.cpp",
            "libkineto/src/RocprofLogger.cpp",
            "libkineto/src/RoctracerActivityApi.cpp",
            "libkineto/src/RoctracerLogger.cpp",
            "libkineto/src/RocLogger.cpp",
            # Exclude CUPTI-specific files that will be conditionally included below.
            # This list mirrors get_libkineto_cupti_srcs() in the vendored
            # libkineto/libkineto_defs.bzl (kineto's own authoritative CPU-only vs.
            # CUPTI-only source split) minus get_libkineto_cpu_only_srcs() and
            # Demangle.cpp (always compiled -- listed in both). CuptiActivityApi.cpp,
            # CuptiActivityProfiler.cpp, and CuptiCbidRegistry.cpp are *not* CPU-only
            # despite an earlier version of this comment claiming otherwise: their
            # headers #include <cupti.h> unconditionally (no HAS_CUPTI guard), so
            # compiling them without CUDA fails with 'cupti.h' file not found.
            "libkineto/src/CuptiActivity.cpp",
            "libkineto/src/CuptiActivityApi.cpp",
            "libkineto/src/CuptiActivityProfiler.cpp",
            "libkineto/src/CuptiCallbackApi.cpp",
            "libkineto/src/CuptiCbidRegistry.cpp",
            "libkineto/src/CuptiEventApi.cpp",
            "libkineto/src/CuptiMetricApi.cpp",
            "libkineto/src/CuptiRangeProfiler.cpp",
            "libkineto/src/CuptiRangeProfilerApi.cpp",
            "libkineto/src/CuptiRangeProfilerConfig.cpp",
            "libkineto/src/CuptiNvPerfMetric.cpp",
            "libkineto/src/CuptiTimestamp.cpp",
            # PM sampling sources include <cupti_pmsampling.h> unconditionally and are
            # not part of get_libkineto_cupti_srcs() (separate
            # get_libkineto_cupti_pm_sampling_srcs()) — kineto's own CMake never
            # compiles them, so exclude them in both CUDA and non-CUDA builds.
            "libkineto/src/CuptiPMSamplingApi.cpp",
            "libkineto/src/CuptiPMSamplingController.cpp",
            "libkineto/src/CuptiPMSamplingProfiler.cpp",
            "libkineto/src/EventProfiler.cpp",
            "libkineto/src/EventProfilerController.cpp",
            "libkineto/src/KernelRegistry.cpp",
            "libkineto/src/WeakSymbols.cpp",
            "libkineto/src/cupti_strings.cpp",
            # Exclude plugin files
            "libkineto/src/plugin/**/*.cpp",
        ],
        allow_empty = True,
    ) + select({
        "@xsigma//bazel:enable_cuda": [
            # CUPTI-only TUs from get_libkineto_cupti_srcs() in the vendored
            # libkineto/libkineto_defs.bzl, minus CPU-only atoms already in the
            # base glob. EventProfiler*, CuptiEventApi, CuptiMetricApi, and the
            # CuptiRangeProfiler/NvPerf files are not in this kineto tree.
            "libkineto/src/CuptiActivityApi.cpp",
            "libkineto/src/CuptiActivityProfiler.cpp",
            "libkineto/src/CuptiCallbackApi.cpp",
            "libkineto/src/CuptiCbidRegistry.cpp",
            "libkineto/src/CuptiTimestamp.cpp",
            "libkineto/src/KernelRegistry.cpp",
            "libkineto/src/WeakSymbols.cpp",
            "libkineto/src/cupti_strings.cpp",
        ],
        "//conditions:default": [],
    }),
    hdrs = glob(
        [
            "libkineto/include/*.h",
            "libkineto/include/**/*.h",
            "libkineto/src/*.h",
        ],
        allow_empty = True,
    ),
    # CuptiActivity.cpp is #included by CuptiActivityProfiler.cpp, not compiled
    # as its own TU. textual_hdrs + allow_empty so a missing file does not fail
    # analysis (older kineto trees omit it).
    textual_hdrs = select({
        "@xsigma//bazel:enable_cuda": glob(
            ["libkineto/src/CuptiActivity.cpp"],
            allow_empty = True,
        ),
        "//conditions:default": [],
    }),
    copts = KINETO_COPTS,
    includes = [
        "libkineto",
        "libkineto/include",
        "libkineto/src",
    ],
    linkopts = select({
        "@platforms//os:windows": [],
        "@platforms//os:macos": ["-lpthread"],
        "//conditions:default": ["-lpthread", "-ldl"],
    }),
    linkstatic = True,
    deps = [
        "@fmt//:fmt",
    ] + select({
        "@xsigma//bazel:enable_cuda": [
            "@local_config_cuda//:cupti",
            "@local_config_cuda//:cudart",
        ],
        "//conditions:default": [],
    }),
)

