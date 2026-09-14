---
type: "always_apply"
---

# XSigma C++ Coding Standards and Best Practices

This document defines mandatory coding standards for the XSigma project. All code contributions must adhere to these rules without exception.

---

## 1. Error Handling

### 1.1 General Principles

* **MANDATORY: No exception-based error handling.** Never use `try`, `catch`, or `throw` under any circumstances.
* Use **return values** (e.g., `bool`, `std::optional<T>`, `std::expected<T, E>`, or custom result types) to communicate success or failure.
* Use **conditional control flow** (`if`, `switch`, early returns) to manage error states.
* Ensure all errors are **predictable, traceable, and testable** through unit tests.
* Propagate errors through clearly defined return codes, result objects, or error enums.

### 1.2 Examples

❌ **Incorrect:**

```cpp
try {
  risky_function();
} catch (...) {
  // handle error
}
```

✅ **Correct:**

```cpp
if (!safe_function()) {
  // handle error gracefully without exceptions
  return false;
}
```

✅ **Better (using std::optional):**

```cpp
std::optional<Result> result = safe_function();
if (!result.has_value()) {
  // handle error gracefully
  return std::nullopt;
}
```

---

## 2. Naming Conventions

### 2.1 C++ Naming Rules

All code must follow these naming conventions consistently:

| Element Type    | Convention                          | Example                      | Notes |
| --------------- | ----------------------------------- | ---------------------------- | ----- |
| Class           | `snake_case`                        | `class my_class`             | All lowercase with underscores |
| Struct          | `snake_case`                        | `struct data_point`          | Same as class |
| Function        | `snake_case`                        | `void do_something()`        | All lowercase with underscores |
| Member Variable | `snake_case_` (trailing underscore) | `int count_;`                | Trailing underscore distinguishes from locals |
| Local Variable  | `snake_case`                        | `int local_value`            | No trailing underscore |
| Constant        | `kConstantName` or `CONSTANT_NAME`  | `const int kMaxCount = 100;` | Prefer `kConstantName` for readability |
| Namespace       | `snake_case`                        | `namespace xsigma`           | All lowercase |
| Enum            | `snake_case`                        | `enum class color_type`      | Use `enum class` for type safety |
| Enum Value      | `snake_case`                        | `color_type::dark_red`       | All lowercase |

**IMPORTANT:** Maintain uniform naming across the entire file. Mixing conventions (e.g., `camelCase` with `snake_case`) is strictly prohibited.

### 2.2 Member Variable Naming - Critical Rule

**MANDATORY:** All class member variables MUST use `snake_case` naming with a trailing underscore (`_`).

**PROHIBITED:** The `m_` prefix (e.g., `m_count`, `m_value`, `m_data`) is **strictly forbidden** for member variables.

**REQUIRED:** Use `snake_case` with a trailing underscore (e.g., `count_`, `value_`, `data_ptr_`).

**Rationale:** The trailing underscore clearly distinguishes member variables from local variables and function parameters, improving code readability and preventing naming conflicts. This convention is enforced throughout the entire XSigma codebase and must be followed in all code reviews and automated linting.

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

### 2.3 Complete Naming Examples

❌ **Incorrect:**

```cpp
class MyClass {
  int myVar;
  void DoSomething();
};
```

✅ **Correct:**

```cpp
class my_class {
  int value_;
  void do_something();
};
```

---

## 3. Code Formatting and Style

### 3.1 Formatting Standards

* **MANDATORY:** Follow **`.clang-format`** and **`.clang-tidy`** rules strictly. These are enforced in CI.
* Conform to the [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html) unless project-specific overrides exist in `.clang-format`.
* Maintain consistent indentation (2 spaces, no tabs), brace placement (opening brace on same line), and spacing.
* **MANDATORY:** Format code automatically before commit using `clang-format`.
* Run `clang-tidy` to catch style violations and potential bugs.

✅ **Example:**

```cpp
if (x == y) {
  foo();
} else {
  bar();
}
```

---

## 4. Include Rules

### 4.1 Include Path Convention

* Include paths must **start from the project subfolder**, not the repository root.
* Do **not** use absolute paths or paths starting with `Core/`.
* Maintain consistent include structure across all files.
* Order includes: standard library → third-party → project headers (separated by blank lines).

**Example:**

File location: `Core/xxx/yyy/a.h`

❌ **Incorrect:**

```cpp
#include "Core/xxx/yyy/a.h"
```

✅ **Correct:**

```cpp
#include "xxx/yyy/a.h"
```

✅ **Complete example with ordering:**

```cpp
#include <memory>
#include <string>

#include <fmt/format.h>
#include <logging/logging.h>

#include "xxx/yyy/a.h"
#include "xxx/zzz/b.h"
```

