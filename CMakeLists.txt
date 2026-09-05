# =============================================================================
# XSigma Main
# CMake Configuration
# =============================================================================
# Third-party deps: ThirdParty/CMakeLists.txt. Feature flags → compile defs:
# Cmake/flags/compile_definitions.cmake. Library modules: Library/*/CMakeLists.txt.
# =============================================================================
cmake_minimum_required(VERSION 3.16)
cmake_policy(SET CMP0069 NEW)

if(${CMAKE_SOURCE_DIR} STREQUAL ${CMAKE_BINARY_DIR})
  message(FATAL_ERROR "In-source build are not supported")
endif()

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/Cmake/tools")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/Cmake/flags")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/Cmake/packages")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/Library/Core/Cmake")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/Library/Vectorization/Cmake")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/Library/Logging/Cmake")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/Library/Parallel/Cmake")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/Library/Memory/Cmake")
include(xcode_toolchain)

project(
  XSigma
  VERSION 1.0.0
  DESCRIPTION "XSigma High-Performance Computing Library"
  LANGUAGES CXX C
)

# Set version macros
set(PROJECT_MAJOR_VERSION 1)
set(PROJECT_MINOR_VERSION 0)
set(PROJECT_BUILD_VERSION 0)
set(PROJECT_VERSION_FULL
    "${PROJECT_MAJOR_VERSION}.${PROJECT_MINOR_VERSION}.${PROJECT_BUILD_VERSION}"
)

set(CMAKE_COLOR_DIAGNOSTICS ON)

