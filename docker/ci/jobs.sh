#!/bin/bash
# One function per .github/workflows/ci.yml job family. Sourced by run.sh, which
# passes matrix values as arguments -- keep each function's CMake/Bazel invocation
# byte-for-byte in sync with the corresponding ci.yml step.
#
# Linux (ubuntu-latest / ubuntu-24.04-arm) coverage only: macOS-only,
# Windows-only, and GPU (CUDA/HIP/Metal) jobs are not represented here.
# See docker/ci/README.md.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib.sh
source "$SCRIPT_DIR/lib.sh"

# ---- build-matrix (ci.yml: build-matrix, Linux entries) --------------------
# args: build_dir build_type cxx_std tbb_enabled [c_compiler cxx_compiler]
job_build_matrix() {
    local build_dir="build/$1" build_type="$2" cxx_std="$3" tbb_enabled="$4"
    local c_compiler="${5:-clang}" cxx_compiler="${6:-clang++}"
    cmake_configure "$build_dir" no \
        -DCMAKE_BUILD_TYPE="$build_type" \
        -DCMAKE_C_COMPILER="$c_compiler" \
        -DCMAKE_CXX_COMPILER="$cxx_compiler" \
        -DCMAKE_CXX_STANDARD="$cxx_std" \
        -DBUILD_TESTING=ON \
        -DPARALLEL_ENABLE_TBB="$tbb_enabled" \
        -DMEMORY_ENABLE_TBB="$tbb_enabled" \
        -DMEMORY_ENABLE_CUDA=OFF
    cmake_build "$build_dir"
    ctest_run "$build_dir"
}

# ---- tbb-specific-tests -----------------------------------------------------
# args: build_type
job_tbb_specific() {
    local build_type="$1" build_dir="build/tbb-$1"
    cmake_configure "$build_dir" yes \
        -DCMAKE_BUILD_TYPE="$build_type" \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_CXX_STANDARD=17 \
        -DBUILD_TESTING=ON \
        -DCORE_ENABLE_BENCHMARK=OFF \
        -DMEMORY_ENABLE_BENCHMARK=OFF \
        -DLOGGING_ENABLE_BENCHMARK=OFF \
        -DVECTORIZATION_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_CUDA=OFF
    cmake_build "$build_dir"
    ctest_run "$build_dir"
}

# ---- sanitizer-tests ---------------------------------------------------------
# args: sanitizer (address|undefined|thread|leak)
job_sanitizer() {
    local sanitizer="$1" build_dir="build/sanitizer-$1"
    cmake_configure "$build_dir" yes \
        -DCMAKE_BUILD_TYPE=Debug \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_CXX_STANDARD=17 \
        -DCORE_ENABLE_SANITIZER=ON -DCORE_SANITIZER_TYPE="$sanitizer" \
        -DMEMORY_ENABLE_SANITIZER=ON -DMEMORY_SANITIZER_TYPE="$sanitizer" \
        -DLOGGING_ENABLE_SANITIZER=ON -DLOGGING_SANITIZER_TYPE="$sanitizer" \
        -DVECTORIZATION_ENABLE_SANITIZER=ON -DVECTORIZATION_SANITIZER_TYPE="$sanitizer" \
        -DPARALLEL_ENABLE_SANITIZER=ON -DPARALLEL_SANITIZER_TYPE="$sanitizer" \
        -DMODELS_ENABLE_SANITIZER=ON -DMODELS_SANITIZER_TYPE="$sanitizer" \
        -DBUILD_TESTING=ON \
        -DPARALLEL_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_CUDA=OFF
    cmake_build "$build_dir"
    export_sanitizer_env "$sanitizer"
    ctest_run "$build_dir"
}

# ---- project-flag-backend-tests ---------------------------------------------
# args: key project external backend_label [extra_cmake_flags...]
job_project_backend() {
    local key="$1" project="$2" external="$3" backend_label="$4"
    shift 4
    local build_dir="build/proj-$key"
    cmake_configure "$build_dir" yes \
        -DCMAKE_BUILD_TYPE=Debug \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_CXX_STANDARD=17 \
        -DXSIGMA_ENABLE_EXTERNAL="$external" \
        -DXSIGMA_LIBRARY_PROJECT="$project" \
        -DBUILD_TESTING=ON \
        -DCORE_ENABLE_BENCHMARK=OFF \
        -DMEMORY_ENABLE_BENCHMARK=OFF \
        -DLOGGING_ENABLE_BENCHMARK=OFF \
        -DVECTORIZATION_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_CUDA=OFF \
        "$@"
    cmake_build "$build_dir"

    local regex=".*${project}.*"
    if ctest --test-dir "$build_dir" -N -R "$regex" | grep -q "Total Tests: 0"; then
        log "No tests matched '$regex'; running full suite."
        ctest_run "$build_dir"
    else
        ctest_run "$build_dir" -R "$regex"
    fi
}

