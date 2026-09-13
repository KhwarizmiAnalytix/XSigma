# =============================================================================
# Overlay BUILD for the KhwarizmiAnalytix/Profiler submodule (ThirdParty/Profiler).
# Do not edit files inside that submodule — this overlay lives in XSigma.
# =============================================================================
load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@xsigma//bazel:profiler.bzl", "profiler_copts", "profiler_defines", "profiler_linkopts")

package(default_visibility = ["//visibility:public"])

# KINETO backend sources (Profiler's default). ITT is not selectable from XSigma.
_KINETO_BACKEND_SRCS = glob(
    [
        "kineto_*.cpp",
        "kineto/**/*.cpp",
        "bespoke/kineto/**/*.cpp",
        "bespoke/common/**/*.cpp",
        "bespoke/base/**/*.cpp",
    ],
    exclude = [
        "bespoke/common/unwind/**/*.cpp",
        "Testing/**",
    ],
    allow_empty = True,
)

_KINETO_BACKEND_HDRS = glob(
    [
        "kineto_*.h",
        "kineto/**/*.h",
        "bespoke/kineto/**/*.h",
        "bespoke/common/**/*.h",
        "bespoke/base/**/*.h",
    ],
    exclude = ["Testing/**"],
    allow_empty = True,
)

filegroup(
    name = "profiler_hdrs",
    srcs = glob(
        [
            "*.h",
            "**/*.h",
        ],
        exclude = [
            "Testing/**",
            "native/**",
            "bespoke/**",
        ],
        allow_empty = True,
    ),
)

filegroup(
    name = "profiler_srcs",
    srcs = glob(
        [
            "*.cpp",
            "**/*.cpp",
        ],
        exclude = [
            "native/**/*.cpp",
            "bespoke/**",
            "kineto_*.cpp",
            "kineto/**/*.cpp",
            "Testing/**",
            "examples/**",
            "consumer/**",
        ],
        allow_empty = True,
    ),
)

# cc_library srcs don't accept .mm without rules_apple. Copy to a .cc suffix and compile
# as Objective-C++ in a dedicated target so ARC copts don't leak onto plain C++ TUs
# (same split as //Library/Memory:memory_metal_objcxx).
copy_file(
    name = "metal_gpu_probe_objcxx",
    src = "native/gpu/metal_gpu_probe.mm",
    out = "native/gpu/metal_gpu_probe_mm.cc",
)

cc_library(
    name = "profiler_metal_objcxx",
    srcs = select({
        "@xsigma//bazel:enable_metal": [":metal_gpu_probe_objcxx"],
        "//conditions:default": [],
    }),
    hdrs = [
        ":profiler_hdrs",
    ] + glob(["native/**/*.h", "native/**/*.hxx"], exclude = ["Testing/**"], allow_empty = True),
    copts = profiler_copts() + select({
        "@xsigma//bazel:enable_metal": [
            "-x",
            "objective-c++",
            "-fobjc-arc",
            "-Wno-deprecated-declarations",
        ],
        "//conditions:default": [],
    }),
    defines = profiler_defines() + select({
        "@xsigma//bazel:shared_libs": ["PROFILER_SHARED_DEFINE", "PROFILER_BUILDING_DLL"],
        "//conditions:default": ["PROFILER_STATIC_DEFINE"],
    }),
    includes = ["."],
    linkopts = profiler_linkopts(),
    visibility = ["//visibility:public"],
    alwayslink = True,
)

# Kineto/ITT-side Metal fallback stub (bespoke/base/metal.mm) -- registers into
# the generic PrivateUse1 ProfilerStubs slot (bespoke/base/base.h), not a new
# device_enum value. Kept separate from profiler_metal_objcxx above: that
# target's hdrs deliberately exclude bespoke/** (it's scoped to the native
# Metal probe), so this stub needs its own bespoke-scoped header set. Same
# copy_file .mm→.cc technique as metal_gpu_probe_objcxx.
copy_file(
    name = "metal_stub_objcxx",
    src = "bespoke/base/metal.mm",
    out = "bespoke/base/metal_mm.cc",
)

