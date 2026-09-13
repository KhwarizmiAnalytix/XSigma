#!/usr/bin/env python3
"""XSigma Bazel Build Configuration Script.

This script provides a simplified interface for building XSigma with Bazel,
mirroring the functionality of setup.py but using Bazel instead of CMake.

Usage:
    python Scripts/setup_bazel.py config.build.test.release.avx2
    python setup_bazel.py config.build.release.test.vv.enzyme   # from repo root (wrapper)
    python setup_bazel.py build.test.debug
    python setup_bazel.py test
    python setup_bazel.py config.build.release.test.cxx20
"""

import glob
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Optional


try:
    import colorama

    colorama.init()
    COLOR_CYAN = colorama.Fore.CYAN
    COLOR_GREEN = colorama.Fore.GREEN
    COLOR_RED = colorama.Fore.RED
    COLOR_WHITE = colorama.Fore.WHITE
    COLOR_YELLOW = colorama.Fore.YELLOW
    COLOR_RESET = colorama.Style.RESET_ALL
except ImportError:  # Bazel CI jobs may not pip-install colorama
    COLOR_CYAN = ""
    COLOR_GREEN = ""
    COLOR_RED = ""
    COLOR_WHITE = ""
    COLOR_YELLOW = ""
    COLOR_RESET = ""


def print_status(message: str, status: str = "INFO") -> None:
    """Print colored status messages."""
    colors = {
        "INFO": COLOR_CYAN,
        "SUCCESS": COLOR_GREEN,
        "WARNING": COLOR_YELLOW,
        "ERROR": COLOR_RED,
    }
    color = colors.get(status, COLOR_WHITE)
    print(f"{color}[{status}]{COLOR_RESET} {message}")


_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from helpers.cpu_isa import runtime_test_skip_reason


def _find_bazel_executable() -> Optional[str]:
    """Return the absolute path of bazelisk or bazel, or None."""
    # On Windows, shutil.which also resolves .exe/.cmd/.ps1 extensions.
    # Return the full path: CreateProcess cannot find a bare "bazelisk"
    # when the hit is bazelisk.cmd (WinError 2).
    for cmd in ["bazelisk", "bazel"]:
        path = shutil.which(cmd)
        if path:
            return path
    return None


def check_bazel_installed() -> bool:
    """Check if Bazel or Bazelisk is installed."""
    cmd = _find_bazel_executable()
    if cmd:
        print_status(f"Found {cmd}", "INFO")
        return True
    return False


def get_bazel_command() -> str:
    """Get the appropriate Bazel command (bazelisk or bazel)."""
    cmd = _find_bazel_executable()
    if cmd:
        return cmd
    raise RuntimeError("Neither bazel nor bazelisk found in PATH")


def bazel_prefix() -> list[str]:
    """Argv prefix that can spawn Bazel on every platform.

    Windows ``.cmd``/``.bat`` launchers need ``cmd /c``; CreateProcess
    cannot execute them directly (WinError 2).
    """
    exe = get_bazel_command()
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/c", exe]
    return [exe]


