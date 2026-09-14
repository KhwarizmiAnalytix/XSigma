/*
 * XSigma: High-Performance Quantitative Library
 *
 * SPDX-License-Identifier: GPL-3.0-or-later OR Commercial
 *
 * This file is part of XSigma and is licensed under a dual-license model:
 *
 *   - Open-source License (GPLv3):
 *       Free for personal, academic, and research use under the terms of
 *       the GNU General Public License v3.0 or later.
 *
 *   - Commercial License:
 *       A commercial license is required for proprietary, closed-source,
 *       or SaaS usage. Contact us to obtain a commercial agreement.
 *
 * Contact: licensing@xsigma.co.uk
 * Website: https://www.xsigma.co.uk
 */

/*
 * Profiles the fused Metal expression `z = z + exp(z) + sin(z)` with Kineto
 * (RecordFunction / USER_SCOPE, including tensor::assign) and the native
 * GpuTracer (command-buffer GPUStartTime for fused_float).
 */

#include "VectorizationTest.h"

#if VECTORIZATION_HAS_METAL && VECTORIZATION_HAS_PROFILER && PROFILER_HAS_KINETO

#include <cstdint>
#include <exception>
#include <iostream>
#include <set>
#include <string>
#include <unordered_set>
#include <vector>

#include <bespoke/common/record_function.h>
#include <bespoke/kineto/hotspot_report.h>
#include <bespoke/kineto/profiler_kineto.h>
#include <native/exporters/xplane/tf_xplane_visitor.h>
#include <native/exporters/xplane/xplane.h>
#include <native/exporters/xplane/xplane_schema.h>
#include <native/exporters/xplane/xplane_utils.h>
#include <native/session/profiler.h>

#include "terminals/tensor.h"

extern "C" int xsigma_metal_device_count();

namespace
{

using namespace vectorization;

constexpr const char* kWorkloadScope = "z_plus_exp_sin";
constexpr const char* kAssignScope   = "vectorization::tensor::assign";
constexpr const char* kKernelName    = "fused_float";
constexpr const char* kKinetoTrace   = "/tmp/xsigma_metal_z_exp_sin_kineto.json";
constexpr const char* kNativeTrace   = "/tmp/xsigma_metal_z_exp_sin_native.json";
constexpr std::size_t kN             = 1U << 20;
constexpr int         kIters         = 16;

profiler::profiler_options make_gpu_options()
{
    profiler::profiler_options opts;
    opts.enable_timing_                 = true;
    opts.enable_hierarchical_profiling_ = true;
    opts.enable_gpu_tracing_            = true;
    opts.output_format_                 = profiler::profiler_options::output_format_enum::JSON;
    return opts;
}

void print_gpu_plane(const profiler::xplane& plane)
{
    std::cout << "\n=== Native GpuTracer plane (" << plane.name() << ") ===\n";
    profiler::xplane_visitor const visitor = profiler::CreateTfXPlaneVisitor(&plane);
    visitor.for_each_line(
        [&](const profiler::xline_visitor& line)
        {
            std::cout << "  line: " << line.name() << "\n";
            line.for_each_event(
                [&](const profiler::xevent_visitor& event)
                {
                    std::cout << "    " << event.name() << "  duration_ns=" << event.duration_ns()
                              << "\n";
                });
        });
    std::cout << std::flush;
}

}  // namespace

