# Contributing to XSigma

Thank you for your interest in contributing to XSigma! We welcome contributions from the community and are grateful for your support.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Contribution Policy and Control](#contribution-policy-and-control)
- [Contribution Rights and Ownership](#contribution-rights-and-ownership)
- [Intellectual Property and Originality](#intellectual-property-and-originality)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)
- [Getting Help](#getting-help)

## Code of Conduct

This project adheres to the Contributor Covenant [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@xsigma.co.uk](mailto:conduct@xsigma.co.uk).

## Contribution Policy and Control

### Welcome and Acceptance Policy

**XSigma welcomes contributions from the community**, and we are grateful for your interest in improving the project. However, it is important to understand the contribution acceptance policy and control structure:

#### XSigmaAnalyitix Authority

- **All contributions are subject to review and approval** by XSigmaAnalyitix maintainers
- **XSigmaAnalyitix retains full control** over what code is accepted into the project
- **Final decision authority** on all technical, architectural, and strategic matters rests with XSigmaAnalyitix
- **XSigmaAnalyitix reserves the right** to refuse contributions that don't align with:
  - Project goals and strategic direction
  - Quality standards and coding conventions
  - Architectural vision and design principles
  - Security and performance requirements
  - Legal and licensing requirements

#### Contribution Rights Grant

By submitting a contribution to XSigma, you grant XSigmaAnalyitix the right to:

- **Use, modify, or reject** your contribution at their sole discretion
- **Incorporate** your contribution into the XSigma codebase
- **Relicense** your contribution under commercial licenses without additional permission
- **Modify or remove** your contribution in future versions
- **Distribute** your contribution as part of XSigma under both GPL-3.0-or-later and commercial licenses

#### Dual Licensing and Commercial Use

XSigma operates under a **dual licensing model**:

- **GPL-3.0-or-later**: The public receives the software under GPL-3.0-or-later terms
- **Commercial License**: XSigmaAnalyitix offers commercial licenses for proprietary use

**By contributing, you explicitly grant XSigmaAnalyitix the ability to offer commercial licenses** for the combined work (including your contributions) **without seeking additional permission or providing compensation**.

This dual licensing model is essential to XSigma's sustainability and allows XSigmaAnalyitix to:
- Fund ongoing development and maintenance
- Provide commercial support and services
- Offer proprietary licensing options to customers who cannot use GPL-3.0

#### No Guarantee of Acceptance

- **Submission does not guarantee acceptance** - XSigmaAnalyitix may reject contributions for any reason
- **Maintainers have sole discretion** over merge decisions
- **Community input is valued** but does not override maintainer decisions
- **Rejected contributions** may be reconsidered if revised to meet project requirements

#### Project Control and Roadmap

- **XSigmaAnalyitix controls the project roadmap**, feature priorities, and release schedule
- **Architectural decisions** are made by XSigmaAnalyitix maintainers
- **Breaking changes** and major refactoring are at XSigmaAnalyitix's discretion
- **Community suggestions** are welcome but not binding

### Why This Model?

This contribution model ensures:

- **Consistent quality** and architectural coherence
- **Legal clarity** for dual licensing
- **Sustainable development** through commercial licensing revenue
- **Clear decision-making** authority
- **Protection** of XSigmaAnalyitix's business interests

We believe this model balances **open-source collaboration** with the **business sustainability** necessary for long-term project success.

## Contribution Rights and Ownership

### Copyright Retention

**You retain copyright** to your original contributions. XSigma does not require copyright assignment.

### License Grant

By submitting a contribution to XSigma, you grant XSigmaAnalyitix a **perpetual, irrevocable, worldwide, royalty-free, non-exclusive license** to:

1. **Use** your contribution in any manner
2. **Reproduce** your contribution in any form
3. **Modify** and create derivative works from your contribution
4. **Distribute** your contribution under GPL-3.0-or-later
5. **Sublicense** your contribution under commercial licenses
6. **Publicly display and perform** your contribution
7. **Grant sublicenses** to third parties under commercial terms

### Irrevocable Grant

This license grant is **irrevocable** - you cannot withdraw permission after your contribution is accepted. This ensures:

- **Legal certainty** for XSigmaAnalyitix and users
- **Business continuity** for commercial licensing
- **Stability** of the codebase

### Waiver of Future Claims

By contributing, you **waive any future claims** to:

- Control how your contribution is used within XSigma
- Demand removal of your contribution
- Object to commercial licensing of your contribution
- Seek compensation for use of your contribution

### Dual Licensing Rights

You explicitly grant XSigmaAnalyitix the **exclusive right** to:

- Offer commercial licenses for the combined work (XSigma + your contributions)
- Negotiate commercial licensing terms without your involvement
- Receive all revenue from commercial licenses
- Modify commercial licensing terms at their discretion

### Public GPL Rights

The public receives your contribution under **GPL-3.0-or-later** terms, ensuring:

- Freedom to use, study, modify, and distribute
- Copyleft protection (derivative works must be GPL-licensed)
- No warranty or liability

### Business Model Support

This licensing model is **necessary to support XSigma's dual licensing business model**:

- Commercial licenses fund development, testing, and support
- GPL ensures open-source availability
- Contributors enable both models by granting broad rights

### Your Rights as a Contributor

You retain the right to:

- **Use your own contribution** in other projects (subject to GPL if derived from XSigma)
- **Be credited** in CHANGELOG.md and project documentation
- **Reference your contribution** in your portfolio or resume

You do **not** retain the right to:

- Control how XSigmaAnalyitix uses your contribution
- Demand removal or modification of your contribution
- Object to commercial licensing
- Receive compensation for commercial use

## Intellectual Property and Originality

### Legal Requirements for Contributions

**All contributions to XSigma must comply with intellectual property laws and licensing requirements.** By submitting a contribution, you certify that your submission meets the following requirements:

#### Original Work and Licensing

1. **Original Work**: All contributions must be your original work or properly licensed open-source code that you have the legal right to contribute.

2. **No Copyright Violations**: You must not submit code that violates any copyright, patent, trademark, or trade secret of any third party.

3. **No Confidentiality Breaches**: You must not submit code that breaches any:
   - Confidentiality agreement
   - Non-disclosure agreement (NDA)
   - Employment contract or agreement
   - Proprietary information obligations

4. **No Proprietary Code**: You must not copy or submit code from:
   - Proprietary software or closed-source projects
   - Confidential repositories or internal company codebases
   - Code you do not have permission to share publicly
   - Code that belongs to your employer (unless you have explicit written permission)

5. **License Compatibility**: You must ensure that any third-party code you include is:
   - Compatible with XSigma's dual license (GPL-3.0-or-later OR LicenseRef-XSigma-Commercial)
   - Properly attributed with original copyright notices and license information
   - From a permissive open-source license (MIT, BSD, Apache 2.0, etc.) or GPL-compatible license

6. **Legal Right to Contribute**: You must have the legal right to contribute the code under XSigma's dual license terms, including:
   - The right to grant the GPL-3.0-or-later license to the public
   - The right to grant XSigmaAnalyitix the ability to offer commercial licenses

#### Third-Party Code Attribution

If your contribution includes or is based on third-party open-source code:

1. **Clearly identify** the third-party code in your pull request description
2. **Preserve** all original copyright notices, license headers, and attribution
3. **Document** the source, license, and any modifications made
4. **Verify** license compatibility with GPL-3.0-or-later
5. **Update** any relevant NOTICE or ATTRIBUTION files

#### Employer and Contractual Obligations

**Important**: If you are employed or under contract:

- **Check your employment agreement** for intellectual property clauses
- **Verify** that your employer does not claim ownership of code you write (even in your personal time)
- **Obtain written permission** from your employer if required
- **Do not contribute** code developed using employer resources, during work hours, or related to your employment duties without explicit permission
- **Consult legal counsel** if you are uncertain about your rights

### Developer Certificate of Origin (DCO)

By submitting a pull request to XSigma, you certify the following:

```
Developer Certificate of Origin
Version 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I have
    the right to submit it under the open source license indicated in
    the file; or

(b) The contribution is based upon previous work that, to the best of
    my knowledge, is covered under an appropriate open source license
    and I have the right under that license to submit that work with
    modifications, whether created in whole or in part by me, under
    the same open source license (unless I am permitted to submit
    under a different license), as indicated in the file; or

(c) The contribution was provided directly to me by some other person
    who certified (a), (b) or (c) and I have not modified it.

(d) I understand and agree that this project and the contribution are
    public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.

(e) I understand that this contribution will be dual-licensed under
    GPL-3.0-or-later OR LicenseRef-XSigma-Commercial, and I have the
    legal right to grant both licenses.

(f) I irrevocably grant XSigmaAnalyitix a perpetual, worldwide,
    royalty-free, non-exclusive license to use, modify, sublicense,
    and distribute my contribution under both GPL-3.0-or-later and
    commercial licenses, without seeking additional permission or
    providing compensation.

(g) I understand and agree that XSigmaAnalyitix has the exclusive
    right to offer commercial licenses for the combined work
    (including my contributions) and to receive all revenue from
    such commercial licenses.

(h) I waive any future claims to control how my contribution is used
    within XSigma, including the right to demand removal, object to
    commercial licensing, or seek compensation.
```

**By submitting a pull request, you implicitly agree to this certification.** You do not need to explicitly sign off on commits, but your submission constitutes your certification that you meet these requirements.

#### What This Means

By contributing to XSigma, you are:

1. **Granting broad rights** to XSigmaAnalyitix to use your contribution in any manner
2. **Enabling commercial licensing** without additional permission or compensation
3. **Waiving future control** over how your contribution is used within the project
4. **Accepting** that XSigmaAnalyitix has final authority over your contribution

The public receives your contribution under **GPL-3.0-or-later**, while XSigmaAnalyitix can offer it under **commercial licenses** to support the project's sustainability.

### Consequences of Violations

Violations of these intellectual property requirements may result in:

- **Immediate rejection** of the pull request
- **Removal** of previously merged code if violations are discovered
- **Revocation** of contributor privileges
- **Legal action** if the violation causes harm to the project or third parties
- **Reporting** to relevant authorities or affected parties

### Questions and Concerns

If you have any questions or concerns about intellectual property, licensing, or your right to contribute:

- **Before contributing**: Contact [licensing@xsigma.co.uk](mailto:licensing@xsigma.co.uk)
- **For legal questions**: Consult your own legal counsel
- **For license compatibility**: Review the [LICENSE](LICENSE) file and consult the [Free Software Foundation's license compatibility guide](https://www.gnu.org/licenses/license-list.html)

**When in doubt, ask first.** It is better to clarify before contributing than to discover issues later.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **CMake** 3.16 or later
- **Python** 3.8 or later
- **C++ Compiler**: GCC 8+, Clang 7+, MSVC 2017+, or Apple Clang 11+
- **Git** with submodule support

See [README.md](README.md#prerequisites) for detailed platform-specific requirements.

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork** and initialize submodules:
   ```bash
   git clone https://github.com/YOUR_USERNAME/XSigma.git
   cd XSigma
   git submodule update --init --recursive
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Build the project** (choose your configuration):
   ```bash
   cd Scripts

   # Debug build with tests
   python setup.py config.build.test.ninja.clang.debug

   # Release build with tests
   python setup.py config.build.test.ninja.clang.release
   ```

5. **Verify the build**:
   ```bash
   # Run tests
   cd ../build_ninja_debug
   ctest --output-on-failure
   ```

## Development Workflow

### Creating a Feature Branch

1. **Create a new branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our [coding standards](#coding-standards)

3. **Write tests** for your changes (see [Testing Requirements](#testing-requirements))

4. **Run tests locally**:
   ```bash
   cd Scripts
   python setup.py config.build.test.ninja.clang.debug
   cd ../build_ninja_debug
   ctest --output-on-failure
   ```

5. **Run linters and formatters**:
   ```bash
   # Format code
   pip install lint-tool
   lintrunner -a

   # Check for issues
   lintrunner
   ```

6. **Commit your changes** with clear, descriptive messages:
   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

7. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request** on GitHub

## Coding Standards

XSigma follows strict coding standards to ensure code quality, consistency, and maintainability. All contributions must adhere to these standards.

### Core Principles

- **No exceptions**: Use return values (`bool`, `std::optional<T>`, `std::expected<T, E>`) for error handling
- **RAII**: All resources must be managed using RAII principles
- **Smart pointers**: Use `std::unique_ptr` and `std::shared_ptr` instead of raw pointers for ownership
- **Const correctness**: Mark all non-mutating methods and variables as `const`

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Class | `snake_case` | `class my_class` |
| Function | `snake_case` | `void do_something()` |
| Member Variable | `snake_case_` (trailing underscore) | `int count_;` |
| Local Variable | `snake_case` | `int local_value` |
| Constant | `kConstantName` | `const int kMaxCount = 100;` |
| Namespace | `snake_case` | `namespace xsigma` |
| Enum | `snake_case` | `enum class color_type` |
| Enum Value | `snake_case` | `color_type::dark_red` |

### Code Formatting

- **Automatic formatting**: Use `clang-format` (configuration in `.clang-format`)
- **Line length**: 100 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **Brace style**: Allman style (opening brace on same line)

**Format your code before committing**:
```bash
pip install lint-tool
lintrunner -a
```

### Static Analysis

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

### Include Paths

- Include paths must start from the project subfolder, not the repository root
- Do **not** use absolute paths or paths starting with `Core/`

**Example**: For file `Core/xxx/yyy/a.h`:
```cpp
// ❌ Incorrect
#include "Core/xxx/yyy/a.h"

// ✅ Correct
#include "xxx/yyy/a.h"
```

### DLL Export Macros

Apply these macros for correct symbol visibility:

- **Functions**: Use `XSIGMA_API` before function return type
- **Classes**: Use `XSIGMA_VISIBILITY` before `class` keyword

```cpp
class XSIGMA_VISIBILITY my_class {
 public:
  XSIGMA_API void do_something();
};
```

### Detailed Standards

For complete coding standards, see [`.augment/rules/coding.md`](.augment/rules/coding.md).


## Testing Requirements

### Coverage and Quality

- **MANDATORY**: Minimum **98% code coverage** required
- Tests must be deterministic, reproducible, and isolated
- Use the `XSIGMATEST` macro exclusively (not `TEST` or `TEST_F`)

### Test File Naming

- Test files must mirror source file hierarchy
- Use naming pattern `Test[ClassName].cpp` (CamelCase for test files only)
- Place test files in the same directory structure under `Tests/` subdirectory

### Test Scope

- Test happy paths and success cases
- Explicitly test boundary conditions and edge cases
- Test error handling and failure scenarios
- Test null pointers, empty collections, and invalid inputs
- Verify state changes and side effects

### Writing Tests

Example:
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

### Running Tests

```bash
cd Scripts
python setup.py config.build.test.ninja.clang.debug
cd ../build_ninja_debug
ctest --output-on-failure
```

### Coverage Reports

```bash
cd Scripts
python setup.py config.build.test.ninja.clang.coverage
cd ../build_ninja_coverage
ctest
# Coverage report generated in coverage/ directory
```

## Pull Request Process

### Before Submitting

**IMPORTANT**: Before submitting your pull request, verify that you understand and accept the following:

#### Contribution Policy Acceptance

- ✅ You have read and accept the [Contribution Policy and Control](#contribution-policy-and-control)
- ✅ You understand that XSigmaAnalyitix has final authority over acceptance/rejection
- ✅ You grant XSigmaAnalyitix irrevocable rights as described in [Contribution Rights and Ownership](#contribution-rights-and-ownership)
- ✅ You accept that XSigmaAnalyitix can offer commercial licenses without additional permission
- ✅ You waive future claims to control how your contribution is used

#### Intellectual Property Requirements

Verify that you meet all [Intellectual Property and Originality](#intellectual-property-and-originality) requirements:

- ✅ The code is your original work or properly licensed open-source code
- ✅ You have the legal right to contribute under XSigma's dual license
- ✅ The code does not violate any copyright, patent, or trade secret
- ✅ The code does not breach any confidentiality agreement or NDA
- ✅ You have obtained employer permission if required
- ✅ Any third-party code is properly attributed and license-compatible

### Pull Request Checklist

Ensure your pull request meets the following criteria:

- [ ] **Code Quality**:
  - [ ] Follows [coding standards](#coding-standards)
  - [ ] Passes all static analysis checks (`clang-tidy`, `cppcheck`, `IWYU`)
  - [ ] Formatted with `clang-format` (run `lintrunner -a`)
  - [ ] No compiler warnings

- [ ] **Testing**:
  - [ ] New tests added for new functionality
  - [ ] All tests pass locally (`ctest --output-on-failure`)
  - [ ] Code coverage ≥ 98%
  - [ ] Tests cover edge cases, error conditions, and boundary values

- [ ] **Documentation**:
  - [ ] Public APIs documented with Doxygen-style comments
  - [ ] README.md updated if adding new features
  - [ ] CHANGELOG.md updated with changes

- [ ] **Contribution Rights**:
  - [ ] Accept XSigmaAnalyitix authority over contribution acceptance
  - [ ] Grant irrevocable license to XSigmaAnalyitix (GPL + commercial)
  - [ ] Accept XSigmaAnalyitix can offer commercial licenses without permission
  - [ ] Waive future claims to control contribution usage

- [ ] **Intellectual Property**:
  - [ ] Code is original work or properly licensed
  - [ ] No copyright, patent, or trade secret violations
  - [ ] No confidentiality or NDA breaches
  - [ ] Third-party code properly attributed
  - [ ] Legal right to contribute under dual license

- [ ] **Commit History**:
  - [ ] Clear, descriptive commit messages
  - [ ] Logical commit organization
  - [ ] No merge commits (rebase on main)

### Submission Process

1. **Push your branch** to your fork
2. **Create a pull request** on GitHub
3. **Fill out the PR template** completely
4. **Link related issues** (if applicable)
5. **Request review** from maintainers
6. **Address review feedback** promptly
7. **Keep your branch up to date** with main

### Review Process

- Maintainers will review your PR within 5 business days
- Reviews check for code quality, testing, documentation, and IP compliance
- Address all review comments before approval
- At least one maintainer approval required for merge
- CI/CD checks must pass (build, tests, linting, coverage)

### After Merge

- Your contribution will be included in the next release
- You will be credited in the CHANGELOG.md
- Thank you for contributing to XSigma!

## Release Process

**Note**: This section is for maintainers only. Contributors do not need to perform these steps.

### Versioning

XSigma follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: Backwards-compatible functionality additions
- **PATCH** version: Backwards-compatible bug fixes

### Release Steps

1. **Update version numbers** in `CMakeLists.txt`:
   ```cmake
   set(PROJECT_MAJOR_VERSION X)
   set(PROJECT_MINOR_VERSION Y)
   set(PROJECT_BUILD_VERSION Z)
   ```

2. **Update CHANGELOG.md**:
   - Move items from `[Unreleased]` to new version section
   - Add release date
   - Create new empty `[Unreleased]` section

3. **Create release commit**:
   ```bash
   git add CMakeLists.txt CHANGELOG.md
   git commit -m "Release v X.Y.Z"
   ```

4. **Create and push tag**:
   ```bash
   git tag -a vX.Y.Z -m "Release version X.Y.Z"
   git push origin main
   git push origin vX.Y.Z
   ```

5. **Create GitHub Release**:
   - Go to GitHub Releases page
   - Click "Draft a new release"
   - Select the tag `vX.Y.Z`
   - Title: "XSigma vX.Y.Z"
   - Description: Copy from CHANGELOG.md
   - Attach release artifacts (if applicable)
   - Publish release

6. **Announce the release**:
   - Update project website (if applicable)
   - Notify community channels
   - Update documentation

## Getting Help

### Documentation

- **README.md**: Project overview and quick start
- **Docs/**: Detailed documentation
- **`.augment/rules/coding.md`**: Complete coding standards
- **SECURITY.md**: Security policy and vulnerability reporting
- **GOVERNANCE.md**: Project governance and decision-making

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community discussions
- **Email**: For private inquiries, contact [info@xsigma.co.uk](mailto:info@xsigma.co.uk)

### Reporting Issues

When reporting bugs or requesting features:

1. **Search existing issues** to avoid duplicates
2. **Use issue templates** provided by the repository
3. **Provide detailed information**:
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
   - Environment details (OS, compiler, versions)
   - Minimal reproducible example
4. **Be respectful** and follow the [Code of Conduct](CODE_OF_CONDUCT.md)

### Getting Support

- **Technical questions**: Use GitHub Discussions
- **Security vulnerabilities**: Follow [SECURITY.md](SECURITY.md) reporting process
- **Licensing questions**: Contact [licensing@xsigma.co.uk](mailto:licensing@xsigma.co.uk)
- **Code of Conduct violations**: Report to [conduct@xsigma.co.uk](mailto:conduct@xsigma.co.uk)

---

**Thank you for contributing to XSigma!** Your contributions help make this project better for everyone.