# Clang does not support MSVC's dllimport annotation on member declarations.
# Apply this at the root so it reaches every first- and third-party target.
if(WIN32 AND CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
  add_compile_options(
    $<$<COMPILE_LANGUAGE:C,CXX>:-Wno-ignored-attributes>
    $<$<COMPILE_LANGUAGE:CXX>:-Wno-deprecated-volatile>
    $<$<AND:$<COMPILE_LANGUAGE:CUDA>,$<CUDA_COMPILER_ID:Clang>>:-Wno-ignored-attributes>
    $<$<AND:$<COMPILE_LANGUAGE:CUDA>,$<CUDA_COMPILER_ID:Clang>>:-Wno-unknown-cuda-version>
  )
  add_link_options("LINKER:/ignore:importeddllmain")
endif()

# CTest sets up dashboard/memcheck infrastructure (DartConfiguration.tcl, MemoryCheckCommand, etc.)
# which is required for `ctest -T memcheck` (used by Scripts/valgrind_ctest.sh).
#
# Important: `include(CTest)` *generates* DartConfiguration.tcl at configure time. To make sure
# custom Valgrind options (from `Cmake/tools/valgrind.cmake`) are reflected there, we need to
# include valgrind (when enabled) BEFORE we include CTest.
if(DEFINED CORE_ENABLE_VALGRIND
   AND CORE_ENABLE_VALGRIND
   OR DEFINED LOGGING_ENABLE_VALGRIND
   AND LOGGING_ENABLE_VALGRIND
   OR DEFINED MEMORY_ENABLE_VALGRIND
   AND MEMORY_ENABLE_VALGRIND
   OR DEFINED PARALLEL_ENABLE_VALGRIND
   AND PARALLEL_ENABLE_VALGRIND
   OR DEFINED PROFILER_ENABLE_VALGRIND
   AND PROFILER_ENABLE_VALGRIND
   OR DEFINED VECTORIZATION_ENABLE_VALGRIND
   AND VECTORIZATION_ENABLE_VALGRIND
   OR DEFINED MODELS_ENABLE_VALGRIND
   AND MODELS_ENABLE_VALGRIND
)
  include(valgrind)
endif()
include(CTest)

# Our Library/*/Testing suites call add_test() regardless of BUILD_TESTING.
# Keep CTest enabled, then turn BUILD_TESTING off so vendored ThirdParty/
# CMakeLists (fmt, glog, kineto, cpuinfo, mimalloc, googletest, …) do not
# register or build their own tests. Do not edit anything under ThirdParty/.
enable_testing()
set(BUILD_TESTING OFF CACHE BOOL "Disable testing for third-party libraries" FORCE)
set(BUILD_EXAMPLES OFF CACHE BOOL "Disable examples for third-party libraries" FORCE)
set(BUILD_BENCHMARKS OFF CACHE BOOL "Disable benchmarks for third-party libraries" FORCE)
set(FMT_TEST OFF CACHE BOOL "Disable fmt tests" FORCE)
set(FMT_DOC OFF CACHE BOOL "Disable fmt documentation" FORCE)
set(gtest_build_tests OFF CACHE BOOL "Disable Google Test's own tests" FORCE)
set(gtest_build_samples OFF CACHE BOOL "Disable Google Test samples" FORCE)
set(gmock_build_tests OFF CACHE BOOL "Disable Google Mock's own tests" FORCE)
set(INSTALL_GTEST OFF CACHE BOOL "Disable Google Test install" FORCE)
set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "Disable Google Benchmark tests" FORCE)
set(BENCHMARK_ENABLE_GTEST_TESTS OFF CACHE BOOL "Disable Google Benchmark gtest tests" FORCE)
set(CPUINFO_BUILD_UNIT_TESTS OFF CACHE BOOL "Disable cpuinfo unit tests" FORCE)
set(CPUINFO_BUILD_MOCK_TESTS OFF CACHE BOOL "Disable cpuinfo mock tests" FORCE)
set(CPUINFO_BUILD_BENCHMARKS OFF CACHE BOOL "Disable cpuinfo benchmarks" FORCE)
set(MI_BUILD_TESTS OFF CACHE BOOL "Disable mimalloc tests" FORCE)
set(KINETO_BUILD_TESTS OFF CACHE BOOL "Disable Kineto tests" FORCE)
set(SLEEF_BUILD_TESTS OFF CACHE BOOL "Disable SLEEF tests" FORCE)
set(LOGURU_BUILD_TESTS OFF CACHE BOOL "Disable loguru tests" FORCE)
set(LOGURU_BUILD_EXAMPLES OFF CACHE BOOL "Disable loguru examples" FORCE)
set(SPDLOG_BUILD_TESTS OFF CACHE BOOL "Disable spdlog tests" FORCE)
set(SPDLOG_BUILD_TESTS_HO OFF CACHE BOOL "Disable spdlog header-only tests" FORCE)
set(SPDLOG_BUILD_EXAMPLE OFF CACHE BOOL "Disable spdlog examples" FORCE)
set(SPDLOG_BUILD_BENCH OFF CACHE BOOL "Disable spdlog benchmarks" FORCE)
set(WITH_GTEST OFF CACHE BOOL "Disable glog gtest" FORCE)
set(WITH_GMOCK OFF CACHE BOOL "Disable glog gmock" FORCE)
set(MAGIC_ENUM_OPT_BUILD_TESTS OFF CACHE BOOL "Disable magic_enum tests" FORCE)
set(MAGIC_ENUM_OPT_BUILD_EXAMPLES OFF CACHE BOOL "Disable magic_enum examples" FORCE)

# Always use bundled googletest — external shared gtest (e.g. from conda) causes rpath failures at
# runtime because its dylib install path is not in our test executables' rpath.
set(CMAKE_DISABLE_FIND_PACKAGE_GTest TRUE)

set(PROJECT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
set(PROJECT_BINARY_DIR "${CMAKE_CURRENT_BINARY_DIR}")
set(PROJECT_VERSION "${PROJECT_VERSION}")

option(BUILD_SHARED_LIBS "Build shared libraries" ON)

# User-facing name. ThirdParty/CMakeLists.txt still declares XSIGMA_ENABLE_EXTERNAL
# (vendored — do not edit). Keep the two cache entries in sync.
option(XSIGMA_ENABLE_EXTERNAL "Use external copies of third party libraries by default" ON)
set(XSIGMA_ENABLE_EXTERNAL "${XSIGMA_ENABLE_EXTERNAL}"
    CACHE BOOL "Vendored ThirdParty option; set XSIGMA_ENABLE_EXTERNAL instead" FORCE
)

add_subdirectory(ThirdParty)

# ThirdParty may have flipped the vendored option; publish it under the project name.
set(XSIGMA_ENABLE_EXTERNAL "${XSIGMA_ENABLE_EXTERNAL}")

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/bin")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/lib")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/lib")

