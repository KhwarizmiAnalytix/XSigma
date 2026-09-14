# =============================================================================
# Library/Core —
# CMakeLists.txt
#
# Provides the Core library: shared utilities, smart ownership primitives, compile-time type traits,
# numeric algorithms, compression wrappers, and optional Enzyme automatic-differentiation support.
#
# Public compile definitions emitted by this file: CORE_HAS_EXCEPTION_PTR=1/0   — std::exception_ptr
# supported by the toolchain CORE_SSE=1/0                 — SSE2 SIMD instructions available
# CORE_AVX=1/0                 — AVX SIMD instructions available CORE_AVX2=1/0                — AVX2
# SIMD instructions available CORE_AVX512=1/0              — AVX-512 SIMD instructions available
# CORE_HAS_MKL=1/0             — Intel MKL math library linked CORE_HAS_ROCM=1/0            — AMD ROCm GPU support compiled
# in CORE_HAS_GTEST=1/0           — Google Test available to Core tests CORE_HAS_EXPERIMENTAL=1/0 —
# Experimental features enabled (use with caution) CORE_HAS_ENZYME=1/0          — Enzyme automatic-differentiation plugin
# loaded CORE_HAS_COMPRESSION=1/0     — Compression wrappers compiled in
# =============================================================================
cmake_minimum_required(VERSION 3.16)

# =============================================================================
# SECTION 1 — Feature
# flags (CORE_ENABLE_*) and backend selectors
#
# These cache variables are the public configuration API for this module. Pass them on the CMake
# command line: -DCORE_ENABLE_ENZYME=ON
# =============================================================================
# Link-Time Optimization — disabled when CORE_ENABLE_COVERAGE or CORE_ENABLE_SANITIZER is ON (LTO
# conflicts with profiling instrumentation and typical sanitizer workflows).
include(lto)
xsigma_lto_compute_default(_lto_default PROFILE PERFORMANCE)
set(CORE_LTO_MODE "${_lto_default}" CACHE STRING
                                          "LTO mode for Core: off | thin | full | ipo | auto"
)
set_property(CACHE CORE_LTO_MODE PROPERTY STRINGS off thin full ipo auto)

# Coverage instrumentation — activates -fprofile-instr-generate / --coverage compiler flags for
# this module only. LTO is automatically skipped when coverage is enabled.
option(CORE_ENABLE_COVERAGE "Enable coverage instrumentation for Core" OFF)

# Testing — gates add_subdirectory(Testing/Cxx).
option(CORE_ENABLE_TESTING "Build Core test suite" ON)

# Examples — gates add_subdirectory(Examples) when Core examples exist.
option(CORE_ENABLE_EXAMPLES "Build Core example programs" OFF)

# Google Test integration for Core tests.
option(CORE_ENABLE_GTEST "Enable GoogleTest for Core" ON)

# Enzyme — LLVM-based automatic differentiation plugin. NOTE: CORE_ENABLE_ENZYME is declared (with a
# NOT DEFINED guard) inside Cmake/tools/enzyme.cmake, which the root CMakeLists.txt includes at line
# ~103 before add_subdirectory(Library/Core).  The option() below would be a no-op, so it is
# intentionally omitted here.  See enzyme.cmake for the canonical declaration, defaults, and
# Clang-requirement warning. Incompatibility note: coverage instrumentation inserts integer
# profile-counter stores that Enzyme's LLVM pass cannot differentiate — never enable both together.

# Google Benchmark integration for Core micro-benchmarks.
option(CORE_ENABLE_BENCHMARK "Enable Google Benchmark for Core" ON)

# Intel MKL — high-performance math kernel library (BLAS, FFT, LAPACK, …).
option(CORE_ENABLE_MKL "Enable Intel MKL math library" OFF)

# AMD ROCm — GPU support for AMD Radeon Instinct / CDNA devices.
option(CORE_ENABLE_ROCM "Enable AMD ROCm GPU support" OFF)

# Experimental — gates features that are not yet production-ready. Enabling this may change API /
# ABI without notice.
option(CORE_ENABLE_EXPERIMENTAL "Enable experimental Core features (use with caution)" OFF)
mark_as_advanced(CORE_ENABLE_EXPERIMENTAL)

# Icecream distributed compilation launcher (rarely needed; hidden by default).
option(CORE_ENABLE_ICECC "Use Icecream (icecc) distributed compiler for Core" OFF)
mark_as_advanced(CORE_ENABLE_ICECC)

