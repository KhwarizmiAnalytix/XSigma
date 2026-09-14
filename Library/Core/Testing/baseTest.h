/*
 * XSigma: High-Performance Computational Library
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

#ifndef XSIGMA_TEST_H
#define XSIGMA_TEST_H

#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

#include "common/macros.h"
//#include <logger/logger.h>

// Include Google Test if available
#if PROJECT_HAS_GTEST
#include <gtest/gtest.h>
#endif

// Logging macros for tests
#if PROJECT_HAS_GTEST
// Google Test functions are void, so END_TEST should not return anything
#define END_TEST()
#else
// Non-Google Test functions return int
#define END_TEST() return EXIT_SUCCESS
#endif

// Test assertion macros
#if PROJECT_HAS_GTEST
// Use Google Test macros when available (Google Test uses EXPECT_*, not GTEST_EXPECT_*)
// Note: The macros are already defined by Google Test, so we don't need to redefine them
// Just ensure they're available by including gtest.h above

// Google Test main function
#define XSIGMATEST(module, name) TEST(module, name)

#define XSIGMATEST_VOID(module, name) TEST(module, name)

#define XSIGMATEST_CALL(module, name)

// Fixture-based Google Test macro (TEST_F)
#define XSIGMATEST_F(fixture, name) TEST_F(fixture, name)

#else
// Simple assertion macros for non-Google Test builds
#define EXPECT_TRUE(condition)                                                             \
    do                                                                                     \
    {                                                                                      \
        if (!(condition))                                                                  \
        {                                                                                  \
            std::cerr << "EXPECT_TRUE failed: " << #condition << " at " << __FILE__ << ":" \
                      << __LINE__ << std::endl;                                            \
        }                                                                                  \
    } while (0)

#define EXPECT_FALSE(condition)                                                             \
    do                                                                                      \
    {                                                                                       \
        if (condition)                                                                      \
        {                                                                                   \
            std::cerr << "EXPECT_FALSE failed: " << #condition << " at " << __FILE__ << ":" \
                      << __LINE__ << std::endl;                                             \
        }                                                                                   \
    } while (0)

#define EXPECT_NEAR(expected, actual, tolerance)                                            \
    do                                                                                      \
    {                                                                                       \
        if (std::abs((expected) - (actual)) > tolerance)                                    \
        {                                                                                   \
            std::cerr << "EXPECT_NEAR failed: " << #expected << " != " << #actual << " at " \
                      << __FILE__ << ":" << __LINE__ << std::endl;                          \
        }                                                                                   \
    } while (0)

#define EXPECT_EQ(expected, actual)                                                       \
    do                                                                                    \
    {                                                                                     \
        if ((expected) != (actual))                                                       \
        {                                                                                 \
            std::cerr << "EXPECT_EQ failed: " << #expected << " != " << #actual << " at " \
                      << __FILE__ << ":" << __LINE__ << std::endl;                        \
        }                                                                                 \
    } while (0)

#define EXPECT_NE(expected, actual)                                                       \
    do                                                                                    \
    {                                                                                     \
        if ((expected) == (actual))                                                       \
        {                                                                                 \
            std::cerr << "EXPECT_NE failed: " << #expected << " == " << #actual << " at " \
                      << __FILE__ << ":" << __LINE__ << std::endl;                        \
        }                                                                                 \
    } while (0)

#define EXPECT_LT(val1, val2)                                                                   \
    do                                                                                          \
    {                                                                                           \
        if (!((val1) < (val2)))                                                                 \
        {                                                                                       \
            std::cerr << "EXPECT_LT failed: " << #val1 << " >= " << #val2 << " at " << __FILE__ \
                      << ":" << __LINE__ << std::endl;                                          \
        }                                                                                       \
    } while (0)

#define EXPECT_LE(val1, val2)                                                                  \
    do                                                                                         \
    {                                                                                          \
        if (!((val1) <= (val2)))                                                               \
        {                                                                                      \
            std::cerr << "EXPECT_LE failed: " << #val1 << " > " << #val2 << " at " << __FILE__ \
                      << ":" << __LINE__ << std::endl;                                         \
        }                                                                                      \
    } while (0)

#define EXPECT_GT(val1, val2)                                                                   \
    do                                                                                          \
    {                                                                                           \
        if (!((val1) > (val2)))                                                                 \
        {                                                                                       \
            std::cerr << "EXPECT_GT failed: " << #val1 << " <= " << #val2 << " at " << __FILE__ \
                      << ":" << __LINE__ << std::endl;                                          \
        }                                                                                       \
    } while (0)

#define EXPECT_GE(val1, val2)                                                                  \
    do                                                                                         \
    {                                                                                          \
        if (!((val1) >= (val2)))                                                               \
        {                                                                                      \
            std::cerr << "EXPECT_GE failed: " << #val1 << " < " << #val2 << " at " << __FILE__ \
                      << ":" << __LINE__ << std::endl;                                         \
        }                                                                                      \
    } while (0)

#define ASSERT_TRUE(condition)                                                             \
    do                                                                                     \
    {                                                                                      \
        if (!(condition))                                                                  \
        {                                                                                  \
            std::cerr << "ASSERT_TRUE failed: " << #condition << " at " << __FILE__ << ":" \
                      << __LINE__ << std::endl;                                            \
            throw std::runtime_error("Assertion failed: " #condition);                     \
        }                                                                                  \
    } while (0)

#define ASSERT_FALSE(condition)                                                             \
    do                                                                                      \
    {                                                                                       \
        if (condition)                                                                      \
        {                                                                                   \
            std::cerr << "ASSERT_FALSE failed: " << #condition << " at " << __FILE__ << ":" \
                      << __LINE__ << std::endl;                                             \
            throw std::runtime_error("Assertion failed: " #condition);                      \
        }                                                                                   \
    } while (0)

#define ASSERT_EQ(expected, actual)                                                       \
    do                                                                                    \
    {                                                                                     \
        if ((expected) != (actual))                                                       \
        {                                                                                 \
            std::cerr << "ASSERT_EQ failed: " << #expected << " != " << #actual << " at " \
                      << __FILE__ << ":" << __LINE__ << std::endl;                        \
            throw std::runtime_error("Assertion failed: " #expected " != " #actual);      \
        }                                                                                 \
    } while (0)

#define ASSERT_NE(expected, actual)                                                       \
    do                                                                                    \
    {                                                                                     \
        if ((expected) == (actual))                                                       \
        {                                                                                 \
            std::cerr << "ASSERT_NE failed: " << #expected << " == " << #actual << " at " \
                      << __FILE__ << ":" << __LINE__ << std::endl;                        \
            throw std::runtime_error("Assertion failed: " #expected " == " #actual);      \
        }                                                                                 \
    } while (0)

#define ASSERT_ANY_THROW(statement)                                                        \
    do                                                                                     \
    {                                                                                      \
        bool threw = false;                                                                \
        try                                                                                \
        {                                                                                  \
            statement;                                                                     \
        }                                                                                  \
        catch (...)                                                                        \
        {                                                                                  \
            threw = true;                                                                  \
        }                                                                                  \
        if (!threw)                                                                        \
        {                                                                                  \
            std::cerr << "ASSERT_ANY_THROW failed: " << #statement << " did not throw at " \
                      << __FILE__ << ":" << __LINE__ << std::endl;                         \
            throw std::runtime_error("Assertion failed: " #statement " did not throw");    \
        }                                                                                  \
    } while (0)

// Standard test main function
#define XSIGMATEST(module, testname) \
    int Test##testname(XSIGMA_UNUSED int argc, XSIGMA_UNUSED char* argv[])

#define XSIGMATEST_VOID(module, testname) \
    void test_##module##testname(XSIGMA_UNUSED int argc, XSIGMA_UNUSED char* argv[])

#define XSIGMATEST_CALL(module, testname) test_##module##testname(argc, argv);

// No fixture support without Google Test; make it explicit.
#define XSIGMATEST_F(fixture, name) \
    static_assert(false, "XSIGMATEST_F requires Google Test (PROJECT_HAS_GTEST=1)")

#endif

namespace xsigma
{
// Helper function to check memory alignment
inline bool IsAligned(void* ptr, size_t alignment)
{
    return (reinterpret_cast<uintptr_t>(ptr) % alignment) == 0;
}

inline bool ValidateMemory(const void* ptr, size_t size, uint8_t pattern)
{
    const uint8_t* bytes = static_cast<const uint8_t*>(ptr);
    for (size_t i = 0; i < size; ++i)
    {
        if (bytes[i] != pattern)
        {
            return false;
        }
    }
    return true;
}
}  // namespace xsigma

#endif  // XSIGMA_TEST_H