cc_library(
    name = "profiler_kineto_metal_objcxx",
    srcs = select({
        "@xsigma//bazel:enable_metal": [":metal_stub_objcxx"],
        "//conditions:default": [],
    }),
    hdrs = [
        ":profiler_hdrs",
    ] + glob(["bespoke/base/*.h"], allow_empty = True),
    copts = profiler_copts() + select({
        "@xsigma//bazel:enable_metal": [
            "-x",
            "objective-c++",
            "-fobjc-arc",
            "-Wno-deprecated-declarations",
        ],
        "//conditions:default": [],
    }),
    defines = profiler_defines() + select({
        "@xsigma//bazel:shared_libs": ["PROFILER_SHARED_DEFINE", "PROFILER_BUILDING_DLL"],
        "//conditions:default": ["PROFILER_STATIC_DEFINE"],
    }),
    includes = ["."],
    linkopts = profiler_linkopts(),
    visibility = ["//visibility:public"],
    alwayslink = True,
)

cc_library(
    name = "Profiler",
    srcs = [
        ":profiler_srcs",
    ] + glob(["native/**/*.cpp"], exclude = ["Testing/**"], allow_empty = True) + _KINETO_BACKEND_SRCS,
    hdrs = [
        ":profiler_hdrs",
    ] + glob(["native/**/*.h", "native/**/*.hxx"], exclude = ["Testing/**"], allow_empty = True) + _KINETO_BACKEND_HDRS,
    copts = profiler_copts(),
    defines = profiler_defines() + select({
        "@xsigma//bazel:shared_libs": ["PROFILER_SHARED_DEFINE", "PROFILER_BUILDING_DLL"],
        "//conditions:default": ["PROFILER_STATIC_DEFINE"],
    }),
    includes = [
        ".",
    ],
    linkopts = profiler_linkopts(),
    linkstatic = select({
        "@xsigma//bazel:shared_libs": False,
        "//conditions:default": True,
    }),
    deps = [
        # No //Library/Core dependency: nothing under bespoke/ or native/ actually
        # includes a Core header (verified by grep and a Core-less build); CMake's
        # CMakeLists.txt never linked Core either. A prior Core dep here was
        # vestigial and, left in place, would create a Memory -> Profiler -> Core
        # -> Memory cycle once Memory takes a Profiler dependency (see
        # Docs/profiler/profiler.md, Instrumentation).
        "@fmt//:fmt",
        # Kineto is private to @profiler (Profiler's default instrumentation).
        "//third_party/kineto:kineto",
    ] + select({
        "@xsigma//bazel:enable_cuda": ["@local_config_cuda//:cuda"],
        "//conditions:default": [],
    }) + select({
        "@xsigma//bazel:enable_hip": ["@local_config_hip//:hip"],
        "//conditions:default": [],
    }) + select({
        "@xsigma//bazel:enable_metal": [
            ":profiler_metal_objcxx",
            ":profiler_kineto_metal_objcxx",
        ],
        "//conditions:default": [],
    }),
    # native/core/profiler_factory.h's registered profilers (host_tracer_factory,
    # python_tracer_factory, gpu_tracer_factory) self-register via static-init --
    # no other code references a symbol in those translation units. Bazel links this
    # target as a static archive (see linkstatic above); without alwayslink, the linker
    # drops those objects and host/GPU tracing never starts. CMake's shared-library
    # build doesn't hit this since every object file in a .so is linked.
    alwayslink = True,
)

# Profiler is consumed as a pure third-party dependency: its test suite
# (Testing/Cxx, ProfilerCxxTests) builds only from the standalone Profiler
# repo, never from XSigma — same as the CMake side (xsigma_add_profiler
# forces PROFILER_ENABLE_TESTING/EXAMPLES OFF).