# Per-target compiler cache — wraps every compile command with ccache / sccache etc. to speed up
# incremental and CI rebuilds. ON by default.
option(CORE_ENABLE_CACHE "Enable compiler caching for the Core target" ON)
mark_as_advanced(CORE_ENABLE_CACHE)

option(CORE_ENABLE_CLANGTIDY "Enable clang-tidy static analysis for Core" OFF)
mark_as_advanced(CORE_ENABLE_CLANGTIDY)
option(CORE_ENABLE_FIX "Enable clang-tidy fix-errors and fix options for Core" OFF)
mark_as_advanced(CORE_ENABLE_FIX)
option(CORE_ENABLE_IWYU "Enable include-what-you-use analysis for Core" OFF)
mark_as_advanced(CORE_ENABLE_IWYU)
option(CORE_ENABLE_SANITIZER "Build Core with sanitizer support (Clang/GCC only)" OFF)
set(CORE_SANITIZER_TYPE "address"
    CACHE STRING "Sanitizer type for Core. Options: address, undefined, thread, memory, leak"
)
set_property(CACHE CORE_SANITIZER_TYPE PROPERTY STRINGS address undefined thread memory leak)
mark_as_advanced(CORE_ENABLE_SANITIZER CORE_SANITIZER_TYPE)
option(CORE_ENABLE_SPELL "Enable check-only spell checking for Core" OFF)
mark_as_advanced(CORE_ENABLE_SPELL)
option(CORE_ENABLE_VALGRIND "Execute Core test suite with Valgrind" OFF)
mark_as_advanced(CORE_ENABLE_VALGRIND)
set(CORE_LINKER_CHOICE "default" CACHE STRING "Linker for Core: default, lld, mold, gold, lld-link")
set_property(CACHE CORE_LINKER_CHOICE PROPERTY STRINGS default lld mold gold lld-link)
mark_as_advanced(CORE_LINKER_CHOICE)
set(CORE_CACHE_BACKEND "none"
    CACHE STRING "Compiler cache backend for Core. Options: none, ccache, sccache, buildcache"
)
set_property(CACHE CORE_CACHE_BACKEND PROPERTY STRINGS none ccache sccache buildcache)
mark_as_advanced(CORE_CACHE_BACKEND)

# C++ standard — applied to every TU in this module via CMAKE_CXX_STANDARD.
set(CORE_CXX_STANDARD "20" CACHE STRING "C++ standard for Core. Options: 11 14 17 20 23")
set_property(CACHE CORE_CXX_STANDARD PROPERTY STRINGS 11 14 17 20 23)
if(NOT CORE_CXX_STANDARD MATCHES "^(11|14|17|20|23)$")
  message(FATAL_ERROR "CORE_CXX_STANDARD must be one of: 11 14 17 20 23")
endif()

# --------------------------------------------------------------------------
# a) Detection-based HAS
# tokens (PROJECT_* set by root CMakeLists.txt includes)
# --------------------------------------------------------------------------
# std::exception_ptr — missing on some embedded or older MSVC toolchains.
if(PROJECT_HAS_EXCEPTION_PTR)
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_HAS_EXCEPTION_PTR=1)
else()
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_HAS_EXCEPTION_PTR=0)
endif()

# SIMD instruction-set tokens — detected at configure time by platform.cmake.
if(PROJECT_SSE)
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_SSE=1)
else()
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_SSE=0)
endif()

if(PROJECT_AVX)
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_AVX=1)
else()
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_AVX=0)
endif()

if(PROJECT_AVX2)
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_AVX2=1)
else()
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_AVX2=0)
endif()

if(PROJECT_AVX512)
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_AVX512=1)
else()
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_AVX512=0)
endif()

# Optional numeric / algorithmic algorithm tokens (set externally or by root). CORE_SOBOL_1111 —
# alternative Sobol direction-number initialisation scheme.
if(CORE_SOBOL_1111)
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_SOBOL_1111=1)
endif()

# CORE_LU_PIVOTING — enable partial-pivoting in the dense LU factorisation.
if(CORE_LU_PIVOTING)
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_LU_PIVOTING=1)
endif()

# Enzyme automatic differentiation.
if(CORE_ENABLE_ENZYME)
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_HAS_ENZYME=1)
else()
  list(APPEND CORE_COMPILE_DEFINITIONS CORE_HAS_ENZYME=0)
endif()

