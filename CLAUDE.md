# XSigma

A cross-platform C++17/20 computational library (Core, Memory, Vectorization,
Models, Graph) built with CMake via `Scripts/setup.py`, with an alternate
Bazel build. GPU support: CUDA, HIP, Metal. Logging, Parallel, and Profiler
are pure third-party dependencies, vendored as the `ThirdParty/Logging`,
`ThirdParty/Parallel`, and `ThirdParty/Profiler` submodules from their own
repositories (KhwarizmiAnalytix/{Logging,Parallel,Profiler}).

**Naming note:** each library has its own C++ namespace matching its name
(`memory`, `vectorization`, `profiler`, `logging`, `parallel`, ...) and its
own family of `<LIB>_*`-prefixed macros for API export, visibility, and
unused-parameter suppression (e.g. `MEMORY_API`/`MEMORY_VISIBILITY`, each
generated into `Library/<Lib>/common/<lib>_export.h`; Logging/Parallel
generate theirs under `ThirdParty/<Lib>/common/`). `Library/Core` is the
one exception — it predates the per-library split and still uses the project
prefix (`XSIGMA_API`, `XSIGMA_VISIBILITY`, `XSIGMA_UNUSED`, … in
`Library/Core/common/macros.h` / `export.h`) instead of a `CORE_*` one.
When editing a file, match that file's existing namespace/macro family —
never import one library's macro/namespace prefix into another library.

## Hard rules

- **Never modify anything under `ThirdParty/`.** These are vendored git
  submodules (fmt, googletest, mimalloc, benchmark, sleef, Logging, Parallel,
  Profiler, and Logging/Profiler nested backends) and must stay pristine —
  no source edits, no patches applied in place, under any condition, even to
  fix a build error that traces back to vendored code. Host XSigma does not
  vendor loguru, glog, spdlog, magic_enum, kineto, or ittapi as its own
  submodules; those live under Logging and Profiler.
  - If a build/compile issue is caused by code inside `ThirdParty/`, fix it
    from our own side instead: an ADL shim / compat header in the consuming
    library (see `Library/Vectorization/Testing/Cxx/cuda_fmt_int128_fix.h`
    for an example — it supplies a missing `fmt::detail::operator~` via ADL
    rather than editing `ThirdParty/fmt`), a force-included header
    (`-include`), extra compile definitions, or a CMake-level guard/exclusion.
  - If no such workaround is possible without editing vendored code, stop and
    ask the user before touching anything in `ThirdParty/`.

## Configuring, building, and testing

- **Use `Scripts/setup.py` to configure, build, and test** — do not invoke
  CMake/ninja/ctest directly. Run it from the `Scripts/` directory, e.g.:
  ```
  cd Scripts
  python3 setup.py build.TEST.native.avx2.vv.torch.benchmark.cuda.config --project.vectorization --packet-size=8
  ```
  - Dotted tokens (`config`, `build`, `test`, plus compiler/generator/feature
    flags like `native`, `avx2`, `torch`, `benchmark`, `cuda`) are chained
    together and are case-insensitive.
  - `--project.NAME` restricts the build to a single library (e.g.
    `--project.vectorization`) instead of the whole tree.
  - `--packet-size=N` sets the SIMD lane count
    (`VECTORIZATION_PACKET_SIZE`, default 4).
  - Run `python3 setup.py --help` from `Scripts/` for the full list of flags
    (sanitizers, logging backend, coverage, spell check, etc.). The
    `xsigma-build` skill has a distilled cheat sheet of common invocations.

## Reviewing major changes

Before declaring a **major change** done — multi-file edits, a new
feature/behavior, a non-trivial bug fix, anything touching build/CMake
config or a public API — go through this before handing back to the user:

1. **Build and run the affected library's tests** via `setup.py` (see
   above / the `xsigma-build` skill). "The diff looks right" is not a
   substitute for a green build — this project has no CI gate that runs
   automatically as you edit.
2. **Self-check the diff against this file**: naming (`snake_case`,
   trailing-underscore members), no new `try`/`catch` outside the
   documented exemptions, `<LIB>_API`/`<LIB>_VISIBILITY`/`<LIB>_UNUSED`
   used consistently with the library you edited, include-path convention,
   `ThirdParty/` untouched, and the test macro matching what's already in
   that library (see "Testing" below).
