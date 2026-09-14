load("//bazel:xsigma.bzl", "xsigma_copts", "xsigma_defines", "xsigma_enzyme_copts", "xsigma_enzyme_linkopts", "xsigma_linkopts")

# C++ standard for Core — mirrors CMake CORE_CXX_STANDARD (default: 20)
CORE_CXX_STD = "c++20"

def core_copts():
    return xsigma_copts(cxx_std = CORE_CXX_STD)

def core_defines():
    """Returns compile definitions for Library/Core.

    Mirrors Library/Core/CMakeLists.txt CORE_HAS_* and CORE_* flags.
    """
    defines = xsigma_defines()

    # SIMD instruction-set tokens — CORE_SSE/AVX/AVX2/AVX512. CMake sets these from
    # PROJECT_SSE/AVX/AVX2/AVX512 (Cmake/tools/utils.cmake), which mirror whichever single
    # VECTORIZATION_CPU_BACKEND tier is active. Reuse the same vectorization_type_* tier
    # config_settings Vectorization already defines (bazel/BUILD.bazel) instead of adding a
    # parallel set of Core-only settings.
    defines += select({
        "//bazel:vectorization_type_sse": ["CORE_SSE=1"],
        "//conditions:default": ["CORE_SSE=0"],
    })
    defines += select({
        "//bazel:vectorization_type_avx": ["CORE_AVX=1"],
        "//conditions:default": ["CORE_AVX=0"],
    })
    defines += select({
        "//bazel:vectorization_type_avx2": ["CORE_AVX2=1"],
        "//conditions:default": ["CORE_AVX2=0"],
    })
    defines += select({
        "//bazel:vectorization_type_avx512": ["CORE_AVX512=1"],
        "//conditions:default": ["CORE_AVX512=0"],
    })

    # std::exception_ptr availability — CORE_HAS_EXCEPTION_PTR. CMake probes this with
    # check_cxx_source_compiles (Cmake/tools/utils.cmake); fixed to 1 here since every
    # compiler this project's Bazel setup targets (MSVC 2019+/Clang/GCC, all C++20) supports
    # std::exception_ptr — the probe result is always 1 in practice.
    defines += ["CORE_HAS_EXCEPTION_PTR=1"]

    # MKL — CORE_HAS_MKL
    defines += select({
        "//bazel:enable_mkl": ["CORE_HAS_MKL=1"],
        "//conditions:default": ["CORE_HAS_MKL=0"],
    })

    # ROCm — CORE_HAS_ROCM
    defines += select({
        "//bazel:enable_rocm": ["CORE_HAS_ROCM=1"],
        "//conditions:default": ["CORE_HAS_ROCM=0"],
    })

    # Experimental API gate — CORE_HAS_EXPERIMENTAL
    defines += select({
        "//bazel:enable_experimental": ["CORE_HAS_EXPERIMENTAL=1"],
        "//conditions:default": ["CORE_HAS_EXPERIMENTAL=0"],
    })

    # Google Test availability — CORE_HAS_GTEST (CMake CORE_ENABLE_GTEST default ON)
    defines += select({
        "//bazel:disable_gtest": ["CORE_HAS_GTEST=0"],
        "//conditions:default": ["CORE_HAS_GTEST=1"],
    })

    # LU pivoting — CORE_LU_PIVOTING (only defined when ON, matching CMake)
    defines += select({
        "//bazel:lu_pivoting": ["CORE_LU_PIVOTING=1"],
        "//conditions:default": [],
    })

    # Sobol 1111-dim — CORE_SOBOL_1111 (defined when ON, absent when OFF, matching CMake)
    defines += select({
        "//bazel:disable_sobol_1111": [],
        "//conditions:default": ["CORE_SOBOL_1111=1"],
    })

    # Enzyme AD — CORE_HAS_ENZYME
    defines += select({
        "//bazel:enable_enzyme": ["CORE_HAS_ENZYME=1"],
        "//conditions:default": ["CORE_HAS_ENZYME=0"],
    })

    # Compression — CORE_HAS_COMPRESSION / CORE_COMPRESSION_TYPE_SNAPPY
    defines += select({
        "//bazel:enable_compression_snappy": [
            "CORE_HAS_COMPRESSION=1",
            "CORE_COMPRESSION_TYPE_SNAPPY=1",
        ],
        "//bazel:enable_compression": [
            "CORE_HAS_COMPRESSION=1",
            "CORE_COMPRESSION_TYPE_SNAPPY=0",
        ],
        "//conditions:default": [
            "CORE_HAS_COMPRESSION=0",
            "CORE_COMPRESSION_TYPE_SNAPPY=0",
        ],
    })

    return defines

def core_linkopts():
    return xsigma_linkopts()

def core_enzyme_copts():
    return xsigma_enzyme_copts()

def core_enzyme_linkopts():
    return xsigma_enzyme_linkopts()