# ---- vectorization-simd-backend-tests (neon/sve only -- see README) --------
# args: vectorization_type
job_vectorization_simd() {
    local vtype="$1" build_dir="build/vec-$1"
    cmake_configure "$build_dir" yes \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_CXX_STANDARD=17 \
        -DVECTORIZATION_CPU_BACKEND="$vtype" \
        -DBUILD_TESTING=ON \
        -DCORE_ENABLE_BENCHMARK=OFF \
        -DMEMORY_ENABLE_BENCHMARK=OFF \
        -DLOGGING_ENABLE_BENCHMARK=OFF \
        -DVECTORIZATION_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_CUDA=OFF
    cmake_build "$build_dir"

    if [ "$vtype" = "avx512" ] && ! python3 "$REPO_ROOT/Scripts/helpers/cpu_isa.py" avx512; then
        log "AVX-512 compile-only: this CPU has no avx512f; skipping tests."
        return 0
    fi

    if ctest --test-dir "$build_dir" -N -R "Vectorization" | grep -q "Total Tests: 0"; then
        log "No tests matched 'Vectorization'; running full suite."
        ctest_run "$build_dir"
    else
        ctest_run "$build_dir" -R "Vectorization"
    fi
}

# ---- optimization-flags-test -------------------------------------------------
# args: opt_level (-O0|-O2|-O3) build_type
job_optimization() {
    local opt_level="$1" build_type="$2"
    local build_dir="build/opt-${opt_level#-}"
    cmake_configure "$build_dir" yes \
        -DCMAKE_BUILD_TYPE="$build_type" \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_C_FLAGS="$opt_level" \
        -DCMAKE_CXX_FLAGS="$opt_level" \
        -DBUILD_TESTING=ON
    cmake_build "$build_dir"
    ctest_run "$build_dir"
}

# ---- lto-tests ----------------------------------------------------------------
# args: lto_enabled (ON|OFF)
job_lto() {
    local lto="$1" build_dir="build/lto-${1,,}"
    cmake_configure "$build_dir" yes \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DBUILD_TESTING=ON \
        -DCORE_ENABLE_LTO="$lto" \
        -DMEMORY_ENABLE_LTO="$lto" \
        -DLOGGING_ENABLE_LTO="$lto" \
        -DVECTORIZATION_ENABLE_LTO="$lto" \
        -DPARALLEL_ENABLE_LTO="$lto" \
        -DPARALLEL_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_TBB=ON
    cmake_build "$build_dir"
    ctest_run "$build_dir"
}

# ---- benchmark-tests ----------------------------------------------------------
job_benchmark() {
    local build_dir="build/benchmark"
    cmake_configure "$build_dir" yes \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DBUILD_TESTING=ON \
        -DCORE_ENABLE_BENCHMARK=OFF \
        -DMEMORY_ENABLE_BENCHMARK=OFF \
        -DLOGGING_ENABLE_BENCHMARK=OFF \
        -DVECTORIZATION_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_BENCHMARK=OFF \
        -DCORE_ENABLE_LTO=ON \
        -DMEMORY_ENABLE_LTO=ON \
        -DLOGGING_ENABLE_LTO=ON \
        -DVECTORIZATION_ENABLE_LTO=ON \
        -DPARALLEL_ENABLE_LTO=ON \
        -DPARALLEL_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_TBB=ON
    cmake_build "$build_dir"
    log "Running benchmarks (ci.yml treats failures here as non-blocking)"
    ctest --test-dir "$build_dir" -R ".*[Bb]enchmark.*" --output-on-failure || true
}

# ---- sccache-baseline-tests (Ubuntu entry) ------------------------------------
job_sccache_baseline() {
    local build_dir="build/sccache-baseline"
    cmake_configure "$build_dir" yes \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DBUILD_TESTING=ON \
        -DCORE_ENABLE_BENCHMARK=OFF \
        -DMEMORY_ENABLE_BENCHMARK=OFF \
        -DLOGGING_ENABLE_BENCHMARK=OFF \
        -DVECTORIZATION_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_BENCHMARK=OFF
    cmake_build "$build_dir"
    ctest_run "$build_dir" --build-config Release
}

