---
name: clang-tidy
description: Run and interpret clang-tidy on XSigma — two separate mechanisms (setup.py build-integrated vs. lintrunner), how fix-mode rewrites source and why to scope it, and how to add a per-directory suppression when a check misfires on a specific file. Use when the user asks to run clang-tidy, fix static-analysis/clang-tidy warnings, or add a clang-tidy suppression.
---

# clang-tidy

XSigma has **two independent ways to run clang-tidy** — they use different
binaries and different scoping, don't assume they agree or that fixing one
satisfies the other.

## 1. Build-integrated (via `setup.py`, CMake `CXX_CLANG_TIDY`/`C_CLANG_TIDY`)

```
cd Scripts
python3 setup.py config.build.ninja.clang.clangtidy              # check only, warnings as errors
python3 setup.py config.build.ninja.clang.clangtidy.fix          # check AND auto-fix
```
- Uses whatever `clang-tidy` is found on `PATH` (`find_program`) — configure
  fails fast if none is found.
- Runs as part of compilation, target by target; `-warnings-as-errors=*` so
  a clang-tidy finding fails the build.
- `.fix` adds `-fix-errors -fix`, which **rewrites source files in place**.
  The CMake module itself warns about this (`Cmake/tools/clang_tidy.cmake`).
  **Never run `.fix` on the whole tree with uncommitted, unrelated changes
  in the working directory** — commit or stash first so an unwanted rewrite
  is a trivial `git diff`/`git checkout` away from being undone, and diff
  the result afterward rather than trusting it blindly.
- `--project.<lib>` narrows this to one library, which is the safer default
  when fixing warnings introduced by a specific change rather than doing a
  repo-wide pass.

## 2. lintrunner (`clang-tidy` from PATH, CI-style check)

```
lintrunner --take CLANGTIDY
lintrunner -a --take CLANGTIDY       # apply available auto-fixes, if any
```
- Resolves `clang-tidy` via PATH (`shutil.which`, code `CLANGTIDY` in
  `.lintrunner.toml`) — **not** a separately pinned/downloaded binary.
  This is deliberate: clang-tidy's bundled resource-dir/builtin headers are
  tightly version-coupled to libc++'s internal header chaining, so a pinned
  binary even a few major versions behind the toolchain that actually
  produced `compile_commands.json` breaks *every* file with bogus "system
  header not found" errors (confirmed: pinned clang-tidy 19.1.4 vs. a
  Homebrew LLVM 22 toolchain failed this way on 100% of files checked).
  Make sure whatever `clang-tidy` is first on `PATH` matches (or is very
  close to) the compiler actually used for the build.
- `--build_dir` has no hardcoded default in `.lintrunner.toml`. `setup.py`
  names build directories with a suffix per feature token
  (`build_ninja_clangtidy_project_memory`, etc.), so there's no single
  stable name to point at; `clangtidy_linter.py` auto-detects the most
  recently modified `build_ninja*` directory under the repo root that has a
  `compile_commands.json`, mirroring `setup.py`'s own `BuildDirectoryDetector`
  freshness logic. In practice: whichever configure/build you ran most
  recently is what lintrunner checks against. Pass `--build_dir` explicitly
  to pin a specific one (e.g. for a future CI job).
- **`compile_commands.json` only ever has entries for compiled `.cpp`/`.cc`/
  `.c` files — never headers**, since headers aren't their own translation
  unit. `clangtidy_linter.py` mirrors how the real build actually validates
  headers (only via inclusion from a `.cpp`, using `--header-filter` —
  never standalone) rather than guessing a synthesized compile command for
  a header directly: a `.h`/`.hxx` with no TU entry is silently skipped
  (visible with `--verbose`), not flagged. A header's findings surface when
  a `.cpp` that includes it gets checked, exactly matching the
  build-integrated pass's `--header-filter=^<root>/(Library|Cmake|Tools|
  Examples)/.*` from `Cmake/tools/clang_tidy.cmake` (kept in sync as
  `HEADER_FILTER`/`EXCLUDE_HEADER_FILTER` constants in
  `clangtidy_linter.py`) — if either changes, update both.
- A `.cpp` file *should* always have a `compile_commands.json` entry once
  the build directory covers it. If one doesn't, `clangtidy_linter.py` fails
  loudly (a `compile-error` lint message) instead of silently passing — a
  clean result for a `.cpp` means clang-tidy actually analyzed it, not just
  that nothing matched. If you see `compile-error` on many `.cpp` files,
  the auto-detected build directory doesn't cover them; rebuild the full
  tree (not a `--project.<lib>`-scoped one) so it does.
- Scope: `Library/**/*.{h,hxx,cpp}`, excluding `ThirdParty/`,
  `**/experimental/**`, `**/generated/**`, `Tools/**`, and
  **`Library/**/Testing/**/*.cpp`** (test files are not clang-tidy-checked
  by this path).
- Not currently run in CI (`.github/workflows/ci.yml` has no lintrunner or
  clang-tidy job) — this is a self-discipline check, not a merge gate.
  Treat "passes clang-tidy" as part of the review checklist in root
  `/CLAUDE.md` ("Reviewing major changes"), not something CI will catch for
  you.

## The check set is a deliberate allowlist — don't casually add to it

Root `.clang-tidy` enables `bugprone-*`, `modernize-*`, `readability-*`,
`misc-*` and then disables ~50 specific checks, each with an inline comment
explaining *why* (e.g. `-modernize-use-override` because override
annotations are "pending a dedicated refactor pass", `-bugprone-reserved-
identifier` because internal header guards intentionally use reserved
names). Read the comment above a disabled check before re-enabling it or
adding a new blanket disable at the root — a narrower, file-scoped fix is
almost always more correct (see below).

## When a check misfires on one file: scope the suppression, don't disable it repo-wide

Two precedents already exist for this — follow the same pattern instead of
editing the root config:
- `Library/Memory/gpu/.clang-tidy` — disables `modernize-macro-to-enum`
  only in that directory, because it crashes clang-tidy on
  `gpu_allocator_tracking.cpp`.
- `ThirdParty/Profiler/bespoke/kineto/.clang-tidy` — disables all
  `bugprone-*` only in that directory, because clang-tidy 21.1.0 crashes
  analyzing the vendored-fork `fmt` usage there at `-O3`.

Both start with `InheritParentConfig: true` (or equivalent) so they narrow
rather than replace the root ruleset. If you hit a real crash or an
unfixable false positive confined to one file/directory, add or extend a
directory-local `.clang-tidy` the same way — with a comment stating the
specific reason — rather than disabling the check for the whole repo.

## `ThirdParty/` is already excluded

Both mechanisms exclude `ThirdParty/` by default (CMake's exclude-header-
filter in `Cmake/tools/clang_tidy.cmake`; lintrunner's `exclude_patterns` in
`.lintrunner.toml`) — this is consistent with the root `/CLAUDE.md` hard
rule of never modifying vendored code. If clang-tidy output ever references
a `ThirdParty/` path, that's a config regression to flag, not something to
silence by editing vendored code.
