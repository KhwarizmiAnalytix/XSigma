# Bazel overlay for the Logging third-party submodule (ThirdParty/Logging,
# https://github.com/KhwarizmiAnalytix/Logging). Used via new_local_repository in
# WORKSPACE.bazel as @logging. Include root is the repo root (no Logging/logging/ nesting).
# Mirrors the CMake build in ThirdParty/Logging/CMakeLists.txt.
load("@xsigma//bazel:logging.bzl", "logging_copts", "logging_defines", "logging_linkopts")

package(default_visibility = ["//visibility:public"])

filegroup(
    name = "logging_hdrs",
    srcs = glob(
        [
            "*.h",
            "common/*.h",
            "util/*.h",
            "logger/*.h",
        ],
        allow_empty = True,
    ),
)

filegroup(
    name = "logging_srcs",
    srcs = glob(
        [
            "util/*.cpp",
        ],
        allow_empty = True,
    ),
)

cc_library(
    name = "logging_lib",
    srcs = [
        ":logging_srcs",
        "logger/back_trace.cpp",
        "logger/logger.cpp",
    ],
    hdrs = [":logging_hdrs"],
    copts = logging_copts(),
    defines = logging_defines() + select({
        "@xsigma//bazel:shared_libs": ["LOGGING_SHARED_DEFINE"],
        "//conditions:default": ["LOGGING_STATIC_DEFINE"],
    }),
    local_defines = select({
        "@xsigma//bazel:shared_libs": ["LOGGING_BUILDING_DLL"],
        "//conditions:default": [],
    }),
    includes = [".", "logger"],
    linkopts = logging_linkopts() + select({
        "@platforms//os:windows": ["dbghelp.lib"],
        "//conditions:default": [],
    }),
    linkstatic = select({
        "@xsigma//bazel:shared_libs": False,
        "//conditions:default": True,
    }),
    deps = [
        "@fmt//:fmt",
    ] + select({
        "@xsigma//bazel:disable_magic_enum": [],
        "//conditions:default": ["@magic_enum//:magic_enum"],
    }) + select({
        "@xsigma//bazel:logging_glog": ["@glog//:glog"],
        "@xsigma//bazel:logging_loguru": ["@loguru//:loguru"],
        "@xsigma//bazel:logging_native": [],
        "@xsigma//bazel:logging_spdlog": ["@spdlog//:spdlog"],
        "//conditions:default": ["@loguru//:loguru"],
    }),
    alwayslink = False,
)

cc_library(
    name = "Logging",
    deps = [":logging_lib"],
    visibility = ["//visibility:public"],
)