# Optional: build only one Library/* module and its CMake dependencies (see Scripts/setup.py
# --project.NAME). When empty or unset, all Library/* projects are enabled (full monolith).
# setup.py always passes -DXSIGMA_LIBRARY_PROJECT=... so omitting --project.* resets any prior
# single-library configure.
set(XSIGMA_LIBRARY_PROJECT
    ""
    CACHE
      STRING
      "If non-empty: only this Library module and deps (Logging|Memory|Vectorization|Core|Parallel|Profiler|Models|Graph). Empty: all Library/* (default)."
)

string(TOLOWER "${XSIGMA_LIBRARY_PROJECT}" _xsigma_libproj_lc)

set(_xsigma_lib_order
    Logging
    # Profiler has no CMake dependency on any other XSigma library (only
    # third-party fmt/kineto/itt/cuda), so it can build early. It must come
    # before Memory/Vectorization/Parallel: each optionally links
    # Profiler::Profiler when it exists (see e.g. Library/Memory/CMakeLists.txt's
    # VECTORIZATION_ENABLE_PROFILER-style gate), and that `TARGET Profiler::Profiler`
    # check only succeeds if Profiler's add_subdirectory has already run.
    Profiler
    Memory
    Vectorization
    Core
    Parallel
    Models
    # Graph links Parallel::Parallel (threaded_callback_queue), so it must come
    # after Parallel in this list.
    Graph
)

if(_xsigma_libproj_lc STREQUAL "")
  foreach(_lib IN LISTS _xsigma_lib_order)
    add_subdirectory(Library/${_lib})
  endforeach()
else()
  if(_xsigma_libproj_lc STREQUAL "logging")
    set(_xsigma_lib_enabled Logging)
  elseif(_xsigma_libproj_lc STREQUAL "memory")
    # Memory always links Logging::Logging.
    set(_xsigma_lib_enabled Logging Memory)
  elseif(_xsigma_libproj_lc STREQUAL "vectorization")
    set(MEMORY_ENABLE_TESTING OFF CACHE BOOL "Skip Memory tests when building Vectorization" FORCE)
    set(MEMORY_ENABLE_BENCHMARK OFF CACHE BOOL "Skip Memory benchmarks when building Vectorization"
                                          FORCE
    )
    set(_xsigma_lib_enabled Logging Memory Vectorization Profiler)
  elseif(_xsigma_libproj_lc STREQUAL "core")
    set(_xsigma_lib_enabled Parallel Profiler Logging Memory Vectorization Core)
  elseif(_xsigma_libproj_lc STREQUAL "parallel")
    set(_xsigma_lib_enabled Parallel Profiler)
  elseif(_xsigma_libproj_lc STREQUAL "profiler")
    set(_xsigma_lib_enabled Profiler)
  elseif(_xsigma_libproj_lc STREQUAL "models")
    set(_xsigma_lib_enabled Models)
  elseif(_xsigma_libproj_lc STREQUAL "graph")
    set(_xsigma_lib_enabled Parallel Profiler Graph)
  else()
    message(
      FATAL_ERROR
        "XSIGMA_LIBRARY_PROJECT='${XSIGMA_LIBRARY_PROJECT}' is invalid. "
        "Use one of: Logging, Memory, Vectorization, Core, Parallel, Profiler, Models, Graph, or leave empty for all."
    )
  endif()

  message(STATUS "XSigma: single-library mode — enabling: ${_xsigma_lib_enabled}")

  foreach(_lib IN LISTS _xsigma_lib_order)
    if(_lib IN_LIST _xsigma_lib_enabled)
      add_subdirectory(Library/${_lib})
    endif()
  endforeach()
endif()

xsigma_clang_windows_gtest_workaround()

include(summary)
print_configuration_summary()
