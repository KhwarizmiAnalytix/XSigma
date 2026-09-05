# =============================================================================
# Library/Profiler —
# CMakeLists.txt
#
# Activity tracing, timing primitives, and pluggable profiler-backend support (Kineto, Intel
# ITT/VTune) layered on top of an always-on native (traceme/xplane) pipeline.
#
# Public compile definitions: PROFILER_HAS_KINETO=1/0  — Kineto (PyTorch-compatible) backend active
# PROFILER_HAS_ITT=1/0     — Intel ITT/VTune backend active (mutually exclusive with Kineto)
# The native (traceme/xplane) pipeline is always compiled — no PROFILER_HAS_NATIVE gate.
# =============================================================================
cmake_minimum_required(VERSION 3.16)

# --- Early-exit gate --- When PROFILER_INCLUDE_GATE_ONLY=ON, only set PROFILER_ENABLE_KINETO and
# return early so the root can gate ThirdParty/Kineto before add_subdirectory runs.
if(PROFILER_INCLUDE_GATE_ONLY)
  set(PROFILER_BACKEND "KINETO" CACHE STRING
                                      "Profiler instrumentation backend. Options: KINETO, ITT"
  )
  set_property(CACHE PROFILER_BACKEND PROPERTY STRINGS KINETO ITT)
  if(PROFILER_BACKEND STREQUAL "KINETO")
    set(PROFILER_ENABLE_KINETO ON)
  else()
    set(PROFILER_ENABLE_KINETO OFF)
  endif()
  return()
endif()

# --- Section 1: Feature flags (PROFILER_ENABLE_*) and backend selector --- PROFILER_BACKEND is the
# single control point; derived booleans are mutually exclusive.

# Link-Time Optimization — disabled when PROFILER_ENABLE_COVERAGE or PROFILER_ENABLE_SANITIZER is ON
# (LTO conflicts with instrumentation / sanitizers).
include(lto)
xsigma_lto_compute_default(_lto_default PROFILE SUPPORT)
set(PROFILER_LTO_MODE "${_lto_default}"
    CACHE STRING "LTO mode for Profiler: off | thin | full | ipo | auto"
)
set_property(CACHE PROFILER_LTO_MODE PROPERTY STRINGS off thin full ipo auto)

# Coverage instrumentation — activates -fprofile-instr-generate / --coverage compiler flags for
# this module only. LTO is automatically skipped when coverage is enabled.
option(PROFILER_ENABLE_COVERAGE "Enable coverage instrumentation for Profiler tests" OFF)

# Testing — gates add_subdirectory(Testing/Cxx).
option(PROFILER_ENABLE_TESTING "Build Profiler test suite" ON)

# LibTorch (PyTorch C++ profiler) in ProfilerCxxTests. setup.py `torch` sets this
# (and VECTORIZATION_ENABLE_LIBTORCH / MEMORY_ENABLE_LIBTORCH). When the Vectorization
# flag is already on in a full-tree configure, default to the same value.
if(DEFINED VECTORIZATION_ENABLE_LIBTORCH)
  set(_profiler_libtorch_default ${VECTORIZATION_ENABLE_LIBTORCH})
else()
  set(_profiler_libtorch_default OFF)
endif()
option(PROFILER_ENABLE_LIBTORCH "Enable LibTorch (PyTorch C++) profiler in ProfilerCxxTests"
       ${_profiler_libtorch_default}
)
unset(_profiler_libtorch_default)

# Examples — gates the Profiling examples under Examples/Profiling.
option(PROFILER_ENABLE_EXAMPLES "Build Profiler example programs" OFF)

# Google Test integration for Profiler tests.
option(PROFILER_ENABLE_GTEST "Enable GoogleTest for Profiler" ON)

# Google Benchmark integration for Profiler micro-benchmarks.
option(PROFILER_ENABLE_BENCHMARK "Enable Google Benchmark for Profiler" ON)

# Icecream distributed compilation launcher (rarely needed; hidden by default).
option(PROFILER_ENABLE_ICECC "Use Icecream (icecc) distributed compiler for Profiler" OFF)
mark_as_advanced(PROFILER_ENABLE_ICECC)

# Per-target compiler cache — wraps every compile command with ccache / sccache etc. to speed up
# incremental and CI rebuilds. ON by default.
option(PROFILER_ENABLE_CACHE "Enable compiler caching for the Profiler target" ON)
mark_as_advanced(PROFILER_ENABLE_CACHE)

