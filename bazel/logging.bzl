load("//bazel:xsigma.bzl", "xsigma_copts", "xsigma_defines", "xsigma_linkopts")

# C++ standard for Logging — mirrors CMake LOGGING_CXX_STANDARD (default: 20)
LOGGING_CXX_STD = "c++20"

def logging_copts():
    return xsigma_copts(cxx_std = LOGGING_CXX_STD)

def logging_defines():
    """Compile definitions for @logging. Native product pipeline only."""
    defines = xsigma_defines()
    defines += [
        "LOGGING_HAS_NATIVE=1",
        "LOGGING_HAS_LOGURU=0",
        "LOGGING_HAS_GLOG=0",
        "LOGGING_HAS_SPDLOG=0",
        "LOGGING_HAS_MAGICENUM=0",
    ]
    defines += select({
        "@xsigma//bazel:disable_logging_cxa_demangle": ["LOGGING_HAS_CXA_DEMANGLE=0"],
        "@platforms//os:windows": ["LOGGING_HAS_CXA_DEMANGLE=0"],
        "//conditions:default": ["LOGGING_HAS_CXA_DEMANGLE=1"],
    })
    defines += select({
        "@xsigma//bazel:logging_portable_float_format": ["LOGGING_PORTABLE_FLOAT_FORMAT=1"],
        "//conditions:default": ["LOGGING_PORTABLE_FLOAT_FORMAT=0"],
    })
    defines += select({
        "@xsigma//bazel:logging_std_format": ["LOGGING_FORMAT_USE_STD=1"],
        "//conditions:default": ["LOGGING_FORMAT_USE_STD=0"],
    })
    defines += select({
        "@xsigma//bazel:logging_default_log_fatal": ["LOGGING_DEFAULT_EXCEPTION_MODE_LOG_FATAL=1"],
        "//conditions:default": ["LOGGING_DEFAULT_EXCEPTION_MODE_LOG_FATAL=0"],
    })
    return defines

def logging_linkopts():
    return xsigma_linkopts()