---

## 5. Testing Requirements

### 5.1 Coverage & Quality

* **MANDATORY:** Minimum **98% code coverage** required for all generated code.
* Tests must be deterministic, reproducible, and isolated (no flaky tests).
* Avoid shared state between tests; each test must be independent.
* Prefer test fixtures or factory patterns for complex setup.
* Use the `XSIGMATEST` macro exclusively for all tests (not `TEST` or `TEST_F`).

### 5.2 File Naming & Structure

* Test files must mirror source file hierarchy exactly.
* Use naming pattern `Test[ClassName].cpp` (CamelCase for test files only).
  * Example: `TestMyClass.cpp`, `TestPaymentProcessor.cpp`
* Place test files in the same directory structure as source files, but under a `Tests/` or `Testing/` subdirectory.

### 5.3 Test Practices

* Each test must validate a **single behavior or condition** (one assertion per test when possible).
* Mock or stub all external dependencies to ensure isolation.
* Verify both **happy path** (success cases) and **failure** conditions (error cases, edge cases, boundary conditions).
* Test null pointers, empty collections, invalid inputs, and boundary values explicitly.

✅ **Examples:**

```cpp
XSIGMATEST(my_class_test, handles_valid_input) {
  my_class obj;
  EXPECT_TRUE(obj.do_something());
}

XSIGMATEST(my_class_test, handles_invalid_input) {
  my_class obj;
  EXPECT_FALSE(obj.do_something_with(-1));
}

XSIGMATEST(my_class_test, handles_null_pointer) {
  my_class obj;
  EXPECT_FALSE(obj.process(nullptr));
}

XSIGMATEST(my_class_test, handles_empty_collection) {
  my_class obj;
  std::vector<int> empty;
  EXPECT_TRUE(obj.process_collection(empty));
}
```

---

## 6. DLL Export and Visibility

### 6.1 Macro Rules

Apply these macros consistently across all public headers to ensure correct symbol visibility:

| Context                          | Macro               | Description                                | When to Use |
| -------------------------------- | ------------------- | ------------------------------------------ | ----------- |
| Function (implemented in `.cpp`) | `XSIGMA_API`        | Mark all externally visible functions      | Before function return type |
| Class declaration                | `XSIGMA_VISIBILITY` | Required for all public class declarations | Before `class` keyword |

**IMPORTANT:** Omitting these macros will cause linking errors on Windows and symbol visibility issues on Linux/macOS.

✅ **Correct Example:**

```cpp
class XSIGMA_VISIBILITY my_class {
 public:
  XSIGMA_API void do_something();
  XSIGMA_API int calculate(int value);
};
```

---

## 7. Architecture & Design Principles

### 7.1 Modularity

* Separate presentation, business logic, and data access layers clearly.
* Use **dependency injection** for testability (pass dependencies as constructor parameters or setters).
* Define clear, minimal interfaces between modules (prefer abstract base classes or concepts).
* Favor loose coupling and composability (modules should depend on abstractions, not concrete implementations).

### 7.2 Design Principles

* Follow **SOLID** design principles:
  * **S**ingle Responsibility: Each class has one reason to change
  * **O**pen/Closed: Open for extension, closed for modification
  * **L**iskov Substitution: Derived classes must be substitutable for base classes
  * **I**nterface Segregation: Many specific interfaces better than one general interface
  * **D**ependency Inversion: Depend on abstractions, not concretions
* Favor **immutability** and **pure functions** (functions without side effects).
* Use **RAII (Resource Acquisition Is Initialization)** for all resource management (files, sockets, locks, memory).
* Avoid global mutable state; use dependency injection or singletons sparingly.
* When declaring unused parameters (e.g., for interface compliance), prefix them with `XSIGMA_UNUSED`:
  ```cpp
  void callback(XSIGMA_UNUSED int unused_param, int used_param) {
    // only use used_param
  }
  ```

---

## 8. Memory Management

### 8.1 Ownership & Lifetime

* **MANDATORY:** Use **smart pointers** (`std::unique_ptr`, `std::shared_ptr`) instead of raw pointers for ownership.
* Avoid `new`/`delete` in application code; encapsulate allocations in factory functions or constructors.
* Apply RAII for all resource management (memory, files, locks, sockets).
* Use raw pointers only for non-owning references (prefer references when possible).

### 8.2 Guidelines

* `std::unique_ptr<T>` → exclusive ownership (default choice for single ownership).
* `std::shared_ptr<T>` → shared ownership (minimize use; prefer unique ownership).
* `std::weak_ptr<T>` → observe shared resources safely without extending lifetime.
* Avoid circular references with `shared_ptr` (use `weak_ptr` to break cycles).
* Prefer `std::make_unique` and `std::make_shared` over direct `new`.