3. **Run clang-tidy on touched C++ files** (see the `clang-tidy` skill for
   the two available mechanisms and how to scope fix-mode safely) — it's
   part of this project's own standard (`CONTRIBUTING.md` "Static
   Analysis") even though CI doesn't currently gate on it, so it's on me to
   check rather than skip.
4. **For anything beyond a trivial/single-line change, run `/code-review`**
   on the working diff before telling the user it's ready — it catches
   correctness and simplification issues a self-check misses. Use
   `/security-review` instead when the change touches parsing untrusted
   input, memory-unsafe code, or GPU buffer handling. `/simplify` is the
   right tool when the change is itself a cleanup/refactor pass rather than
   new behavior.
5. Report what you built/ran and what the review step found — don't just
   assert "done" without naming the verification you did.

This is a process expectation for me to follow, not a CI gate — small,
single-file, low-risk edits (a comment, a doc-only change, a one-line
config tweak) don't need the full sequence.

### End of session / before commit

Additionally, at the end of a session that made non-trivial changes, or
before creating a commit, run the **`session-checklist`** skill: it checks
that CMake and Bazel build definitions stayed in sync, builds and tests
*both* build systems (not just the one used mid-session), and runs
`lintrunner` and fixes what it finds. Same "not a CI gate" threshold as
above — skip it deliberately for trivial edits, don't skip it by default.

## C++ coding standards

### Naming

| Element | Convention | Example |
|---|---|---|
| Class / struct | `snake_case` | `class flat_hash_map` |
| Function | `snake_case` | `void do_something()` |
| Member variable | `snake_case_` (trailing underscore) | `int count_;` |
| Local variable | `snake_case` | `int local_value` |
| Constant | `kConstantName` | `const int kMaxCount = 100;` |
| Namespace | `snake_case` | `namespace memory`, `namespace vectorization` |
| Enum / enum value | `snake_case`, `enum class` | `enum class device_enum { cuda };` |

- Never mix conventions within a file.
- **Member variables must never use the `m_` prefix** — trailing underscore
  only (`count_`, not `m_count`). This is enforced project-wide.

### Error handling

- Default policy for new application code: **no `try`/`catch`/`throw`**.
  Communicate failure via return values (`bool`, `std::optional<T>`, result
  structs/enums) and handle it with ordinary control flow.
- **Exception:**  boundary/interop code that wraps a third-party API which
 itself throws is allowed to keep `try`/`catch` — e.g. the GPU allocator
 code in `Library/Memory/gpu/`, the `ThirdParty/Profiler/bespoke/` kineto
 fork, `ThirdParty/Logging/util/exception.cpp` (in the standalone Logging
 repo), and the test-assertion macros
  in `Library/*/Testing/**/baseTest.h`-style headers (whose `ASSERT_*`
  macros throw internally in non-gtest builds so failures abort the test).
  Don't treat existing `try`/`catch` in those areas as a bug to clean up,
  and don't add new `try`/`catch` elsewhere without checking with the user
  first.

### Includes

- Include paths start from the library subfolder, not the repo root or
  `Core/` — e.g. `#include "xxx/yyy/a.h"`, never
  `#include "Core/xxx/yyy/a.h"` or an absolute path.
- Third-party headers use angle brackets (`#include <fmt/format.h>`),
  never quotes. Quotes are for project headers only. This includes
  Logging (`<logger/logger.h>`, `<util/exception.h>`), Parallel
  (`<tools/threaded_callback_queue.h>`), and Profiler (`<native/...>`,
  `<bespoke/...>`). `"profiler/"` is first-party Memory
  (`Library/Memory/profiler/`), not ThirdParty/Profiler.
- Order: standard library → third-party → project headers, each group
  separated by a blank line.

### Visibility macros

Each library defines its own `<LIB>_API`/`<LIB>_VISIBILITY`/`<LIB>_UNUSED`
macros in `Library/<Lib>/common/<lib>_export.h` (e.g. `MEMORY_API`,
`VECTORIZATION_VISIBILITY`, `PROFILER_UNUSED`) — use the one matching the
library the file lives in, never another library's:

- Public classes: `<LIB>_VISIBILITY` before the `class` keyword.
- Externally visible functions implemented in a `.cpp`: `<LIB>_API` before
  the return type.
- Unused parameters kept for interface/ABI compliance: wrap with
  `<LIB>_UNUSED` rather than deleting the name or `(void)`-casting.