# Compression wrappers — CORE_HAS_COMPRESSION / CORE_COMPRESSION_TYPE_SNAPPY are appended after
# include(compression) in Section 3 so standalone cmake -S Library/Core configures correctly (root
# may not have run first).

# Accumulate compile definitions that do not depend on Section 3 finders.
set(CORE_DEPENDENCY_COMPILE_DEFINITIONS ${PROJECT_DEPENDENCY_COMPILE_DEFINITIONS})
list(APPEND CORE_DEPENDENCY_COMPILE_DEFINITIONS ${CORE_COMPILE_DEFINITIONS})

# =============================================================================
# SECTION 3 — CMake
# module includes
#
# Inclusion order: a) Standard CMake introspection helpers b) Shared toolchain helpers
# (Cmake/tools/, Cmake/flags/) b2) Sanitizer (LTO already cleared before first include() when
# enabled) c) Core-owned feature finders — compression, MKL, Enzyme d) Coverage gate — must follow
# Enzyme (see note below); must run before LTO/linker e) LTO + linker — IPO must reflect
# coverage/sanitizer before xsigma_find_linker()
#
# Coverage + Enzyme conflict: -fprofile-instr-generate inserts integer profile-counter stores into
# each function.  Enzyme's LLVM pass cannot differentiate integer arithmetic and aborts with "cannot
# handle unknown binary operator".  Therefore CORE_ENABLE_COVERAGE and CORE_ENABLE_ENZYME must never
# both be ON at the same time.  The coverage gate is placed after include(enzyme) so that a
# developer enabling both gets a clear diagnostic from the build system.
# =============================================================================
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
if(CORE_ENABLE_SANITIZER)
  include(sanitize)
endif()
if(CORE_ENABLE_SPELL)
  include(spell)
endif()
if(CORE_ENABLE_VALGRIND)
  include(valgrind)
endif()
include(helper_macros)

# c) Core-owned feature finders NOTE: compression, mkl, and enzyme are also included by the root
# CMakeLists.txt (before add_subdirectory) so that ThirdParty targets can be gated on their results.
# All three carry include_guard(GLOBAL), so the calls below are no-ops in a normal full-project
# build.  They are kept here so that Library/Core can be used as a standalone sub-project (cmake -S
# Library/Core).
include(compression) # Finds compression libs (Snappy, …); sets CORE_ENABLE_COMPRESSION
include(mkl) # Finds Intel MKL when CORE_ENABLE_MKL=ON
include(enzyme) # Finds/configures Enzyme plugin when CORE_ENABLE_ENZYME=ON

# Compression compile defs — must follow include(compression); sets CORE_COMPRESSION_TYPE_SNAPPY.
if(CORE_ENABLE_COMPRESSION)
  list(APPEND CORE_DEPENDENCY_COMPILE_DEFINITIONS CORE_HAS_COMPRESSION=1)
  if(CORE_COMPRESSION_TYPE_SNAPPY)
    list(APPEND CORE_DEPENDENCY_COMPILE_DEFINITIONS CORE_COMPRESSION_TYPE_SNAPPY=1)
  else()
    list(APPEND CORE_DEPENDENCY_COMPILE_DEFINITIONS CORE_COMPRESSION_TYPE_SNAPPY=0)
  endif()
else()
  list(APPEND CORE_DEPENDENCY_COMPILE_DEFINITIONS CORE_HAS_COMPRESSION=0
       CORE_COMPRESSION_TYPE_SNAPPY=0
  )
endif()

# Enzyme validation: if the plugin was not found, disable gracefully. NOTE: enzyme.cmake itself
# already sets CORE_ENABLE_ENZYME=OFF when the plugin is absent, and the root CMakeLists.txt runs
# the same check at ~line 105. This guard is a standalone-build safety net — it is a no-op in a full
# project configure because enzyme.cmake's include_guard already ran.
if(CORE_ENABLE_ENZYME AND NOT TARGET Enzyme::enzyme)
  message(STATUS "Enzyme plugin not found — disabling CORE_ENABLE_ENZYME")
  set(CORE_ENABLE_ENZYME OFF CACHE BOOL "Enable Enzyme automatic differentiation" FORCE)
endif()

# d) Coverage gate When enabled, appends -fprofile-instr-generate / --coverage to global
# CMAKE_CXX_FLAGS for this module.  LTO is cleared before Section 3 includes when coverage or
# sanitizer is ON; LTO can otherwise corrupt .profraw data. WARNING: enabling coverage while
# CORE_ENABLE_ENZYME=ON will cause Enzyme to fail — the two features are mutually exclusive.
if(CORE_ENABLE_COVERAGE)
  include(coverage)
