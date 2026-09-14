/**
 * @file example_profiling_basic.cpp
 * @brief CPU profiling through profiler's public session API.
 */

#include <algorithm>
#include <cmath>
#include <iostream>
#include <random>
#include <vector>

#include <profiler.h>

namespace xsigma::examples::profiling
{

std::vector<std::vector<double>> matrix_multiply(
    const std::vector<std::vector<double>>& a, const std::vector<std::vector<double>>& b)
{
    PROFILER_SCOPE("matrix_multiply");

    const size_t rows_a = a.size();
    const size_t cols_a = a[0].size();
    const size_t cols_b = b[0].size();

    std::vector<std::vector<double>> result(rows_a, std::vector<double>(cols_b, 0.0));

    {
        PROFILER_SCOPE("matrix_multiply_computation");

        for (size_t i = 0; i < rows_a; ++i)
        {
            for (size_t j = 0; j < cols_b; ++j)
            {
                for (size_t k = 0; k < cols_a; ++k)
                {
                    result[i][j] += a[i][k] * b[k][j];
                }
            }
        }
    }

    return result;
}

std::vector<std::vector<double>> generate_matrix(size_t rows, size_t cols)
{
    PROFILER_SCOPE("generate_matrix");

    std::vector<std::vector<double>> matrix(rows, std::vector<double>(cols));

    std::random_device                     rd;
    std::mt19937                           gen(rd());
    std::uniform_real_distribution<double> dis(0.0, 1.0);

    for (size_t i = 0; i < rows; ++i)
    {
        for (size_t j = 0; j < cols; ++j)
        {
            matrix[i][j] = dis(gen);
        }
    }

    return matrix;
}

void merge_sort(std::vector<double>& arr, size_t left, size_t right)
{
    PROFILER_SCOPE("merge_sort");

    if (left >= right)
    {
        return;
    }

    size_t mid = left + (right - left) / 2;

    merge_sort(arr, left, mid);
    merge_sort(arr, mid + 1, right);

    std::vector<double> temp(right - left + 1);
    size_t              i = left, j = mid + 1, k = 0;

    while (i <= mid && j <= right)
    {
        if (arr[i] <= arr[j])
        {
            temp[k++] = arr[i++];
        }
        else
        {
            temp[k++] = arr[j++];
        }
    }

    while (i <= mid)
    {
        temp[k++] = arr[i++];
    }
    while (j <= right)
    {
        temp[k++] = arr[j++];
    }

    for (size_t idx = 0; idx < temp.size(); ++idx)
    {
        arr[left + idx] = temp[idx];
    }
}

void example_cpu_profiler()
{
    std::cout << "\n=== CPU profiler session ===" << std::endl;

    profiler::session session;
    if (!session.start())
    {
        std::cout << "session failed to start" << std::endl;
        return;
    }

    {
        PROFILER_SCOPE("matrix_operations");

        const size_t matrix_size = 100;
        auto         matrix_a    = generate_matrix(matrix_size, matrix_size);
        auto         matrix_b    = generate_matrix(matrix_size, matrix_size);
        auto         result      = matrix_multiply(matrix_a, matrix_b);
        (void)result;

        std::cout << "  Matrix multiplication completed (" << matrix_size << "x" << matrix_size
                  << ")" << std::endl;
    }

    {
        PROFILER_SCOPE("sorting_operations");

        const size_t        array_size = 10000;
        std::vector<double> test_data(array_size);

        std::random_device                     rd;
        std::mt19937                           gen(rd());
        std::uniform_real_distribution<double> dis(0.0, 1000.0);

        for (size_t i = 0; i < array_size; ++i)
        {
            test_data[i] = dis(gen);
        }

        merge_sort(test_data, 0, test_data.size() - 1);

        std::cout << "  Sorting completed (" << array_size << " elements)" << std::endl;
    }

    session.stop();

    std::string const output_file = "xsigma_profile.json";
    session.write_trace(output_file);

    std::cout << "Trace saved to: " << output_file << std::endl;
}

}  // namespace xsigma::examples::profiling

int main()
{
    std::cout << "============================================" << std::endl;
    std::cout << "XSigma Profiling Examples" << std::endl;
    std::cout << "============================================" << std::endl;

    xsigma::examples::profiling::example_cpu_profiler();

    std::cout << "\n============================================" << std::endl;
    std::cout << "All examples completed!" << std::endl;
    std::cout << "============================================" << std::endl;

    return 0;
}