- Omitting these causes link errors on Windows and visibility issues on
  Linux/macOS — don't skip them on "it compiles locally."

### Memory & concurrency

- Ownership goes through `std::unique_ptr`/`std::shared_ptr`
  (`std::make_unique`/`std::make_shared`), not raw `new`/`delete`. Raw
  pointers are for non-owning references only (prefer references where
  possible).
- Shared mutable state is protected with `std::scoped_lock`/
  `std::lock_guard`/`std::unique_lock`; prefer `std::atomic<T>` for simple
  counters/flags and condition variables over busy-waiting.

### Builder classes (`xxx_builder`)

- Class name ends in `_builder`; typically holds the object under
  construction via `ptr_mutable<xxx>`.
- Setter methods: named `with_<field>`, take exactly one parameter, return
  the enclosing library's own namespaced type to support fluent chaining,
  and carry a doc comment.

## Testing

- **The current, dominant convention across the codebase is plain Google
  Test — `TEST(suite, name)` / `TEST_F(fixture, name)`.** Actual usage:
  `TEST(`/`TEST_F(` outnumber Core's legacy test macro roughly 14:1
  project-wide, and that legacy macro is used *only* inside `Library/Core`
  (and even there it's a minority next to plain `TEST`). Memory, Graph, and
  Vectorization use `TEST`/`TEST_F` exclusively and don't include the header
  the legacy macro is defined in at all. (Logging/Parallel/Profiler tests
  live in their standalone repos — `ThirdParty/Logging` etc. build with
  tests disabled when embedded in XSigma.)
  - Writing a new test in Core: either convention already exists there —
    check neighboring files in `Library/Core/Testing/Cxx/` and match
    whichever one the class you're testing is closer to; don't introduce a
    third style.
  - Writing a new test anywhere else: use `TEST`/`TEST_F`. Do **not** carry
    Core's legacy test macro into another library — it isn't available
    there.
- Test files: `Test<ClassName>.cpp`, living under a `Testing/Cxx/`
  subdirectory that mirrors the source layout (see any `Library/*/Testing/`
  tree). Benchmarks follow the same pattern under `Benchmark<Name>.cpp`.
- Cover happy path, boundary/edge cases, error/failure return paths, and
  null/empty/invalid inputs — each test case should check one behavior.
- Coverage is tracked via `setup.py config.build.test.coverage` (requires
  `pip install coverage-tool` from KhwarizmiAnalytix/coverage-tool); treat
  high coverage as the project norm on touched code, but note CI does not
  currently hard-gate on a specific percentage — don't assert "98% is
  required" as a build-breaking fact.

## Docs and markdown files

- **Do not create summary/verification/status markdown files
  (`SUMMARY.md`, `*_COMPLETE.md`, `VERIFICATION_CHECKLIST.md`,
  `*_ANALYSIS.md`, etc.) unless the user explicitly asks for one.** Explain
  what changed directly in the response instead.
- If the user does ask for a written doc and doesn't name a location, put
  it in `Docs/` with a clear, descriptive name matching existing
  conventions there. Core project files (README, CHANGELOG, LICENSE) stay
  at the repo root.

## Cross-platform

- Code and scripts must work on Linux, macOS, and Windows unless a section
  is explicitly platform-scoped (e.g. `#if MEMORY_HAS_CUDA`,
  `Library/*/backend/gpu/`). Avoid hardcoded paths, OS-specific shell
  commands, and machine-specific assumptions; use relative paths and
  standard/cross-platform libraries.

## Python (Scripts/, Tools/)

- Follow the Google Python Style Guide; target Python 3.9+.
- Modules: lowercase-with-underscores filenames, one module per file,
  `pathlib` for filesystem paths (not raw string concatenation).
- Lintrunner adapters are the `lint-tool` PyPI package
  (`pip install lint-tool`), not an in-tree `Tools/linter` tree. Host
  policy stays in `.lintrunner.toml`.
- Format with `ruff-format` + `usort` (the `PYFMT`/`RUFF` linters in
  `.lintrunner.toml`), lint with `ruff`/`flake8`/`mypy` per the root
  `pyproject.toml` / `.pylintrc` — these already exist and are wired into
  `.lintrunner.toml`; don't add a competing config. (`black` is not the
  project formatter; isort's `profile = "black"` is only an
  import-style compatibility setting.)
