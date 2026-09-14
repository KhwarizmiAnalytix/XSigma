# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Lintrunner adapters moved to the `lint-tool` PyPI package
  (https://github.com/KhwarizmiAnalytix/lint-tool). Host policy stays in
  `.lintrunner.toml`; the in-tree `Tools/linter` tree is gone.
- Logging backends (glog, loguru, spdlog) come from
  `ThirdParty/Logging/ThirdParty/` instead of duplicate XSigma root
  submodules. fmt and magic_enum stay at the XSigma root so Core can
  share them.

### Added
- Lintrunner `TPINCLUDE` rule: third-party C++ headers must use `#include <>`,
  not quotes. Logging, Parallel, and Profiler public headers are in scope
  (`<logger/...>`, `<util/exception.h>`, `<native/...>`, `<bespoke/...>`,
  `<tools/threaded_callback_queue.h>`).

## [1.0.0] - 2025-11-02

### Added
- Initial release of XSigma quantitative analysis library
- High-performance CPU and GPU computing support with CUDA and HIP backends
- Cross-platform compatibility (Windows, Linux, macOS)
- Modern CMake build system (3.16+) with flexible configuration options
- Comprehensive testing framework using Google Test (800+ tests)
- Code coverage analysis with 98% target coverage requirement
- Multi-compiler coverage support (Clang/LLVM, GCC/gcov, MSVC/OpenCppCoverage)
- Static analysis tools integration:
  - clang-tidy with comprehensive checks
  - cppcheck for additional code quality analysis
  - Include-What-You-Use (IWYU) for header optimization
- Dynamic analysis capabilities:
  - Address Sanitizer (ASan)
  - Thread Sanitizer (TSan)
  - Undefined Behavior Sanitizer (UBSan)
  - Memory Sanitizer (MSan)
  - Leak Sanitizer (LSan)
  - Valgrind integration for memory profiling
- Comprehensive linting system with 20+ linters (.lintrunner.toml)
- Extensive documentation (70+ files in Docs/ directory)
- Automated CI/CD pipeline with GitHub Actions:
  - Multi-platform testing (Ubuntu, Windows, macOS)
  - Multiple C++ standards (C++17, C++20, C++23)
  - Multiple compilers (Clang, GCC, MSVC)
  - Coverage reporting with Codecov integration
  - Sanitizer testing
  - Build caching (sccache, buildcache)
- Performance benchmarking with Google Benchmark
- Link Time Optimization (LTO) support
- Intel Threading Building Blocks (TBB) integration
- Logging backends (Loguru, spdlog)
- Compression support (zlib, zstd)
- NUMA awareness for optimized memory allocation
- Intel MKL integration for optimized linear algebra
- Profiling support with Intel ITT API and Kineto
- Python bindings infrastructure
- Flexible setup.py build system with 50+ configuration variants

### Security
- Implemented comprehensive security policy (SECURITY.md)
- Vulnerability reporting process via GitHub Security Advisories
- 90-day coordinated disclosure timeline
- Secure coding standards enforced (.augment/rules/coding.md)
- No exception-based error handling (return-value error handling only)
- RAII-based resource management
- Smart pointer usage for memory safety
- Comprehensive sanitizer testing in CI/CD

### Documentation
- Comprehensive README.md with build instructions and examples
- Security policy (SECURITY.md)
- OpenSSF Best Practices badge and security documentation
- Code of Conduct (CODE_OF_CONDUCT.md)
- Contributing guidelines (CONTRIBUTING.md)
- Governance documentation (GOVERNANCE.md)
- Extensive guides in Docs/ directory:
  - Setup and installation guides
  - Testing documentation
  - Coverage analysis guides
  - Static analysis configuration
  - Profiling guides
  - Architecture documentation

### Build System
- Modern CMake 3.16+ with target-based configuration
- Cross-platform support (Windows, Linux, macOS)
- Flexible Python-based setup.py build orchestration
- Support for multiple build systems (Ninja, Make, Visual Studio)
- Compiler detection and validation
- Feature detection and configuration
- Third-party dependency management via git submodules
- Build caching support (sccache, buildcache)
- Incremental build optimization
- Parallel build support

### Quality Assurance
- Minimum 98% code coverage requirement
- Comprehensive test suite (800+ tests)
- Automated testing in CI/CD
- Static analysis enforcement (clang-tidy, cppcheck)
- Dynamic analysis (sanitizers, Valgrind)
- Code formatting enforcement (clang-format)
- Linting system with multiple adapters
- Compiler warning enforcement (-Wall -Wextra for GCC/Clang, /W4 for MSVC)

[Unreleased]: https://github.com/KhwarizmiAnalytix/XSigma/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/KhwarizmiAnalytix/XSigma/releases/tag/v1.0.0
