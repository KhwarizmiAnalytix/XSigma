#!/bin/bash
# Runs one (or all) local reproductions of .github/workflows/ci.yml's Linux jobs.
# Meant to be invoked via docker/ci/xci, which mounts the repo at /workspace and
# execs this script inside the docker/ci image. See docker/ci/README.md.
#
# Usage (from inside the container, or via ./docker/ci/xci <args>):
#   run.sh --list                 List every available config key
#   run.sh <key> [<key> ...]      Run one or more configs
#   run.sh --all                  Run the entire matrix, print a pass/fail summary

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./jobs.sh
source "$SCRIPT_DIR/jobs.sh"

# key -> human label, used by --list and the summary table.
ALL_KEYS=(
    bm-cpp17-loguru-tbb bm-cpp17-native-notbb bm-cpp17-glog-tbb bm-cpp20-tbb bm-cpp23-tbb
    bm-cpp17-gcc-tbb bm-cpp17-spdlog-tbb
    tbb-debug tbb-release
    sanitizer-address sanitizer-undefined sanitizer-thread sanitizer-leak sanitizer-memory
    proj-core-on proj-core-off
    proj-logging-loguru proj-logging-native proj-logging-glog proj-logging-spdlog
    proj-memory-on proj-memory-off
    proj-parallel-std proj-parallel-openmp proj-parallel-tbb
    proj-vectorization-on proj-vectorization-off
    proj-models-on proj-models-off
    vec-neon vec-sve
    opt-O0 opt-O2 opt-O3
    lto-on lto-off
    benchmark
    sccache-baseline sccache-enabled
    coverage
    feature-numa feature-mimalloc-off feature-shared feature-magic-enum-off
    feature-examples
    feature-packet-size-8 feature-lto-thin feature-ccache feature-linker-lld
    bazel-default bazel-tbb
    bazel-proj-core bazel-proj-memory
    bazel-proj-logging-loguru bazel-proj-logging-native bazel-proj-logging-glog bazel-proj-logging-spdlog
    bazel-proj-parallel-std bazel-proj-parallel-openmp bazel-proj-parallel-tbb
    bazel-proj-vectorization bazel-proj-models
    bazel-vec-neon bazel-vec-sve
    bazel-feature-numa bazel-feature-gcc
)