option(PROFILER_ENABLE_CLANGTIDY "Enable clang-tidy static analysis for Profiler" OFF)
mark_as_advanced(PROFILER_ENABLE_CLANGTIDY)
option(PROFILER_ENABLE_FIX "Enable clang-tidy fix-errors and fix options for Profiler" OFF)
mark_as_advanced(PROFILER_ENABLE_FIX)
option(PROFILER_ENABLE_IWYU "Enable include-what-you-use analysis for Profiler" OFF)
mark_as_advanced(PROFILER_ENABLE_IWYU)
option(PROFILER_ENABLE_SANITIZER "Build Profiler with sanitizer support (Clang/GCC only)" OFF)
set(PROFILER_SANITIZER_TYPE "address"
    CACHE STRING "Sanitizer type for Profiler. Options: address, undefined, thread, memory, leak"
)
set_property(CACHE PROFILER_SANITIZER_TYPE PROPERTY STRINGS address undefined thread memory leak)
mark_as_advanced(PROFILER_ENABLE_SANITIZER PROFILER_SANITIZER_TYPE)
option(PROFILER_ENABLE_SPELL "Enable check-only spell checking for Profiler" OFF)
mark_as_advanced(PROFILER_ENABLE_SPELL)
option(PROFILER_ENABLE_VALGRIND "Execute Profiler test suite with Valgrind" OFF)
mark_as_advanced(PROFILER_ENABLE_VALGRIND)
set(PROFILER_LINKER_CHOICE "default"
    CACHE STRING "Linker for Profiler: default, lld, mold, gold, lld-link"
)
set_property(CACHE PROFILER_LINKER_CHOICE PROPERTY STRINGS default lld mold gold lld-link)
mark_as_advanced(PROFILER_LINKER_CHOICE)
set(PROFILER_CACHE_BACKEND "none"
    CACHE STRING "Compiler cache backend for Profiler. Options: none, ccache, sccache, buildcache"
)
set_property(CACHE PROFILER_CACHE_BACKEND PROPERTY STRINGS none ccache sccache buildcache)
mark_as_advanced(PROFILER_CACHE_BACKEND)

# Backend selector — the single control point for the *instrumentation* backend layered on top of
# the always-on native profiler (traceme/xplane/host_tracer/profiler_session — see Section 2 and
# the unconditional source-discovery block below). Derived booleans (PROFILER_ENABLE_KINETO etc.)
# are set immediately below. KINETO — full PyTorch-compatible activity tracing (default) ITT    —
# Intel Instrumentation and Tracing Technology / VTune
set(PROFILER_BACKEND "KINETO" CACHE STRING "Profiler instrumentation backend. Options: KINETO, ITT")
set_property(CACHE PROFILER_BACKEND PROPERTY STRINGS KINETO ITT)
if(NOT PROFILER_BACKEND MATCHES "^(KINETO|ITT)$")
  message(FATAL_ERROR "Invalid PROFILER_BACKEND '${PROFILER_BACKEND}'. Valid options: KINETO, ITT")
endif()

# Derive mutually-exclusive enable booleans from the backend selector.
if(PROFILER_BACKEND STREQUAL "KINETO")
  set(PROFILER_ENABLE_KINETO ON)
  set(PROFILER_ENABLE_ITT OFF)
else()
  set(PROFILER_ENABLE_KINETO OFF)
  set(PROFILER_ENABLE_ITT ON)
endif()

# Native pipeline (traceme/xplane/host_tracer/profiler_session) is always compiled alongside
# whichever of Kineto/ITT is selected above — it is no longer a backend choice.
set(PROFILER_ENABLE_NATIVE_PROFILER ON)

# C++ standard — applied to every TU in this module via CMAKE_CXX_STANDARD.
set(PROFILER_CXX_STANDARD "20" CACHE STRING "C++ standard for Profiler. Options: 11 14 17 20 23")
set_property(CACHE PROFILER_CXX_STANDARD PROPERTY STRINGS 11 14 17 20 23)
if(NOT PROFILER_CXX_STANDARD MATCHES "^(11|14|17|20|23)$")
  message(FATAL_ERROR "PROFILER_CXX_STANDARD must be one of: 11 14 17 20 23")
endif()

# --- Section 2: compile-definition accumulator --- PROFILER_HAS_KINETO / HAS_ITT
# are appended after dependency discovery (Kineto/ITT may be forced OFF if missing).
# Native (traceme/xplane) is always compiled and needs no HAS_* gate.
set(PROFILER_DEPENDENCY_COMPILE_DEFINITIONS ${PROJECT_DEPENDENCY_COMPILE_DEFINITIONS})

# Native Metal GPU tracer (command-buffer GPUStartTime → `/device:GPU:N`). Independent of
# Kineto/CUPTI. Matches Memory's MEMORY_GPU_BACKEND=metal gate.
set(PROFILER_HAS_METAL 0)
if(APPLE AND MEMORY_GPU_BACKEND STREQUAL "metal")
  set(PROFILER_HAS_METAL 1)
endif()
list(APPEND PROFILER_DEPENDENCY_COMPILE_DEFINITIONS PROFILER_HAS_METAL=${PROFILER_HAS_METAL})

# --- Section 3: CMake module includes --- Order: introspection → toolchain helpers →
# coverage/sanitizer → LTO/linker.

# a) Standard CMake introspection
include(CheckCXXSourceCompiles)
include(CheckCXXSourceRuns)
include(CheckSymbolExists)

# b) Shared toolchain helpers
include(compiler_checks) # Detects compiler capabilities; sets PROJECT_* flags
include(checks) # Additional feature-check macros
include(build_type) # Validates / normalises CMAKE_BUILD_TYPE
include(platform) # Platform flags (macOS rpath, Windows /utf-8, …)
include(CMakeDependentOption)

include(cache) # Configures per-target compiler cache launcher

if(PROFILER_ENABLE_SANITIZER)
  include(sanitize)
endif()
if(PROFILER_ENABLE_SPELL)
  include(spell)
endif()
if(PROFILER_ENABLE_VALGRIND)
  include(valgrind)
endif()
include(helper_macros)

