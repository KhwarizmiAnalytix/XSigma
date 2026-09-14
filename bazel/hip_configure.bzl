"""HIP/ROCm external repository for WORKSPACE — resolves install path on Linux
(mirrors CMake's find_package(hip), ThirdParty/Parallel/Cmake/hip.cmake... actually
Library/Memory/Cmake/hip.cmake).

HIP/ROCm is Unix-only in this project (hip.cmake fails fast on WIN32) -- this
rule does the same: it only probes on Linux, matching Memory's actual HIP
usage, which is host-side runtime linking only (gpu/gpu_runtime.h reuses the
CUDA allocator implementation with HIP API spellings; there's no separate
device-language .hip source needing hipcc in this codebase), so exposing the
ROCm runtime as a plain cc_library -- the same shape as cuda_configure.bzl's
:cudart -- is sufficient; no device-code compilation support is needed here.

Priority:
  1. ROCM_PATH or HIP_PATH (environment), ignored if the path is /usr
     (dirname of the apt hipcc alternatives wrapper) or lacks HIP headers
  2. Linux: /opt/rocm, then /opt/rocm-*

Not verified against a real ROCm install (none available in this repo's
development environment) -- verified only for the not-found fail-fast path,
the same bar bazel/sleef_configure.bzl's fail-fast path was held to.
"""

def _is_windows(repository_ctx):
    name = repository_ctx.os.name.lower()
    return name == "windows" or name.startswith("win")

def _is_bogus_rocm_root(path):
    # /usr/bin/hipcc is an alternatives wrapper; dirname(hipcc) => /usr is not an SDK.
    return path in ("/usr", "/usr/local", "/")

def _is_rocm_sdk(repository_ctx, root):
    """True if `root` looks like a ROCm install (headers or hip-config.cmake)."""
    if not root or _is_bogus_rocm_root(root):
        return False
    if not repository_ctx.path(root).exists:
        return False
    markers = (
        "/include/hip/hip_runtime.h",
        "/lib/cmake/hip/hip-config.cmake",
        "/lib64/cmake/hip/hip-config.cmake",
        "/hip/lib/cmake/hip/hip-config.cmake",
        "/hip/include/hip/hip_runtime.h",
    )
    for suffix in markers:
        if repository_ctx.path(root + suffix).exists:
            return True
    return False

def _resolve_rocm_path(repository_ctx):
    candidates = []
    env = repository_ctx.os.environ.get("ROCM_PATH") or repository_ctx.os.environ.get("HIP_PATH")
    if env:
        candidates.append(env.replace("\\", "/").strip().rstrip("/"))
    candidates.append("/opt/rocm")

    opt = repository_ctx.path("/opt")
    if opt.exists:
        for d in opt.readdir():
            name = d.basename
            if name.startswith("rocm"):
                candidates.append("/opt/" + name)

    for root in candidates:
        if _is_rocm_sdk(repository_ctx, root):
            return root
    return None

_SETUP_HINT = (
    "HIP/ROCm (--define memory_enable_hip=true or --define vectorization_enable_hip=true) " +
    "requires the ROCm toolkit. Install ROCm (https://rocm.docs.amd.com) to the default " +
    "/opt/rocm location, or set ROCM_PATH/HIP_PATH to your install root. HIP/ROCm is " +
    "Unix-only in this project (matches Library/Memory/Cmake/hip.cmake's and " +
    "Library/Vectorization/CMakeLists.txt's own WIN32 fail-fast) -- use " +
    "MEMORY_GPU_BACKEND=cuda / VECTORIZATION_GPU_BACKEND=cuda on Windows."
)

_MISSING_BUILD_FILE = """\
package(default_visibility = ["//visibility:public"])

genrule(
    name = "hip_missing",
    outs = ["hip_missing.cc"],
    cmd = "echo HIP_NOT_FOUND_SEE_MESSAGE_ABOVE >&2; exit 1",
    message = {message},
)

cc_library(
    name = "hip",
    srcs = [":hip_missing"],
)
""".format(message = repr(_SETUP_HINT))

_FOUND_BUILD_TEMPLATE = """\
package(default_visibility = ["//visibility:public"])

# libamdhip64 DT_NEEDED (ROCm 6.x) includes librocprofiler-register,
# libhsa-runtime64, libamd_comgr, and libhsakmt. Keep them next to
# libamdhip64 so $ORIGIN rpath works when LD_LIBRARY_PATH is unset.
cc_library(
    name = "hip",
    srcs = glob([
        "rocm/lib/libamdhip64.so*",
        "rocm/lib/libroctx64.so*",
        "rocm/lib/libroctracer64.so*",
        "rocm/lib/librocprofiler-register.so*",
        "rocm/lib/libhsa-runtime64.so*",
        "rocm/lib/libamd_comgr.so*",
        "rocm/lib/libhsakmt.so*",
        "rocm/lib64/libamdhip64.so*",
        "rocm/lib64/libroctx64.so*",
        "rocm/lib64/librocprofiler-register.so*",
        "rocm/lib64/libhsa-runtime64.so*",
        "rocm/hip/lib/libamdhip64.so*",
    ], allow_empty = True),
    hdrs = glob([
        {hdr_globs}
    ], allow_empty = True),
    includes = [
        {includes}
    ],
    defines = ["__HIP_PLATFORM_AMD__=1"],
    linkopts = ["-Wl,-rpath,$$ORIGIN"],
)
"""

def _hip_configure_impl(repository_ctx):
    if _is_windows(repository_ctx):
        repository_ctx.file("BUILD.bazel", _MISSING_BUILD_FILE)
        return

    rocm_path = _resolve_rocm_path(repository_ctx)
    if not rocm_path:
        repository_ctx.file("BUILD.bazel", _MISSING_BUILD_FILE)
        return

    root = repository_ctx.path(rocm_path)
    if not root.exists:
        repository_ctx.file("BUILD.bazel", _MISSING_BUILD_FILE)
        return

    repository_ctx.symlink(root, "rocm")

    hdr_globs = []
    includes = []
    for rel in ("include", "hip/include"):
        if repository_ctx.path(rocm_path + "/" + rel).exists:
            hdr_globs.append('"rocm/' + rel + '/**/*.h"')
            hdr_globs.append('"rocm/' + rel + '/**/*.hpp"')
            includes.append('"rocm/' + rel + '"')
    for rel in ("include/roctracer", "include/hip"):
        if repository_ctx.path(rocm_path + "/" + rel).exists:
            includes.append('"rocm/' + rel + '"')
    if not hdr_globs:
        repository_ctx.file("BUILD.bazel", _MISSING_BUILD_FILE)
        return

    repository_ctx.file(
        "BUILD.bazel",
        _FOUND_BUILD_TEMPLATE.format(
            hdr_globs = ",\n        ".join(hdr_globs),
            includes = ",\n        ".join(includes),
        ),
    )

hip_configure = repository_rule(
    implementation = _hip_configure_impl,
    environ = ["ROCM_PATH", "HIP_PATH"],
)
