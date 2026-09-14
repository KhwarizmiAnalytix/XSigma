---
name: session-checklist
description: End-of-session / pre-commit checklist for XSigma — verify CMake and Bazel build definitions stay in sync, build and test both build systems, and run lintrunner and fix issues. Use when wrapping up a session that made non-trivial changes, or before creating a commit.
---

# session-checklist

Run this before ending a session that made non-trivial changes (new files,
a new library, anything touching build/CMake/Bazel config, or a multi-file
change) or before creating a commit. It's the same "process expectation, not
a CI gate" standard as CLAUDE.md's "Reviewing major changes" section — a
comment tweak or a one-line doc fix doesn't need the full sequence, but skip
it deliberately, not by default.

## 1. CMake ↔ Bazel sync check

XSigma ships two parallel, independently-maintained build systems
(`Scripts/setup.py` for CMake, `Scripts/setup_bazel.py` for Bazel — see the
root `/CLAUDE.md`). A file or option added to one and not the other builds
fine on whichever system you happened to test and silently breaks (or
silently drops coverage/tests) on the other. There is no automated diff
tool for this yet, so check by reading the relevant files side by side for
anything touched this session:

- **Library list**: root `CMakeLists.txt`'s `_xsigma_lib_order` list
  matches the libraries wired into `Scripts/setup_bazel.py`
  (`_BAZEL_LIBRARY_PACKAGE_DIR`, the `--project.NAME` valid-projects list)
  and declared in `bazel/*.bzl` / referenced from the root `BUILD.bazel`.
- **Per-library sources**: for each `Library/<Name>` you touched, diff the
  sources/headers listed (or globbed) in `Library/<Name>/CMakeLists.txt`
  against `srcs`/`hdrs` in `Library/<Name>/BUILD.bazel`. A new `.cpp`/`.h`
  must appear on both sides.
- **New library scaffolding**: adding a library needs, on both sides —
  CMake (`Library/<Name>/CMakeLists.txt`, an `add_subdirectory` entry in
  the root `CMakeLists.txt`) and Bazel (`Library/<Name>/BUILD.bazel`, a
  `bazel/<name>.bzl` copts/defines helper if the library follows that
  pattern, and wiring into `Scripts/setup_bazel.py`'s project map).
- **Feature/config tokens**: a new CMake option (`*_ENABLE_X`) needs a
  matching `.bazelrc` `--config=`/`--define=` and the corresponding token
  handled in `Scripts/setup_bazel.py`'s `build_bazel_command`.

## 2. Build and test — both build systems

CMake (see the `xsigma-build` skill for the full flag cheat sheet):
```
cd Scripts
python3 setup.py config.build.test.native
```

Bazel:
```
cd Scripts
python3 setup_bazel.py config.build.test.native
```

Scope to the library you touched with `--project.<name>` on either side to
keep the cycle fast; also build/test any library that depends on it if the
change could have cross-library fallout (e.g. a Core/Memory header change).
Both builds must succeed and both test suites must pass — a change that
only builds under one build system is not done.

## 3. Lint before commit

```
lintrunner -m main
```
`-m/--merge-base-with main` catches everything that differs from `main`,
not just the current working-tree diff — needed because prior uncommitted
work can still be sitting in the tree. Apply the mechanical fixes first:
```
lintrunner -a -m main
```
then hand-fix whatever `-a` can't patch (docstring length, missing type
annotations, genuine lint errors). Two known pre-existing items are *not*
mine/yours to silently fix as a drive-by — confirm they're still the same
(don't assume, re-check), and only touch them if the user asks:
- `Scripts/setup.py`'s `import colorama` triggers the `IMPORT` "disallowed
  import" lint. Pre-existing on `main`; fixing it means removing colorama
  from a widely-used script — a real but separate refactor.
- The `BAZEL_LINTER` "Advice" failure
  (`bazel query 'kind(http_archive, //external:*)'` exits 7) is a bug in
  `lint-tool`'s `bazel_linter` adapter — it queries a WORKSPACE-era
  construct this repo no longer has after migrating to Bzlmod. Not
  fixable by changing repo content.

Two CMake linters in this repo's `.lintrunner.toml` (`cmakelint` via the
`CMAKE` code, and `cmake-format` via `CMAKEFORMAT`) can disagree on
`AND (`/`OR (` spacing when a line starts with the operator immediately
followed by a parenthesized sub-expression — `cmakelint` misreads the
operator as a command name. If the parens are redundant (AND binds tighter
than OR in CMake), just drop them. If they're load-bearing, hoist the
sub-expression into a `set(_var TRUE/FALSE)` guard before the `if()` so no
line starts with `AND (`/`OR (` at all — see
`Library/Vectorization/Testing/Cxx/CMakeLists.txt`'s
`_vectorization_has_cuda_gpu_test_source` /
`_vectorization_has_hip_gpu_test_source` for the pattern.

## Reporting

State plainly which of the three checks passed, which didn't, and why —
same standard as CLAUDE.md's "Reviewing major changes": don't say "done"
without naming what was actually run.
