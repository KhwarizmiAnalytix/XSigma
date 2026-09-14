# =============================================================================
# cpuinfo Library BUILD Configuration
# =============================================================================
# CPU feature detection library — XSigma-owned overlay for the vendored
# ThirdParty/cpuinfo submodule, consumed as @cpuinfo (new_local_repository in
# WORKSPACE.bazel).
#
# The submodule's own in-tree BUILD.bazel is NOT used: it assumes an external
# @cpuinfo repo layout (-Iexternal/cpuinfo/include) and, when built in-tree,
# resolves <cpuinfo.h> from system include paths (/usr/local/include), which
# breaks whenever the system header is older than the vendored sources.
#
# Source selection mirrors the platform/arch split in the submodule's own
# BUILD.bazel (TensorFlow-style explicit lists), expressed with globs so the
# overlay keeps working when the vendored sources add/remove files.
# =============================================================================

package(default_visibility = ["//visibility:public"])

# Common, platform-independent sources (src/api.c, src/cache.c, src/init.c, ...).
_COMMON_SRCS = glob(["src/*.c"])

# Architecture-specific sources (platform subdirectories excluded by glob depth).
_X86_SRCS = glob(
    [
        "src/x86/*.c",
        "src/x86/cache/*.c",
    ],
    exclude = ["src/x86/mockcpuid.c"],
)

# src/arm/tlb.c is a source fragment (starts mid-function with `switch (uarch)`)
# that upstream never lists as a compiled source — exclude it.
_ARM_SRCS = glob(
    ["src/arm/*.c"],
    exclude = ["src/arm/tlb.c"],
)

_RISCV_SRCS = glob(["src/riscv/*.c"])

# Platform-specific sources. mockfile.c is test-only (needs cpuinfo-mock.h).
_LINUX_SRCS = glob(
    ["src/linux/*.c"],
    exclude = ["src/linux/mockfile.c"],
)

_MACH_SRCS = ["src/mach/topology.c"]

# Platform + architecture sources.
_X86_LINUX_SRCS = glob(["src/x86/linux/*.c"])

# Android properties.c needs <sys/system_properties.h>; do not compile it on
# linux_arm64 (ubuntu-24.04-arm). Upstream lists ANDROID_ARM_SRCS separately.
_ARM_LINUX_SRCS = glob(["src/arm/linux/*.c"])

_RISCV_LINUX_SRCS = glob(["src/riscv/linux/*.c"])

_X86_MACH_SRCS = glob(["src/x86/mach/*.c"])

_ARM_MACH_SRCS = glob(["src/arm/mach/*.c"])

_X86_WINDOWS_SRCS = glob(["src/x86/windows/*.c"])

_ARM_WINDOWS_SRCS = glob(["src/arm/windows/*.c"])

config_setting(
    name = "linux_x86_64",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
)

config_setting(
    name = "linux_arm64",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:arm64",
    ],
)

config_setting(
    name = "linux_riscv64",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:riscv64",
    ],
)

config_setting(
    name = "macos_x86_64",
    constraint_values = [
        "@platforms//os:macos",
        "@platforms//cpu:x86_64",
    ],
)

config_setting(
    name = "macos_arm64",
    constraint_values = [
        "@platforms//os:macos",
        "@platforms//cpu:arm64",
    ],
)

config_setting(
    name = "windows_x86_64",
    constraint_values = [
        "@platforms//os:windows",
        "@platforms//cpu:x86_64",
    ],
)

config_setting(
    name = "windows_arm64",
    constraint_values = [
        "@platforms//os:windows",
        "@platforms//cpu:arm64",
    ],
)

cc_library(
    name = "cpuinfo",
    srcs = _COMMON_SRCS + select({
        ":linux_x86_64": _X86_SRCS + _LINUX_SRCS + _X86_LINUX_SRCS,
        ":linux_arm64": _ARM_SRCS + _LINUX_SRCS + _ARM_LINUX_SRCS,
        ":linux_riscv64": _RISCV_SRCS + _LINUX_SRCS + _RISCV_LINUX_SRCS,
        ":macos_x86_64": _X86_SRCS + _MACH_SRCS + _X86_MACH_SRCS,
        ":macos_arm64": _ARM_SRCS + _MACH_SRCS + _ARM_MACH_SRCS,
        ":windows_x86_64": _X86_SRCS + _X86_WINDOWS_SRCS,
        ":windows_arm64": _ARM_SRCS + _ARM_WINDOWS_SRCS,
        "//conditions:default": [],
    }),
    hdrs = glob(
        [
            "include/*.h",
            "include/cpuinfo/*.h",
            "src/**/*.h",
            "deps/clog/include/*.h",
        ],
        # include/cpuinfo/ does not exist in the vendored cpuinfo (single
        # include/cpuinfo.h) — keep the pattern for other versions. The
        # vendored deps/clog is header-only (include/clog.h, no src/).
        allow_empty = True,
    ),
    copts = select({
        "@platforms//os:windows": [],
        "//conditions:default": [
            "-w",  # Suppress warnings for third-party code
            # sched.h's CPU_SETSIZE is GNU; src/linux/processors.c needs it.
            "-D_GNU_SOURCE=1",
        ],
    }) + [
        # Force -I (not -isystem) for our own headers: Apple clang's driver injects
        # /usr/local/include AHEAD of command-line -isystem paths, and this machine
        # has a stale /usr/local/include/cpuinfo.h that would otherwise shadow the
        # vendored header. Mirrors the submodule's own BUILD.bazel (-Iexternal/...).
        "-Iexternal/cpuinfo/include",
        "-Iexternal/cpuinfo/src",
        "-Iexternal/cpuinfo/deps/clog/include",
    ],
    defines = [
        "CPUINFO_LOG_LEVEL=2",  # Set log level (0=none, 1=error, 2=warning, 3=info, 4=debug)
    ],
    # NOTE: no `includes` attribute on purpose. `includes` generates -isystem paths,
    # and Apple clang's driver injects -I/usr/local/include ahead of -isystem; a
    # stale /usr/local/include/cpuinfo.h on the host would then shadow the vendored
    # header. Worse, the -isystem entries would make our copts' -I flags below get
    # dropped as "duplicates". Consumers that include <cpuinfo.h> (Library/Core)
    # add the same -I copt themselves.
    linkopts = select({
        "@platforms//os:windows": [],
        "@platforms//os:macos": [],
        "//conditions:default": ["-lpthread"],
    }),
    linkstatic = True,
)
