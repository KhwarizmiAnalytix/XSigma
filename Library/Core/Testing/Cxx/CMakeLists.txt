# =============================================================================
# Core Library C++
# Tests
# =============================================================================
# Following cpuinfo's simple pattern for test integration

xsigma_add_googletest()

# =============================================================================
# Test Source Files
# Discovery
# =============================================================================
file(GLOB_RECURSE test_sources LIST_DIRECTORIES false "${CMAKE_CURRENT_SOURCE_DIR}/Test*.cpp")

# Exclude special test files that need separate handling
set(TestFiles)
foreach(_test_source IN ITEMS ${test_sources})
  get_filename_component(file_name "${_test_source}" NAME)

  # Always exclude TestLoggerDisableSignalHandler
  if(file_name MATCHES "TestLoggerDisableSignalHandler")
    continue()
  endif()

  # Exclude GPU-related test files based on compile flags
  if(MEMORY_GPU_BACKEND STREQUAL "none")
    if(file_name MATCHES "TestGpu" OR file_name MATCHES "TestGPU")
      message(STATUS "Excluding GPU test (no GPU support): ${file_name}")
      continue()
    endif()
  endif()

  # When CUDA is not the backend, exclude CUDA-specific tests
  if(NOT MEMORY_GPU_BACKEND STREQUAL "cuda")
    if(file_name MATCHES "TestCuda")
      message(STATUS "Excluding CUDA test (CUDA disabled): ${file_name}")
      continue()
    endif()
  endif()

  # When HIP is not the backend, exclude HIP-specific tests
  if(NOT MEMORY_GPU_BACKEND STREQUAL "hip")
    if(file_name MATCHES "TestHip")
      message(STATUS "Excluding HIP test (HIP disabled): ${file_name}")
      continue()
    endif()
  endif()

  # When Enzyme is disabled, exclude Enzyme-specific tests
  if(NOT CORE_ENABLE_ENZYME)
    if(file_name MATCHES "TestEnzyme")
      message(STATUS "Excluding Enzyme test (Enzyme disabled): ${file_name}")
      continue()
    endif()
  endif()

  list(APPEND TestFiles "${_test_source}")
endforeach()

# =============================================================================
# CoreCxxTests
# Executable
# =============================================================================
add_executable(CoreCxxTests ${TestFiles})

# Compile definitions
target_compile_definitions(
  CoreCxxTests PRIVATE XSIGMA_HAS_GTEST=1 XSIGMA_GOOGLE_TEST USE_GTEST _VARIADIC_MAX=10
)

# Workaround for Clang 20/21.x compiler crash in register allocator The crash occurs in the Greedy
# Register Allocator pass when compiling with -O3 This is a known Clang bug:
# https://github.com/llvm/llvm-project/issues/ Disable optimization for affected files to work
# around the ICE
if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
  set_source_files_properties(
    "${CMAKE_CURRENT_SOURCE_DIR}/TestPointer.cpp" PROPERTIES COMPILE_FLAGS "-O1"
  )
  message(STATUS "Applied Clang ICE workaround: TestPointer.cpp compiled with -O1")
endif()

# Link libraries Core library is linked which transitively brings in Core-local dependencies via
# CORE_DEPENDENCY_LIBS
target_link_libraries(CoreCxxTests PRIVATE Gtest::gtest Gtest::gtest_main Core::Core)

# Set target properties
set_target_properties(
  CoreCxxTests PROPERTIES FOLDER "Tests" VS_DEBUGGER_WORKING_DIRECTORY
                                         "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}"
)

# =============================================================================
# Google Test
# Discovery for CTest and Visual Studio Test Explorer
# =============================================================================
# Register test with CTest
add_test(NAME CoreCxxTests COMMAND CoreCxxTests
         WORKING_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}"
)

# Set test properties Unit tests finish in seconds when healthy; keep timeout modest for faster
# feedback.
set_tests_properties(CoreCxxTests PROPERTIES TIMEOUT 120 LABELS "Core;Unit")

# Set coverage environment variable if enabled
if(CORE_ENABLE_COVERAGE AND DEFINED PROJECT_LLVM_PROFILE_FILE)
  set_tests_properties(
    CoreCxxTests PROPERTIES ENVIRONMENT "LLVM_PROFILE_FILE=${PROJECT_LLVM_PROFILE_FILE}"
  )
endif()

if(CORE_ENABLE_ENZYME)
  target_link_libraries(CoreCxxTests PRIVATE Enzyme::enzyme)
endif()