elseif(MSVC)
  string(APPEND CMAKE_EXE_LINKER_FLAGS " /DEBUG:FULL")
  string(APPEND CMAKE_SHARED_LINKER_FLAGS " /DEBUG:FULL")
endif()

# --------------------------------------------------------------------------
# b) User-option HAS
# tokens — compile_definition() converts ENABLE_X → HAS_X.
# --------------------------------------------------------------------------
# Intel MKL — high-performance BLAS/FFT/LAPACK.
compile_definition(CORE_COMPILE_DEFINITIONS CORE_ENABLE_MKL)

# AMD ROCm — heterogeneous GPU computing.
compile_definition(CORE_COMPILE_DEFINITIONS CORE_ENABLE_ROCM)

# Google Test availability.
compile_definition(CORE_COMPILE_DEFINITIONS CORE_ENABLE_GTEST)

# Experimental API gate.
compile_definition(CORE_COMPILE_DEFINITIONS CORE_ENABLE_EXPERIMENTAL)

# =============================================================================
# Third-party
# dependencies owned by Core
# =============================================================================
set(_tpdir "${CMAKE_SOURCE_DIR}/ThirdParty")

# Logging — pure third-party (ThirdParty/CMakeLists.txt), added on demand. Core links
# Logging::Logging publicly; Logging's own build also initializes fmt (the identical
# add_third_party_library(fmt ...) call below is then a no-op via the processed flag).
xsigma_add_logging()

set(BUILD_TESTING OFF CACHE BOOL "Disable testing for third-party libraries" FORCE)
set(BUILD_EXAMPLES OFF CACHE BOOL "Disable examples for third-party libraries" FORCE)
set(BUILD_BENCHMARKS OFF CACHE BOOL "Disable benchmarks for third-party libraries" FORCE)

# fmt — modern formatting library; also consumed by Kineto (via FMT_SOURCE_DIR).
set(FMT_TEST OFF CACHE BOOL "Disable fmt tests" FORCE)
set(FMT_DOC OFF CACHE BOOL "Disable fmt documentation" FORCE)
set(FMT_INSTALL OFF CACHE BOOL "Disable fmt install" FORCE)
set(FMT_HEADER_ONLY ON CACHE BOOL "Use header-only fmt library" FORCE)

add_third_party_library(
  fmt
  LIBRARY_TYPE
  STATIC
  SOURCE_DIR
  "${_tpdir}/fmt"
  ALIASES
  "fmt::fmt-header-only"
  XSIGMA_TARGETS
  "Fmt::fmt=fmt::fmt-header-only|fmt::fmt|fmt"
  INCLUDE_DIR
  "${_tpdir}/fmt/include"
  AUTO_ADD_TO_DEPENDENCIES
  OFF
)

# cpuinfo — CPU feature detection used across the project.
set(CPUINFO_BUILD_TOOLS OFF CACHE BOOL "Disable cpuinfo tools" FORCE)
set(CPUINFO_BUILD_UNIT_TESTS OFF CACHE BOOL "Disable cpuinfo unit tests" FORCE)
set(CPUINFO_BUILD_MOCK_TESTS OFF CACHE BOOL "Disable cpuinfo mock tests" FORCE)
set(CPUINFO_BUILD_BENCHMARKS OFF CACHE BOOL "Disable cpuinfo benchmarks" FORCE)
set(CPUINFO_LIBRARY_TYPE "static"
    CACHE STRING "Type of cpuinfo library (shared, static, or default) to build"
)

add_third_party_library(
  cpuinfo
  LIBRARY_TYPE
  STATIC
  SOURCE_DIR
  "${_tpdir}/cpuinfo"
  FILTER_FLAGS
  "-flto=thin"
  "-flto=full"
  XSIGMA_TARGETS
  "Cpuinfo::cpuinfo=cpuinfo::cpuinfo|cpuinfo"
  INCLUDE_DIR
  "${_tpdir}/cpuinfo/include"
  AUTO_ADD_TO_DEPENDENCIES
  OFF
)
foreach(_cpuinfo_target cpuinfo cpuinfo_internals)
  if(TARGET ${_cpuinfo_target})
    set_property(TARGET ${_cpuinfo_target} PROPERTY POSITION_INDEPENDENT_CODE ON)
  endif()
endforeach()