def find_enzyme_pass_plugin() -> Optional[str]:
    """Resolve the Enzyme LLVM plugin path (mirrors Cmake/tools/enzyme.cmake).

    Prefer LLDEnzyme over ClangEnzyme when multiple matches exist. Honour
    ENZYME_PLUGIN_PATH when set to an existing file.
    """
    env_path = os.environ.get("ENZYME_PLUGIN_PATH", "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path

    system = platform.system()
    search_dirs: list[str] = []
    if system == "Darwin":
        search_dirs = ["/opt/homebrew/lib", "/usr/local/lib", "/usr/lib"]
    elif system == "Linux":
        search_dirs = ["/usr/lib", "/usr/local/lib"]
        llvm_dir = os.environ.get("LLVM_DIR", "").strip()
        if llvm_dir:
            search_dirs.insert(0, os.path.join(llvm_dir, "lib"))
    elif system == "Windows":
        # Match FindEnzyme.cmake: optional ignore of LLVM_DIR for unwanted prefixes.
        restrict = os.environ.get(
            "ENZYME_RESTRICT_TO_SYSTEM_LLVM_INSTALL", ""
        ).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if restrict:
            search_dirs = [
                r"C:\Program Files\LLVM\bin",
                r"C:\Program Files\LLVM\lib",
                r"C:\Program Files (x86)\LLVM\bin",
                r"C:\Program Files (x86)\LLVM\lib",
            ]
        else:
            search_dirs = [
                os.path.join(os.environ.get("LLVM_DIR", ""), "bin"),
                os.path.join(os.environ.get("LLVM_DIR", ""), "lib"),
                r"C:\Program Files\LLVM\bin",
                r"C:\Program Files\LLVM\lib",
            ]

    patterns: list[str] = []
    if system == "Darwin":
        patterns = ["LLDEnzyme-*.dylib", "ClangEnzyme-*.dylib", "LLVMEnzyme-*.dylib"]
    elif system == "Linux":
        patterns = ["LLDEnzyme-*.so", "ClangEnzyme-*.so", "LLVMEnzyme-*.so"]
    elif system == "Windows":
        patterns = ["LLDEnzyme-*.dll", "ClangEnzyme-*.dll", "LLVMEnzyme-*.dll"]

    candidates: list[str] = []
    for directory in search_dirs:
        if not directory or not os.path.isdir(directory):
            continue
        for pattern in patterns:
            candidates.extend(glob.glob(os.path.join(directory, pattern)))

    # Prefer LLDEnzyme (same as CMake enzyme.cmake)
    for marker in ("LLDEnzyme", "ClangEnzyme", "LLVMEnzyme"):
        for path in candidates:
            if marker in os.path.basename(path):
                return path
    return candidates[0] if candidates else None


# Maps CMake sanitizer names (setup.py / -DSANITIZER_TYPE) to Bazel --config names in .bazelrc
_CMAKE_SAN_TO_BAZEL = {
    "address": "asan",
    "undefined": "ubsan",
    "thread": "tsan",
    "memory": "msan",
    "leak": "lsan",
}

# Library/* scope for --project.NAME / dotted project.NAME (matches CMake XSIGMA_LIBRARY_PROJECT)
_BAZEL_LIBRARY_PROJECTS = (
    "logging",
    "memory",
    "vectorization",
    "core",
    "parallel",
    "profiler",
    "models",
)

_BAZEL_LIBRARY_PACKAGE_DIR = {
    "logging": "Logging",
    "memory": "Memory",
    "vectorization": "Vectorization",
    "core": "Core",
    "parallel": "Parallel",
    "profiler": "Profiler",
    "models": "Models",
}


def _bazel_project_pattern(name: str) -> str:
    """Bazel target pattern for --project.NAME (Profiler lives in @profiler)."""
    if name == "profiler":
        return "@profiler//..."
    pkg = _BAZEL_LIBRARY_PACKAGE_DIR[name]
    return f"//Library/{pkg}/..."


def _merge_dotted_segments(parts: list[str]) -> list[str]:
    """Merge split segments like parallel.openmp, sanitizer.address into single tokens."""
    out: list[str] = []
    pl = [p.lower() for p in parts]
    i = 0
    while i < len(pl):
        if (
            pl[i] == "parallel"
            and i + 1 < len(pl)
            and pl[i + 1] in ("std", "openmp", "tbb")
        ):
            out.append(f"parallel.{pl[i + 1]}")
            i += 2
        elif (
            pl[i] == "sanitizer"
            and i + 1 < len(pl)
            and pl[i + 1] in _CMAKE_SAN_TO_BAZEL
        ):
            out.append(_CMAKE_SAN_TO_BAZEL[pl[i + 1]])
            i += 2
        elif (
            pl[i] == "profiler"
            and i + 1 < len(pl)
            and pl[i + 1] in ("kineto", "itt", "native")
        ):
            out.append(f"profiler_{pl[i + 1]}")
            i += 2
        elif (
            pl[i] == "logging"
            and i + 1 < len(pl)
            and pl[i + 1]
            in (
                "native",
                "loguru",
                "glog",
                "spdlog",
            )
        ):
            out.append(f"logging_{pl[i + 1]}")
            i += 2
        elif (
            pl[i] == "lto"
            and i + 1 < len(pl)
            and pl[i + 1] in ("off", "thin", "full", "ipo", "auto")
        ):
            out.append(f"lto.{pl[i + 1]}")
            i += 2
        elif (
            pl[i] == "project"
            and i + 1 < len(pl)
            and pl[i + 1] in _BAZEL_LIBRARY_PROJECTS
        ):
            out.append(f"project.{pl[i + 1]}")
            i += 2
        elif (
            pl[i] == "cpu_backend"
            and i + 1 < len(pl)
            and pl[i + 1] in ("no", "sse", "avx", "avx2", "avx512", "neon", "sve")
        ):
            out.append(f"cpu_backend.{pl[i + 1]}")
            i += 2
        elif (
            pl[i] == "gpu_backend"
            and i + 1 < len(pl)
            and pl[i + 1] in ("none", "cuda", "hip", "metal")
        ):
            out.append(f"gpu_backend.{pl[i + 1]}")
            i += 2
        else:
            out.append(pl[i])
            i += 1
    return out


class BazelConfiguration:
    """Manages Bazel build configuration and execution."""

    def __init__(self, args: list[str]) -> None:
        """Initialize configuration from command-line arguments."""
        self.args = args
        self.build_type = "debug"  # Default build type
        self.vectorization: Optional[str] = None
        self.cxx_standard: Optional[str] = None
        self.configs: list[str] = []
        self.targets: list[str] = [
            "//Library/..."
        ]  # Our code only; never test/build ThirdParty cc_test trees
        self.run_tests = False
        self.run_build = False
        self.run_clean = False
        self.run_config = False
        self.run_coverage = False
        self.timing_data: dict[str, float] = {}
        # Warn when a phase exceeds this many seconds (incremental builds should stay fast)
        self.slow_phase_warn_seconds: float = 60.0
        # Pass --batch to bazel (avoids waiting on a stuck server; slower per invocation)
        self.use_batch: bool = False
        # Verbose test output (--test_output=all) when token "vv" is present
        self.verbose_tests = False
        # Timeout in seconds for build/test/coverage subprocesses (default: 10 min)
        self.subprocess_timeout: int = 600

        # Default backends (matching CMake defaults)
        self.logging_backend = "loguru"  # Default: LOGURU (matches CMake)
        self.profiler_backend = "kineto"  # Default: KINETO (matches CMake)

        # Compiler and build tool configuration
        self.compiler: Optional[str] = (
            None  # Compiler type: "clang", "gcc", "msvc", etc.
        )
        self.build_tool: Optional[str] = (
            None  # Build tool: "ninja", "xcode", "msvc", etc.
        )
        self.visual_studio_version: Optional[str] = (
            None  # VS version: "vs17", "vs19", "vs22", "vs26"
        )
        self.system = platform.system()

        # CPU SIMD backend: mirrors CMake VECTORIZATION_CPU_BACKEND (no|sse|avx|avx2|avx512|neon|sve).
        self.cpu_backend: str = ""
        # GPU backend: mirrors CMake MEMORY_GPU_BACKEND / VECTORIZATION_GPU_BACKEND.
        self.gpu_backend: str = "none"
        # Mirrors CMake PARALLEL_BACKEND (std | openmp | tbb). None = infer only from tbb/openmp tokens.
        self.parallel_backend: Optional[str] = None
        # CMake: passing `gtest` disables per-module ENABLE_GTEST (default ON).
        self.disable_gtest: bool = False
        # CMake: token `static` sets BUILD_SHARED_LIBS=ON (shared DLLs).
        self.shared_libs: bool = False
        # Limit Bazel build/test to //Library/<Name>/... (--project.NAME / project.NAME).
        self.library_project: Optional[str] = None

        # LTO mode: "off" | "thin" | "full" | "ipo" | "auto"
        # All non-"off" values map to --config=lto in Bazel; the mode label is surfaced in summaries.
        self.lto_mode: str = "off"

        # SLEEF SIMD math library for NEON/SVE (AArch64; maps to --config=sleef in .bazelrc)
        self.enable_sleef: bool = False

        # CMake-only flags — not executed in Bazel but tracked so the summary is accurate.
        self.spell: bool = False
        self.clangtidy: bool = False
        self.fix: bool = False
        self.iwyu: bool = False
        self.valgrind: bool = False
        self.icecc: bool = False
        self.examples: bool = False
        self.cppcheck: bool = False

        self._parse_arguments()
        self._apply_library_project_targets()
        self._finalize_parallel_configs()
        self._apply_defaults()

    def _is_visual_studio_arg(self, arg: str) -> bool:
        """Check if argument matches Visual Studio version pattern (.vsXX.)."""
        # Match patterns like .vs26., .vs22., .vs19., .vs17.
        return arg.lower() in ["vs17", "vs19", "vs22", "vs26"]

    def _is_xcode_arg(self, arg: str) -> bool:
        """Check if argument is xcode."""
        return arg.lower() == "xcode"

    def _is_ninja_arg(self, arg: str) -> bool:
        """Check if argument is ninja."""
        return arg.lower() == "ninja"

    def _is_clang_compiler(self, arg: str) -> bool:
        """Check if argument is a Clang compiler specification."""
        return "clang" in arg.lower() and arg.lower() not in [
            "clang-cl",
            "clangtidy",
            "clangtid",
            "clang-tidy",
            "clang_tidy",
        ]

    def _is_gcc_compiler(self, arg: str) -> bool:
        """Check if argument is a GCC compiler specification."""
        return ("gcc" in arg.lower() or "g++" in arg.lower()) and arg.lower() not in [
            "cppcheck"
        ]

    def _apply_library_project_targets(self) -> None:
        """Narrow self.targets to one Library/* tree when project.NAME was set."""
        if not self.library_project:
            return
        if self.library_project not in _BAZEL_LIBRARY_PACKAGE_DIR:
            return
        pattern = _bazel_project_pattern(self.library_project)
        self.targets = [pattern]
        print_status(
            f"Library scope: targets = {pattern} (Bazel does not trim transitive deps)",
            "INFO",
        )

    def _parse_arguments(self) -> None:
        """Parse command-line arguments to extract build configuration."""
        for arg in self.args:
            arg_lower = arg.lower()

            # Compiler and build tool detection
            if self._is_visual_studio_arg(arg):
                self.visual_studio_version = arg
                self.build_tool = "msvc"
                self.compiler = "msvc"
            elif self._is_xcode_arg(arg):
                self.build_tool = "xcode"
                self.compiler = "clang"
            elif self._is_ninja_arg(arg):
                self.build_tool = "ninja"
            elif self._is_clang_compiler(arg):
                self.compiler = "clang"
            elif self._is_gcc_compiler(arg):
                self.compiler = "gcc"

            # Build type
            elif arg_lower in ["debug", "release", "relwithdebinfo"]:
                self.build_type = arg_lower
                self.configs.append(arg_lower)

            # C++ Standard
            elif arg_lower in ["cxx17", "cxx20", "cxx23"]:
                self.cxx_standard = arg_lower

            # Vectorization
            elif arg_lower in ["sse", "avx", "avx2", "avx512", "neon", "sve"]:
                self.vectorization = arg_lower
                self.configs.append(arg_lower)

            # SLEEF SIMD math library (NEON/SVE — maps to --config=sleef in .bazelrc)
            elif arg_lower == "sleef":
                self.enable_sleef = True
                self.configs.append("sleef")

            # LTO — bare token or dotted mode (lto.thin, lto.full, lto.ipo, lto.auto)
            elif arg_lower == "lto" or arg_lower.startswith("lto."):
                _lto_modes = {"off", "thin", "full", "ipo", "auto"}
                if "." in arg_lower:
                    _mode = arg_lower.split(".", 1)[1]
                else:
                    _mode = "auto"  # bare 'lto' → auto
                if _mode not in _lto_modes:
                    print_status(
                        f"Invalid LTO mode '{_mode}'. Valid options: {', '.join(sorted(_lto_modes))}",
                        "ERROR",
                    )
                    sys.exit(1)
                self.lto_mode = _mode
                if _mode != "off":
                    self.configs.append("lto")

            # CPU SIMD backend
            elif arg_lower.startswith("cpu_backend."):
                _cpu = arg_lower.split(".", 1)[1]
                _valid_cpu = ("no", "sse", "avx", "avx2", "avx512", "neon", "sve")
                if _cpu in _valid_cpu:
                    self.cpu_backend = _cpu
                else:
                    print_status(
                        f"Invalid CPU backend '{_cpu}'. Valid options: {', '.join(_valid_cpu)}",
                        "ERROR",
                    )
                    sys.exit(1)

            # Bare SIMD tokens (e.g. neon, avx2 as a dotted-chain segment)
            elif arg_lower in ("no", "sse", "avx", "avx2", "avx512", "neon", "sve"):
                self.cpu_backend = arg_lower

            # Optional features
            elif arg_lower in ("cuda", "hip", "metal"):
                self.gpu_backend = arg_lower
                self.configs.append(arg_lower)

            elif arg_lower.startswith("gpu_backend."):
                backend = arg_lower.split(".", 1)[1]
                if backend in ("none", "cuda", "hip", "metal"):
                    self.gpu_backend = backend
                    if backend != "none":
                        self.configs.append(backend)
                else:
                    print_status(
                        f"Invalid GPU backend '{backend}'. Valid options: none, cuda, hip, metal",
                        "ERROR",
                    )
                    sys.exit(1)

            elif arg_lower in ["mimalloc", "magic_enum", "tbb", "mkl", "openmp"]:
                self.configs.append(arg_lower)

            # NUMA / memkind (see .bazelrc build:numa / build:memkind)
            elif arg_lower in ("numa", "memkind"):
                self.configs.append(arg_lower)

            # Google Benchmark (opt-in, matches CMake)
            elif arg_lower == "benchmark":
                self.configs.append("benchmark")

            # CMake inverse: `gtest` token disables CORE_HAS_GTEST / test framework defines
            elif arg_lower == "gtest":
                self.disable_gtest = True

            # CMake: token `static` enables shared libraries (BUILD_SHARED_LIBS=ON)
            elif arg_lower == "static":
                self.shared_libs = True

            # SMP backend (same semantics as setup.py --parallel.* / parallel.openmp in dotted args)
            elif arg_lower.startswith("parallel."):
                backend = arg_lower.split(".", 1)[1]
                if backend in ("std", "openmp", "tbb"):
                    self.parallel_backend = backend
                else:
                    print_status(
                        f"Invalid parallel backend '{backend}'. Use std, openmp, or tbb.",
                        "ERROR",
                    )
                    sys.exit(1)

            elif arg_lower.startswith("project."):
                proj = arg_lower.split(".", 1)[1]
                if proj not in _BAZEL_LIBRARY_PROJECTS:
                    print_status(
                        f"Invalid --project / project.* value '{proj}'. "
                        f"Valid: {', '.join(_BAZEL_LIBRARY_PROJECTS)}",
                        "ERROR",
                    )
                    sys.exit(1)
                self.library_project = proj

            # Sanitizer shorthand (matches help text and CMake names via parse_args)
            elif arg_lower in ("asan", "tsan", "ubsan", "msan", "lsan"):
                self.configs.append(arg_lower)

            # Enzyme AD (matches .bazelrc build:enzyme)
            elif arg_lower == "enzyme":
                self.configs.append("enzyme")

            # CMake-only developer flags — tracked for summary accuracy, not executed in Bazel
            elif arg_lower in ["spell"]:
                self.spell = True
                print_status(
                    "Token 'spell': spell-checking is CMake-only (shown in summary, not run).",
                    "WARNING",
                )

            elif arg_lower in ["clangtidy", "clangtid", "clang-tidy", "clang_tidy"]:
                self.clangtidy = True
                print_status(
                    "Token 'clangtidy': clang-tidy is CMake-only (shown in summary, not run).",
                    "WARNING",
                )

            elif arg_lower in ["fix"]:
                self.fix = True
                print_status(
                    "Token 'fix': clang-tidy --fix is CMake-only (shown in summary, not run).",
                    "WARNING",
                )

            elif arg_lower in ["iwyu"]:
                self.iwyu = True
                print_status(
                    "Token 'iwyu': include-what-you-use is CMake-only (shown in summary, not run).",
                    "WARNING",
                )

            elif arg_lower in ["valgrind"]:
                self.valgrind = True
                print_status(
                    "Token 'valgrind': Valgrind is CMake-only (shown in summary, not run).",
                    "WARNING",
                )

            elif arg_lower in ["icecc"]:
                self.icecc = True
                print_status(
                    "Token 'icecc': Icecream compiler is CMake-only (shown in summary, not run).",
                    "WARNING",
                )

            elif arg_lower in ["examples"]:
                self.examples = True
                print_status(
                    "Token 'examples': examples are CMake-only (shown in summary, not run).",
                    "WARNING",
                )

            elif arg_lower in ["cppcheck"]:
                self.cppcheck = True
                print_status(
                    "Token 'cppcheck': cppcheck is CMake-only (shown in summary, not run).",
                    "WARNING",
                )

            elif arg_lower in ("external", "cache", "linker"):
                print_status(
                    f"Token '{arg_lower}': CMake-only, no Bazel equivalent (see Docs/readme/bazel.md).",
                    "WARNING",
                )

            # Verbose test log output (maps to --test_output=all)
            elif arg_lower == "vv":
                self.verbose_tests = True

            # Avoid blocking on another Bazel server PID (use if you see "Another command is running")
            elif arg_lower == "batch":
                self.use_batch = True

            # Logging backends (with logging_ prefix)
            elif arg_lower.startswith("logging_"):
                backend = arg_lower[8:]  # Remove "logging_" prefix
                if backend in ["glog", "loguru", "native", "spdlog"]:
                    self.logging_backend = backend
                    self.configs.append(arg_lower)

            # Profiler backends (with profiler_ prefix)
            elif arg_lower.startswith("profiler_"):
                backend = arg_lower[9:]  # Remove "profiler_" prefix
                if backend in ["kineto", "itt"]:
                    self.profiler_backend = backend
                    self.configs.append(backend)
                elif backend == "native":
                    # The native traceme/xplane pipeline is always compiled now (no longer a
                    # selectable backend -- see bazel/profiler.bzl); "native" only used to mean
                    # "skip the Kineto/ITT instrumentation backend", which no longer applies.
                    print_status(
                        "profiler_native is a no-op: the native profiler pipeline is always "
                        "compiled now, independent of the Kineto/ITT instrumentation backend.",
                        "WARNING",
                    )

            # Sanitizers: sanitizer_asan or legacy sanitizer_address -> asan
            elif arg_lower.startswith("sanitizer_"):
                sanitizer = arg_lower[10:]
                if sanitizer in _CMAKE_SAN_TO_BAZEL:
                    self.configs.append(_CMAKE_SAN_TO_BAZEL[sanitizer])
                elif sanitizer in ("asan", "tsan", "ubsan", "msan", "lsan"):
                    self.configs.append(sanitizer)
                else:
                    print_status(
                        f"Unknown sanitizer token '{arg_lower}'. "
                        f"Use asan, tsan, ubsan, msan, lsan or CMake-style sanitizer.*",
                        "ERROR",
                    )
                    sys.exit(1)

            # Actions
            elif arg_lower == "build":
                self.run_build = True
            elif arg_lower == "test":
                self.run_tests = True
            elif arg_lower == "coverage":
                self.run_coverage = True
            elif arg_lower == "clean":
                self.run_clean = True
            elif arg_lower == "config":
                self.run_config = True

    def _finalize_parallel_configs(self) -> None:
        """Apply PARALLEL_BACKEND-style exclusivity (std vs OpenMP vs TBB)."""
        if self.parallel_backend is None:
            return
        self.configs = [c for c in self.configs if c not in ("openmp", "tbb")]
        if self.parallel_backend == "openmp":
            self.configs.append("openmp")
        elif self.parallel_backend == "tbb":
            self.configs.append("tbb")

    def _apply_defaults(self) -> None:
        """Apply default compiler and build tool settings.

        Default Behavior (All Platforms):
        - If no Visual Studio or Xcode is detected/specified
        - If the compiler or build tool is not explicitly defined
        - Then default to using Ninja + Clang on all platforms

        Windows-Specific Behavior:
        - If a Visual Studio version is specified (.vs26., .vs22., .vs19., .vs17.)
        - Then build using the corresponding Visual Studio version
        """
        # If Visual Studio is specified on Windows, use it
        if self.visual_studio_version and self.system == "Windows":
            print_status(
                f"Using Visual Studio {self.visual_studio_version.upper()}", "INFO"
            )
            return

        # If Xcode is specified on macOS, use it (Kineto unsupported — matches setup.py). ITT is
        # the only other instrumentation backend, so use it to avoid Kineto under Xcode (the
        # native traceme/xplane pipeline compiles either way, independent of this choice).
        if self.build_tool == "xcode" and self.system == "Darwin":
            print_status("Using Xcode generator", "INFO")
            self.profiler_backend = "itt"
            return

        # Default to Ninja + Clang on all platforms
        if not self.build_tool:
            self.build_tool = "ninja"
        if not self.compiler:
            self.compiler = "clang"

        print_status(
            f"Using default build configuration: {self.build_tool.upper()} + {self.compiler.upper()}",
            "INFO",
        )

    def build_bazel_command(self, action: str) -> list[str]:
        """Build the Bazel command with all configurations."""
        cmd = bazel_prefix()
        if self.use_batch:
            cmd.append("--batch")
        cmd.append(action)

        # Add compiler-specific configuration
        if self.compiler == "clang":
            cmd.append("--config=clang")
        elif self.compiler == "gcc":
            cmd.append("--config=gcc")
        elif self.compiler == "msvc":
            cmd.append("--config=msvc")

        # Add build tool specific configuration
        if self.build_tool == "xcode":
            cmd.append("--config=xcode")

        if self.shared_libs:
            cmd.append("--define=build_shared_libs=true")

        # Stable, de-duplicated config list (do not mutate self.configs — execute() may call twice)
        cfg_list: list[str] = []
        seen_cfg: set[str] = set()
        for c in self.configs:
            if c not in seen_cfg:
                seen_cfg.add(c)
                cfg_list.append(c)

        # GoogleTest: CMake defaults ENABLE_GTEST ON; token `gtest` turns it OFF (see disable_gtest).
        if self.disable_gtest:
            cmd.append("--define=enable_gtest=false")
            cfg_list = [c for c in cfg_list if c != "gtest"]
        elif "gtest" not in cfg_list:
            cfg_list.append("gtest")

        # Google Benchmark: CMake defaults *ENABLE_BENCHMARK ON for all library modules.
        if "benchmark" not in cfg_list:
            cfg_list.append("benchmark")

        # Add default logging backend if not explicitly set
        if not any(c.startswith("logging_") for c in cfg_list):
            cfg_list.append(f"logging_{self.logging_backend}")

        # Add default profiler backend if not explicitly set
        profiler_configs = ["kineto", "itt"]
        if not any(c in profiler_configs for c in cfg_list):
            if self.profiler_backend in profiler_configs:
                cfg_list.append(self.profiler_backend)

        # Add all config flags
        for config in cfg_list:
            cmd.append(f"--config={config}")

        # CPU SIMD backend define — mirrors CMake -DVECTORIZATION_CPU_BACKEND. Bazel's
        # vectorization_type_{no,sse,avx,avx2,avx512,neon,sve} config_settings (bazel/BUILD.bazel)
        # key on "vectorization_type", not "vectorization_cpu" -- the latter was never consumed
        # by any config_setting, so this token silently did nothing before this fix.
        if self.cpu_backend:
            cmd.append(f"--define=vectorization_type={self.cpu_backend}")

        # GPU backend defines — mirrors CMake -DMEMORY_GPU_BACKEND / -DVECTORIZATION_GPU_BACKEND.
        # Memory's and Vectorization's GPU backends are two independent CMake cache variables
        # (see Docs/BAZEL_USER_GUIDE.md's Known Gaps section); Bazel models each as three
        # mutually-exclusive booleans per library (enable_cuda/enable_hip/enable_metal), not a
        # single "gpu_backend" string define (which -- like vectorization_cpu above -- was never
        # consumed by any config_setting). Emit the matching pair of booleans for both libraries
        # together, since this script only exposes one --gpu_backend chain to the user.
        if self.gpu_backend in ("cuda", "hip", "metal"):
            cmd.append(f"--define=memory_enable_{self.gpu_backend}=true")
            cmd.append(f"--define=vectorization_enable_{self.gpu_backend}=true")

        # Enzyme: CMake applies -fpass-plugin at compile and link for Enzyme::enzyme.
        # Bazel only toggles XSIGMA_HAS_ENZYME; without the plugin, __enzyme_* calls are
        # unresolved (crash at null). Restrict --per_file_copt to //Library so GCC-built
        # third-party targets never see -fpass-plugin.
        if "enzyme" in cfg_list:
            if self.compiler != "clang":
                print_status(
                    "Enzyme requires Clang; skipping -fpass-plugin (Enzyme tests may fail).",
                    "WARNING",
                )
            else:
                plugin = find_enzyme_pass_plugin()
                if plugin:
                    cmd.append(
                        f"--per_file_copt=//Library/Core/.*\\.cpp$@-fpass-plugin={plugin}"
                    )
                    cmd.append(f"--linkopt=-fpass-plugin={plugin}")
                    print_status(f"Enzyme LLVM pass plugin: {plugin}", "INFO")
                else:
                    print_status(
                        "Enzyme enabled but no plugin found. Set ENZYME_PLUGIN_PATH or install "
                        "enzyme (e.g. brew install enzyme). Enzyme AD tests may crash.",
                        "WARNING",
                    )

        # Add C++ standard if specified
        if self.cxx_standard:
            if self.cxx_standard == "cxx17":
                cmd.append("--cxxopt=-std=c++17")
            elif self.cxx_standard == "cxx20":
                cmd.append("--cxxopt=-std=c++20")
            elif self.cxx_standard == "cxx23":
                cmd.append("--cxxopt=-std=c++23")

        # Bazel derives a default --instrumentation_filter from the package(s) of the
        # target(s) on the command line. A single test target such as
        # //Library/Core/Testing/Cxx:CoreCxxTests only matches that test package, not the
        # //Library/Core/... packages it actually exercises -- so `bazel coverage` silently
        # emits an empty report ("WARNING: There was no coverage found.") unless the filter
        # is widened explicitly. Scope it to the selected library when --project.NAME
        # narrowed the target set, otherwise cover all of //Library.
        if action == "coverage":
            filter_pkg = "//Library"
            if self.library_project == "profiler":
                filter_pkg = "@profiler"
            elif self.library_project:
                pkg = _BAZEL_LIBRARY_PACKAGE_DIR.get(self.library_project)
                if pkg:
                    filter_pkg = f"//Library/{pkg}"
            cmd.append(f"--instrumentation_filter={filter_pkg}[/:]")

        # Add targets
        cmd.extend(self.targets)

        return cmd

    def _kill_stale_bazel_processes(self) -> None:
        """Force-kill any stale Bazel server processes holding the output base lock.

        Uses taskkill directly — never calls 'bazel shutdown' which itself requires
        the lock and will hang if another instance is holding it.
        """
        print_status("Killing any stale Bazel server processes...", "INFO")
        for proc_name in ["bazel-real.exe", "bazel.exe"]:
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", proc_name],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                if result.returncode == 0:
                    print_status(f"Killed stale process: {proc_name}", "WARNING")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    def _shutdown_bazel_for_batch(self) -> None:
        """Stop the Bazel server so --batch does not warn about differing startup options."""
        if not self.use_batch:
            return
        print_status(
            "Running `bazel shutdown` before `--batch` (avoids startup-option mismatch on the server).",
            "INFO",
        )
        try:
            subprocess.run(
                bazel_prefix() + ["shutdown"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # -------------------------------------------------------------------------
    # Per-module summary helpers
    # -------------------------------------------------------------------------

    def _on_off(self, condition: bool) -> str:
        return (
            f"{COLOR_GREEN}ON{COLOR_RESET}"
            if condition
            else f"{COLOR_RED}OFF{COLOR_RESET}"
        )

    def _na(self) -> str:
        return self._on_off(False)

    def _cxx_std_display(self) -> str:
        if self.cxx_standard:
            return self.cxx_standard.replace("cxx", "C++")
        return "C++20"

    def _sanitizer_info(self) -> tuple[bool, str]:
        for token, san_type in [
            ("asan", "address"),
            ("tsan", "thread"),
            ("ubsan", "undefined"),
            ("msan", "memory"),
            ("lsan", "leak"),
        ]:
            if token in self.configs:
                return True, san_type
        return False, "address"

    def _pf(self, label: str, value: str, width: int = 20) -> None:
        print(f"  {label:{width}}: {value}")

    def print_module_summaries(self) -> None:
        """Print per-module configuration summaries mirroring CMake's per-module output."""
        W = 20  # uniform column width across all modules
        na = self._na()
        cxx = self._cxx_std_display()
        has_san, san_type = self._sanitizer_info()
        lto = (
            self.lto_mode if self.lto_mode != "off" else f"{COLOR_RED}off{COLOR_RESET}"
        )
        coverage = self._on_off(self.run_coverage)
        testing = self._on_off(self.run_tests)
        gtest = self._on_off(not self.disable_gtest)
        benchmark = self._on_off("benchmark" in self.configs)
        vec = self.vectorization.upper() if self.vectorization else "None"
        sanitizer = self._on_off(has_san)
        mimalloc_on = True  # default: .bazelrc + memory.bzl; opt out: --define=memory_enable_mimalloc=false

        # Common trailing fields shared by all modules — every flag reflects actual passed state
        def common() -> None:
            self._pf("Cache", na, W)
            self._pf("Cache backend", na, W)
            self._pf("Icecc", self._on_off(self.icecc), W)
            self._pf("Linker", na, W)
            self._pf("Lto", lto, W)
            self._pf("Coverage", coverage, W)
            self._pf("Testing", testing, W)
            self._pf("Examples", self._on_off(self.examples), W)
            self._pf("Gtest", gtest, W)
            self._pf("Benchmark", benchmark, W)
            self._pf("Clang-tidy", self._on_off(self.clangtidy), W)
            self._pf("Fix", self._on_off(self.fix), W)
            self._pf("Iwyu", self._on_off(self.iwyu), W)
            self._pf("Sanitizer", sanitizer, W)
            self._pf("Sanitizer type", san_type, W)
            self._pf("Spell", self._on_off(self.spell), W)
            self._pf("Valgrind", self._on_off(self.valgrind), W)

        # ── Core ──────────────────────────────────────────────────────────────
        print(f"\n{COLOR_CYAN}******** Core module (Bazel flags) ********{COLOR_RESET}")
        self._pf("Vectorization type", vec, W)
        self._pf("Sleef", self._on_off(self.enable_sleef), W)
        self._pf("Mkl", self._on_off("mkl" in self.configs), W)
        self._pf("Svml", na, W)
        self._pf("Rocm", na, W)
        self._pf("Experimental", na, W)
        self._pf("Magic enum", self._on_off(True), W)
        self._pf("Enzyme", self._on_off("enzyme" in self.configs), W)
        self._pf("Compression", na, W)
        self._pf("Cxx standard", cxx, W)
        common()

        # ── Logging ───────────────────────────────────────────────────────────
        print(
            f"\n{COLOR_CYAN}******** Logging module (Bazel flags) ********{COLOR_RESET}"
        )
        self._pf("Backend", self.logging_backend.upper(), W)
        self._pf("Cxx standard", cxx, W)
        common()

        # ── Memory ────────────────────────────────────────────────────────────
        print(
            f"\n{COLOR_CYAN}******** Memory module (Bazel flags) ********{COLOR_RESET}"
        )
        self._pf("Mimalloc", self._on_off(mimalloc_on), W)
        self._pf("Memkind", na, W)
        self._pf("Numa", na, W)
        self._pf("Tbb", self._on_off("tbb" in self.configs), W)
        self._pf("Cuda", self._on_off("cuda" in self.configs), W)
        self._pf("Hip", self._on_off("hip" in self.configs), W)
        self._pf("Metal", self._on_off("metal" in self.configs), W)
        self._pf("Cxx standard", cxx, W)
        common()

        # ── Parallel ──────────────────────────────────────────────────────────
        print(
            f"\n{COLOR_CYAN}******** Parallel module (Bazel flags) ********{COLOR_RESET}"
        )
        self._pf("Tbb", self._on_off("tbb" in self.configs), W)
        self._pf("Openmp", self._on_off("openmp" in self.configs), W)
        self._pf("Cxx standard", cxx, W)
        common()

        # ── Profiler ──────────────────────────────────────────────────────────
        print(
            f"\n{COLOR_CYAN}******** Profiler module (Bazel flags) ********{COLOR_RESET}"
        )
        self._pf("Backend", self.profiler_backend.upper(), W)
        self._pf("Cxx standard", cxx, W)
        common()

    def print_configuration_summary(self) -> None:
        """Print a summary of the resolved build configuration to stdout."""
        print("\n" + "=" * 80)
        print("XSIGMA BAZEL BUILD CONFIGURATION SUMMARY")
        print("=" * 80)

        # Compiler and build tool
        print(f"\n{COLOR_CYAN}Compiler & Build Tool:{COLOR_RESET}")
        print(f"  Platform:          {self.system}")
        print(
            f"  Build Tool:        {self.build_tool.upper() if self.build_tool else 'NINJA (default)'}"
        )
        print(
            f"  Compiler:          {self.compiler.upper() if self.compiler else 'CLANG (default)'}"
        )
        if self.visual_studio_version:
            print(f"  Visual Studio:     {self.visual_studio_version.upper()}")

        # Build type
        print(f"\n{COLOR_CYAN}Build Configuration:{COLOR_RESET}")
        print(f"  Build Type:        {self.build_type.upper()}")

        # C++ Standard
        if self.cxx_standard:
            print(f"  C++ Standard:      {self.cxx_standard.upper()}")
        else:
            print("  C++ Standard:      C++20 (default)")

        # Vectorization
        if self.vectorization:
            print(f"  Vectorization:     {self.vectorization.upper()}")
        else:
            print("  Vectorization:     None")

        if self.library_project:
            print(f"  Library scope:     {_bazel_project_pattern(self.library_project)}")

        # Feature flags — computed from the same state as per-module summaries
        mimalloc_on = True  # Bazel default ON (see .bazelrc memory_enable_mimalloc)
        gtest_on = (
            not self.disable_gtest
        )  # ON by default (mirrors CMake option(... ON))

        print(f"\n{COLOR_CYAN}Feature Flags:{COLOR_RESET}")
        flags: list[tuple[str, bool | str]] = [
            ("MEMORY_ENABLE_MIMALLOC", mimalloc_on),
            ("CORE_HAS_MAGICENUM", True),
            ("PARALLEL/MEMORY_HAS_TBB", "tbb" in self.configs),
            ("PARALLEL_HAS_OPENMP", "openmp" in self.configs),
            ("MEMORY_HAS_CUDA", "cuda" in self.configs),
            ("MEMORY_HAS_HIP", "hip" in self.configs),
            ("LTO_MODE", self.lto_mode),
            ("CORE_HAS_ENZYME", "enzyme" in self.configs),
            ("VECTORIZATION_ENABLE_SLEEF", self.enable_sleef),
            ("XSIGMA_ENABLE_GTEST", gtest_on),
            ("BUILD_SHARED_LIBS", self.shared_libs),
            ("ENABLE_SPELL", self.spell),
            ("ENABLE_CLANGTIDY", self.clangtidy),
            ("ENABLE_FIX", self.fix),
            ("ENABLE_IWYU", self.iwyu),
            ("ENABLE_CPPCHECK", self.cppcheck),
            ("ENABLE_VALGRIND", self.valgrind),
            ("ENABLE_ICECC", self.icecc),
            ("ENABLE_EXAMPLES", self.examples),
        ]
        for flag, state in flags:
            if isinstance(state, str):
                print(f"  {flag:30} {state}")
            else:
                print(f"  {flag:30} {self._on_off(state)}")

        # Logging / Profiler backends
        print(f"\n{COLOR_CYAN}Logging Backend:{COLOR_RESET}")
        print(f"  Backend:           {self.logging_backend.upper()}")
        print(f"\n{COLOR_CYAN}Profiler Backend:{COLOR_RESET}")
        print(f"  Backend:           {self.profiler_backend.upper()}")

        # Sanitizers
        sanitizers = [c for c in self.configs if c in ["asan", "tsan", "ubsan", "msan"]]
        print(f"\n{COLOR_CYAN}Sanitizers:{COLOR_RESET}")
        if sanitizers:
            for san in sanitizers:
                print(f"  {san.upper():30} {self._on_off(True)}")
        else:
            print(f"  {'None':30} {self._on_off(False)}")

        # Bazel command preview
        if self.run_build or self.run_tests or self.run_coverage:
            action = (
                "test"
                if self.run_tests
                else ("coverage" if self.run_coverage else "build")
            )
            cmd = self.build_bazel_command(action)
            print(f"\n{COLOR_CYAN}Bazel Command:{COLOR_RESET}")
            print(f"  {' '.join(cmd)}")

        print("\n" + "=" * 80 + "\n")

    def config(self) -> None:
        """Handle config action (summary already printed by execute())."""

    def clean(self) -> None:
        """Clean Bazel build artifacts."""
        if not self.run_clean:
            return

        print_status("Cleaning Bazel build artifacts...", "INFO")

        try:
            start_time = time.time()
            subprocess.run(
                bazel_prefix() + ["clean", "--expunge"],
                check=True,
                timeout=300,  # 5 minute timeout for clean operation
            )
            elapsed = time.time() - start_time
            self.timing_data["clean"] = elapsed
            print_status(f"Clean completed successfully ({elapsed:.2f}s)", "SUCCESS")
        except subprocess.CalledProcessError as e:
            print_status(f"Clean failed with exit code {e.returncode}", "ERROR")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print_status("Clean operation timed out (exceeded 5 minutes)", "ERROR")
            sys.exit(1)

    def build(self) -> None:
        """Execute Bazel build."""
        if not self.run_build:
            return

        print_status("Starting Bazel build...", "INFO")
        self._shutdown_bazel_for_batch()
        cmd = self.build_bazel_command("build")

        print_status(f"Running: {' '.join(cmd)}", "INFO")

        try:
            start_time = time.time()
            subprocess.run(cmd, check=True, timeout=self.subprocess_timeout)
            elapsed = time.time() - start_time
            self.timing_data["build"] = elapsed
            print_status(f"Build completed successfully ({elapsed:.2f}s)", "SUCCESS")
            if elapsed > self.slow_phase_warn_seconds:
                print_status(
                    f"Build took longer than {self.slow_phase_warn_seconds:.0f}s — check cold cache, "
                    "machine load, or run a narrower target (e.g. //Library/Core:core_lib).",
                    "WARNING",
                )
        except subprocess.CalledProcessError as e:
            print_status(f"Build failed with exit code {e.returncode}", "ERROR")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print_status(
                f"Build timed out (exceeded {self.subprocess_timeout}s)", "ERROR"
            )
            sys.exit(1)

    def test(self) -> None:
        """Execute Bazel tests."""
        if not self.run_tests:
            return

        skip_reason = runtime_test_skip_reason(self.cpu_backend)
        if skip_reason:
            print_status(skip_reason, "WARNING")
            return

        print_status("Running Bazel tests...", "INFO")
        self._shutdown_bazel_for_batch()
        cmd = self.build_bazel_command("test")

        # Add test output flags (vv = full log for failures)
        if self.verbose_tests:
            cmd.append("--test_output=all")
            cmd.append("--verbose_failures")
        else:
            cmd.append("--test_output=errors")

        print_status(f"Running: {' '.join(cmd)}", "INFO")

        try:
            start_time = time.time()
            result = subprocess.run(cmd, check=False, timeout=self.subprocess_timeout)
            elapsed = time.time() - start_time
            self.timing_data["test"] = elapsed

            if result.returncode == 0:
                print_status(
                    f"Tests completed successfully ({elapsed:.2f}s)", "SUCCESS"
                )
                if elapsed > self.slow_phase_warn_seconds:
                    print_status(
                        f"Tests took longer than {self.slow_phase_warn_seconds:.0f}s — "
                        "narrow targets or check for hangs.",
                        "WARNING",
                    )
            elif result.returncode == 4:
                # No test targets found - this is not an error
                print_status(f"No test targets found ({elapsed:.2f}s)", "WARNING")
            else:
                print_status(
                    f"Tests failed with exit code {result.returncode}", "ERROR"
                )
                sys.exit(1)
        except subprocess.TimeoutExpired:
            print_status(
                f"Tests timed out (exceeded {self.subprocess_timeout}s)", "ERROR"
            )
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print_status(f"Tests failed with exit code {e.returncode}", "ERROR")
            sys.exit(1)

    def coverage(self) -> None:
        """Execute Bazel coverage."""
        if not self.run_coverage:
            return

        skip_reason = runtime_test_skip_reason(self.cpu_backend)
        if skip_reason:
            print_status(skip_reason, "WARNING")
            return

        print_status("Running Bazel coverage...", "INFO")
        self._shutdown_bazel_for_batch()
        cmd = self.build_bazel_command("coverage")

        if self.verbose_tests:
            cmd.append("--test_output=all")
            cmd.append("--verbose_failures")
        else:
            cmd.append("--test_output=errors")

        print_status(f"Running: {' '.join(cmd)}", "INFO")

        try:
            start_time = time.time()
            result = subprocess.run(cmd, check=False, timeout=self.subprocess_timeout)
            elapsed = time.time() - start_time
            self.timing_data["coverage"] = elapsed

            if result.returncode == 0:
                print_status(
                    f"Coverage completed successfully ({elapsed:.2f}s)", "SUCCESS"
                )
                dat_path = self._build_llvm_coverage_report(start_time)
                if dat_path is None:
                    dat_path = self._resolve_coverage_dat_path()
                print_status(f"Coverage report (LCOV): {dat_path}", "INFO")
                self._generate_coverage_html(dat_path)
            elif result.returncode == 4:
                print_status(f"No coverage targets found ({elapsed:.2f}s)", "WARNING")
            else:
                print_status(
                    f"Coverage failed with exit code {result.returncode}", "ERROR"
                )
                sys.exit(1)
        except subprocess.TimeoutExpired:
            print_status(
                f"Coverage timed out (exceeded {self.subprocess_timeout}s)", "ERROR"
            )
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print_status(f"Coverage failed with exit code {e.returncode}", "ERROR")
            sys.exit(1)

    def _bazel_info(self, key: str, fallback: str) -> str:
        """Resolve a `bazel info <key>` value (absolute path, cwd-independent).

        setup_bazel.py is normally invoked from Scripts/, not the workspace root, so a
        cwd-relative guess (e.g. "bazel-out/...") can silently miss the real path.
        """
        try:
            result = subprocess.run(
                bazel_prefix() + ["info", key],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.stdout.strip()
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            return fallback

    def _resolve_coverage_dat_path(self) -> str:
        """Resolve the absolute path to Bazel's own combined LCOV coverage report.

        This is Bazel's own report (see the known-empty-DA-records issue in
        Docs/BAZEL_USER_GUIDE.md's Coverage section) -- prefer
        _build_llvm_coverage_report()'s output when available.
        """
        output_path = self._bazel_info("output_path", "bazel-out")
        return os.path.join(output_path, "_coverage", "_coverage_report.dat")

    def _find_recent_profraw_files(self, since: float) -> list[str]:
        """Find .profraw files the just-run coverage tests produced.

        `bazel coverage` genuinely runs the instrumented tests and writes real .profraw
        profile data (confirmed non-empty, with real per-function counters) -- it's only
        Bazel's own downstream report merging that's broken (see
        _build_llvm_coverage_report). The raw files land under the output base's sandbox
        stash, e.g. <output_base>/sandbox/sandbox_stash/TestRunner/<n>/.../_coverage/
        <target-path>/test/*.profraw, which Bazel keeps around (for sandbox reuse) rather
        than deleting immediately after the action completes -- reliable enough to harvest
        right after this same coverage run, filtered by mtime to exclude stale leftovers
        from earlier runs reusing the same stash slots.
        """
        output_base = self._bazel_info("output_base", "")
        if not output_base:
            return []

        stash_root = os.path.join(output_base, "sandbox", "sandbox_stash", "TestRunner")
        if not os.path.isdir(stash_root):
            return []

        profraw_files = []
        for root, _dirs, files in os.walk(stash_root):
            if "_coverage" not in root:
                continue
            for name in files:
                if not name.endswith(".profraw"):
                    continue
                path = os.path.join(root, name)
                try:
                    if os.path.getmtime(path) >= since:
                        profraw_files.append(path)
                except OSError:
                    continue
        return profraw_files

    def _find_coverage_test_binaries(self) -> list[str]:
        """Resolve bazel-bin paths for every cc_test target covered by this run."""
        targets_expr = " + ".join(self.targets)
        try:
            query_result = subprocess.run(
                bazel_prefix()
                + [
                    "query",
                    f"kind(cc_test, {targets_expr})",
                    "--output=label",
                    # `query` doesn't inherit .bazelrc's "build --enable_workspace" the
                    # way build/test/coverage do. This repo has one WORKSPACE-registered
                    # repository rule (parallel_openmp, via openmp_configure() in
                    # WORKSPACE.bazel) -- loading //Library/Parallel/... without this flag
                    # fails with "unknown repo 'parallel_openmp'", which a full-tree
                    # query would also hit.
                    "--enable_workspace",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            return []

        bazel_bin = self._bazel_info("bazel-bin", "")
        if not bazel_bin:
            return []

        binaries = []
        for label in query_result.stdout.splitlines():
            label = label.strip()
            if not label.startswith("//"):
                continue
            pkg, _, name = label[2:].partition(":")
            binaries.append(os.path.join(bazel_bin, pkg, name))
        return binaries

    def _build_llvm_coverage_report(self, since: float) -> Optional[str]:
        """Build a real LCOV trace directly via llvm-profdata/llvm-cov (Clang only).

        Bazel's own C++ coverage report merging is broken: its bundled
        collect_cc_coverage.sh never populates the runtime_objects_list.txt manifest
        entry that `llvm-cov export -object <binary>` needs, so its combined report
        always has zero DA: (line-hit) records despite real .profraw data existing --
        this is an acknowledged upstream limitation (that script's own header comment:
        "Bazel C++ code coverage collection support is poor and limited... tracking
        issue #1118"), not something fixable via Bazel flags. Drive the same
        llvm-profdata merge + llvm-cov export pipeline manually instead, using the
        .profraw files bazel coverage already wrote and the compiled test binaries --
        verified to produce real per-line coverage data.

        Clang-only, mirroring setup.py's CMake coverage dispatch (Clang ->
        llvm-profdata/llvm-cov, GCC -> gcov/lcov, MSVC -> OpenCppCoverage; see
        Docs/BAZEL_USER_GUIDE.md's Coverage Tools by Compiler table). Bazel's own
        "gcc" compiler identity isn't wired up to a real GNU GCC on this repo's
        supported platforms the way CMake's is (and hits an unrelated, pre-existing
        ThirdParty/cpuinfo incompatibility when forced), and MSVC-via-Bazel isn't
        set up here at all -- so unlike CMake, only the Clang path is implemented
        for Bazel coverage right now.
        """
        if self.compiler != "clang":
            print_status(
                f"Bazel coverage HTML generation is only implemented for Clang "
                f"(compiler is '{self.compiler}'); falling back to Bazel's own "
                "(known-empty) report. See Docs/BAZEL_USER_GUIDE.md's Coverage "
                "section.",
                "WARNING",
            )
            return None

        profraw_files = self._find_recent_profraw_files(since)
        if not profraw_files:
            print_status(
                "No .profraw files found from this coverage run; "
                "falling back to Bazel's own (known-empty) report",
                "WARNING",
            )
            return None

        binaries = [b for b in self._find_coverage_test_binaries() if os.path.isfile(b)]
        if not binaries:
            print_status(
                "Could not resolve test binaries for llvm-cov -object; "
                "falling back to Bazel's own (known-empty) report",
                "WARNING",
            )
            return None

        llvm_profdata = shutil.which("llvm-profdata")
        llvm_cov = shutil.which("llvm-cov")
        if not llvm_profdata or not llvm_cov:
            print_status(
                "llvm-profdata/llvm-cov not found on PATH; "
                "falling back to Bazel's own (known-empty) report",
                "WARNING",
            )
            return None

        output_path = self._bazel_info("output_path", "bazel-out")
        coverage_dir = os.path.join(output_path, "_coverage")
        os.makedirs(coverage_dir, exist_ok=True)
        merged_profdata = os.path.join(coverage_dir, "_merged.profdata")
        dat_path = os.path.join(coverage_dir, "_llvm_coverage_report.dat")

        try:
            merge_result = subprocess.run(
                [llvm_profdata, "merge", "-o", merged_profdata, *profraw_files],
                capture_output=True,
                text=True,
                timeout=self.subprocess_timeout,
            )
            if merge_result.returncode != 0:
                print_status(
                    f"llvm-profdata merge failed: {merge_result.stderr.strip()}",
                    "WARNING",
                )
                return None

            export_cmd = [
                llvm_cov,
                "export",
                "-instr-profile",
                merged_profdata,
                "-format=lcov",
                # /external/ is Bazel's staging path for non-vendored deps (googletest,
                # abseil, ...) -- exclude those the same way /ThirdParty/ (our vendored
                # submodules) is excluded, so the report only covers our own code.
                "-ignore-filename-regex=(/external/|/ThirdParty/|^/opt/|^/usr/|^/Applications/)",
            ]
            for binary in binaries:
                export_cmd += ["-object", binary]
            export_result = subprocess.run(
                export_cmd,
                capture_output=True,
                text=True,
                timeout=self.subprocess_timeout,
            )
            if export_result.returncode != 0:
                print_status(
                    f"llvm-cov export failed: {export_result.stderr.strip()}",
                    "WARNING",
                )
                return None

            # llvm-cov reports source paths as seen at compile time, i.e. under the
            # per-action sandbox (.../execroot/_main/<workspace-relative-path>) --
            # that directory is transient and typically gone by the time genhtml
            # reads it back. Rewrite to the real, persistent repo path so genhtml can
            # actually find and annotate the source.
            workspace_root = self._bazel_info("workspace", "")
            lcov_text = export_result.stdout
            if workspace_root:
                lcov_text = re.sub(
                    r"^SF:.*?/execroot/_main/",
                    f"SF:{workspace_root}/",
                    lcov_text,
                    flags=re.MULTILINE,
                )
            with open(dat_path, "w", encoding="utf-8") as f:
                f.write(lcov_text)
        except OSError as e:
            print_status(f"Failed to build coverage report: {e}", "WARNING")
            return None

        return dat_path

    def _generate_coverage_html(self, dat_path: str) -> None:
        """Convert the Bazel LCOV coverage report into an HTML report via genhtml."""
        if not os.path.isfile(dat_path):
            print_status(
                f"Coverage LCOV file not found at {dat_path}; skipping HTML report",
                "WARNING",
            )
            return

        genhtml = shutil.which("genhtml")
        if genhtml is None:
            print_status(
                "genhtml not found on PATH; skipping HTML report "
                "(install lcov to enable it, e.g. 'brew install lcov' or "
                "'apt install lcov')",
                "WARNING",
            )
            return

        html_dir = os.path.join(os.path.dirname(dat_path), "html")
        cmd = [
            genhtml,
            dat_path,
            "--output-directory",
            html_dir,
            # llvm-cov's LCOV export and genhtml's newer strict consistency checker
            # (added in lcov 2.x) don't always agree on function-vs-line hit counts
            # for lambdas/closures (e.g. inside googletest internals) -- a known
            # translation quirk between the two tools, not actual data corruption.
            "--ignore-errors",
            "inconsistent,corrupt,unsupported",
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                timeout=self.subprocess_timeout,
                capture_output=True,
                text=True,
            )
            index_html = os.path.abspath(os.path.join(html_dir, "index.html"))
            print_status(f"Coverage HTML report: {index_html}", "SUCCESS")
        except subprocess.CalledProcessError as e:
            print_status(
                f"Failed to generate HTML coverage report: {(e.stderr or '').strip()[-500:]}",
                "WARNING",
            )
        except subprocess.TimeoutExpired as e:
            print_status(f"Failed to generate HTML coverage report: {e}", "WARNING")

    def print_timing_summary(self) -> None:
        """Print timing summary for build phases."""
        if not self.timing_data:
            return

        print("\n" + "=" * 80)
        print("BUILD TIMING SUMMARY")
        print("=" * 80)

        total_time = sum(self.timing_data.values())

        for phase, elapsed in self.timing_data.items():
            percentage = (elapsed / total_time * 100) if total_time > 0 else 0
            print(f"  {phase.capitalize():20} {elapsed:8.2f}s ({percentage:5.1f}%)")

        print(f"  {'-' * 40}")
        print(f"  {'Total':20} {total_time:8.2f}s (100.0%)")
        print("=" * 80 + "\n")

    def execute(self) -> None:
        """Execute the build pipeline."""
        self.print_module_summaries()
        self.print_configuration_summary()
        self.config()
        # config token implies a clean slate — force expunge before any build/test.
        if self.run_config and (self.run_build or self.run_tests or self.run_coverage):
            print_status(
                "Config requested: forcing clean build (bazel clean --expunge).", "INFO"
            )
            self.run_clean = True
        self.clean()
        if self.run_build or self.run_tests or self.run_coverage:
            self._kill_stale_bazel_processes()
        # `bazel coverage` requires instrumented compilation (different compiler flags than a
        # plain build/test), so it can never reuse the action cache from a preceding `bazel
        # build`/`bazel test` run -- those would just be a second, wasted full build under
        # different flags, and `bazel coverage` already builds everything and runs all tests
        # itself (instrumented) as part of computing coverage. Skip the redundant steps rather
        # than pay for three separate Bazel invocations when coverage is requested.
        if self.run_coverage:
            if self.run_build or self.run_tests:
                print_status(
                    "Coverage requested: skipping separate build/test steps (bazel coverage "
                    "builds and tests everything itself, under different instrumented flags "
                    "that wouldn't reuse a plain build's cache anyway).",
                    "INFO",
                )
            self.coverage()
        else:
            self.build()
            self.test()
        self.print_timing_summary()


def parse_args(args: list[str]) -> list[str]:
    """Parse argv like Scripts/setup.py: long flags, dotted shortcuts, compiler paths.

    Supports the same long-option spellings as setup.py where applicable:
      --sanitizer.address, --logging.LOGURU, --profiler.kineto, --parallel.tbb
    """
    processed: list[str] = []

    for arg in args:
        if arg.startswith("--project."):
            proj = arg.split(".", 1)[1].lower()
            if proj not in _BAZEL_LIBRARY_PROJECTS:
                print_status(
                    f"Invalid --project value '{proj}'. Valid: {', '.join(_BAZEL_LIBRARY_PROJECTS)}",
                    "ERROR",
                )
                sys.exit(1)
            processed.append(f"project.{proj}")
            print_status(
                f"Library scope: {_bazel_project_pattern(proj)}",
                "INFO",
            )
            continue

        if arg.startswith("--lto."):
            _lto_mode = arg.split(".", 1)[1].lower()
            _valid = ("off", "thin", "full", "ipo", "auto")
            if _lto_mode in _valid:
                processed.append(f"lto.{_lto_mode}")
                print_status(f"LTO mode set to {_lto_mode}", "INFO")
            else:
                print_status(
                    f"Invalid LTO mode '{_lto_mode}'. Valid options: {', '.join(_valid)}",
                    "ERROR",
                )
                sys.exit(1)
            continue

        if arg.startswith("--sanitizer."):
            st = arg.split(".", 1)[1].lower()
            if st in _CMAKE_SAN_TO_BAZEL:
                processed.append(_CMAKE_SAN_TO_BAZEL[st])
            else:
                print_status(
                    f"Invalid sanitizer type: {st}. Valid: {', '.join(_CMAKE_SAN_TO_BAZEL)}",
                    "ERROR",
                )
                sys.exit(1)
            continue

        if arg.startswith("--logging="):
            bt = arg.split("=", 1)[1].lower()
            if bt in ("native", "loguru", "glog", "spdlog"):
                processed.append(f"logging_{bt}")
                print_status(f"Logging backend set to {bt.upper()}", "INFO")
            else:
                print_status(
                    f"Invalid logging backend: {bt}. Valid: native, loguru, glog, spdlog",
                    "ERROR",
                )
                sys.exit(1)
            continue

        if arg.startswith("--logging."):
            bt = arg.split(".", 1)[1].lower()
            if bt in ("native", "loguru", "glog", "spdlog"):
                processed.append(f"logging_{bt}")
                print_status(f"Logging backend set to {bt.upper()}", "INFO")
            else:
                print_status(
                    f"Invalid logging backend: {bt}. Valid: native, loguru, glog, spdlog",
                    "ERROR",
                )
                sys.exit(1)
            continue

        if arg.startswith("--profiler."):
            bt = arg.split(".", 1)[1].lower()
            prof_map = {"kineto": "kineto", "itt": "itt", "native": "native"}
            if bt in prof_map:
                processed.append(f"profiler_{bt}")
                print_status(f"Profiler backend set to {prof_map[bt]}", "INFO")
            else:
                print_status(
                    f"Invalid profiler backend: {bt}. Valid: {', '.join(prof_map)}",
                    "ERROR",
                )
                sys.exit(1)
            continue

        if arg.startswith("--parallel."):
            bt = arg.split(".", 1)[1].lower()
            if bt in ("std", "openmp", "tbb"):
                processed.append(f"parallel.{bt}")
                print_status(f"SMP backend set to {bt}", "INFO")
            else:
                print_status(
                    f"Invalid SMP backend: {bt}. Valid: std, openmp, tbb",
                    "ERROR",
                )
                sys.exit(1)
            continue

        if arg.startswith(("--cpu_backend.", "--cpu-backend.")):
            bt = arg.split(".", 1)[1].lower()
            if bt in ("no", "sse", "avx", "avx2", "avx512", "neon", "sve"):
                processed.append(f"cpu_backend.{bt}")
            else:
                print_status(
                    f"Invalid CPU backend: {bt}. Valid options: no, sse, avx, avx2, avx512, neon, sve",
                    "ERROR",
                )
                sys.exit(1)
            continue

        if arg.startswith(("--gpu_backend.", "--gpu-backend.")):
            bt = arg.split(".", 1)[1].lower()
            if bt in ("none", "cuda", "hip", "metal"):
                processed.append(f"gpu_backend.{bt}")
            else:
                print_status(
                    f"Invalid GPU backend: {bt}. Valid options: none, cuda, hip, metal",
                    "ERROR",
                )
                sys.exit(1)
            continue

        # Compiler path: pass through verbatim (matches setup.py)
        if re.search(r"[/\\]", arg) and re.search(
            r"[Cc]lang|[Gg][Cc][Cc]|[Gg]\+\+", arg
        ):
            processed.append(arg)
            continue

        # Dot-separated convenience tokens: config.build.parallel.openmp
        if "." in arg and not arg.startswith("--"):
            parts = arg.split(".")
            processed.extend(_merge_dotted_segments(parts))
            continue

        processed.append(arg.lower())

    return processed


def print_help() -> None:
    """Print usage examples and the full list of supported dotted tokens."""
    print_status("XSigma Bazel Build Configuration Helper", "INFO")
    print("\n" + "=" * 80)
    print("BAZEL BUILD SYSTEM")
    print("=" * 80)
    print("\nUsage examples:")
    print("  1. Show configuration (no build):")
    print("     python setup_bazel.py config.release")
    print("  2. Default debug build (Ninja + Clang):")
    print("     python setup_bazel.py build.test")
    print("  3. Release build with AVX2:")
    print("     python setup_bazel.py build.test.release.avx2")
    print("  4. Release build with C++20:")
    print("     python setup_bazel.py config.build.release.test.cxx20")
    print("  5. Release build with optimizations:")
    print("     python setup_bazel.py build.test.release.lto.avx2")
    print("  6. Build with optional features:")
    print("     python setup_bazel.py build.release.avx2.mimalloc.magic_enum")
    print("  7. Run tests only:")
    print("     python setup_bazel.py test")
    print("  8. Clean build:")
    print("     python setup_bazel.py clean.build.test.release")
    print("  9. Build with Visual Studio 2026 (Windows only):")
    print("     python setup_bazel.py build.test.release.vs26")
    print("  10. Build with Xcode (macOS only):")
    print("      python setup_bazel.py build.test.release.xcode")
    print("\nBuild types:")
    print("  debug         - Debug build (default)")
    print("  release       - Release build with optimizations")
    print("  relwithdebinfo- Release with debug info")
    print("\nCompiler & Build Tool (Default: Ninja + Clang on all platforms):")
    print("  ninja         - Ninja build system (default)")
    print("  xcode         - Xcode generator (macOS only)")
    print("  vs17          - Visual Studio 2017 (Windows only)")
    print("  vs19          - Visual Studio 2019 (Windows only)")
    print("  vs22          - Visual Studio 2022 (Windows only)")
    print("  vs26          - Visual Studio 2026 (Windows only)")
    print("  clang         - Clang compiler (default)")
    print("  gcc           - GCC compiler")
    print("\nC++ Standard:")
    print("  cxx17         - C++17")
    print("  cxx20         - C++20 (default)")
    print("  cxx23         - C++23")
    print("\nVectorization options:")
    print("  sse           - SSE vectorization")
    print("  avx           - AVX vectorization")
    print("  avx2          - AVX2 vectorization (recommended)")
    print("  avx512        - AVX512 vectorization")
    print("  neon          - AArch64 NEON (128-bit SIMD)")
    print("  sve           - AArch64 SVE fixed 128-bit (-msve-vector-bits=128)")
    print(
        "  sleef         - SLEEF SIMD math for NEON/SVE (maps to --config=sleef in .bazelrc)"
    )
    print("\nOptional features:")
    print("  lto           - Link-time optimization (auto mode; maps to --config=lto)")
    print("  --lto.thin    - ThinLTO (Clang; Bazel maps to --config=lto)")
    print("  --lto.full    - Full/monolithic LTO (Bazel maps to --config=lto)")
    print("  --lto.ipo     - CMake-managed IPO (Bazel maps to --config=lto)")
    print("  --lto.auto    - Auto-select mode (same as bare 'lto')")
    print("  --lto.off     - Explicitly disable LTO")
    print("  mimalloc      - Microsoft mimalloc allocator")
    print("  magic_enum    - Magic enum library")
    print("  tbb           - Intel TBB")
    print("  openmp        - OpenMP support")
    print("  enzyme        - Enzyme AD defines (see .bazelrc build:enzyme)")
    print("  numa          - NUMA (build:numa)")
    print("  memkind       - memkind (build:memkind)")
    print("  benchmark     - Google Benchmark (default ON; token optional)")
    print(
        "  gtest         - Disables GTest defines (CMake inverse; default is ON in both systems)"
    )
    print("  static        - Shared libraries (CMake: BUILD_SHARED_LIBS=ON)")
    print("  parallel.std | parallel.openmp | parallel.tbb  — exclusive SMP backend")
    print(
        "  project.NAME | --project.NAME  — only //Library/<Name>/... (logging, memory, …)"
    )
    print("  --parallel.* / --logging.* / --profiler.*  — same long flags as setup.py")
    print("  vv            - Verbose Bazel test output (--test_output=all)")
    print(
        "  batch         - Pass --batch to Bazel; script runs `bazel shutdown` first to avoid"
    )
    print(
        "                  startup-option warnings (or run: bazel shutdown; bazel --batch ...)"
    )
    print(
        "  spell         - (CMake only) Spell-check — ignored in Bazel, warning emitted"
    )
    print(
        "  clangtidy     - (CMake only) Clang-tidy — ignored in Bazel, warning emitted"
    )
    print("\nLogging backends:")
    print("  glog          - Google glog")
    print("  loguru        - Loguru logging")
    print("  native        - Native logging")
    print("  spdlog        - spdlog (header-only, external fmt)")
    print(
        "\nSanitizers (Bazel --config; CMake names accepted via dotted args or --sanitizer.*):"
    )
    print("  asan          - AddressSanitizer (CMake: address)")
    print("  tsan          - ThreadSanitizer (CMake: thread)")
    print("  ubsan         - UndefinedBehaviorSanitizer (CMake: undefined)")
    print("  msan          - MemorySanitizer (CMake: memory)")
    print("  lsan          - LeakSanitizer (CMake: leak)")
    print(
        "  --sanitizer.address | .undefined | .thread | .memory | .leak  (same as setup.py)"
    )
    print("\nActions:")
    print("  config        - Show configuration summary (no build)")
    print("  build         - Build the project")
    print("  test          - Run tests")
    print("  coverage      - Run tests with coverage instrumentation (lcov report)")
    print("  clean         - Clean build artifacts")
    print("\nDefault Behavior:")
    print("  If no compiler or build tool is specified, defaults to Ninja + Clang")
    print("  on all platforms (Windows, macOS, Linux).")
    print("\nEquivalent to CMake setup.py:")
    print("  CMake:  python setup.py config.build.test.ninja.clang.release")
    print("  Bazel:  python setup_bazel.py config.build.test.release")
    print()


def main() -> None:
    """Main entry point."""
    if len(sys.argv) == 2 and sys.argv[1] == "--help":
        print_help()
        return

    # Check if Bazel is installed
    """if not check_bazel_installed():
        print_status("Bazel or Bazelisk is not installed!", "ERROR")
        print_status("Install Bazelisk:", "INFO")
        print_status("  macOS:  brew install bazelisk", "INFO")
        print_status("  Linux:  npm install -g @bazel/bazelisk", "INFO")
        print_status("  Or download from: https://github.com/bazelbuild/bazelisk/releases", "INFO")
        sys.exit(1)"""

    if len(sys.argv) < 2:
        print_status(
            "No build configuration specified. Use --help for usage information.",
            "ERROR",
        )
        sys.exit(1)

    try:
        # Parse arguments
        arg_list = parse_args(sys.argv[1:])

        print_status(f"Starting Bazel build for {platform.system()}", "INFO")

        # Create configuration
        config = BazelConfiguration(arg_list)

        # If no actions specified, default to build
        if not (
            config.run_build
            or config.run_tests
            or config.run_clean
            or config.run_config
            or config.run_coverage
        ):
            config.run_build = True

        # Execute build pipeline
        config.execute()

        print_status("Build process completed successfully!", "SUCCESS")

    except KeyboardInterrupt:
        print_status("\nBuild process interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        print_status(f"An unexpected error occurred: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