✅ **Example:**

```cpp
class resource_manager {
 public:
  resource_manager() : data_(std::make_unique<Data>()) {}
  
 private:
  std::unique_ptr<Data> data_;  // Exclusive ownership
};
```

---

## 9. Concurrency & Thread Safety

### 9.1 General Rules

* Prefer standard library concurrency primitives: **`std::thread`, `std::async`, `std::future`, `std::mutex`, `std::condition_variable`**.
* Protect shared resources using scoped locks (`std::scoped_lock`, `std::lock_guard`, `std::unique_lock`).
* **NEVER** expose mutable shared state without synchronization.
* Avoid manual thread lifecycle management when possible (prefer RAII wrappers or thread pools).
* Document thread-safety guarantees in class comments.

### 9.2 Modern C++20 Practices

* Use **atomic types** (`std::atomic<T>`) for shared counters, flags, and simple state.
* Prefer **structured concurrency** (RAII-thread ownership: threads owned by objects that join in destructor).
* Avoid busy-wait loops; use condition variables (`std::condition_variable`) for signaling.
* Use `std::jthread` (C++20) for automatic joining.

✅ **Example:**

```cpp
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

---

## 10. CI/CD and Static Analysis

### 10.1 Automated Validation

* **MANDATORY:** Every code generation pipeline must run:
  * `clang-tidy` (static analysis)
  * `clang-format` (code formatting verification)
  * Unit and integration test suites
  * Code coverage analysis (minimum 98%)

### 10.2 Build System Integration

* Use **CMake** targets for all builds and tests.
* Define explicit dependencies to ensure reproducibility.
* **MANDATORY:** CI must fail on any formatting, linting, or coverage violation.
* All checks must pass before code can be merged.

---

## 11. AI Code Review Guidelines

### 11.1 AI-Generated Code Validation

* All AI-generated code must undergo human review before merge.
* Reviewers must check adherence to these standards (naming, error handling, testing, etc.).
* AI suggestions should be deterministic, documented, and traceable (include rationale in comments or commit messages).

### 11.2 Prompt Hygiene

* Avoid ambiguous or overly general prompts when requesting AI code generation.
* Include context: module purpose, dependencies, naming rules, and design constraints.
* Review generated code for compliance before committing (run `clang-format`, `clang-tidy`, and tests).

---

## 12. Security and Robustness

### 12.1 Secure Coding Practices

* **MANDATORY:** Validate all input; never assume trust (especially user input, network data, file contents).
* Avoid unsafe functions: `strcpy`, `sprintf`, `gets`, `scanf` (use `strncpy`, `snprintf`, `std::string`, `std::getline` instead).
* Use safe standard library alternatives (`std::string`, `std::vector`, `std::array`).
* Sanitize external data before use (escape special characters, validate ranges).
* Implement boundary checks on all buffers and arrays (use `.at()` instead of `[]` for bounds checking).
* Check return values of all system calls and library functions.

---

## 13. Documentation & Maintainability

### 13.1 Documentation Standards

* Document **intent and rationale**, not obvious implementation details.
* Annotate non-trivial algorithms, corner cases, and performance considerations.
* Keep all comments synchronized with code changes (outdated comments are worse than no comments).
* Use Doxygen-style comments for public APIs:
  ```cpp
  /**
   * @brief Calculates the sum of two integers.
   * @param a First integer
   * @param b Second integer
   * @return Sum of a and b
   */
  XSIGMA_API int add(int a, int b);
  ```

### 13.2 Review Readiness

* Code must be production-ready and fully tested before submission.
* All style, build, and test checks must pass before submission.
* Code reviews must verify adherence to these standards.

---

## 14. Common Pitfalls to Avoid

* Using exceptions or `try`/`catch`/`throw`
* Violating include path rules (starting with `Core/` instead of subfolder)
* Mixing naming conventions (e.g., `camelCase` with `snake_case`)
* Omitting required macros (`XSIGMA_API`, `XSIGMA_VISIBILITY`)
* Submitting untested or low-coverage code (below 98%)
* Hardcoding values instead of using configuration or constants
* Creating oversized classes or functions (prefer small, focused units)
* Failing to document reasoning behind design choices
* Ignoring `clang-tidy` and `clang-format` warnings
* Using raw pointers for ownership (use smart pointers)
* Exposing mutable shared state without synchronization
* Using `TEST` or `TEST_F` instead of `XSIGMATEST` macro

---

**End of Document**

**Enforcement:** These standards are enforced through automated CI checks and code reviews. Non-compliant code will not be merged.