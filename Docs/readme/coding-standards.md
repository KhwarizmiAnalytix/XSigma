# XSigma Coding Standards

## Overview

XSigma maintains strict coding standards to ensure code quality, consistency, and maintainability across the entire codebase. All contributions must adhere to these standards. This document provides a comprehensive guide to XSigma's coding conventions, best practices, and requirements.

For a quick reference, see the [Coding Standards section in README.md](../../README.md#coding-standards).

## Table of Contents

- [Core Principles](#core-principles)
  - [No Exceptions](#1-no-exceptions)
  - [RAII](#2-raii-resource-acquisition-is-initialization)
  - [Smart Pointers](#3-smart-pointers)
  - [Const Correctness](#4-const-correctness)
- [Naming Conventions](#naming-conventions)
- [Code Formatting](#code-formatting)
- [Include Path Rules](#include-path-rules)
- [DLL Export Macros](#dll-export-macros)
- [Testing Requirements](#testing-requirements)
- [Static Analysis](#static-analysis)
- [Documentation](#documentation)
- [Memory Management](#memory-management)
- [Concurrency and Thread Safety](#concurrency-and-thread-safety)
- [Security and Robustness](#security-and-robustness)
- [Use Standard Library Algorithms](#use-standard-library-algorithms)
  - [Prefer STL Algorithms Over Raw Loops](#prefer-stl-algorithms-over-raw-loops)
  - [Common STL Algorithms](#common-stl-algorithms)
  - [Incorrect vs. Correct Approaches](#incorrect-vs-correct-approaches)
  - [Custom Implementations](#custom-implementations)
- [Header and Implementation File Organization](#header-and-implementation-file-organization)
  - [File Naming Convention](#file-naming-convention)
  - [Correct File Organization](#correct-file-organization)
  - [Why This Matters](#why-this-matters)
  - [Example: Correct Organization](#example-correct-organization)
  - [Inline Implementations](#inline-implementations)
  - [Header and Implementation File Extensions](#header-and-implementation-file-extensions)
  - [One Class Per File Pair](#one-class-per-file-pair)
  - [File Names Must Match Class Names](#file-names-must-match-class-names)
- [Builder Class Conventions](#builder-class-conventions)
  - [Overview](#overview-1)
  - [Builder Class Naming](#builder-class-naming)
  - [Member Variables](#member-variables)
  - [Method Naming and Signature](#method-naming-and-signature)
  - [Complete Builder Example](#complete-builder-example)
  - [Builder Implementation Example](#builder-implementation-example)
  - [Using the Builder](#using-the-builder)
  - [Builder Conventions Summary](#builder-conventions-summary)
  - [Constructor Visibility for Classes with Builders](#constructor-visibility-for-classes-with-builders)
  - [XSigma Macros Usage](#xsigma-macros-usage)
    - [XSIGMA_NODISCARD](#xsigma_nodiscard)
    - [XSIGMA_UNUSED](#xsigma_unused)
    - [noexcept](#noexcept)
    - [Macro Usage Summary](#macro-usage-summary)
    - [Benefits of Using These Macros](#benefits-of-using-these-macros)
- [Clang-Tidy Configuration and Enforcement](#clang-tidy-configuration-and-enforcement)
  - [Overview](#overview-2)
  - [Running Clang-Tidy Locally](#running-clang-tidy-locally)
  - [Enabled Clang-Tidy Checks](#enabled-clang-tidy-checks)
  - [Common Clang-Tidy Warnings and Fixes](#common-clang-tidy-warnings-and-fixes)
  - [Interpreting Clang-Tidy Output](#interpreting-clang-tidy-output)
  - [Clang-Tidy Configuration File](#clang-tidy-configuration-file)
  - [Suppressing Clang-Tidy Warnings](#suppressing-clang-tidy-warnings)
- [Auto Keyword Usage Guidelines](#auto-keyword-usage-guidelines)
  - [Overview](#overview-3)
  - [When `auto` is Required](#when-auto-is-required)
  - [When `auto` is Preferred](#when-auto-is-preferred)
  - [When Explicit Types Should Be Used](#when-explicit-types-should-be-used)
  - [Reference Types with `auto`](#reference-types-with-auto)
  - [Clang-Tidy Auto Enforcement](#clang-tidy-auto-enforcement)
  - [Auto Usage Summary](#auto-usage-summary)
- [Common Pitfalls to Avoid](#common-pitfalls-to-avoid)
- [Related Documentation](#related-documentation)

## Core Principles

### 1. No Exceptions

XSigma **prohibits exception-based error handling**. Instead, use return values to communicate success or failure:

```cpp
// ❌ Incorrect - Never use exceptions
try {
  risky_function();
} catch (...) {
  // handle error
}

// ✅ Correct - Use return values
if (!safe_function()) {
  // handle error gracefully
  return false;
}

// ✅ Better - Use std::optional
std::optional<Result> result = safe_function();
if (!result.has_value()) {
  // handle error gracefully
  return std::nullopt;
}
```

**Benefits:**
- Predictable error handling
- Easier to test and trace
- Better performance (no exception overhead)
- Clearer control flow

### 2. RAII (Resource Acquisition Is Initialization)

All resources must be managed using RAII principles. Resources are acquired in constructors and released in destructors:

```cpp
// ✅ Correct - RAII pattern
class file_handler {
 public:
  file_handler(const std::string& filename) {
    file_ = std::fopen(filename.c_str(), "r");
    if (!file_) {
      throw std::runtime_error("Failed to open file");
    }
  }

  ~file_handler() {
    if (file_) {
      std::fclose(file_);
    }
  }

 private:
  FILE* file_;
};
```

### 3. Smart Pointers

Use `std::unique_ptr` and `std::shared_ptr` instead of raw pointers for ownership:

```cpp
// ❌ Incorrect - Raw pointer ownership
class data_processor {
 private:
  data_buffer* buffer_;  // Who owns this?
};

// ✅ Correct - Exclusive ownership
class data_processor {
 private:
  std::unique_ptr<data_buffer> buffer_;
};

// ✅ Correct - Shared ownership
class data_processor {
 private:
  std::shared_ptr<data_buffer> buffer_;
};
```

**Guidelines:**
- Use `std::unique_ptr<T>` for exclusive ownership (default choice)
- Use `std::shared_ptr<T>` for shared ownership (minimize use)
- Use `std::weak_ptr<T>` to observe shared resources without extending lifetime
- Prefer `std::make_unique` and `std::make_shared` over direct `new`

### 4. Const Correctness

Mark all non-mutating methods and variables as `const`:

```cpp
// ✅ Correct - Const correctness
class calculator {
 public:
  int get_result() const {  // Non-mutating method
    return result_;
  }

  void set_value(int value) {  // Mutating method
    result_ = value;
  }

 private:
  int result_;
};

// ✅ Correct - Const variables
const int kMaxValue = 100;
const std::string kDefaultName = "default";
```

## Naming Conventions

XSigma uses `snake_case` for most identifiers, following the Google C++ Style Guide:

| Element | Convention | Example | Notes |
|---------|-----------|---------|-------|
| Class | `snake_case` | `class my_class` | All lowercase with underscores |
| Struct | `snake_case` | `struct data_point` | Same as class |
| Function | `snake_case` | `void do_something()` | All lowercase with underscores |
| Member Variable | `snake_case_` | `int count_;` | Trailing underscore distinguishes from locals |
| Local Variable | `snake_case` | `int local_value` | No trailing underscore |
| Constant | `kConstantName` | `const int kMaxCount = 100;` | Prefer `kConstantName` for readability |
| Namespace | `snake_case` | `namespace xsigma` | All lowercase |
| Enum | `snake_case` | `enum class color_type` | Use `enum class` for type safety |
| Enum Value | `snake_case` | `color_type::dark_red` | All lowercase |

### Member Variable Naming Convention

**CRITICAL RULE:** All class member variables MUST use `snake_case` naming with a trailing underscore (`_`).

**PROHIBITED:** The `m_` prefix (e.g., `m_count`, `m_value`, `m_data`) is **strictly forbidden** for member variables.

**REQUIRED:** Use `snake_case` with a trailing underscore (e.g., `count_`, `value_`, `data_ptr_`).

**Rationale:** The trailing underscore clearly distinguishes member variables from local variables and function parameters, improving code readability and preventing naming conflicts.

#### Member Variable Examples

❌ **Incorrect - Using m_ prefix:**
```cpp
class my_class {
 private:
  int m_count;           // WRONG - Do not use m_ prefix
  std::string m_name;    // WRONG - Do not use m_ prefix
  DataType* m_data;      // WRONG - Do not use m_ prefix
};
```

✅ **Correct - Using trailing underscore:**
```cpp
class my_class {
 private:
  int count_;            // Correct - snake_case with trailing _
  std::string name_;     // Correct - snake_case with trailing _
  DataType* data_;       // Correct - snake_case with trailing _
};
```

### Naming Examples

```cpp
// ✅ Correct naming
class data_processor {
 public:
  void process_data(const std::vector<int>& input_data) {
    int total_count = 0;  // Local variable - no trailing underscore
    for (int value : input_data) {
      total_count += value;
    }
  }

 private:
  int result_;                    // Member variable - trailing underscore
  const int kMaxBufferSize = 1024;  // Constant - kConstantName style
};

enum class status_type {
  success,
  error,
  pending
};
```

## Code Formatting

### Automatic Formatting

XSigma uses `clang-format` for automatic code formatting. Configuration is in `.clang-format`:

- **Line length**: 100 characters maximum
- **Indentation**: 2 spaces (no tabs)
- **Brace style**: Opening brace on same line (Google C++ Style)
- **Spacing**: Consistent spacing around operators and keywords

### Format Your Code

Before committing, format your code using the linter:

```bash
pip install lint-tool
lintrunner -a
```

### Example Formatting

```cpp
// ✅ Correct formatting
if (x == y) {
  foo();
} else {
  bar();
}

class my_class {
 public:
  void do_something() {
    // implementation
  }

 private:
  int value_;
};
```

## Include Path Rules

### Include Path Convention

Include paths must start from the project subfolder, not the repository root:

```cpp
// ❌ Incorrect - Do not use Core/ prefix
#include "Core/xxx/yyy/a.h"

// ✅ Correct - Start from subfolder
#include "xxx/yyy/a.h"
```

### Include Ordering

Order includes as follows (separated by blank lines):

1. Standard library headers
2. Third-party library headers
3. Project headers

```cpp
// ✅ Correct include ordering
#include <memory>
#include <string>
#include <vector>

#include <fmt/format.h>

#include "xxx/yyy/a.h"
#include "xxx/zzz/b.h"
```

Third-party headers (fmt, gtest, benchmark, sleef, mimalloc, Logging,
Parallel, Profiler, …) **must** use angle brackets (`#include <fmt/format.h>`,
`#include <logging/logging.h>`, `#include <profiler.h>`,
`#include <parallel.h>`). Quotes
are for project headers only. Do not write `#include "third_party/..."`.
Logging's `<logging/util/exception.h>` is third-party; Core's `"util/hash.h"` is not.
`"profiler/"` is Memory's first-party profiler, not ThirdParty/Profiler.

## DLL Export Macros

Apply the **library’s own** visibility macros (Windows export / Unix default
visibility). Core uses the project prefix `XSIGMA_API` / `XSIGMA_VISIBILITY`.
Every other library uses its own family (`MEMORY_API`, `VECTORIZATION_API`,
`LOGGING_VISIBILITY`, …) from `Library/<Lib>/common/<lib>_export.h`.

| Context | Core | Other libraries | Usage |
|---------|------|-----------------|-------|
| Function | `XSIGMA_API` | `<LIB>_API` | Before function return type |
| Class | `XSIGMA_VISIBILITY` | `<LIB>_VISIBILITY` | Before `class` keyword |

### DLL Export Examples

```cpp
// ✅ Correct DLL export usage
class XSIGMA_VISIBILITY my_class {
 public:
  XSIGMA_API void do_something();
  XSIGMA_API int calculate(int value);
  XSIGMA_API std::string get_name() const;
};

// ✅ Correct for standalone functions
XSIGMA_API void process_data(const std::vector<int>& data);
XSIGMA_API bool validate_input(const std::string& input);
```

**Important:** Omitting these macros will cause linking errors on Windows and symbol visibility issues on Linux/macOS.

## Testing Requirements

### Coverage and Quality

- **Minimum 98% code coverage** required for all new code
- Tests must be deterministic, reproducible, and isolated
- Use Google Test `TEST` / `TEST_F`. Core still defines `XSIGMATEST` as an
  alias for `TEST`; do not introduce that macro in other libraries.

### Test File Naming and Structure

- Test files must mirror source file hierarchy
- Use naming pattern `Test[ClassName].cpp` (CamelCase for test files only)
- Place test files in the same directory structure under `Tests/` subdirectory

**Example:**
- Source: `Core/xxx/yyy/my_class.h`
- Test: `Core/xxx/yyy/Tests/TestMyClass.cpp`

### Test Scope

Tests must cover:
- Happy paths and success cases
- Boundary conditions and edge cases
- Error handling and failure scenarios
- Null pointers, empty collections, and invalid inputs
- State changes and side effects

### Writing Tests

```cpp
TEST(my_class_test, handles_valid_input) {
  my_class obj;
  EXPECT_TRUE(obj.do_something());
}

TEST(my_class_test, handles_invalid_input) {
  my_class obj;
  EXPECT_FALSE(obj.do_something_with(-1));
}

TEST(my_class_test, handles_null_pointer) {
  my_class obj;
  EXPECT_FALSE(obj.process(nullptr));
}

TEST(my_class_test, handles_empty_collection) {
  my_class obj;
  std::vector<int> empty;
  EXPECT_TRUE(obj.process_collection(empty));
}
```

## Static Analysis

All code must pass static analysis checks:

```bash
cd Scripts

# Run clang-tidy
python setup.py config.build.ninja.clang.clangtidy

# Run cppcheck
python setup.py config.build.ninja.clang.cppcheck

# Run IWYU (Include-What-You-Use)
python setup.py config.build.ninja.clang.iwyu
```

## Documentation

### Documentation Standards

- Document **intent and rationale**, not obvious implementation details
- Use Doxygen-style comments for public APIs
- Keep comments synchronized with code changes
- Annotate non-trivial algorithms and corner cases

### Doxygen-Style Comments

```cpp
/**
 * @brief Calculates the sum of two integers.
 * @param a First integer
 * @param b Second integer
 * @return Sum of a and b
 */
XSIGMA_API int add(int a, int b);

/**
 * @brief Processes data from the input buffer.
 * @param input_data Vector of input values
 * @return true if processing succeeded, false otherwise
 */
bool process_data(const std::vector<int>& input_data);
```

## Memory Management

### Smart Pointer Guidelines

```cpp
// ✅ Exclusive ownership - use unique_ptr
std::unique_ptr<data_buffer> buffer = std::make_unique<data_buffer>();

// ✅ Shared ownership - use shared_ptr
std::shared_ptr<resource> res = std::make_shared<resource>();

// ✅ Observe shared resource - use weak_ptr
std::weak_ptr<resource> observer = res;
```

### Avoid Raw Pointers for Ownership

```cpp
// ❌ Incorrect - Raw pointer ownership is ambiguous
class processor {
 private:
  data_buffer* buffer_;  // Who owns this? When is it deleted?
};

// ✅ Correct - Clear ownership semantics
class processor {
 private:
  std::unique_ptr<data_buffer> buffer_;
};
```

## Concurrency and Thread Safety

### Thread-Safe Code

- Protect shared resources using scoped locks
- Use `std::scoped_lock`, `std::lock_guard`, or `std::unique_lock`
- Document thread-safety guarantees in class comments
- Use atomic types for simple shared state

```cpp
// ✅ Thread-safe counter
class thread_safe_counter {
 public:
  void increment() {
    std::scoped_lock lock(mutex_);
    ++count_;
  }

  int get() const {
    std::scoped_lock lock(mutex_);
    return count_;
  }

 private:
  mutable std::mutex mutex_;
  int count_ = 0;
};
```

## Security and Robustness

### Input Validation

- Validate all input; never assume trust
- Check return values of all system calls
- Implement boundary checks on all buffers and arrays
- Use `.at()` instead of `[]` for bounds checking

### Secure Coding Practices

- Avoid unsafe functions: `strcpy`, `sprintf`, `gets`, `scanf`
- Use safe alternatives: `strncpy`, `snprintf`, `std::string`, `std::getline`
- Sanitize external data before use
- Never hardcode credentials or secrets

## Use Standard Library Algorithms

### Prefer STL Algorithms Over Raw Loops

XSigma requires developers to use existing STL algorithms instead of reimplementing equivalent functionality with raw loops. The C++ Standard Library provides a comprehensive set of algorithms that are optimized, well-tested, and more readable than manual loops.

### Common STL Algorithms

| Algorithm | Purpose | Example |
|-----------|---------|---------|
| `std::all_of` | Check if all elements satisfy a condition | `std::all_of(v.begin(), v.end(), [](int x) { return x > 0; })` |
| `std::any_of` | Check if any element satisfies a condition | `std::any_of(v.begin(), v.end(), [](int x) { return x < 0; })` |
| `std::none_of` | Check if no elements satisfy a condition | `std::none_of(v.begin(), v.end(), [](int x) { return x == 0; })` |
| `std::find` | Find first element with specific value | `std::find(v.begin(), v.end(), target)` |
| `std::find_if` | Find first element satisfying a condition | `std::find_if(v.begin(), v.end(), predicate)` |
| `std::count` | Count elements with specific value | `std::count(v.begin(), v.end(), value)` |
| `std::count_if` | Count elements satisfying a condition | `std::count_if(v.begin(), v.end(), predicate)` |
| `std::transform` | Apply function to each element | `std::transform(v.begin(), v.end(), result.begin(), func)` |
| `std::sort` | Sort elements | `std::sort(v.begin(), v.end())` |
| `std::for_each` | Apply function to each element (for side effects) | `std::for_each(v.begin(), v.end(), func)` |

### Incorrect vs. Correct Approaches

**❌ Incorrect - Raw loop:**
```cpp
// Manual loop to check if all values are positive
bool all_positive = true;
for (int i = 0; i < values.size(); ++i) {
  if (values[i] <= 0) {
    all_positive = false;
    break;
  }
}
```

**✅ Correct - STL algorithm:**
```cpp
// Use std::all_of
bool all_positive = std::all_of(values.begin(), values.end(),
                                 [](int x) { return x > 0; });
```

**❌ Incorrect - Raw loop:**
```cpp
// Manual loop to find an element
int target = 42;
int index = -1;
for (int i = 0; i < values.size(); ++i) {
  if (values[i] == target) {
    index = i;
    break;
  }
}
```

**✅ Correct - STL algorithm:**
```cpp
// Use std::find
auto it = std::find(values.begin(), values.end(), 42);
if (it != values.end()) {
  int index = std::distance(values.begin(), it);
}
```

**❌ Incorrect - Raw loop:**
```cpp
// Manual loop to transform elements
std::vector<int> result;
for (int i = 0; i < values.size(); ++i) {
  result.push_back(values[i] * 2);
}
```

**✅ Correct - STL algorithm:**
```cpp
// Use std::transform
std::vector<int> result(values.size());
std::transform(values.begin(), values.end(), result.begin(),
               [](int x) { return x * 2; });
```

### Custom Implementations

If no appropriate STL algorithm exists for your use case, you **must** provide a comment explaining why a custom implementation is necessary:

```cpp
// ✅ Correct - Custom implementation with explanation
// Custom implementation needed because we need to process elements
// in reverse order while maintaining original indices for error reporting.
// No STL algorithm provides this specific combination of requirements.
std::vector<error_info> process_with_indices(const std::vector<int>& data) {
  std::vector<error_info> errors;
  for (int i = data.size() - 1; i >= 0; --i) {
    if (!validate(data[i])) {
      errors.push_back({i, "validation failed"});
    }
  }
  return errors;
}
```

---

## Header and Implementation File Organization

### File Naming Convention

Function declarations and their implementations must follow a consistent naming convention. If a function is declared in a `.h` header file, its implementation **must** be in the corresponding `.cpp` implementation file with the same base name.

### Correct File Organization

| Declaration | Implementation | ✅ Correct | ❌ Incorrect |
|-------------|----------------|-----------|-------------|
| `my_class.h` | `my_class.cpp` | ✅ Yes | - |
| `my_class.h` | `my_class_impl.cpp` | - | ❌ No |
| `my_class.h` | `my_class_implementation.cpp` | - | ❌ No |
| `data_processor.h` | `data_processor.cpp` | ✅ Yes | - |
| `data_processor.h` | `processor_impl.cpp` | - | ❌ No |

### Why This Matters

- **Consistency**: Developers can easily locate implementations by knowing the header file name
- **Maintainability**: Clear 1:1 mapping between headers and implementations
- **Build System**: CMake and other build tools can automatically discover and link files
- **Readability**: No confusion about where implementations are located

### Example: Correct Organization

**File: `Core/data/my_class.h`**
```cpp
#pragma once

#include <string>

namespace xsigma {

class XSIGMA_VISIBILITY my_class {
 public:
  XSIGMA_API my_class();
  XSIGMA_API ~my_class();

  XSIGMA_API void process_data(const std::string& input);
  XSIGMA_API std::string get_result() const;

 private:
  std::string result_;
};

}  // namespace xsigma
```

**File: `Core/data/my_class.cpp`** (✅ Correct)
```cpp
#include "data/my_class.h"

namespace xsigma {

my_class::my_class() : result_("") {}

my_class::~my_class() {}

void my_class::process_data(const std::string& input) {
  result_ = input;
}

std::string my_class::get_result() const {
  return result_;
}

}  // namespace xsigma
```

**File: `Core/data/my_class_impl.cpp`** (❌ Incorrect - Wrong naming)
```cpp
// This file should NOT exist. Implementation should be in my_class.cpp
```

### Inline Implementations

For small, performance-critical functions, implementations can be inline in the header file:

```cpp
// ✅ Correct - Inline implementation in header
class XSIGMA_VISIBILITY my_class {
 public:
  // Simple getter - can be inline
  int get_value() const { return value_; }

  // Complex method - should be in .cpp file
  XSIGMA_API void process_complex_data(const std::vector<int>& data);

 private:
  int value_;
};
```

### Header and Implementation File Extensions

XSigma uses **strict file extension conventions** to maintain consistency across the codebase:

- **Header files**: `.h` (not `.hpp`, `.hxx`, or other variants)
- **Implementation files**: `.cpp` (not `.cpp`, `.cc`, `.c++`, or other variants)

This convention applies to all C++ source files in the XSigma project.

**Rationale:**
- **Consistency**: Uniform extensions across the entire codebase make it easier to identify file types
- **Build System Integration**: CMake and other build tools are configured to recognize `.h` and `.cpp` files
- **Cross-Platform Compatibility**: `.cpp` is more portable than `.cpp` on some systems
- **Clarity**: Distinguishes XSigma files from third-party code that may use different conventions

**Examples:**

✅ **Correct file extensions:**
```
Core/data/my_class.h
Core/data/my_class.cpp
Core/processing/data_processor.h
Core/processing/data_processor.cpp
Library/utilities/string_helper.h
Library/utilities/string_helper.cpp
```

❌ **Incorrect file extensions:**
```
Core/data/my_class.hpp          // Wrong - use .h
Core/data/my_class.cpp          // Wrong - use .cpp
Core/data/my_class.hxx          // Wrong - use .h
Core/data/my_class.cc           // Wrong - use .cpp
Core/data/my_class.c++          // Wrong - use .cpp
Core/data/my_class_impl.cpp     // Wrong - use .cpp and match header name
```

### One Class Per File Pair

Each `.h`/`.cpp` file pair **should contain exactly one primary class**. Small helper classes or nested classes that are only used within that primary class are acceptable exceptions.

**Rationale:**
- **Maintainability**: Clear separation of concerns makes code easier to understand and modify
- **Compilation Times**: Smaller files compile faster and reduce unnecessary recompilation
- **Code Organization**: Developers can quickly locate class definitions
- **Testing**: Easier to write focused unit tests for individual classes
- **Dependency Management**: Reduces coupling between unrelated classes

**Examples:**

✅ **Correct - One class per file pair:**
```
Core/data/my_class.h
├── class my_class { ... }

Core/data/data_processor.h
├── class data_processor { ... }

Core/utilities/string_helper.h
├── class string_helper { ... }
```

❌ **Incorrect - Multiple unrelated classes in one file:**
```
Core/data/my_class.h
├── class my_class { ... }
├── class data_processor { ... }      // Wrong - separate file needed
├── class string_helper { ... }       // Wrong - separate file needed

Core/processing/processor.h
├── class processor { ... }
├── class validator { ... }           // Wrong - separate file needed
├── class formatter { ... }           // Wrong - separate file needed
```

**Exception - Helper classes:**
```cpp
// ✅ Acceptable - Helper class only used within primary class
// File: Core/data/my_class.h
namespace xsigma {

class XSIGMA_VISIBILITY my_class {
 public:
  // ... public interface ...
 private:
  // Helper class used only internally
  class internal_helper {
    // ... implementation ...
  };

  internal_helper helper_;
};

}  // namespace xsigma
```

### File Names Must Match Class Names

File names **must** match the name of the main class they contain. The file name should be the class name converted to `snake_case` if the class uses `snake_case` naming.

**Rationale:**
- **Predictability**: Developers can immediately find a class by its name
- **Consistency**: No ambiguity about which file contains which class
- **Build System**: Automated tools can map classes to files
- **Code Review**: Easier to verify that files are organized correctly

**Examples:**

✅ **Correct - File names match class names:**
```
Class: my_class
Files: my_class.h, my_class.cpp

Class: data_processor
Files: data_processor.h, data_processor.cpp

Class: string_helper
Files: string_helper.h, string_helper.cpp

Class: configuration_builder
Files: configuration_builder.h, configuration_builder.cpp
```

❌ **Incorrect - File names don't match class names:**
```
Class: my_class
Files: processor.h, processor.cpp          // Wrong - name doesn't match

Class: data_processor
Files: data_proc.h, data_proc.cpp          // Wrong - abbreviated name

Class: string_helper
Files: helper.h, helper.cpp                // Wrong - incomplete name

Class: configuration_builder
Files: builder.h, builder.cpp              // Wrong - incomplete name

Class: my_class
Files: my_class_impl.h, my_class_impl.cpp  // Wrong - extra suffix
```

**File Path Examples:**

```
Core/
├── data/
│   ├── my_class.h              ✅ Correct
│   ├── my_class.cpp
│   ├── data_processor.h        ✅ Correct
│   ├── data_processor.cpp
│   └── processor.h             ❌ Wrong - should be data_processor.h
│
├── processing/
│   ├── string_helper.h         ✅ Correct
│   ├── string_helper.cpp
│   └── helper.h                ❌ Wrong - should be string_helper.h
│
└── builders/
    ├── configuration_builder.h ✅ Correct
    ├── configuration_builder.cpp
    └── builder.h               ❌ Wrong - should be configuration_builder.h
```

---

## Builder Class Conventions

### Overview

XSigma uses the builder pattern for constructing complex objects. Builder classes follow strict naming and implementation conventions to ensure consistency and enable fluent method chaining.

### Builder Class Naming

Builder class names **must** end with `_builder`:

```cpp
// ✅ Correct
class my_class_builder { /* ... */ };
class data_processor_builder { /* ... */ };
class configuration_builder { /* ... */ };

// ❌ Incorrect
class my_class_builder_impl { /* ... */ };
class builder_my_class { /* ... */ };
class my_class_factory { /* ... */ };
```

### Member Variables

Builders **prefer** using `ptr_mutable<xxx>` to hold the object under construction. This is the recommended approach for clear ownership semantics:

```cpp
// ✅ Preferred - Using ptr_mutable
class my_class_builder {
 private:
  ptr_mutable<my_class> object_;
};

// ⚠️ Acceptable but less preferred - Using raw pointer
class my_class_builder {
 private:
  my_class* object_;  // Ownership is ambiguous
};
```

**Note:** While `ptr_mutable<xxx>` is preferred, other approaches are acceptable if they clearly communicate ownership semantics.

### Method Naming and Signature

All setter methods **must** follow the `with_<field>` naming convention:

| Requirement | Rule | Example |
|-------------|------|---------|
| Method name | Start with `with_` | `with_name()`, `with_value()` |
| Parameters | Exactly one parameter | `with_name(const std::string& name)` |
| Return type | Start with `xsigma::` | `xsigma::my_class_builder&` |
| Documentation | Descriptive comment required | `/// Sets the name for the object` |

### Complete Builder Example

```cpp
// ✅ Correct builder implementation
namespace xsigma {

/// Builder for constructing my_class instances with fluent interface.
class XSIGMA_VISIBILITY my_class_builder {
 public:
  /// Creates a new builder for my_class.
  XSIGMA_API my_class_builder();

  /// Sets the name for the object being constructed.
  /// @param name The name to set
  /// @return Reference to this builder for method chaining
  XSIGMA_API xsigma::my_class_builder& with_name(const std::string& name);

  /// Sets the value for the object being constructed.
  /// @param value The value to set
  /// @return Reference to this builder for method chaining
  XSIGMA_API xsigma::my_class_builder& with_value(int value);

  /// Sets the description for the object being constructed.
  /// @param description The description to set
  /// @return Reference to this builder for method chaining
  XSIGMA_API xsigma::my_class_builder& with_description(
      const std::string& description);

  /// Builds and returns the constructed my_class instance.
  /// @return Constructed my_class object
  XSIGMA_API my_class build();

 private:
  ptr_mutable<my_class> object_;
};

}  // namespace xsigma
```

### Builder Implementation Example

```cpp
// ✅ Correct builder implementation in .cpp file
namespace xsigma {

my_class_builder::my_class_builder()
    : object_(std::make_unique<my_class>()) {}

xsigma::my_class_builder& my_class_builder::with_name(
    const std::string& name) {
  object_->set_name(name);
  return *this;
}

xsigma::my_class_builder& my_class_builder::with_value(int value) {
  object_->set_value(value);
  return *this;
}

xsigma::my_class_builder& my_class_builder::with_description(
    const std::string& description) {
  object_->set_description(description);
  return *this;
}

my_class my_class_builder::build() {
  return *object_;
}

}  // namespace xsigma
```

### Using the Builder

```cpp
// ✅ Fluent builder usage
xsigma::my_class obj = xsigma::my_class_builder()
    .with_name("example")
    .with_value(42)
    .with_description("An example object")
    .build();
```

### Builder Conventions Summary

| Element | Rule Type | Requirement | Example |
|---------|-----------|-------------|---------|
| **Class name** | Must | Ends with `_builder` | `my_class_builder` |
| **Member variable** | Preferred | Use `ptr_mutable<xxx>` to hold the object being constructed | `ptr_mutable<my_class> object_;` |
| **Setter method name** | Must | Follows `with_<field>` naming | `with_name()` |
| **Setter parameters** | Must | Exactly one parameter | `with_name(const std::string& name)` |
| **Setter return type** | Must | Starts with `xsigma::` for fluent chaining | `xsigma::my_class_builder&` |
| **Method documentation** | Must | Each method must have a descriptive comment | `/// Sets the name for the object` |
| **Class documentation** | Must | Describes the role of the builder | `/// Builder for constructing my_class instances` |

### Constructor Visibility for Classes with Builders

When a class has a corresponding builder class, the class's constructors **must** be declared as `private` or `protected` to enforce the use of the builder pattern. This prevents direct instantiation and ensures all objects are created through the builder.

**Rationale:**
- **Pattern Enforcement**: Guarantees that objects are only created through the builder, ensuring all required initialization steps are followed
- **Consistency**: Prevents accidental direct instantiation that bypasses builder logic
- **API Clarity**: Makes it clear to users that the builder is the intended way to create instances
- **Validation**: Ensures all validation and setup logic in the builder is executed

**Implementation:**

The builder class should be declared as a `friend` to access the private constructor:

```cpp
// ✅ Correct - Private constructor with builder as friend
namespace xsigma {

class XSIGMA_VISIBILITY my_class {
 public:
  // No public constructors - use builder instead

  // Public methods
  XSIGMA_API void process_data(const std::string& input);
  XSIGMA_API std::string get_result() const;

 private:
  // Private constructor - only accessible to builder
  my_class();

  // Builder is a friend and can access private constructor
  friend class my_class_builder;

  std::string result_;
};

/// Builder for constructing my_class instances
class XSIGMA_VISIBILITY my_class_builder {
 public:
  XSIGMA_API my_class_builder();
  XSIGMA_API xsigma::my_class_builder& with_name(const std::string& name);
  XSIGMA_API my_class build();

 private:
  ptr_mutable<my_class> object_;
};

}  // namespace xsigma
```

**❌ Incorrect - Public constructor allows direct instantiation:**

```cpp
namespace xsigma {

class XSIGMA_VISIBILITY my_class {
 public:
  // ❌ Wrong - Public constructor bypasses builder
  XSIGMA_API my_class();

  XSIGMA_API void process_data(const std::string& input);
  XSIGMA_API std::string get_result() const;

 private:
  std::string result_;
};

}  // namespace xsigma

// Users can now bypass the builder:
// ❌ This should not be allowed
xsigma::my_class obj;  // Direct instantiation - bypasses builder logic
```

**Protected Constructor Exception:**

Use `protected` constructors when the class is meant to be subclassed:

```cpp
// ✅ Correct - Protected constructor for base classes
class XSIGMA_VISIBILITY base_class {
 public:
  // No public constructors

 protected:
  // Protected constructor - accessible to derived classes and builder
  base_class();

  friend class base_class_builder;
};
```

### XSigma Macros Usage

XSigma provides several important macros from `macros.h` that must be used throughout the codebase to improve code quality, enable compiler warnings, and support static analysis.

#### XSIGMA_NODISCARD

**Purpose:** Marks functions whose return values should not be ignored. The compiler will warn if the return value is discarded.

**When Required:**
- Functions returning error codes or status values
- Functions returning resource handles or pointers
- Functions returning important computation results
- Functions that perform operations with side effects only through return values

**When Optional:**
- Functions returning `void`
- Functions with obvious side effects (e.g., `print()`, `log()`)

**Examples:**

✅ **Correct - Using XSIGMA_NODISCARD:**
```cpp
// Error code should not be ignored
XSIGMA_NODISCARD XSIGMA_API bool validate_input(const std::string& input);

// Resource handle should not be ignored
XSIGMA_NODISCARD XSIGMA_API std::unique_ptr<resource> create_resource();

// Important result should not be ignored
XSIGMA_NODISCARD XSIGMA_API int calculate_value(int x, int y);

// Optional result should not be ignored
XSIGMA_NODISCARD XSIGMA_API std::optional<data> fetch_data(int id);
```

❌ **Incorrect - Missing XSIGMA_NODISCARD:**
```cpp
// ❌ Error code can be accidentally ignored
XSIGMA_API bool validate_input(const std::string& input);

// ❌ Resource handle can be accidentally ignored
XSIGMA_API std::unique_ptr<resource> create_resource();

// ❌ Important result can be accidentally ignored
XSIGMA_API int calculate_value(int x, int y);
```

**Usage Example:**
```cpp
// ✅ Correct - Return value is used
if (validate_input(user_input)) {
  process_input(user_input);
}

// ❌ Incorrect - Return value is ignored (compiler warning)
validate_input(user_input);  // Warning: nodiscard attribute ignored
```

#### XSIGMA_UNUSED

**Purpose:** Marks intentionally unused parameters to suppress compiler warnings. Used in interface implementations or callbacks where not all parameters are needed.

**When Required:**
- Interface implementations that don't use all parameters
- Callback functions that don't use all parameters
- Virtual function overrides that don't use all parameters
- Template specializations that don't use all parameters

**When Optional:**
- Parameters that are actually used
- Parameters in private functions where unused parameters are obvious

**Examples:**

✅ **Correct - Using XSIGMA_UNUSED:**
```cpp
// Interface implementation that doesn't use all parameters
class my_handler : public event_handler {
 public:
  void on_event(XSIGMA_UNUSED int event_id, const std::string& message) override {
    // Only uses message, not event_id
    log_message(message);
  }
};

// Callback that doesn't use all parameters
void process_with_callback(
    std::function<void(XSIGMA_UNUSED int status, const data& result)> callback) {
  data result = compute();
  callback(0, result);  // Caller might not use status
}

// Virtual function override
class XSIGMA_VISIBILITY my_processor : public base_processor {
 public:
  XSIGMA_API void process(XSIGMA_UNUSED const config& cfg) override {
    // Uses default configuration, doesn't need cfg parameter
    process_with_defaults();
  }
};
```

❌ **Incorrect - Missing XSIGMA_UNUSED:**
```cpp
// ❌ Compiler warning: unused parameter 'event_id'
class my_handler : public event_handler {
 public:
  void on_event(int event_id, const std::string& message) override {
    log_message(message);  // event_id is not used
  }
};

// ❌ Compiler warning: unused parameter 'status'
void process_with_callback(
    std::function<void(int status, const data& result)> callback) {
  data result = compute();
  callback(0, result);
}
```

#### noexcept

**Purpose:** Specifies that a function is guaranteed not to throw exceptions. Aligns with XSigma's no-exceptions policy and enables compiler optimizations.

**When Required:**
- Destructors (always use `noexcept`)
- Move constructors and move assignment operators
- Functions that explicitly handle all errors without throwing
- Swap functions and other exception-safe operations

**When Recommended:**
- Simple getter functions
- Functions that only call other `noexcept` functions
- Functions that use only error codes or return values for error handling

**Examples:**

✅ **Correct - Using noexcept:**
```cpp
class XSIGMA_VISIBILITY my_class {
 public:
  // Destructor - always noexcept
  XSIGMA_API ~my_class() noexcept;

  // Move constructor - should be noexcept
  XSIGMA_API my_class(my_class&& other) noexcept;

  // Move assignment - should be noexcept
  XSIGMA_API my_class& operator=(my_class&& other) noexcept;

  // Simple getter - can be noexcept
  XSIGMA_API int get_value() const noexcept { return value_; }

  // Function that handles errors without throwing
  XSIGMA_API bool process_data(const std::string& data) noexcept;

 private:
  int value_;
};
```

❌ **Incorrect - Missing noexcept:**
```cpp
class XSIGMA_VISIBILITY my_class {
 public:
  // ❌ Destructors should always be noexcept
  XSIGMA_API ~my_class();

  // ❌ Move constructor should be noexcept
  XSIGMA_API my_class(my_class&& other);

  // ❌ Simple getter could be noexcept
  XSIGMA_API int get_value() const { return value_; }

 private:
  int value_;
};
```

#### Macro Usage Summary

| Macro | Purpose | Required | Optional | Example |
|-------|---------|----------|----------|---------|
| **XSIGMA_NODISCARD** | Mark return values that shouldn't be ignored | Error codes, resource handles, important results | Void functions, obvious side effects | `XSIGMA_NODISCARD XSIGMA_API bool validate();` |
| **XSIGMA_UNUSED** | Mark intentionally unused parameters | Interface implementations, callbacks | Actually used parameters | `void handler(XSIGMA_UNUSED int id, const data& d)` |
| **noexcept** | Guarantee no exceptions thrown | Destructors, move operations | Simple getters, error-handling functions | `~my_class() noexcept;` |

#### Benefits of Using These Macros

- **Compiler Warnings**: Enables the compiler to warn about potential issues (unused return values, unused parameters)
- **Static Analysis**: Tools like clang-tidy can better analyze code when these macros are present
- **Documentation**: Makes intent clear to other developers
- **Optimization**: Compiler can optimize better with `noexcept` specifications
- **API Safety**: Prevents accidental misuse of functions

---

## Clang-Tidy Configuration and Enforcement

### Overview

**Clang-Tidy** is a static analysis tool that enforces code quality, consistency, and best practices across the XSigma codebase. All code must pass clang-tidy checks before being merged into the main branch.

Clang-Tidy performs automated checks for:
- **Modernization**: Using modern C++ features and idioms
- **Readability**: Code clarity and maintainability
- **Performance**: Optimization opportunities and inefficiencies
- **Bug Prevention**: Common programming errors and pitfalls
- **Style Consistency**: Adherence to project conventions

### Running Clang-Tidy Locally

Before submitting code, run clang-tidy locally to catch issues early:

```bash
cd Scripts

# Run clang-tidy checks
python setup.py config.build.ninja.clang.clangtidy

# Or run clang-tidy on specific files
cd ../build_ninja_clangtidy
clang-tidy -p . ../Core/path/to/file.cpp
```

### Enabled Clang-Tidy Checks

XSigma's `.clang-tidy` configuration enables the following check categories:

| Category | Purpose | Examples |
|----------|---------|----------|
| **modernize-*** | Use modern C++ features | `modernize-use-auto`, `modernize-use-nullptr`, `modernize-use-override` |
| **readability-*** | Improve code clarity | `readability-identifier-naming`, `readability-function-size`, `readability-magic-numbers` |
| **performance-*** | Optimize performance | `performance-unnecessary-copy-initialization`, `performance-move-const-arg` |
| **bugprone-*** | Detect common bugs | `bugprone-use-after-move`, `bugprone-integer-division`, `bugprone-unused-raii` |
| **cppcoreguidelines-*** | Follow C++ Core Guidelines | `cppcoreguidelines-pro-type-cstyle-cast`, `cppcoreguidelines-avoid-goto` |

### Common Clang-Tidy Warnings and Fixes

#### Warning: `modernize-use-auto`

**❌ Incorrect - Explicit type when auto is clearer:**
```cpp
std::vector<int> values = {1, 2, 3};
std::vector<int>::iterator it = values.begin();  // Verbose type

std::unique_ptr<my_class> obj(std::make_unique<my_class>());  // Redundant type
```

**✅ Correct - Use auto for clarity:**
```cpp
std::vector<int> values = {1, 2, 3};
auto it = values.begin();  // Type is clear from context

auto obj = std::make_unique<my_class>();  // Type is obvious
```

#### Warning: `readability-identifier-naming`

**❌ Incorrect - Inconsistent naming:**
```cpp
class MyClass {  // camelCase - violates snake_case convention
 private:
  int myValue;  // camelCase - should be snake_case_
};

void DoSomething() {  // PascalCase - should be snake_case
  // implementation
}
```

**✅ Correct - Consistent snake_case naming:**
```cpp
class my_class {  // snake_case
 private:
  int my_value_;  // snake_case with trailing underscore
};

void do_something() {  // snake_case
  // implementation
}
```

#### Warning: `performance-unnecessary-copy-initialization`

**❌ Incorrect - Unnecessary copy:**
```cpp
std::vector<int> get_data() {
  std::vector<int> data = {1, 2, 3};
  std::vector<int> result = data;  // Unnecessary copy
  return result;
}
```

**✅ Correct - Use move semantics:**
```cpp
std::vector<int> get_data() {
  std::vector<int> data = {1, 2, 3};
  return data;  // Compiler optimizes with RVO/move
}
```

#### Warning: `bugprone-use-after-move`

**❌ Incorrect - Using variable after move:**
```cpp
std::unique_ptr<my_class> obj = std::make_unique<my_class>();
std::unique_ptr<my_class> other = std::move(obj);
obj->do_something();  // ERROR: obj is now nullptr
```

**✅ Correct - Don't use after move:**
```cpp
std::unique_ptr<my_class> obj = std::make_unique<my_class>();
std::unique_ptr<my_class> other = std::move(obj);
// Don't use obj after move
other->do_something();
```

#### Warning: `cppcoreguidelines-pro-type-cstyle-cast`

**❌ Incorrect - C-style cast:**
```cpp
int value = 42;
double result = (double)value;  // C-style cast

void* ptr = (void*)&value;  // Unsafe cast
```

**✅ Correct - C++ style casts:**
```cpp
int value = 42;
double result = static_cast<double>(value);  // Safe, explicit

void* ptr = static_cast<void*>(&value);  // Clear intent
```

### Interpreting Clang-Tidy Output

Clang-Tidy output typically looks like:

```
/path/to/file.cpp:42:5: warning: variable 'result' of type 'std::vector<int>' can be constructed with std::move [modernize-use-move-on-return]
  std::vector<int> result = data;
  ^
  std::move(data)
```

**Format breakdown:**
- **File and line**: `/path/to/file.cpp:42:5`
- **Message type**: `warning`
- **Description**: What the issue is
- **Check name**: `[modernize-use-move-on-return]` - Use this to understand the rule
- **Suggested fix**: Often provided (e.g., `std::move(data)`)

### Clang-Tidy Configuration File

XSigma's clang-tidy configuration is defined in `.clang-tidy` at the project root. This file specifies:
- Which checks are enabled/disabled
- Check-specific options and severity levels
- Header filter patterns

**View the configuration:**
```bash
cat .clang-tidy
```

### Suppressing Clang-Tidy Warnings

In rare cases where a clang-tidy warning is a false positive or intentionally violated, suppress it with a comment:

```cpp
// ✅ Correct - Suppress specific warning with explanation
// NOLINTNEXTLINE(readability-magic-numbers)
// Magic number 42 is intentional - represents the answer to everything
const int kAnswerToEverything = 42;

// ✅ Suppress multiple checks
// NOLINTNEXTLINE(modernize-use-auto, readability-identifier-naming)
int explicit_type_needed = calculate_value();
```

**Important**: Always provide a comment explaining why the warning is suppressed. Suppressions without justification will be rejected in code review.

---

## Auto Keyword Usage Guidelines

### Overview

The `auto` keyword in C++ allows the compiler to deduce types automatically. XSigma uses `auto` strategically to improve code clarity and reduce verbosity while maintaining type safety.

### When `auto` is Required

Use `auto` in these situations where explicit types are impractical or impossible:

#### 1. Iterator Types

```cpp
// ✅ Correct - auto for iterators
auto it = values.begin();
auto result = std::find(values.begin(), values.end(), target);

// ❌ Incorrect - Verbose explicit type
std::vector<int>::iterator it = values.begin();
std::vector<int>::const_iterator result = std::find(values.begin(), values.end(), target);
```

#### 2. Complex Template Types

```cpp
// ✅ Correct - auto for complex types
auto result = std::make_pair(1, "hello");
auto map_entry = my_map.find(key);

// ❌ Incorrect - Verbose explicit type
std::pair<int, std::string> result = std::make_pair(1, "hello");
std::map<std::string, int>::iterator map_entry = my_map.find(key);
```

#### 3. Lambda Expressions

```cpp
// ✅ Correct - auto for lambdas
auto compare = [](int a, int b) { return a < b; };
auto process = [this](const std::string& s) { return transform(s); };

// ❌ Incorrect - Can't use explicit type for lambdas
// Each lambda has a unique, unnamed type
```

### When `auto` is Preferred

Use `auto` in these situations for clarity and conciseness:

#### 1. With `std::make_unique` and `std::make_shared`

```cpp
// ✅ Preferred - auto with make_unique
auto buffer = std::make_unique<data_buffer>(size);
auto resource = std::make_shared<resource>();

// ⚠️ Less preferred - Explicit type (redundant)
std::unique_ptr<data_buffer> buffer = std::make_unique<data_buffer>(size);
std::shared_ptr<resource> resource = std::make_shared<resource>();
```

#### 2. Range-Based For Loops

```cpp
// ✅ Preferred - auto in range-based for
for (auto& item : collection) {
  process(item);
}

for (const auto& value : values) {
  print(value);
}

// ⚠️ Less preferred - Explicit type
for (my_class& item : collection) {
  process(item);
}
```

#### 3. Function Return Values

```cpp
// ✅ Preferred - auto for function returns
auto result = calculate_value();
auto data = fetch_from_database();

// ⚠️ Less preferred - Explicit type (if obvious from function name)
int result = calculate_value();
std::vector<record> data = fetch_from_database();
```

### When Explicit Types Should Be Used

Use explicit types when `auto` would reduce code clarity:

#### 1. When Type Clarity is Important

```cpp
// ✅ Correct - Explicit type for clarity
int count = 0;  // Clear that this is a count
double percentage = 0.0;  // Clear that this is a percentage
bool is_valid = true;  // Clear that this is a boolean

// ❌ Incorrect - auto obscures intent
auto count = 0;  // Is this an int? size_t? What does it represent?
auto percentage = 0.0;  // What is this used for?
auto is_valid = true;  // What does this flag mean?
```

#### 2. When Type Affects Behavior

```cpp
// ✅ Correct - Explicit type when it matters
unsigned int size = collection.size();  // Explicitly unsigned
int signed_value = -42;  // Explicitly signed

// ❌ Incorrect - auto might deduce unexpected type
auto size = collection.size();  // Might be size_t, not int
auto signed_value = -42;  // Might be unsigned
```

#### 3. When Documenting API Contracts

```cpp
// ✅ Correct - Explicit type in public APIs
class data_processor {
 public:
  // Clear return type for API users
  std::vector<result> process_data(const std::vector<input>& data);

 private:
  // auto is fine for internal implementation
  auto calculate_intermediate() { /* ... */ }
};

// ❌ Incorrect - auto in public API
class data_processor {
 public:
  // Unclear what this returns
  auto process_data(const std::vector<input>& data);
};
```

### Reference Types with `auto`

Use appropriate reference qualifiers with `auto`:

#### 1. `auto` (Value Type)

```cpp
// ✅ Correct - Copy when you need a copy
auto value = get_data();  // Copies the data
std::vector<int> copy = value;  // Another copy
```

#### 2. `auto&` (Mutable Reference)

```cpp
// ✅ Correct - Reference to modify
auto& item = collection[0];  // Reference to first item
item.modify();  // Modifies the original

for (auto& element : collection) {
  element.update();  // Modifies each element
}
```

#### 3. `const auto&` (Const Reference)

```cpp
// ✅ Correct - Const reference to avoid copy
const auto& data = get_large_data();  // No copy, read-only access
for (const auto& item : collection) {
  process(item);  // Read-only access
}
```

#### 4. `auto&&` (Forwarding Reference)

```cpp
// ✅ Correct - Forwarding reference in templates
template<typename T>
void process(auto&& value) {
  // Preserves lvalue/rvalue nature of value
  forward_to_next(std::forward<decltype(value)>(value));
}
```

### Clang-Tidy Auto Enforcement

XSigma's clang-tidy configuration includes `modernize-use-auto` which enforces appropriate `auto` usage:

```cpp
// ✅ Passes clang-tidy
auto it = values.begin();
auto obj = std::make_unique<my_class>();

// ❌ Fails clang-tidy - should use auto
std::vector<int>::iterator it = values.begin();
std::unique_ptr<my_class> obj = std::make_unique<my_class>();
```

### Auto Usage Summary

| Situation | Use `auto` | Use Explicit Type | Example |
|-----------|-----------|-------------------|---------|
| Iterators | ✅ Yes | - | `auto it = v.begin();` |
| Complex templates | ✅ Yes | - | `auto result = std::make_pair(...);` |
| Lambdas | ✅ Yes (required) | - | `auto fn = [](int x) { return x * 2; };` |
| `std::make_unique` | ✅ Preferred | ⚠️ Acceptable | `auto obj = std::make_unique<T>();` |
| Range-based for | ✅ Preferred | ⚠️ Acceptable | `for (auto& item : collection)` |
| Function returns | ✅ Preferred | ⚠️ Acceptable | `auto result = calculate();` |
| Primitive types | ❌ No | ✅ Yes | `int count = 0;` |
| Type clarity needed | ❌ No | ✅ Yes | `bool is_valid = true;` |
| Public API returns | ❌ No | ✅ Yes | `std::vector<T> get_data();` |

---

## Common Pitfalls to Avoid

- ❌ Using exceptions or `try`/`catch`/`throw`
- ❌ Violating include path rules (starting with `Core/`)
- ❌ Mixing naming conventions (e.g., `camelCase` with `snake_case`)
- ❌ Using `m_` prefix for member variables (e.g., `m_count`, `m_value`) instead of trailing underscore (`count_`, `value_`)
- ❌ Omitting required macros (`XSIGMA_API`, `XSIGMA_VISIBILITY`)
- ❌ Submitting untested or low-coverage code (below 98%)
- ❌ Using raw pointers for ownership
- ❌ Exposing mutable shared state without synchronization
- ❌ Using a different test macro than the one already used in that library (`TEST`/`TEST_F`; Core may still use `XSIGMATEST`)
- ❌ Using `auto` for primitive types where explicit types improve clarity (e.g., `auto count = 0;`)
- ❌ Using `auto` in public API declarations where type clarity is important
- ❌ Using `auto` when the deduced type is not obvious from context
- ❌ Ignoring clang-tidy warnings without justification or suppression comments
- ❌ Suppressing clang-tidy warnings without explaining why in a comment
- ❌ Using `.cpp`, `.hpp`, `.hxx`, or other non-standard extensions instead of `.h` and `.cpp`
- ❌ Placing multiple unrelated classes in a single `.h`/`.cpp` file pair
- ❌ File names that don't match the class name they contain (e.g., `processor.h` for `class data_processor`)
- ❌ Using suffixes like `_impl`, `_implementation`, or `_helper` in file names when they should match the class name exactly
- ❌ Public constructors in classes that have builder classes (should be `private` or `protected`)
- ❌ Not declaring the builder class as a `friend` when using private constructors
- ❌ Not using `XSIGMA_NODISCARD` on functions returning error codes, resource handles, or important results
- ❌ Not using `XSIGMA_UNUSED` on intentionally unused parameters in interface implementations or callbacks
- ❌ Not using `noexcept` on destructors, move constructors, or move assignment operators
- ❌ Ignoring compiler warnings about unused return values or unused parameters

## Related Documentation

- **[Contributing Guide](../../CONTRIBUTING.md)** - Contributor-specific requirements and pull request process
- **[Complete Coding Standards Rules](../../.augment/rules/coding.md)** - Detailed standards covering all aspects
- **[README.md - Coding Standards Section](../../README.md#coding-standards)** - Quick reference guide

---

**Last Updated:** 2025-11-03
**Maintained by:** XSigma Development Team
