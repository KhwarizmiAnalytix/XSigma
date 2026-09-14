---
name: xsigma-build
description: Cheat sheet for configuring, building, and testing XSigma via Scripts/setup.py — dotted-token syntax, single-library builds, sanitizers, coverage, GPU backends, packet size. Use whenever the user asks to build, configure, test, or run a sanitizer/coverage pass on this repo.
---

# xsigma-build

XSigma is configured/built/tested exclusively through `Scripts/setup.py` —
never invoke CMake/ninja/ctest directly (see root `/CLAUDE.md`). Run
everything from the `Scripts/` directory. `python3 setup.py --help` is the
source of truth; this is a distilled cheat sheet of the common cases.

## Core invocation shape

Dotted tokens chain together, case-insensitive, in any order:
```
python3 setup.py <config|build|test>.<compiler/generator>.<feature tokens...> [--flag=value ...]
```

```
# Standard dev loop: configure + build + run tests, Ninja + Clang (defaults)
python3 setup.py config.build.test

# Restrict to one library instead of the whole tree
python3 setup.py config.build.test --project.vectorization
python3 setup.py config.build.test --project.memory

# Release + Visual Studio 2022
python3 setup.py config.build.test.vs22.release.python

# macOS + Xcode
python3 setup.py config.build.test.xcode

# GCC instead of default Clang
python3 setup.py config.build.test.gcc
```

## SIMD packet size

`--packet-size=N` or shorthand `psizeN` (default 4, sets
`VECTORIZATION_PACKET_SIZE`). Changing it means rebuilding, not reusing an
existing `build_*` directory.
```
python3 setup.py config.build.test.native.avx2.psize8 --project.vectorization
```

## CPU/GPU backend selection

- CPU SIMD: token is one of `sse`, `avx`, `avx2`, `avx512`, `neon`, `sve`
  (or `no` for scalar).
- GPU: `--gpu_backend=none|hip|cuda|metal`. HIP is Unix-only (fails fast on
  Windows by policy — see `Library/Vectorization/CLAUDE.md`).
- `sleef` token enables the SLEEF transcendentals library for NEON/SVE
  (auto-enabled already when Apple Accelerate vForce isn't present).

## Sanitizers

```
python3 setup.py config.build.test.ninja.clang --sanitizer.address
python3 setup.py config.build.test.ninja.clang --sanitizer.undefined
python3 setup.py config.build.test.vs22 --sanitizer.thread
```
Also: `--sanitizer.memory` (Clang only), `--sanitizer.leak`, or generic
`--sanitizer-type=<address|undefined|thread|memory|leak>`.

## Coverage

```
python3 setup.py config.build.test.ninja.clang.coverage
# Coverage analysis runs automatically — no separate .analyze step needed.
# To re-analyze an existing coverage build with more detail:
python3 setup.py analyze.v
```
Report parsing is the `coverage-tool` PyPI package
(https://github.com/KhwarizmiAnalytix/coverage-tool); CI does not
currently hard-gate on a specific coverage percentage. Install with
`pip install coverage-tool`.

## Static analysis (clang-tidy)

`clangtidy` / `clangtidy.fix` tokens — see the dedicated `clang-tidy` skill
for the two available mechanisms (build-integrated vs. lintrunner), since
fix-mode rewrites source files and needs to be scoped carefully.

## Benchmarks

Google Benchmark is on by default; use Release for real numbers:
```
python3 setup.py config.build.ninja.clang.release.benchmark
python3 setup.py config.build.ninja.clang.release.lto.benchmark
```
LTO variants: `--lto.thin` (Clang ThinLTO), `--lto.full`, `--lto.ipo`
(GCC/MSVC IPO fallback).

## Spell check / clang-tidy fix

```
python3 setup.py config.build.test.ninja.clang.spell   # check-only; skips ThirdParty
python3 setup.py config.build.test.ninja.clang.fix     # clang-tidy --fix-errors
```

## Other useful tokens

`tbb`, `openmp`, `mkl`, `numa`, `memkind`, `static`, `clangtidy`, `iwyu`,
`valgrind`, `mimalloc`, `external`, `cxx17`/`cxx20`/`cxx23`,
`cppcheck`, `icecc`, `examples`,
`--linker.mold|lld|gold|lld-link`, cache backend
`--cache=none|ccache|sccache|buildcache`.