# ---- sccache-enabled-tests (Ubuntu entry) -------------------------------------
job_sccache_enabled() {
    local build_dir="build/sccache-enabled"
    cmake_configure "$build_dir" yes \
        -DCMAKE_CXX_COMPILER_LAUNCHER=sccache \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCORE_ENABLE_BENCHMARK=OFF \
        -DMEMORY_ENABLE_BENCHMARK=OFF \
        -DLOGGING_ENABLE_BENCHMARK=OFF \
        -DVECTORIZATION_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_BENCHMARK=OFF \
        -DBUILD_TESTING=ON
    cmake_build "$build_dir"
    ctest_run "$build_dir" --build-config Release
    sccache --show-stats || true
}

# ---- clang-coverage-tests -------------------------------------------------------
job_coverage() {
    local build_dir="build/coverage"
    cd "$REPO_ROOT"
    log "Installing Tools/coverage[test] (editable)"
    python3 -m pip install --break-system-packages -e "Tools/coverage[test]"
    python3 -m pytest Tools/coverage/tests/ -v

    cmake_configure "$build_dir" no \
        -DCMAKE_BUILD_TYPE=Debug \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_CXX_STANDARD=17 \
        -DBUILD_TESTING=ON \
        -DCORE_ENABLE_COVERAGE=ON \
        -DMEMORY_ENABLE_COVERAGE=ON \
        -DLOGGING_ENABLE_COVERAGE=ON \
        -DVECTORIZATION_ENABLE_COVERAGE=ON \
        -DPARALLEL_ENABLE_COVERAGE=ON \
        -DMEMORY_ENABLE_CUDA=OFF
    cmake_build "$build_dir"
    ctest_run "$build_dir"

    log "Running coverage-tool"
    coverage-tool --build="$build_dir"
    [ -f "$build_dir/coverage_report/coverage_summary.json" ] || die "JSON coverage report not generated"
    [ -f "$build_dir/coverage_report/html/index.html" ] || die "HTML coverage report not generated"
    ok "Coverage reports generated under $build_dir/coverage_report/"
}

# ---- bazel-build-matrix (default config, Ubuntu entry) --------------------------
job_bazel_default() {
    # Skip the `config` token: it runs `bazel clean --expunge`, which on this
    # Docker bind-mount can make /workspace/Tools briefly unreadable
    # ("Failed to list directory contents, for Tools"). Incremental
    # `build.test` is enough to exercise the tree.
    bazel_run build.test
}

# ---- bazel-tbb-tests ------------------------------------------------------------
job_bazel_tbb() {
    bazel_run config.build.test.tbb
}

# ---- bazel-project-flag-backend-tests --------------------------------------------
# args: project [extra_config]
job_bazel_project_backend() {
    local project="$1" extra_config="${2:-}"
    if [ -n "$extra_config" ]; then
        bazel_run "config.build.test.${extra_config}" "--project.${project}"
    else
        bazel_run config.build.test "--project.${project}"
    fi
}

# ---- bazel-vectorization-simd-tests (neon/sve only -- see README) ----------------
# args: vectorization_type
job_bazel_vectorization_simd() {
    local vtype="$1"
    bazel_run "config.build.test.${vtype}" "--project.vectorization"
}

# ---- feature-flag-tests (Linux entries) ----------------------------------------
# args: key [extra cmake flags...]
job_feature_flag() {
    local key="$1"
    shift
    local build_dir="build/feature-$key"
    cmake_configure "$build_dir" yes \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_CXX_STANDARD=17 \
        -DBUILD_TESTING=ON \
        -DCORE_ENABLE_BENCHMARK=OFF \
        -DMEMORY_ENABLE_BENCHMARK=OFF \
        -DLOGGING_ENABLE_BENCHMARK=OFF \
        -DVECTORIZATION_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_BENCHMARK=OFF \
        -DPARALLEL_ENABLE_TBB=ON \
        -DMEMORY_ENABLE_TBB=ON \
        "$@"
    cmake_build "$build_dir"
    ctest_run "$build_dir"
}

# ---- bazel-feature-flag-tests --------------------------------------------------
# args: extra dotted tokens (e.g. numa, avx2, gcc)
job_bazel_feature() {
    bazel_run "config.build.test.$1"
}