VECTORIZATIONTEST(TensorGpuKineto, metal_z_plus_exp_sin)
{
    if (xsigma_metal_device_count() <= 0)
    {
        GTEST_SKIP() << "No Metal device";
    }

    std::vector<float> host(kN);
    for (std::size_t i = 0; i < kN; ++i)
    {
        host[i] = static_cast<float>(static_cast<double>(i) / static_cast<double>(kN) * 0.5);
    }

    tensor<float> z(kN, device_enum::METAL);
    z.copy_from_host(host);
    // Compile the fused MSL kernel once so the timed region is dispatch, not JIT.
    z = z + ::exp(z) + ::sin(z);

    profiler::profiler_session native_session(make_gpu_options());
    ASSERT_TRUE(native_session.start());

    profiler::profiler_impl::ProfilerConfig const config(
        profiler::profiler_impl::ProfilerState::KINETO_PRIVATEUSE1_FALLBACK,
        /*report_input_shapes=*/false,
        /*profile_memory=*/false,
        /*with_stack=*/false,
        /*with_flops=*/false,
        /*with_modules=*/false);
    const std::set<profiler::profiler_impl::ActivityType> activities{
        profiler::profiler_impl::ActivityType::CPU, profiler::profiler_impl::ActivityType::Metal};
    const std::unordered_set<profiler::RecordScope> scopes{profiler::RecordScope::USER_SCOPE};

    try
    {
        profiler::profiler_impl::prepareProfiler(config, activities);
        profiler::profiler_impl::enableProfiler(config, activities, scopes);
    }
    catch (const std::exception& ex)
    {
        native_session.stop();
        GTEST_SKIP() << "Kineto profiler unavailable: " << ex.what();
    }

    {
        PROFILER_RECORD_USER_SCOPE(kWorkloadScope);
        for (int i = 0; i < kIters; ++i)
        {
            z = z + ::exp(z) + ::sin(z);
        }
    }

    auto kineto_result = profiler::profiler_impl::disableProfiler();
    ASSERT_TRUE(native_session.stop());
    ASSERT_NE(kineto_result, nullptr);

    const auto& events = kineto_result->events();
    if (events.empty())
    {
        GTEST_SKIP() << "Kineto produced no CPU events in this environment";
    }

    std::cout << "\n=== Kineto events (z = z + exp(z) + sin(z), N=" << kN << ", iters=" << kIters
              << ") ===\n";
    uint64_t assign_count = 0;
    uint64_t assign_ns    = 0;
    bool     saw_workload = false;
    for (const auto& event : events)
    {
        std::cout << "  " << event.name() << "  cpu_ns=" << event.durationNs()
                  << "  metal_us=" << event.privateuse1ElapsedUs() << "\n";
        if (event.name() == kWorkloadScope)
        {
            saw_workload = true;
            EXPECT_GT(event.durationNs(), 0U);
        }
        if (event.name() == kAssignScope)
        {
            ++assign_count;
            assign_ns += event.durationNs();
        }
    }
    std::cout << std::flush;

    EXPECT_TRUE(saw_workload);
    EXPECT_EQ(assign_count, static_cast<uint64_t>(kIters));
    EXPECT_GT(assign_ns, 0U);

    profiler::profiler_impl::hotspot_report const hotspot(*kineto_result);
    std::cout << "\n=== Kineto hotspot table ===\n" << hotspot.table();
    std::cout << "\n=== Kineto top-down ===\n" << hotspot.top_down_tree() << std::flush;

    EXPECT_TRUE(kineto_result->save(kKinetoTrace));
    std::cout << "Kineto Chrome trace: " << kKinetoTrace << "\n";

    ASSERT_TRUE(native_session.has_collected_xspace());
    const profiler::xplane* gpu = profiler::find_plane_with_name(
        native_session.collected_xspace(), profiler::GpuPlaneName(0));
    ASSERT_NE(gpu, nullptr) << "expected native GpuTracer plane for Metal fused_float";
    print_gpu_plane(*gpu);

    uint64_t                       kernel_count = 0;
    double                         kernel_ns    = 0.0;
    profiler::xplane_visitor const visitor      = profiler::CreateTfXPlaneVisitor(gpu);
    visitor.for_each_line(
        [&](const profiler::xline_visitor& line)
        {
            line.for_each_event(
                [&](const profiler::xevent_visitor& event)
                {
                    if (event.name() == kKernelName)
                    {
                        ++kernel_count;
                        kernel_ns += event.duration_ns();
                    }
                });
        });
    EXPECT_EQ(kernel_count, static_cast<uint64_t>(kIters));
    EXPECT_GT(kernel_ns, 0.0);
    if (kernel_count > 0)
    {
        std::cout << "fused_float mean GPU ns=" << (kernel_ns / static_cast<double>(kernel_count))
                  << "  assign mean CPU ns="
                  << (static_cast<double>(assign_ns) / static_cast<double>(assign_count)) << "\n";
    }

    EXPECT_TRUE(native_session.write_chrome_trace(kNativeTrace));
    std::cout << "Native Chrome trace: " << kNativeTrace << "\n" << std::flush;
}

#else

VECTORIZATIONTEST(TensorGpuKineto, metal_z_plus_exp_sin)
{
    GTEST_SKIP() << "requires VECTORIZATION_HAS_METAL + Profiler Kineto";
}

#endif