if(MEMORY_GPU_BACKEND STREQUAL "cuda")
  target_link_libraries(CoreCxxTests PRIVATE ${PROJECT_CUDA_LIBRARIES})
endif()

# CudaEnzymeADTest.cu provides the fixture implementation used by TestEnzymeAD.cpp. It must be
# compiled as a CUDA TU (contains __device__ code and <<<>>> launches).
#
# On Windows with the MinGW toolchain, compiling CUDA (.cu) with clang++ regularly fails due to host
# header / CUDA wrapper incompatibilities (e.g. math_functions.hpp redefinitions and missing
# texture_fetch_functions.h). Keep the rest of the suite buildable by skipping this CUDA TU.
if(MEMORY_GPU_BACKEND STREQUAL "cuda" AND CORE_ENABLE_ENZYME)
  if(WIN32 AND (MINGW OR CMAKE_CXX_COMPILER MATCHES "msys64"))
    message(
      WARNING
        "Skipping CudaEnzymeADTest.cu on Windows+MSYS2/MinGW: Clang CUDA wrapper is incompatible with CUDA 13 headers "
        "(math_functions.hpp / texture_fetch_functions.h). "
        "The rest of CoreCxxTests will still build."
    )
  else()
    target_sources(CoreCxxTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/CudaEnzymeADTest.cu")
    set_source_files_properties(
      "${CMAKE_CURRENT_SOURCE_DIR}/CudaEnzymeADTest.cu" PROPERTIES LANGUAGE CUDA
    )
  endif()
endif()

message(STATUS "✓ CoreCxxTests registered with CTest")
message(STATUS "  - Working directory: ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}")

# =============================================================================
# Output Directory
# Configuration
# =============================================================================
if(COMMAND xsigma_set_target_output_directories)
  xsigma_set_target_output_directories(CoreCxxTests)
endif()

# =============================================================================
# Individual Benchmark
# Executables
# =============================================================================
if(CORE_ENABLE_BENCHMARK)
  # --- Google Benchmark setup ---
  if(NOT TARGET benchmark)
    set(_bench_external_found FALSE)
    if(XSIGMA_ENABLE_EXTERNAL)
      find_package(benchmark QUIET)
      if(benchmark_FOUND)
        message(STATUS "Found external Google Benchmark")
        _create_third_party_interface_targets(
          "Benchmark::benchmark=benchmark::benchmark|benchmark"
          "Benchmark::benchmark_main=benchmark::benchmark_main|benchmark_main"
        )
        set(_bench_external_found TRUE)
      endif()
    endif()
    if(NOT _bench_external_found)
      # googlebenchmark uses -pedantic-errors on non-MSVC paths; Clang diagnoses __COUNTER__ in
      # benchmark headers as -Wc2y-extensions, which is fatal under -pedantic-errors.
      if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        string(APPEND CMAKE_CXX_FLAGS " -Wno-c2y-extensions")
      endif()
      # Pre-cache benchmark's regex-backend feature checks so cxx_feature_check()
      # returns immediately without invoking try_run().  try_run() inherits global
      # CMAKE_CXX_FLAGS including coverage/profile instrumentation flags that
      # require the Clang profiling runtime — which CMake does not auto-link in
      # its internal test projects — causing a spurious build failure.
      if(NOT DEFINED HAVE_STD_REGEX)
        set(HAVE_STD_REGEX 1 CACHE INTERNAL "")
      endif()
      set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "Disable benchmark tests" FORCE)
      set(BENCHMARK_ENABLE_EXCEPTIONS ON CACHE BOOL "Enable benchmark exceptions" FORCE)
      set(BENCHMARK_ENABLE_LTO OFF CACHE BOOL "Disable benchmark LTO" FORCE)
      set(BENCHMARK_USE_LIBCXX OFF CACHE BOOL "Disable benchmark libcxx" FORCE)
      set(BENCHMARK_ENABLE_WERROR OFF CACHE BOOL "Disable benchmark werror" FORCE)
      set(BENCHMARK_FORCE_WERROR OFF CACHE BOOL "Disable benchmark force werror" FORCE)
      set(BENCHMARK_ENABLE_INSTALL OFF CACHE BOOL "Disable benchmark install" FORCE)
      set(BENCHMARK_INSTALL_DOCS OFF CACHE BOOL "Disable benchmark docs install" FORCE)
      set(BENCHMARK_ENABLE_DOXYGEN OFF CACHE BOOL "Disable benchmark doxygen" FORCE)
      set(BENCHMARK_ENABLE_GTEST_TESTS OFF CACHE BOOL "Disable benchmark gtest tests" FORCE)
      set(BENCHMARK_USE_BUNDLED_GTEST OFF CACHE BOOL "Don't use bundled gtest for benchmark" FORCE)
      set(BENCHMARK_DOWNLOAD_DEPENDENCIES OFF CACHE BOOL "Don't download dependencies" FORCE)
      add_subdirectory(
        "${XSIGMA_THIRDPARTY_DIR}/benchmark" "${CMAKE_BINARY_DIR}/ThirdParty/benchmark_build"
        EXCLUDE_FROM_ALL
      )
      _set_third_party_folder_properties(
        "benchmark" "${CMAKE_BINARY_DIR}/ThirdParty/benchmark_build"
      )
    endif()
  endif()
  _create_third_party_interface_targets(
    "Benchmark::benchmark=benchmark::benchmark|benchmark"
    "Benchmark::benchmark_main=benchmark::benchmark_main|benchmark_main"
  )
  if(TARGET Benchmark::benchmark AND NOT TARGET Core::benchmark)
    add_library(Core::benchmark ALIAS benchmark)
    add_library(Core::benchmark_main ALIAS benchmark_main)
  endif()

  # Discover all benchmark source files
  file(GLOB_RECURSE bench_sources LIST_DIRECTORIES false
       "${CMAKE_CURRENT_SOURCE_DIR}/Benchmark*.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/Benchmark*.cu"
  )

  # Exclude CUDA-related benchmarks when GPU support is disabled
  set(filtered_bench_sources)
  foreach(_bench_source IN ITEMS ${bench_sources})
    get_filename_component(file_name "${_bench_source}" NAME)

    # Exclude CUDA-related benchmarks when no GPU backend is active
    if(MEMORY_GPU_BACKEND STREQUAL "none")
      if(file_name MATCHES ".*[Cc]uda.*" OR _bench_source MATCHES "\\.cu$")
        message(STATUS "Excluding CUDA benchmark (no GPU support): ${file_name}")
        continue()
      endif()
    endif()

    list(APPEND filtered_bench_sources "${_bench_source}")
  endforeach()
  set(bench_sources ${filtered_bench_sources})

  # Create a separate executable target for each benchmark file
  foreach(_bench_source IN ITEMS ${bench_sources})
    # Extract benchmark name from filename (remove .cpp/.cu extension)
    get_filename_component(bench_name "${_bench_source}" NAME_WE)

    # Create executable target with consistent naming: benchmark_<name> Example: BenchmarkSMP.cpp ->
    # benchmark_parallel
    string(REPLACE "Benchmark" "" bench_suffix "${bench_name}")
    string(TOLOWER "${bench_suffix}" bench_suffix_lower)
    set(target_name "benchmark_${bench_suffix_lower}")

    # Create the executable
    add_executable(${target_name} "${_bench_source}")

    # Link libraries - Core::benchmark: Google Benchmark library - Core::benchmark_main: Provides
    # main() function - Core::Core: Core library with all dependencies
    target_link_libraries(${target_name} PRIVATE Core::benchmark Core::benchmark_main Core::Core)

    # Set target properties
    set_target_properties(
      ${target_name} PROPERTIES FOLDER "Benchmarks" OUTPUT_NAME "${target_name}"
    )

    # Apply XSigma output directory configuration This ensures benchmarks are placed in
    # ${PROJECT_BINARY_DIR}/bin
    if(COMMAND xsigma_set_target_output_directories)
      xsigma_set_target_output_directories(${target_name})
    else()
      # Fallback: use standard output directories
      set_target_properties(
        ${target_name} PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}"
      )
    endif()

    # Register with CTest for integrated test execution This allows running benchmarks via: ctest -R
    # benchmark_ Or specific benchmark: ctest -R benchmark_parallel
    add_test(NAME ${target_name} COMMAND ${target_name} --benchmark_min_time=0.01s
             WORKING_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}"
    )

    # Set test properties
    set_tests_properties(
      ${target_name} PROPERTIES TIMEOUT 600 # 10 minutes timeout for benchmarks
                                LABELS "Benchmark;Performance;Core"
    )

    message(STATUS "✓ Benchmark target configured: ${target_name} (from ${bench_name}.cpp)")
  endforeach()

  # Report total number of benchmarks configured
  list(LENGTH bench_sources bench_count)
  message(STATUS "✓ Individual benchmark executables configured (${bench_count} total)")
endif()
