load("//bazel:xsigma.bzl", "xsigma_copts", "xsigma_defines", "xsigma_linkopts")

# C++ standard for Profiler — mirrors CMake PROFILER_CXX_STANDARD (default: 20)
PROFILER_CXX_STD = "c++20"

def profiler_copts():
    return xsigma_copts(cxx_std = PROFILER_CXX_STD)

def profiler_defines():
    """Returns compile definitions for the ThirdParty Profiler package.

    Mirrors ThirdParty/Profiler/CMakeLists.txt: PROFILER_HAS_* flags.
    Project-wide PROJECT_HAS_* flags are included via xsigma_defines().
    """
    defines = xsigma_defines()

    # Instrumentation backend — mutually exclusive; default KINETO (matches CMake
    # PROFILER_BACKEND default). PROFILER_HAS_KINETO / PROFILER_HAS_ITT
    defines += select({
        "@xsigma//bazel:enable_itt": [
            "PROFILER_HAS_ITT=1",
            "PROFILER_HAS_KINETO=0",
        ],
        "//conditions:default": [
            "PROFILER_HAS_KINETO=1",
            "PROFILER_HAS_ITT=0",
        ],
    })

    # Native pipeline (traceme/xplane/host_tracer/profiler_session) is always compiled
    # alongside whichever instrumentation backend is selected above — no HAS_* gate.

    # PROFILER_HAS_CUDA / PROFILER_HAS_HIP — independent of backend selection
    # above, and of each other's build (MEMORY_GPU_BACKEND only ever selects
    # one GPU vendor). Both gate bespoke/base/cuda.cpp's event-fallback stub
    # (generalized to also serve HIP via bespoke/base/gpu_runtime.h) and
    # profiler_kineto.h's hasGPU(). Mirrors CMakeLists.txt's
    # find_package(CUDAToolkit) / find_package(hip) gates.
    defines += select({
        # Match CMake: prefer the NVTX C API (nvToolsExt.h / CUDA::nvToolsExt).
        # CUDA 12's cuda-nvtx package often has no nvtx3.hpp, so forcing
        # PROFILER_CUDA_USE_NVTX3=1 fails the Bazel CUDA compile.
        "@xsigma//bazel:enable_cuda": [
            "PROFILER_HAS_CUDA=1",
            "PROFILER_HAS_NVTX=1",
        ],
        "//conditions:default": ["PROFILER_HAS_CUDA=0", "PROFILER_HAS_NVTX=0"],
    })
    defines += select({
        # Roctracer/ROCTX is optional; CI's hiplibsdk often has HIP runtime
        # without roctx.h. CMake sets PROFILER_HAS_ROCTX only when find_library
        # succeeds — keep Bazel at 0 so cuda.cpp uses the no-op markers.
        "@xsigma//bazel:enable_hip": ["PROFILER_HAS_HIP=1", "PROFILER_HAS_ROCTX=0"],
        "//conditions:default": ["PROFILER_HAS_HIP=0", "PROFILER_HAS_ROCTX=0"],
    })
    defines += select({
        "@xsigma//bazel:enable_metal": ["PROFILER_HAS_METAL=1"],
        "//conditions:default": ["PROFILER_HAS_METAL=0"],
    })

    return defines

def profiler_linkopts():
    return xsigma_linkopts() + select({
        "@xsigma//bazel:enable_metal": ["-framework", "Metal", "-framework", "Foundation"],
        "//conditions:default": [],
    }) + select({
        # nvtx3.hpp dlopens the injector; FindCUDAToolkit's CUDA::nvtx3
        # target adds CMAKE_DL_LIBS for the same reason. Linux-only: -ldl
        # is invalid on Windows and redundant on Apple.
        "@platforms//os:linux": ["-ldl"],
        "//conditions:default": [],
    })