list(APPEND CORE_DEPENDENCY_INCLUDE_DIRS "${_tpdir}/fmt/include")
list(APPEND CORE_DEPENDENCY_INCLUDE_DIRS "${_tpdir}/cpuinfo/include")

# =============================================================================
set(xsigma_headers "")
set(xsigma_sources "")
set(xsigma_templates "")

# Per-module override — propagates to all targets in this directory scope, including test targets in
# Testing/Cxx.  CMAKE_CXX_STANDARD_REQUIRED and CMAKE_CXX_EXTENSIONS are set globally in the root
# CMakeLists.txt.
set(CMAKE_CXX_STANDARD ${CORE_CXX_STANDARD})

file(GLOB_RECURSE headers LIST_DIRECTORIES false
     "${CMAKE_CURRENT_SOURCE_DIR}/util/*.h" "${CMAKE_CURRENT_SOURCE_DIR}/common/*.h"
     "${CMAKE_CURRENT_SOURCE_DIR}/c17/*.h" ${xsigma_headers}
)

file(GLOB_RECURSE sources LIST_DIRECTORIES false
     "${CMAKE_CURRENT_SOURCE_DIR}/common/*.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/util/*.cpp"
     "${CMAKE_CURRENT_SOURCE_DIR}/c17/*.h" ${xsigma_sources}
)

file(GLOB_RECURSE templates LIST_DIRECTORIES false
     "${CMAKE_CURRENT_SOURCE_DIR}/util/*.hxx" "${CMAKE_CURRENT_SOURCE_DIR}/common/*.hxx"
     ${xsigma_templates}
)

# Compression sources are included only when Snappy is selected (case-insensitive).
if(CORE_ENABLE_COMPRESSION)
  string(TOUPPER "${CORE_COMPRESSION_TYPE}" _core_ctype_uc)
  if(_core_ctype_uc STREQUAL "SNAPPY")
    list(APPEND headers "${CMAKE_CURRENT_SOURCE_DIR}/compression/snappy.h")
    list(APPEND sources "${CMAKE_CURRENT_SOURCE_DIR}/compression/snappy.cpp")
  endif()
endif()

# =============================================================================
# Target definition
# =============================================================================
add_library(Core ${sources} ${headers} ${templates})
xsigma_target_apply_lto(Core CORE)
if(CORE_ENABLE_SANITIZER)
  xsigma_configure_sanitizer(CORE)
endif()
xsigma_find_linker(${CORE_LINKER_CHOICE} Core CORE_LTO_MODE)
xsigma_target_apply_cache(Core CORE_ENABLE_CACHE CORE_CACHE_BACKEND)
xsigma_target_optional_icecc(Core CORE_ENABLE_ICECC)

if(BUILD_SHARED_LIBS)
  target_compile_definitions(Core PUBLIC XSIGMA_SHARED_DEFINE PRIVATE XSIGMA_BUILDING_DLL)
  if(COMMAND xsigma_set_target_output_directories)
    xsigma_set_target_output_directories(Core)
  endif()
else()
  target_compile_definitions(Core PUBLIC XSIGMA_STATIC_DEFINE)
endif()

add_library(XSigma::Core ALIAS Core)
add_library(Core::Core ALIAS Core)

if(CORE_ENABLE_IWYU)
  include(iwyu)
  xsigma_apply_iwyu(Core)
endif()

xsigma_module_create_filters("${CMAKE_CURRENT_SOURCE_DIR}")

message(STATUS "Compiler: ${CMAKE_CXX_COMPILER}")
message(STATUS "Compiler ID: ${CMAKE_CXX_COMPILER_ID}, std++=${CORE_CXX_STANDARD}")

set_target_properties(
  Core PROPERTIES CXX_STANDARD ${CORE_CXX_STANDARD} CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS OFF
)

if(MSVC)
  target_compile_options(Core PRIVATE /WX)
else()
  target_compile_options(Core PRIVATE -include cstdlib)
endif()

# Include roots: Library/Core → "util/…", "common/…", "c17/…"
target_include_directories(
  Core
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
         $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}>
         $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/Testing>
         $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/Testing>
         $<INSTALL_INTERFACE:include>
  PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}
)

configure_file(
  "${CMAKE_CURRENT_SOURCE_DIR}/Testing/CoreTest.h.in"
  "${CMAKE_CURRENT_BINARY_DIR}/Testing/CoreTest.h" @ONLY
)