dispatch() {
    local key="$1"
    case "$key" in
        bm-cpp17-loguru-tbb)   job_build_matrix "$key" Debug   17 LOGURU ON ;;
        bm-cpp17-native-notbb) job_build_matrix "$key" Debug   17 NATIVE OFF ;;
        bm-cpp17-glog-tbb)     job_build_matrix "$key" Release 17 GLOG ON ;;
        bm-cpp20-tbb)          job_build_matrix "$key" Release 20 LOGURU ON ;;
        bm-cpp23-tbb)          job_build_matrix "$key" Release 23 GLOG ON ;;
        bm-cpp17-gcc-tbb)      job_build_matrix "$key" Release 17 LOGURU ON gcc g++ ;;
        bm-cpp17-spdlog-tbb)   job_build_matrix "$key" Release 17 SPDLOG ON ;;

        tbb-debug)   job_tbb_specific Debug ;;
        tbb-release) job_tbb_specific Release ;;

        sanitizer-address)   job_sanitizer address ;;
        sanitizer-undefined) job_sanitizer undefined ;;
        sanitizer-thread)    job_sanitizer thread ;;
        sanitizer-leak)      job_sanitizer leak ;;
        sanitizer-memory)    job_sanitizer memory ;;

        proj-core-on)          job_project_backend "$key" Core ON default ;;
        proj-core-off)         job_project_backend "$key" Core OFF default ;;
        proj-logging-loguru)   job_project_backend "$key" Logging ON LOGURU -DLOGGING_BACKEND=LOGURU ;;
        proj-logging-native)   job_project_backend "$key" Logging OFF NATIVE -DLOGGING_BACKEND=NATIVE ;;
        proj-logging-glog)     job_project_backend "$key" Logging ON GLOG -DLOGGING_BACKEND=GLOG ;;
        proj-logging-spdlog)   job_project_backend "$key" Logging ON SPDLOG -DLOGGING_BACKEND=SPDLOG ;;
        proj-memory-on)        job_project_backend "$key" Memory ON default ;;
        proj-memory-off)       job_project_backend "$key" Memory OFF default ;;
        proj-parallel-std)     job_project_backend "$key" Parallel ON std -DPARALLEL_BACKEND=std ;;
        proj-parallel-openmp)  job_project_backend "$key" Parallel OFF openmp -DPARALLEL_BACKEND=openmp ;;
        proj-parallel-tbb)     job_project_backend "$key" Parallel ON tbb -DPARALLEL_BACKEND=tbb ;;
        proj-vectorization-on)  job_project_backend "$key" Vectorization ON default ;;
        proj-vectorization-off) job_project_backend "$key" Vectorization OFF default ;;
        proj-models-on)         job_project_backend "$key" Models ON default ;;
        proj-models-off)        job_project_backend "$key" Models OFF default ;;

        vec-neon) job_vectorization_simd neon ;;
        vec-sve)  job_vectorization_simd sve ;;

        opt-O0) job_optimization -O0 Debug ;;
        opt-O2) job_optimization -O2 Release ;;
        opt-O3) job_optimization -O3 Release ;;

        lto-on)  job_lto ON ;;
        lto-off) job_lto OFF ;;

        benchmark) job_benchmark ;;

        sccache-baseline) job_sccache_baseline ;;
        sccache-enabled)  job_sccache_enabled ;;

        coverage) job_coverage ;;

        bazel-default) job_bazel_default ;;
        bazel-tbb)     job_bazel_tbb ;;

        bazel-proj-core)             job_bazel_project_backend core ;;
        bazel-proj-memory)           job_bazel_project_backend memory ;;
        bazel-proj-logging-loguru)   job_bazel_project_backend logging logging_loguru ;;
        bazel-proj-logging-native)   job_bazel_project_backend logging logging_native ;;
        bazel-proj-logging-glog)     job_bazel_project_backend logging logging_glog ;;
        bazel-proj-parallel-std)     job_bazel_project_backend parallel parallel.std ;;
        bazel-proj-parallel-openmp)  job_bazel_project_backend parallel parallel.openmp ;;
        bazel-proj-parallel-tbb)     job_bazel_project_backend parallel parallel.tbb ;;
        bazel-proj-logging-spdlog)   job_bazel_project_backend logging logging_spdlog ;;
        bazel-proj-vectorization)    job_bazel_project_backend vectorization ;;
        bazel-proj-models)           job_bazel_project_backend models ;;

        bazel-vec-neon) job_bazel_vectorization_simd neon ;;
        bazel-vec-sve)  job_bazel_vectorization_simd sve ;;

        feature-examples)        job_feature_flag examples -DCORE_ENABLE_EXAMPLES=ON -DMEMORY_ENABLE_EXAMPLES=ON -DLOGGING_ENABLE_EXAMPLES=ON -DVECTORIZATION_ENABLE_EXAMPLES=ON -DPARALLEL_ENABLE_EXAMPLES=ON -DMODELS_ENABLE_EXAMPLES=ON ;;
        feature-numa)            job_feature_flag numa -DMEMORY_ENABLE_NUMA=ON ;;
        feature-mimalloc-off)    job_feature_flag mimalloc-off -DMEMORY_ENABLE_MIMALLOC=OFF ;;
        feature-shared)          job_feature_flag shared -DBUILD_SHARED_LIBS=ON ;;
        feature-magic-enum-off)  job_feature_flag magic-enum-off -DCORE_ENABLE_MAGICENUM=OFF ;;
        feature-packet-size-8)   job_feature_flag psize8 -DVECTORIZATION_PACKET_SIZE=8 -DVECTORIZATION_CPU_BACKEND=avx2 ;;

        bazel-feature-numa) job_bazel_feature numa ;;
        bazel-feature-gcc)  job_bazel_feature gcc ;;

        *)
            die "Unknown config key: $key (run.sh --list to see all)"
            ;;
    esac
}

if [ "${1:-}" = "--list" ]; then
    printf '%s\n' "${ALL_KEYS[@]}"
    exit 0
fi

if [ "${1:-}" = "--all" ]; then
    declare -a passed=() failed=()
    for key in "${ALL_KEYS[@]}"; do
        log "==== $key ===="
        if ( dispatch "$key" ); then
            passed+=("$key")
        else
            failed+=("$key")
        fi
    done
    echo
    ok "Passed (${#passed[@]}): ${passed[*]:-none}"
    if [ "${#failed[@]}" -gt 0 ]; then
        die "Failed (${#failed[@]}): ${failed[*]}"
    fi
    exit 0
fi

[ $# -ge 1 ] || die "Usage: run.sh <key> [<key> ...] | --all | --list"

status=0
for key in "$@"; do
    log "==== $key ===="
    if ! ( dispatch "$key" ); then
        status=1
    fi
done
exit "$status"