# c) Coverage gate — appends -fprofile-instr-generate / --coverage; LTO already cleared above.
if(PROFILER_ENABLE_COVERAGE)
  include(coverage)
elseif(MSVC)
  string(APPEND CMAKE_EXE_LINKER_FLAGS " /DEBUG:FULL")
  string(APPEND CMAKE_SHARED_LINKER_FLAGS " /DEBUG:FULL")
endif()

# --- Third-party dependencies owned by Profiler ---
set(_tpdir "${CMAKE_SOURCE_DIR}/ThirdParty")

set(BUILD_TESTING OFF CACHE BOOL "Disable testing for third-party libraries" FORCE)
set(BUILD_EXAMPLES OFF CACHE BOOL "Disable examples for third-party libraries" FORCE)
set(BUILD_BENCHMARKS OFF CACHE BOOL "Disable benchmarks for third-party libraries" FORCE)

# Kineto: configure GPU-backend knobs before building the library.
if(PROFILER_ENABLE_KINETO)
  set(LIBKINETO_NOAIUPTI ON CACHE STRING "" FORCE)
  if(NOT MEMORY_GPU_BACKEND STREQUAL "cuda")
    set(LIBKINETO_NOCUPTI ON CACHE STRING "" FORCE)
  else()
    set(LIBKINETO_NOCUPTI OFF CACHE STRING "" FORCE)
    message(STATUS "Using Kineto with CUPTI support")
  endif()

  # CUDA runtime + NVTX for the profiler's own CUDA event-fallback stub
  # (bespoke/base/cuda.cpp, used when full CUPTI activity tracing isn't
  # available) and for the PROFILER_HAS_CUDA guard in
  # bespoke/kineto/profiler_kineto.h -- independent of the CUPTI gate above.
  set(PROFILER_HAS_CUDA 0)
  if(MEMORY_GPU_BACKEND STREQUAL "cuda")
    find_package(CUDAToolkit QUIET)
    if(CUDAToolkit_FOUND)
      set(PROFILER_HAS_CUDA 1)
      list(APPEND PROFILER_DEPENDENCY_LIBS CUDA::cudart)
      set(PROFILER_HAS_NVTX 0)
      if(TARGET CUDA::nvToolsExt)
        list(APPEND PROFILER_DEPENDENCY_LIBS CUDA::nvToolsExt)
        set(PROFILER_HAS_NVTX 1)
      else()
        # CMake's FindCUDAToolkit creates CUDA::nvtx3 unconditionally whenever
        # CUDA >= 10.0 is found -- it does not verify that nvtx3/nvtx3.hpp
        # actually exists on disk (some Windows installs, e.g. the network
        # installer's silent full install, can omit the NVTX headers). Check
        # for the header ourselves before trusting the target.
        set(_profiler_nvtx3_header_found 0)
        foreach(_nvtx_inc IN LISTS CUDAToolkit_INCLUDE_DIRS)
          if(EXISTS "${_nvtx_inc}/nvtx3/nvtx3.hpp")
            set(_profiler_nvtx3_header_found 1)
            break()
          endif()
        endforeach()
        unset(_nvtx_inc)
        if(TARGET CUDA::nvtx3 AND _profiler_nvtx3_header_found)
          list(APPEND PROFILER_DEPENDENCY_LIBS CUDA::nvtx3)
          list(APPEND PROFILER_DEPENDENCY_COMPILE_DEFINITIONS PROFILER_CUDA_USE_NVTX3=1)
          set(PROFILER_HAS_NVTX 1)
        else()
          find_library(
            PROFILER_NVTOOLSEXT_LIBRARY
            NAMES nvToolsExt nvToolsExt64_1
            HINTS ${CUDAToolkit_LIBRARY_DIR} ${CUDAToolkit_LIBRARY_ROOT}
            PATH_SUFFIXES lib lib64 lib/x64
          )
          if(PROFILER_NVTOOLSEXT_LIBRARY)
            list(APPEND PROFILER_DEPENDENCY_LIBS ${PROFILER_NVTOOLSEXT_LIBRARY})
            set(PROFILER_HAS_NVTX 1)
          elseif(_profiler_nvtx3_header_found)
            list(APPEND PROFILER_DEPENDENCY_COMPILE_DEFINITIONS PROFILER_CUDA_USE_NVTX3=1)
            if(CMAKE_DL_LIBS)
              list(APPEND PROFILER_DEPENDENCY_LIBS ${CMAKE_DL_LIBS})
            endif()
            set(PROFILER_HAS_NVTX 1)
          endif()
        endif()
        unset(_profiler_nvtx3_header_found)
      endif()
      list(APPEND PROFILER_DEPENDENCY_COMPILE_DEFINITIONS PROFILER_HAS_NVTX=${PROFILER_HAS_NVTX})
      message(STATUS "Profiler: CUDA Toolkit found -- enabling PROFILER_HAS_CUDA"
                     " (NVTX=${PROFILER_HAS_NVTX})"
      )
    else()
      message(STATUS "Profiler: MEMORY_GPU_BACKEND=cuda but CUDA Toolkit was not found by "
                     "find_package(CUDAToolkit) -- PROFILER_HAS_CUDA stays disabled"
      )
    endif()
  endif()
  list(APPEND PROFILER_DEPENDENCY_COMPILE_DEFINITIONS PROFILER_HAS_CUDA=${PROFILER_HAS_CUDA})

  # HIP runtime for the profiler's own event-fallback stub (bespoke/base/cuda.cpp,
  # generalized to also serve HIP via bespoke/base/gpu_runtime.h) and for the
  # PROFILER_HAS_HIP guard in bespoke/kineto/profiler_kineto.h -- independent of
  # the Roctracer gate below. Mirrors the PROFILER_HAS_CUDA block above; mutually
  # exclusive with it since MEMORY_GPU_BACKEND only ever selects one GPU vendor.
  set(PROFILER_HAS_HIP 0)
  if(MEMORY_GPU_BACKEND STREQUAL "hip")
    include(rocm_prefix)
    xsigma_setup_rocm_prefix()
    find_package(hip QUIET)
    if(hip_FOUND)
      set(PROFILER_HAS_HIP 1)
      list(APPEND PROFILER_DEPENDENCY_LIBS hip::host)
      find_library(
        PROFILER_ROCTX_LIBRARY
        NAMES roctx64 roctx
        PATHS "$ENV{ROCM_PATH}" "$ENV{HIP_PATH}" "${ROCM_PATH}" "${HIP_ROOT_DIR}" /opt/rocm
        PATH_SUFFIXES lib lib64
      )
      set(PROFILER_HAS_ROCTX 0)
      if(PROFILER_ROCTX_LIBRARY)
        list(APPEND PROFILER_DEPENDENCY_LIBS ${PROFILER_ROCTX_LIBRARY})
        set(PROFILER_HAS_ROCTX 1)
      endif()
      find_path(
        PROFILER_ROCTX_INCLUDE_DIR
        NAMES roctx.h
        PATHS "$ENV{ROCM_PATH}" "$ENV{HIP_PATH}" "${ROCM_PATH}" "${HIP_ROOT_DIR}" /opt/rocm
        PATH_SUFFIXES include include/roctracer include/roctx
      )
      if(PROFILER_ROCTX_INCLUDE_DIR)
        list(APPEND PROFILER_DEPENDENCY_INCLUDE_DIRS ${PROFILER_ROCTX_INCLUDE_DIR})
      endif()
      list(APPEND PROFILER_DEPENDENCY_COMPILE_DEFINITIONS PROFILER_HAS_ROCTX=${PROFILER_HAS_ROCTX})
      message(STATUS "Profiler: HIP found -- enabling PROFILER_HAS_HIP"
                     " (ROCTX=${PROFILER_HAS_ROCTX})"
      )
    else()
      message(STATUS "Profiler: MEMORY_GPU_BACKEND=hip but find_package(hip) failed -- "
                     "PROFILER_HAS_HIP stays disabled"
      )
    endif()
  endif()
  list(APPEND PROFILER_DEPENDENCY_COMPILE_DEFINITIONS PROFILER_HAS_HIP=${PROFILER_HAS_HIP})

  if(NOT PROFILER_HAS_HIP)
    set(LIBKINETO_NOROCTRACER ON CACHE STRING "" FORCE)
  else()
    # Kineto's KINETO_BACKEND=rocm path requires ROCM_SOURCE_DIR (or
    # ROCTRACER_INCLUDE_DIR) plus rocm-core/rocm_version.h. HIP_PATH=/usr from
    # the apt hipcc wrapper is not an SDK; use the prefix we just resolved.
    if(NOT ROCM_SOURCE_DIR)
      if(XSIGMA_ROCM_PREFIX)
        set(ROCM_SOURCE_DIR "${XSIGMA_ROCM_PREFIX}" CACHE PATH "ROCm SDK root for Kineto roctracer"
                                                          FORCE
        )
      elseif(DEFINED ENV{ROCM_PATH} AND NOT "$ENV{ROCM_PATH}" STREQUAL "/usr")
        set(ROCM_SOURCE_DIR "$ENV{ROCM_PATH}" CACHE PATH "ROCm SDK root for Kineto roctracer" FORCE)
      endif()
    endif()
    set(_profiler_roctracer_ok FALSE)
    if(ROCM_SOURCE_DIR AND EXISTS "${ROCM_SOURCE_DIR}/include/roctracer"
       AND EXISTS "${ROCM_SOURCE_DIR}/include/rocm-core/rocm_version.h"
    )
      set(_profiler_roctracer_ok TRUE)
      set(ROCTRACER_INCLUDE_DIR "${ROCM_SOURCE_DIR}/include/roctracer"
          CACHE PATH "roctracer headers for Kineto" FORCE
      )
    endif()
    if(_profiler_roctracer_ok)
      set(LIBKINETO_NOROCTRACER OFF CACHE STRING "" FORCE)
      set(KINETO_BACKEND "rocm" CACHE STRING "" FORCE)
      message(STATUS "Using Kineto with Roctracer support (ROCM_SOURCE_DIR=${ROCM_SOURCE_DIR})")
    else()
      set(LIBKINETO_NOROCTRACER ON CACHE STRING "" FORCE)
      message(STATUS "Profiler: HIP found but roctracer/rocm-core headers were not "
                     "under ${ROCM_SOURCE_DIR} -- Kineto stays CPU-only"
      )
    endif()
    unset(_profiler_roctracer_ok)
  endif()
  if(LIBKINETO_NOCUPTI AND LIBKINETO_NOROCTRACER AND LIBKINETO_NOXPUPTI)
    message(STATUS "Using CPU-only version of Kineto")
  endif()
  set(KINETO_BUILD_TESTS OFF CACHE BOOL "" FORCE)
  set(KINETO_LIBRARY_TYPE "static" CACHE STRING "" FORCE)
  # Reuse XSigma's fmt build to avoid duplicate symbols.
  set(FMT_SOURCE_DIR "${_tpdir}/fmt" CACHE STRING "Use XSigma's fmt library" FORCE)

  add_third_party_library(
    kineto
    CONDITION
    PROFILER_ENABLE_KINETO
    LIBRARY_TYPE
    STATIC
    SOURCE_DIR
    "${_tpdir}/kineto/libkineto"
    DISABLE_WARNINGS
    FILTER_FLAGS
    "-flto=thin"
    "-flto=full"
    XSIGMA_TARGETS
    "Kineto::kineto=kineto"
    INCLUDE_DIR
    "${_tpdir}/kineto/libkineto/include"
    AUTO_ADD_TO_DEPENDENCIES
    OFF
  )
  foreach(_kineto_target kineto kineto_base kineto_api)
    if(TARGET ${_kineto_target})
      set_property(TARGET ${_kineto_target} PROPERTY POSITION_INDEPENDENT_CODE ON)
    endif()
  endforeach()
  # Clang 20 crashes at -O3 on kineto sources: ReachingDefAnalysis bug on Linux/macOS and
  # fmt-header-only inliner stack overflow on Windows (clang-cl). Downgrade to -O2 for all Clang
  # variants. clang-cl requires the /clang: prefix to pass native Clang driver flags.
  if(TARGET kineto_base AND CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    if(MSVC)
      foreach(_kt kineto_base kineto_api)
        if(TARGET ${_kt})
          target_compile_options(${_kt} PRIVATE /clang:-O2)
        endif()
      endforeach()
    else()
      target_compile_options(kineto_base PRIVATE -O2)
    endif()
  endif()
  if(TARGET kineto AND DEFINED CUDA_nvperf_host_LIBRARY)
    target_link_libraries(kineto PUBLIC "${CUDA_nvperf_host_LIBRARY}")
  endif()

  if(NOT TARGET Kineto::kineto)
    message(STATUS "Kineto not found — disabling PROFILER_ENABLE_KINETO")
    set(PROFILER_ENABLE_KINETO OFF CACHE BOOL "Enable XSigma Kineto profiling library." FORCE)
  endif()
  list(APPEND PROFILER_DEPENDENCY_INCLUDE_DIRS "${_tpdir}/kineto/libkineto/include")
endif()

list(APPEND PROFILER_DEPENDENCY_INCLUDE_DIRS "${_tpdir}/fmt/include")

# ITT — Intel VTune API (external system dependency, not bundled).
if(PROFILER_ENABLE_ITT)
  find_package(ITT)
  if(ITT_FOUND)
    if(TARGET Itt::itt)
      list(APPEND PROFILER_DEPENDENCY_LIBS Itt::itt)
      if(TARGET Itt::jitprofiling)
        list(APPEND PROFILER_DEPENDENCY_LIBS Itt::jitprofiling)
      endif()
      message(STATUS "Dependency: Itt::itt added to PROFILER_DEPENDENCY_LIBS")
    endif()
  else()
    message(STATUS "ITT API not found — disabling PROFILER_ENABLE_ITT")
    set(PROFILER_ENABLE_ITT OFF CACHE BOOL "Enable Intel ITT API for VTune profiling." FORCE)
  endif()
endif()

# Final HAS_* after dependency discovery. ENABLE_* may have been forced OFF
# above when Kineto or ITT was requested but not found. Both 0 is allowed
# (native pipeline still compiles); both 1 is rejected in profiler_export.h.
if(PROFILER_ENABLE_KINETO)
  list(APPEND PROFILER_COMPILE_DEFINITIONS PROFILER_HAS_KINETO=1 PROFILER_HAS_ITT=0)
elseif(PROFILER_ENABLE_ITT)
  list(APPEND PROFILER_COMPILE_DEFINITIONS PROFILER_HAS_KINETO=0 PROFILER_HAS_ITT=1)
else()
  list(APPEND PROFILER_COMPILE_DEFINITIONS PROFILER_HAS_KINETO=0 PROFILER_HAS_ITT=0)
endif()
list(APPEND PROFILER_DEPENDENCY_COMPILE_DEFINITIONS ${PROFILER_COMPILE_DEFINITIONS})

# --- Runtime library wiring ---
# Kineto's subtree builds fmt as target `fmt` (not `Fmt::fmt`). Profiler TUs
# such as profiler_kineto.cpp call fmt::print(stderr, ...), which needs the
# compiled FILE* vprint symbol. With coverage/Debug that symbol is not always
# pulled through libkineto.a alone, so link fmt whenever either alias exists.
if(TARGET Fmt::fmt)
  list(APPEND PROFILER_DEPENDENCY_LIBS Fmt::fmt)
elseif(TARGET fmt)
  list(APPEND PROFILER_DEPENDENCY_LIBS fmt)
endif()
if(PROFILER_ENABLE_KINETO AND TARGET Kineto::kineto)
  list(APPEND PROFILER_DEPENDENCY_LIBS Kineto::kineto)
endif()

# --- Source discovery: only sources for the active backend are compiled ---
set(profiler_headers "")
set(profiler_sources "")
set(CMAKE_CXX_STANDARD ${PROFILER_CXX_STANDARD})

# Common utilities — always compiled (approximate_clock, small_vector, etc.)
file(GLOB common_util_headers LIST_DIRECTORIES false "${CMAKE_CURRENT_SOURCE_DIR}/common/*.h")
file(GLOB common_util_sources LIST_DIRECTORIES false "${CMAKE_CURRENT_SOURCE_DIR}/common/*.cpp")
list(APPEND profiler_headers ${common_util_headers})
list(APPEND profiler_sources ${common_util_sources})

# Native pipeline — always compiled (traceme/xplane/host_tracer/profiler_session), independent of
# and alongside whichever of Kineto/ITT is selected below.
file(GLOB_RECURSE native_headers LIST_DIRECTORIES false "${CMAKE_CURRENT_SOURCE_DIR}/native/*.h")
file(GLOB_RECURSE native_sources LIST_DIRECTORIES false "${CMAKE_CURRENT_SOURCE_DIR}/native/*.cpp")
list(APPEND profiler_headers ${native_headers})
list(APPEND profiler_sources ${native_sources})
if(PROFILER_HAS_METAL)
  enable_language(OBJCXX)
  set(CMAKE_OBJCXX_STANDARD ${PROFILER_CXX_STANDARD})
  set(CMAKE_OBJCXX_STANDARD_REQUIRED ON)
  find_library(PROFILER_METAL_FRAMEWORK Metal REQUIRED)
  find_library(PROFILER_FOUNDATION_FRAMEWORK Foundation REQUIRED)
  file(GLOB_RECURSE profiler_mm LIST_DIRECTORIES false "${CMAKE_CURRENT_SOURCE_DIR}/native/*.mm")
  list(APPEND profiler_sources ${profiler_mm})
  set_source_files_properties(
    ${profiler_mm} PROPERTIES COMPILE_OPTIONS "-fobjc-arc;-Wno-deprecated-declarations"
  )
  list(APPEND PROFILER_DEPENDENCY_LIBS ${PROFILER_METAL_FRAMEWORK} ${PROFILER_FOUNDATION_FRAMEWORK})
  message(STATUS "Native profiler: Metal GPU tracer enabled (PROFILER_HAS_METAL=1)")

  # Kineto/ITT-side Metal fallback stub (bespoke/base/metal.mm), reusing the
  # PROFILER_HAS_METAL gate and OBJCXX/framework setup above -- registers into
  # the generic PrivateUse1 ProfilerStubs slot (see bespoke/base/base.h), not a
  # new device_enum value. bespoke/base/ is otherwise *.cpp-only compiled by
  # the Kineto/ITT blocks below, so the .mm file is appended here directly.
  file(GLOB_RECURSE profiler_kineto_mm LIST_DIRECTORIES false
       "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/base/*.mm"
  )
  list(APPEND profiler_sources ${profiler_kineto_mm})
  set_source_files_properties(
    ${profiler_kineto_mm} PROPERTIES COMPILE_OPTIONS "-fobjc-arc;-Wno-deprecated-declarations"
  )
endif()
message(
  STATUS "Native profiler pipeline: always included (traceme/xplane/host_tracer/profiler_session)"
)

# Kineto backend — base/ is shared infrastructure between Kineto and ITT.
if(PROFILER_ENABLE_KINETO)
  file(
    GLOB_RECURSE kineto_headers LIST_DIRECTORIES false
    "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/base/*.h" "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/kineto/*.h"
    "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/common/*.h"
  )
  file(
    GLOB_RECURSE kineto_sources
    LIST_DIRECTORIES false
    "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/base/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/kineto/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/common/*.cpp"
  )
  # Platform-specific unwinder is not used by Kineto; exclude it.
  file(GLOB_RECURSE KINETO_UNWIND_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/common/unwind/*.cpp")
  list(REMOVE_ITEM kineto_sources ${KINETO_UNWIND_SOURCES})
  list(APPEND profiler_headers ${kineto_headers})
  list(APPEND profiler_sources ${kineto_sources})
  message(STATUS "Kineto profiler enabled: including base, kineto, and common sources")
endif()

# ITT backend — base/ is shared with Kineto; guard against double-inclusion.
if(PROFILER_ENABLE_ITT)
  if(NOT PROFILER_ENABLE_KINETO)
    # profiler_kineto.{h,cpp} is the shared enableProfiler/disableProfiler
    # orchestration layer for every backend (Kineto, ITT, NVTX, PRIVATEUSE1) --
    # its ITT dispatch branch is internally guarded by #if PROFILER_HAS_ITT and
    # does not touch libkineto. kineto_client_interface.* defines
    # global_kineto_init() in both builds: the real body when HAS_KINETO=1,
    # and an empty definition otherwise, so the declared symbol always links.
    file(
      GLOB_RECURSE itt_base_headers
      LIST_DIRECTORIES false
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/base/*.h"
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/common/*.h"
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/kineto/kineto_shim.h"
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/kineto/profiler_kineto.h"
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/kineto/kineto_client_interface.h"
    )
    file(
      GLOB_RECURSE itt_base_sources
      LIST_DIRECTORIES false
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/base/*.cpp"
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/common/*.cpp"
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/kineto/kineto_shim.cpp"
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/kineto/profiler_kineto.cpp"
      "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/kineto/kineto_client_interface.cpp"
    )
    list(APPEND profiler_headers ${itt_base_headers})
    list(APPEND profiler_sources ${itt_base_sources})
    # Without Kineto, nothing builds fmt's compiled sources (Kineto's own
    # vendored build normally does this as a side effect via FMT_SOURCE_DIR).
    # Profiler's bespoke/common/*.cpp files (collection.cpp, util.cpp,
    # profiler_kineto.cpp) use fmt
    # unconditionally, so fall back to fmt's header-only mode for this
    # target specifically -- scoped to Profiler's own compile definitions so
    # it cannot affect Core/Logging's separate (also header-only) fmt setup
    # or Kineto's compiled one.
    set(PROFILER_NEEDS_FMT_HEADER_ONLY ON)
  endif()
  file(GLOB_RECURSE itt_headers LIST_DIRECTORIES false
       "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/itt/*.h"
  )
  file(GLOB_RECURSE itt_sources LIST_DIRECTORIES false
       "${CMAKE_CURRENT_SOURCE_DIR}/bespoke/itt/*.cpp"
  )
  list(APPEND profiler_headers ${itt_headers})
  list(APPEND profiler_sources ${itt_sources})
  message(STATUS "ITT profiler enabled: including base and ITT sources")
endif()

# --- Target definition ---
add_library(Profiler ${profiler_sources} ${profiler_headers})
xsigma_target_apply_lto(Profiler PROFILER)
if(PROFILER_ENABLE_SANITIZER)
  xsigma_configure_sanitizer(PROFILER)
endif()
xsigma_find_linker(${PROFILER_LINKER_CHOICE} Profiler PROFILER_LTO_MODE)
xsigma_target_apply_cache(Profiler PROFILER_ENABLE_CACHE PROFILER_CACHE_BACKEND)
xsigma_target_optional_icecc(Profiler PROFILER_ENABLE_ICECC)

if(BUILD_SHARED_LIBS)
  target_compile_definitions(Profiler PUBLIC PROFILER_SHARED_DEFINE PRIVATE PROFILER_BUILDING_DLL)
  if(COMMAND xsigma_set_target_output_directories)
    xsigma_set_target_output_directories(Profiler)
  endif()
else()
  target_compile_definitions(Profiler PUBLIC PROFILER_STATIC_DEFINE)
endif()

add_library(Profiler::Profiler ALIAS Profiler)

if(PROFILER_NEEDS_FMT_HEADER_ONLY)
  target_compile_definitions(Profiler PRIVATE FMT_HEADER_ONLY=1)
endif()

# The CUPTI runtime DLL (versioned, e.g. cupti64_2026.1.1.dll) lives next to
# its unversioned import lib under CUDA's extras/CUPTI/lib64 -- that
# directory is not on PATH by default, so Profiler.dll fails to load at
# runtime (STATUS_DLL_NOT_FOUND). Stage the DLL beside Profiler.dll instead,
# same convention as the SVML runtime staging in Vectorization's CMakeLists.
if(WIN32 AND TARGET CUDA::cupti)
  get_target_property(_profiler_cupti_implib CUDA::cupti IMPORTED_LOCATION)
  if(_profiler_cupti_implib)
    get_filename_component(_profiler_cupti_dir "${_profiler_cupti_implib}" DIRECTORY)
    file(GLOB _profiler_cupti_dll "${_profiler_cupti_dir}/cupti64_*.dll")
    if(_profiler_cupti_dll)
      add_custom_command(
        TARGET Profiler
        POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_profiler_cupti_dll}"
                "$<TARGET_FILE_DIR:Profiler>"
        COMMENT "Staging CUPTI runtime: ${_profiler_cupti_dll}"
        VERBATIM
      )
    endif()
  endif()
  unset(_profiler_cupti_implib)
  unset(_profiler_cupti_dir)
  unset(_profiler_cupti_dll)
endif()

xsigma_module_create_filters("${CMAKE_CURRENT_SOURCE_DIR}")

set_target_properties(
  Profiler PROPERTIES CXX_STANDARD ${PROFILER_CXX_STANDARD} CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS
                                                                                     OFF
)

if(MSVC)
  target_compile_options(Profiler PRIVATE /WX)
else()
  target_compile_options(Profiler PRIVATE -include cstdlib)
endif()

# Include roots: Library/Profiler → "common/profiler_export.h", "bespoke/…"
target_include_directories(
  Profiler BEFORE
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}>
         $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/Testing>
         $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/Testing> $<INSTALL_INTERFACE:include>
  PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}
)

configure_file(
  "${CMAKE_CURRENT_SOURCE_DIR}/Testing/ProfilerTest.h.in"
  "${CMAKE_CURRENT_BINARY_DIR}/Testing/ProfilerTest.h" @ONLY
)

if(PROFILER_DEPENDENCY_INCLUDE_DIRS)
  target_include_directories(Profiler PUBLIC ${PROFILER_DEPENDENCY_INCLUDE_DIRS})
  message(STATUS "Profiler: extra include dirs: ${PROFILER_DEPENDENCY_INCLUDE_DIRS}")
endif()

if(PROFILER_DEPENDENCY_LIBS)
  target_link_libraries(Profiler PUBLIC ${PROFILER_DEPENDENCY_LIBS})
  message(STATUS "Profiler: linked dependencies: ${PROFILER_DEPENDENCY_LIBS}")
endif()

# Xcode does not archive a static library whose only inputs are
# $<TARGET_OBJECTS:...> (kineto is kineto_base + kineto_api objects, no
# compile units of its own), and it also does not treat that .a as a
# target link dependency. Give kineto a dummy source so Libtool runs, then
# wait for it before linking Profiler (same pattern as mimalloc on Core).
if(PROFILER_ENABLE_KINETO AND TARGET kineto)
  if(CMAKE_GENERATOR STREQUAL "Xcode")
    set(_kineto_xcode_dummy "${CMAKE_CURRENT_BINARY_DIR}/kineto_xcode_dummy.cpp")
    if(NOT EXISTS "${_kineto_xcode_dummy}")
      file(WRITE "${_kineto_xcode_dummy}"
           "/* Xcode requires a source file to archive object-only static libs. */\n"
      )
    endif()
    target_sources(kineto PRIVATE "${_kineto_xcode_dummy}")
    if(TARGET kineto_base)
      add_dependencies(kineto kineto_base)
    endif()
    if(TARGET kineto_api)
      add_dependencies(kineto kineto_api)
    endif()
  endif()
  add_dependencies(Profiler kineto)
endif()

if(PROFILER_ENABLE_CLANGTIDY)
  include(clang_tidy)
  xsigma_target_clang_tidy(Profiler ${PROFILER_ENABLE_FIX})
endif()

if(PROFILER_ENABLE_IWYU)
  include(iwyu)
  xsigma_apply_iwyu(Profiler)
endif()

if(PROFILER_DEPENDENCY_COMPILE_DEFINITIONS)
  target_compile_definitions(Profiler PUBLIC ${PROFILER_DEPENDENCY_COMPILE_DEFINITIONS})
  message(STATUS "Profiler: compile definitions: ${PROFILER_DEPENDENCY_COMPILE_DEFINITIONS}")
endif()

# --- Examples ---
if(PROFILER_ENABLE_EXAMPLES)
  add_subdirectory(
    "${CMAKE_SOURCE_DIR}/Examples/Profiling" "${CMAKE_BINARY_DIR}/Examples/Profiling"
  )
  message(STATUS "Profiling Examples enabled")
endif()

# --- Testing ---
if(PROFILER_ENABLE_TESTING)
  add_subdirectory(Testing/Cxx)
endif()

if(PROFILER_ENABLE_VALGRIND AND PROFILER_ENABLE_TESTING)
  xsigma_apply_valgrind_timeouts()
endif()

message("")
message("******** Profiler module (CMake flags) ********")
message("  Instrumentation backend : ${PROFILER_BACKEND}")
message("  Native profiler  : ON (always compiled)")
message("  CUDA fallback    : ${PROFILER_HAS_CUDA}")
message("  HIP fallback     : ${PROFILER_HAS_HIP}")
message("  Metal GPU tracer : ${PROFILER_HAS_METAL}")
message("  Cxx standard     : ${PROFILER_CXX_STANDARD}")
message("  Cache            : ${PROFILER_ENABLE_CACHE}")
message("  Cache backend    : ${PROFILER_CACHE_BACKEND}")
message("  Icecc            : ${PROFILER_ENABLE_ICECC}")
xsigma_print_lto_linker_summary(PROFILER)
message("  Coverage         : ${PROFILER_ENABLE_COVERAGE}")
message("  Testing          : ${PROFILER_ENABLE_TESTING}")
message("  Examples         : ${PROFILER_ENABLE_EXAMPLES}")
message("  Gtest            : ${PROFILER_ENABLE_GTEST}")
message("  Benchmark        : ${PROFILER_ENABLE_BENCHMARK}")
message("  LibTorch         : ${PROFILER_ENABLE_LIBTORCH}")
message("  Clang-tidy       : ${PROFILER_ENABLE_CLANGTIDY}")
message("  Fix              : ${PROFILER_ENABLE_FIX}")
message("  Iwyu             : ${PROFILER_ENABLE_IWYU}")
message("  Sanitizer        : ${PROFILER_ENABLE_SANITIZER}")
message("  Sanitizer type   : ${PROFILER_SANITIZER_TYPE}")
message("  Spell            : ${PROFILER_ENABLE_SPELL}")
message("  Valgrind         : ${PROFILER_ENABLE_VALGRIND}")
message("")
message("Build:")
message("  Default C++ standard     : ${CMAKE_CXX_STANDARD}")
message("  C flags                  : ${CMAKE_C_FLAGS}")
message("  CXX flags                : ${CMAKE_CXX_FLAGS}")
message("  Shared linker flags      : ${CMAKE_SHARED_LINKER_FLAGS}")
message("  Static linker flags      : ${CMAKE_STATIC_LINKER_FLAGS}")
message("  Module linker flags      : ${CMAKE_MODULE_LINKER_FLAGS}")
get_directory_property(_summary_compile_defs DIRECTORY ${PROJECT_SOURCE_DIR} COMPILE_DEFINITIONS)
message("  Top-level compile defs   : ${_summary_compile_defs}")
message("")