if(CORE_DEPENDENCY_INCLUDE_DIRS)
  target_include_directories(Core PUBLIC ${CORE_DEPENDENCY_INCLUDE_DIRS})
  message(STATUS "Core: extra include dirs: ${CORE_DEPENDENCY_INCLUDE_DIRS}")
endif()

target_link_libraries(Core PUBLIC Logging::Logging Memory::Memory)
if(TARGET Fmt::fmt)
  target_link_libraries(Core PUBLIC Fmt::fmt)
endif()
if(TARGET Cpuinfo::cpuinfo)
  target_link_libraries(Core PUBLIC Cpuinfo::cpuinfo)
endif()

if(CORE_ENABLE_CLANGTIDY)
  include(clang_tidy)
  xsigma_target_clang_tidy(Core ${CORE_ENABLE_FIX})
endif()

if(CORE_DEPENDENCY_LIBS)
  target_link_libraries(Core PUBLIC ${CORE_DEPENDENCY_LIBS})
  message(STATUS "Core: linked dependencies: ${CORE_DEPENDENCY_LIBS}")
endif()

if(CORE_ENABLE_ENZYME)
  target_link_libraries(Core PRIVATE Enzyme::enzyme)
endif()

if(CORE_DEPENDENCY_COMPILE_DEFINITIONS)
  target_compile_definitions(Core PUBLIC ${CORE_DEPENDENCY_COMPILE_DEFINITIONS})
  message(STATUS "Core: compile definitions: ${CORE_DEPENDENCY_COMPILE_DEFINITIONS}")
endif()

if(MEMORY_ENABLE_MIMALLOC AND TARGET Memory::mimalloc)
  add_dependencies(Core Memory::mimalloc)
endif()

# =============================================================================
# Installation
# =============================================================================
install(
  TARGETS Core
  EXPORT XSigmaTargets
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
  RUNTIME DESTINATION bin
  INCLUDES
  DESTINATION include
)
install(FILES ${headers} DESTINATION include/XSigma/Core COMPONENT Development)
install(
  FILES "${CMAKE_CURRENT_BINARY_DIR}/xsigma_version_macros.h"
        "${CMAKE_CURRENT_BINARY_DIR}/xsigma_threads.h"
        "${CMAKE_CURRENT_BINARY_DIR}/Testing/CoreTest.h"
  DESTINATION include/XSigma/Core
  COMPONENT Development
)

# =============================================================================
# Testing
# =============================================================================
if(CORE_ENABLE_TESTING)
  add_subdirectory(Testing/Cxx)
endif()

if(CORE_ENABLE_VALGRIND AND CORE_ENABLE_TESTING)
  xsigma_apply_valgrind_timeouts()
endif()

message("")
message("******** Core module (CMake flags) ********")
message("  Vectorization type   : ${VECTORIZATION_CPU_BACKEND}")
message("  Mkl                  : ${CORE_ENABLE_MKL}")
message("  Rocm                 : ${CORE_ENABLE_ROCM}")
message("  Experimental         : ${CORE_ENABLE_EXPERIMENTAL}")
message("  Enzyme               : ${CORE_ENABLE_ENZYME}")
message("  Compression          : ${CORE_ENABLE_COMPRESSION}")
message("  Cxx standard         : ${CORE_CXX_STANDARD}")
message("  Cache                : ${CORE_ENABLE_CACHE}")
message("  Cache backend        : ${CORE_CACHE_BACKEND}")
message("  Icecc                : ${CORE_ENABLE_ICECC}")
xsigma_print_lto_linker_summary(CORE)
message("  Coverage             : ${CORE_ENABLE_COVERAGE}")
message("  Testing              : ${CORE_ENABLE_TESTING}")
message("  Examples             : ${CORE_ENABLE_EXAMPLES}")
message("  Gtest                : ${CORE_ENABLE_GTEST}")
message("  Benchmark            : ${CORE_ENABLE_BENCHMARK}")
message("  Clang-tidy           : ${CORE_ENABLE_CLANGTIDY}")
message("  Fix                  : ${CORE_ENABLE_FIX}")
message("  Iwyu                 : ${CORE_ENABLE_IWYU}")
message("  Sanitizer            : ${CORE_ENABLE_SANITIZER}")
message("  Sanitizer type       : ${CORE_SANITIZER_TYPE}")
message("  Spell                : ${CORE_ENABLE_SPELL}")
message("  Valgrind             : ${CORE_ENABLE_VALGRIND}")
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
