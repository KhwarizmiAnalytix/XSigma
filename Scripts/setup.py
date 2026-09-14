import glob
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


try:
    import colorama
    from colorama import Fore, Style

    colorama.init()
except ImportError:  # Windows CLI smoke and some CI jobs skip pip install

    class Fore:  # pylint: disable=too-few-public-methods
        CYAN = GREEN = YELLOW = RED = WHITE = ""

    class Style:  # pylint: disable=too-few-public-methods
        RESET_ALL = ""


# Import helper modules
from helpers import (
    build as build_helper,
    config as config_helper,
    cppcheck as cppcheck_helper,
    test as test_helper,
)
from helpers.cpu_isa import runtime_test_skip_reason


DEBUG_FLAG = False


class ErrorLogger:
    """Centralized error logging system for comprehensive error tracking."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = (
            self.log_dir
            / f"xsigma_build_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        self.errors = []

    def log_error(
        self,
        command: str,
        error_output: str,
        context: str = "",
        suggestions: Optional[list[str]] = None,
    ):
        """Log a comprehensive error with context and suggestions."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        error_entry = {
            "timestamp": timestamp,
            "command": command,
            "error_output": error_output,
            "context": context,
            "suggestions": suggestions or [],
        }

        self.errors.append(error_entry)

        # Write to log file immediately
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"ERROR LOG ENTRY - {timestamp}\n")
            f.write(f"{'=' * 80}\n")
            f.write(f"Context: {context}\n")
            f.write(f"Command: {command}\n")
            f.write(f"Error Output:\n{error_output}\n")
            if suggestions:
                f.write("Troubleshooting Suggestions:\n")
                for i, suggestion in enumerate(suggestions, 1):
                    f.write(f"  {i}. {suggestion}\n")
            f.write(f"{'=' * 80}\n\n")

    def get_log_file_path(self) -> str:
        """Get the path to the current log file."""
        return str(self.log_file)

    def has_errors(self) -> bool:
        """Check if any errors have been logged."""
        return len(self.errors) > 0


class BuildDirectoryDetector:
    """Utility to detect build directories dynamically, independent of naming conventions."""

    @staticmethod
    def find_build_directories(source_path: str) -> list[Path]:
        """Find all potential build directories in the project root."""
        source_root = Path(source_path)
        build_dirs = set()  # Use set to avoid duplicates

        # Common build directory patterns
        patterns = [
            "build*",
            "*build*",
        ]

        for pattern in patterns:
            matches = list(source_root.glob(pattern))
            for match in matches:
                if match.is_dir() and BuildDirectoryDetector._is_build_directory(match):
                    build_dirs.add(match)

        # Convert back to list and sort by modification time (most recent first)
        build_dirs_list = list(build_dirs)
        build_dirs_list.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return build_dirs_list

    @staticmethod
    def _is_build_directory(path: Path) -> bool:
        """Check if a directory looks like a CMake build directory."""
        # Look for CMake artifacts
        cmake_indicators = [
            "CMakeCache.txt",
            "cmake_install.cmake",
            "CMakeFiles",
            "Makefile",
            "build.ninja",
        ]

        return any((path / indicator).exists() for indicator in cmake_indicators)

    @staticmethod
    def find_best_build_directory(
        source_path: str, preferred_name: Optional[str] = None
    ) -> Optional[Path]:
        """Find the best build directory, optionally preferring a specific name."""
        build_dirs = BuildDirectoryDetector.find_build_directories(source_path)

        if not build_dirs:
            return None

        # If a preferred name is specified, look for it first
        if preferred_name:
            for build_dir in build_dirs:
                if preferred_name in build_dir.name:
                    return build_dir

        # Return the most recently modified build directory
        return build_dirs[0]


class SummaryReporter:
    """Generate and display summary reports for various analysis tools."""

    def __init__(self):
        self.reports = {}

    def add_cppcheck_report(self, log_file: str, exit_code: int):
        """Add cppcheck analysis results to the summary."""
        if not os.path.exists(log_file):
            self.reports["cppcheck"] = {
                "status": "not_run",
                "message": "Cppcheck was not executed",
            }
            return

        try:
            with open(log_file, encoding="utf-8") as f:
                content = f.read()

            # Count issues by severity
            issues = {
                "error": len(re.findall(r",error,", content)),
                "warning": len(re.findall(r",warning,", content)),
                "style": len(re.findall(r",style,", content)),
                "performance": len(re.findall(r",performance,", content)),
                "portability": len(re.findall(r",portability,", content)),
                "information": len(re.findall(r",information,", content)),
            }

            total_issues = sum(issues.values())

            self.reports["cppcheck"] = {
                "status": "completed",
                "exit_code": exit_code,
                "total_issues": total_issues,
                "issues_by_type": issues,
                "log_file": log_file,
            }
        except Exception as e:
            self.reports["cppcheck"] = {
                "status": "error",
                "message": f"Failed to parse cppcheck results: {e}",
            }

    def add_valgrind_report(self, build_path: str, exit_code: int):
        """Add valgrind analysis results to the summary."""
        valgrind_logs = glob.glob(
            os.path.join(build_path, "Testing", "Temporary", "MemoryChecker.*.log")
        )

        if not valgrind_logs:
            self.reports["valgrind"] = {
                "status": "not_run",
                "message": "Valgrind was not executed or no logs found",
            }
            return

        try:
            memory_leaks = 0
            memory_errors = 0

            for log_file in valgrind_logs:
                with open(log_file, encoding="utf-8") as f:
                    content = f.read()

                # Count memory issues
                leak_matches = re.findall(r"definitely lost: (\d+)", content)
                memory_leaks += sum(
                    int(match) for match in leak_matches if int(match) > 0
                )

                error_matches = re.findall(r"ERROR SUMMARY: (\d+) errors", content)
                memory_errors += sum(
                    int(match) for match in error_matches if int(match) > 0
                )

            self.reports["valgrind"] = {
                "status": "completed",
                "exit_code": exit_code,
                "memory_leaks": memory_leaks,
                "memory_errors": memory_errors,
                "log_files": valgrind_logs,
            }
        except Exception as e:
            self.reports["valgrind"] = {
                "status": "error",
                "message": f"Failed to parse valgrind results: {e}",
            }

    def add_coverage_report(self, build_path: str, exit_code: int):
        """Add coverage analysis results to the summary.

        Parses JSON coverage reports and extracts metrics including line coverage,
        function coverage, and region coverage.
        """
        import json

        # Look for coverage JSON files (primary source)
        coverage_json_paths = [
            os.path.join(build_path, "coverage_report", "coverage_summary.json"),
            os.path.join(build_path, "coverage_report", "coverage.json"),
        ]

        coverage_json = None
        for path in coverage_json_paths:
            if os.path.exists(path):
                coverage_json = path
                break

        if not coverage_json:
            self.reports["coverage"] = {
                "status": "not_run",
                "message": "Coverage report not found",
            }
            return

        try:
            with open(coverage_json, encoding="utf-8") as f:
                coverage_data = json.load(f)

            # Extract metrics from global_metrics (preferred format)
            if "global_metrics" in coverage_data:
                metrics = coverage_data["global_metrics"]
                self.reports["coverage"] = {
                    "status": "completed",
                    "exit_code": exit_code,
                    "total_lines": metrics.get("total_lines", 0),
                    "covered_lines": metrics.get("covered_lines", 0),
                    "line_coverage_percent": metrics.get("line_coverage_percent", 0.0),
                    "total_functions": metrics.get("total_functions", 0),
                    "covered_functions": metrics.get("covered_functions", 0),
                    "function_coverage_percent": metrics.get(
                        "function_coverage_percent", 0.0
                    ),
                    "total_regions": metrics.get("total_regions", 0),
                    "covered_regions": metrics.get("covered_regions", 0),
                    "region_coverage_percent": metrics.get(
                        "region_coverage_percent", 0.0
                    ),
                    "report_file": coverage_json,
                }
            # Extract metrics from summary (alternative format)
            elif "summary" in coverage_data:
                summary = coverage_data["summary"]
                line_cov = summary.get("line_coverage", {})
                func_cov = summary.get("function_coverage", {})

                self.reports["coverage"] = {
                    "status": "completed",
                    "exit_code": exit_code,
                    "total_lines": line_cov.get("total", 0),
                    "covered_lines": line_cov.get("covered", 0),
                    "line_coverage_percent": line_cov.get("percent", 0.0),
                    "total_functions": func_cov.get("total", 0),
                    "covered_functions": func_cov.get("covered", 0),
                    "function_coverage_percent": func_cov.get("percent", 0.0),
                    "total_regions": 0,
                    "covered_regions": 0,
                    "region_coverage_percent": 0.0,
                    "report_file": coverage_json,
                }
            else:
                self.reports["coverage"] = {
                    "status": "error",
                    "message": "Coverage JSON format not recognized",
                }
        except Exception as e:
            self.reports["coverage"] = {
                "status": "error",
                "message": f"Failed to parse coverage results: {e}",
            }

    def display_summary(self):
        """Display a comprehensive summary of all analysis results."""
        if not self.reports:
            return

        print_status("\n" + "=" * 80, "INFO")
        print_status("BUILD AND ANALYSIS SUMMARY REPORT", "INFO")
        print_status("=" * 80, "INFO")

        for tool, report in self.reports.items():
            self._display_tool_summary(tool, report)

        print_status("=" * 80, "INFO")

    def _display_tool_summary(self, tool: str, report: dict):
        """Display summary for a specific tool."""
        tool_name = tool.upper()

        if report["status"] == "not_run":
            print_status(f"{tool_name}: Not executed", "INFO")
            return

        if report["status"] == "error":
            print_status(f"{tool_name}: Error - {report['message']}", "ERROR")
            return

        if tool == "cppcheck":
            total = report["total_issues"]
            if total == 0:
                print_status(f"{tool_name}: ✓ No issues found", "SUCCESS")
            else:
                print_status(f"{tool_name}: Found {total} issues", "WARNING")
                for issue_type, count in report["issues_by_type"].items():
                    if count > 0:
                        print_status(f"  - {issue_type}: {count}", "INFO")
                print_status(f"  Log file: {report['log_file']}", "INFO")

        elif tool == "valgrind":
            leaks = report["memory_leaks"]
            errors = report["memory_errors"]
            if leaks == 0 and errors == 0:
                print_status(f"{tool_name}: ✓ No memory issues found", "SUCCESS")
            else:
                if leaks > 0:
                    print_status(f"{tool_name}: Found {leaks} memory leaks", "ERROR")
                if errors > 0:
                    print_status(f"{tool_name}: Found {errors} memory errors", "ERROR")

        elif tool == "coverage":
            # Display coverage summary in the same format as _display_coverage_summary
            print_status("\n" + "=" * 80, "INFO")
            print_status("CODE COVERAGE SUMMARY", "INFO")
            print_status("=" * 80, "INFO")

            total_lines = report.get("total_lines", 0)
            covered_lines = report.get("covered_lines", 0)
            coverage_percent = report.get("line_coverage_percent", 0.0)

            print_status(f"Total Lines:    {total_lines}", "INFO")
            print_status(f"Covered Lines:  {covered_lines}", "INFO")
            print_status(
                f"Coverage:       {coverage_percent:.2f}%",
                "SUCCESS"
                if coverage_percent >= 95.0
                else "WARNING"
                if coverage_percent >= 80.0
                else "ERROR",
            )

            # Display function coverage if available
            if report.get("total_functions", 0) > 0:
                func_coverage = report.get("function_coverage_percent", 0.0)
                print_status(f"Function Coverage: {func_coverage:.2f}%", "INFO")

            # Display region coverage if available
            if report.get("total_regions", 0) > 0:
                region_coverage = report.get("region_coverage_percent", 0.0)
                print_status(f"Region Coverage:   {region_coverage:.2f}%", "INFO")

            # Display HTML report location if available
            report_file = report.get("report_file", "")
            if report_file:
                # Try to find HTML report in the same directory structure
                report_dir = os.path.dirname(report_file)
                html_report_paths = [
                    os.path.join(report_dir, "html", "index.html"),
                    os.path.join(report_dir, "index.html"),
                ]

                for html_path in html_report_paths:
                    if os.path.exists(html_path):
                        print_status(f"\nHTML Report: {html_path}", "INFO")
                        break

            print_status("=" * 80, "INFO")


def check_dependencies() -> list[str]:
    """Check if required dependencies are installed."""
    missing_deps = []

    try:
        import psutil  # noqa: F401
    except ImportError:
        missing_deps.append("psutil")

    # Check for CMake
    try:
        subprocess.run(["cmake", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing_deps.append("CMake")

    # Check for compiler
    if platform.system() == "Windows":
        try:
            subprocess.run(["clang", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(["cl"], capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing_deps.append("C++ compiler (MSVC or Clang)")
    elif platform.system() == "Darwin":
        # Check for Xcode command line tools
        try:
            subprocess.run(
                ["xcode-select", "--print-path"], capture_output=True, check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_deps.append(
                "Xcode Command Line Tools (run: xcode-select --install)"
            )

        # Check for clang++ (should be available with Xcode tools)
        try:
            subprocess.run(["clang++", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_deps.append("C++ compiler (Clang)")
    else:
        try:
            subprocess.run(["clang++", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(["g++", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing_deps.append("C++ compiler (GCC or Clang)")

    return missing_deps


def check_xcode_availability() -> bool:
    """Check if Xcode is available on macOS."""
    if platform.system() != "Darwin":
        return False

    try:
        # Check if xcodebuild is available
        result = subprocess.run(
            ["xcodebuild", "-version"], capture_output=True, check=True, text=True
        )
        print_status(f"Found Xcode: {result.stdout.strip().split()[1]}", "INFO")
        return True
    except subprocess.CalledProcessError as e:
        stderr_output = (
            e.stderr
            if isinstance(e.stderr, str)
            else e.stderr.decode()
            if e.stderr
            else ""
        )
        if "command line tools instance" in stderr_output:
            print_status(
                "Xcode Command Line Tools found, but full Xcode is required for Xcode generator",
                "WARNING",
            )
            print_status(
                "Install Xcode from the App Store or use 'sudo xcode-select -s /Applications/Xcode.app'",
                "INFO",
            )
        else:
            print_status(f"Xcode check failed: {stderr_output.strip()}", "WARNING")
        return False
    except FileNotFoundError:
        print_status(
            "xcodebuild not found - install Xcode or Xcode Command Line Tools",
            "WARNING",
        )
        return False


def check_xcode_installation() -> bool:
    """Check if Xcode app is installed but not configured."""
    if platform.system() != "Darwin":
        return False

    xcode_path = "/Applications/Xcode.app"
    if os.path.exists(xcode_path):
        print_status(f"Found Xcode at {xcode_path}", "INFO")
        print_status(
            "Try running: sudo xcode-select -s /Applications/Xcode.app/Contents/Developer",
            "INFO",
        )

        # Ask user if they want to configure Xcode automatically
        try:
            response = (
                input("Would you like to configure Xcode automatically? (y/N): ")
                .strip()
                .lower()
            )
            if response in ["y", "yes"]:
                try:
                    subprocess.run(
                        [
                            "sudo",
                            "xcode-select",
                            "-s",
                            "/Applications/Xcode.app/Contents/Developer",
                        ],
                        check=True,
                    )
                    print_status("Xcode configured successfully", "SUCCESS")
                    return True
                except subprocess.CalledProcessError as e:
                    print_status(f"Failed to configure Xcode: {e}", "ERROR")
        except (KeyboardInterrupt, EOFError):
            print_status("\nSkipping Xcode configuration", "INFO")

        return True
    return False


def print_status(message: str, status: str = "INFO", end: str = "\n") -> None:
    """Print a formatted status message."""
    status_colors = {
        "INFO": Fore.BLUE,
        "SUCCESS": Fore.GREEN,
        "ERROR": Fore.RED,
        "WARNING": Fore.YELLOW,
    }
    color = status_colors.get(status, Fore.WHITE)
    print(f"{color}[{status}]{Style.RESET_ALL} {message}", end=end)


def get_logical_processor_count():
    try:
        import psutil

        return psutil.cpu_count(logical=True)
    except ImportError:
        # Fallback methods if psutil is not available
        try:
            # Try using os.cpu_count() (available in Python 3.4+)
            return os.cpu_count()
        except AttributeError:
            # For older Python versions
            import multiprocessing

            return multiprocessing.cpu_count()


def debug_print(message):
    if DEBUG_FLAG:
        print(message)


class XSigmaFlags:
    OFF = "OFF"
    ON = "ON"

    def __init__(self, arg_list):
        self.__initialize_flags()
        if arg_list:
            self.__build_cmake_flag()
            self.__fill_option_flags(arg_list)
            self.__validate_flags()  # New validation step

    def __initialize_flags(self):
        self.__key = [
            # Valid CMake options
            "cpu_backend",
            "gpu_backend",
            "tbb",
            "openmp",
            "mkl",
            "numa",
            "memkind",
            "static",
            "clangtidy",
            "iwyu",
            "sanitizer",
            "sanitizer_enum",
            "valgrind",
            "coverage",
            "benchmark",
            "gtest",
            "test",
            "logging_backend",
            "lto",
            "magic_enum",
            "mimalloc",
            "mimalloc_stats",
            "external",
            "cxxstd",
            "cppcheck",
            "spell",
            "fix",
            "icecc",
            "examples",
            "linker",
            "cache",
            "cache_type",
            "enzyme",
            "parallel_backend",
            "native",
            "sleef",
            "torch",
        ]
        self.__description = [
            # Valid CMake options
            "cpu backend: no, sse, avx, avx2, avx512, neon, or sve",
            "GPU backend: none, hip, cuda, metal",
            "enable Intel TBB (Threading Building Blocks) support",
            "enable OpenMP",
            "enable MKL",
            "enable NUMA node support",
            "enable memkind extended memory support",
            "build shared or static libraries",
            "enable clang-tidy checks",
            "enable include-what-you-use (iwyu) checks",
            "enable sanitizer memory check (Clang only)",
            "sanitizer type: address, undefined, thread, memory, leak",
            "enable valgrind memory check",
            "enable code coverage",
            "enable google benchmark",
            "enable google test",
            "enable testing",
            "logging backend: NATIVE, LOGURU, GLOG, or SPDLOG",
            "LTO mode for all modules: off | thin | full | ipo | auto (bare 'lto' = auto)",
            "enable magic_enum static reflection in Logging",
            "enable Microsoft mimalloc high-performance memory allocator",
            "compile mimalloc statistics (MI_STAT=1); enable via --mimalloc_stats ('_' is a token delimiter in dotted args)",
            "use external copies of third party libraries by default",
            "C++ standard: cxx17, cxx20, cxx23",
            "enable cppcheck static analysis",
            "enable check-only spell checking (does not rewrite sources; skips ThirdParty)",
            "enable clang-tidy fix-errors and fix options",
            "enable Icecream distributed compilation (icecc)",
            "build example programs for all modules",
            "linker selection for all modules: --linker.mold, --linker.lld, --linker.gold, --linker.lld-link",
            "enable per-target compiler cache launchers (default ON; pass flag to disable)",
            "compiler cache backend for all library targets: none, ccache, sccache, or buildcache",
            "enable Enzyme automatic differentiation support",
            "SMP backend: std, openmp, or tbb",
            "Clang/GCC: -march=native for max CPU tuning (binary may not run on older CPUs)",
            "enable SLEEF SIMD math library for NEON/SVE (AArch64; auto-enabled when Accelerate vForce is unavailable)",
            "enable LibTorch (PyTorch C++) comparison tests/benchmarks and the Profiler "
            "heavy-function PyTorch profiler (requires LibTorch in CMAKE_PREFIX_PATH)",
        ]

    def __build_cmake_flag(self):
        debug_print("Build cmake flag")
        self.__name = {
            # Valid CMake options that exist in CMakeLists.txt
            "tbb": "MEMORY_ENABLE_TBB",
            "openmp": "PARALLEL_ENABLE_OPENMP",
            "mkl": "CORE_ENABLE_MKL",
            "numa": "MEMORY_ENABLE_NUMA",
            "memkind": "MEMORY_ENABLE_MEMKIND",
            "cpu_backend": "VECTORIZATION_CPU_BACKEND",
            "packet_size": "VECTORIZATION_PACKET_SIZE",
            "static": "BUILD_SHARED_LIBS",
            "test": "BUILD_TESTING",
            "logging_backend": "LOGGING_BACKEND",
            "magic_enum": "LOGGING_ENABLE_MAGICENUM",
            "mimalloc": "MEMORY_ENABLE_MIMALLOC",
            "mimalloc_stats": "MEMORY_ENABLE_MIMALLOC_STATS",
            "external": "XSIGMA_ENABLE_EXTERNAL",
            "enzyme": "CORE_ENABLE_ENZYME",
            "parallel_backend": "PARALLEL_BACKEND",
            "sleef": "VECTORIZATION_ENABLE_SLEEF",
            "torch": "VECTORIZATION_ENABLE_LIBTORCH",
            # Non-CMake flags (for internal use, not passed to CMake)
            "mkl_threading": "MKL_THREADING",
            "mkl_link": "MKL_LINK",
            # All other flags (clangtidy, iwyu, sanitizer, sanitizer_enum, valgrind,
            # gtest, coverage, benchmark, spell, fix, icecc, examples, lto, cache,
            # cache_type, linker, cppcheck) are fanned out per-module in create_cmake_flags.
        }

    def __fill_option_flags(self, arg_list):
        debug_print("Fill option flags")
        self.__value = {}

        if "all" in arg_list:
            self.__set_all_flags()
        else:
            self.__set_default_flags()
            self.__process_arg_list(arg_list)

    def __set_all_flags(self):
        # Enable most flags for "all" mode, but respect some constraints
        self.__value = dict.fromkeys(self.__key, self.ON)
        self.__value.update(
            {
                "cpu_backend": "avx2",
                "parallel_backend": "std",
                "javasourceversion": 1.8,
                "javatargetversion": 1.8,
                "cxxstd": "cxx20",
                # Keep some flags OFF even in "all" mode for safety/compatibility
                "gpu_backend": "none",  # GPU backend off by default in "all" mode
                "sanitizer": self.OFF,  # Can conflict with other tools
                "valgrind": self.OFF,  # Can conflict with sanitizer
                "coverage": self.OFF,  # Coverage analysis is optional
                "icecc": self.OFF,  # Distributed compilation is site-specific
                "native": self.OFF,  # Portable binaries by default
                "torch": self.OFF,  # LibTorch install is not guaranteed to be present
                "examples": self.ON,
                "linker": "default",  # Keep auto-detect in "all" mode
                "cache": self.ON,
                "cache_type": "ccache",
                "library_project": "",
            }
        )

    def __set_default_flags(self):
        # Initialize all flags to OFF first
        self.__value = dict.fromkeys(self.__key, self.OFF)

        # Set defaults based on CMake option defaults (inverse logic)
        # When CMake default is ON, setup.py default should be ON (no arg = ON)
        # When CMake default is OFF, setup.py default should be OFF (no arg = OFF)
        self.__value.update(
            {
                "cpu_backend": "",  # Special case: string value
                "gpu_backend": "",  # Special case: empty = let CMake use its default (none)
                "static": self.ON,  # BUILD_SHARED_LIBS default is OFF, so static=ON
                "test": self.ON,  # BUILD_TESTING default is ON
                "javasourceversion": 1.8,  # Special case: numeric value
                "javatargetversion": 1.8,  # Special case: numeric value
                "cxxstd": "",  # Special case: let CMake decide
                "logging_backend": "LOGURU",  # Default logging backend
                "cache": self.ON,  # Per-module compiler cache (CMake defaults ON)
                "cache_type": "none",  # Default cache backend is none
                "parallel_backend": "std",  # Default SMP backend
                "lto": "",  # empty = not specified; CMake picks the smart default per compiler
                "gtest": self.ON,  # *_ENABLE_GTEST CMake defaults are ON
                "benchmark": self.OFF,  # *_ENABLE_BENCHMARK CMake defaults are ON
                "magic_enum": self.ON,
                "mimalloc": self.ON,
                "icecc": self.OFF,
                "native": self.OFF,
                "examples": self.OFF,
                "linker": "default",  # *_LINKER_CHOICE default is "default" (auto-detect)
                "library_project": "",
            }
        )

    def __process_arg_list(self, arg_list):
        sanitizer_list = ["address", "undefined", "thread", "memory", "leak"]
        cpu_backend_list = ["no", "sse", "avx", "avx2", "avx512", "neon", "sve"]
        gpu_backend_list = ["none", "hip", "cuda", "metal"]
        cxx_std_list = ["cxx17", "cxx20", "cxx23"]
        logging_backend_list = ["native", "loguru", "glog", "spdlog"]
        cache_type_list = ["none", "ccache", "sccache", "buildcache"]
        parallel_backend_list = ["std", "openmp", "tbb"]
        linker_list = ["default", "mold", "lld", "gold", "lld-link"]

        # Set default values for special flags
        self.__value["mkl_link"] = "static"

        self.builder_suffix = ""
        for arg in arg_list:
            if arg == "wheel":
                self.__value["wheel"] = self.ON
                self.__value["python"] = self.ON
                self.builder_suffix += "_wheel"
            elif arg == "static":
                self.__value["static"] = self.OFF
                self.builder_suffix += "_static"
            elif arg in sanitizer_list:
                self.__value["sanitizer"] = self.ON
                self.__value["sanitizer_enum"] = arg
                self.builder_suffix += f"_{arg}"
            elif arg.startswith("lto."):
                lto_modes = ["off", "thin", "full", "ipo", "auto"]
                lto_mode = arg.split(".", 1)[1].lower()
                if lto_mode in lto_modes:
                    self.__value["lto"] = lto_mode
                    if lto_mode != "off":
                        self.builder_suffix += f"_lto_{lto_mode}"
                    print_status(f"LTO mode: {lto_mode}", "INFO")
                else:
                    print_status(
                        f"Unknown LTO mode '{lto_mode}'. Valid options: {', '.join(lto_modes)}",
                        "ERROR",
                    )
                    sys.exit(1)
            elif arg.startswith("linker."):
                linker_value = arg.split(".", 1)[1].lower()
                if linker_value in linker_list and linker_value != "default":
                    self.__value["linker"] = linker_value
                    self.builder_suffix += f"_linker_{linker_value}"
                    print_status(f"Setting linker to {linker_value}", "INFO")
                else:
                    print_status(
                        f"Unknown linker '{linker_value}'. Valid options: {', '.join(l for l in linker_list if l != 'default')}",
                        "ERROR",
                    )
                    sys.exit(1)
            elif arg == "pythondebug":
                self.__value["python"] = self.ON
                self.__value["pythondebug"] = self.ON
                self.builder_suffix += "_pythondebug"
            elif arg in cpu_backend_list:
                self.__value["cpu_backend"] = arg
                self.builder_suffix += f"_{arg}"
            elif arg in ("cuda", "hip", "metal"):
                self.__value["gpu_backend"] = arg
                self.builder_suffix += f"_{arg}"
            elif arg.startswith("gpu_backend."):
                backend = arg.split(".", 1)[1]
                if backend in gpu_backend_list:
                    self.__value["gpu_backend"] = backend
                    if backend != "none":
                        self.builder_suffix += f"_{backend}"
                else:
                    print_status(
                        f"Invalid GPU backend '{backend}'. Valid options: {', '.join(gpu_backend_list)}",
                        "ERROR",
                    )
                    sys.exit(1)
            elif re.match(r"^psize([1-9][0-9]*)$", arg.lower()):
                n = int(re.match(r"^psize([1-9][0-9]*)$", arg.lower()).group(1))
                if n > 256:
                    print_status(
                        "packet size must be between 1 and 256 (inclusive)",
                        "ERROR",
                    )
                    sys.exit(1)
                self.__value["packet_size"] = n
                self.builder_suffix += f"_psize{n}"
                print_status(f"Setting VECTORIZATION_PACKET_SIZE to {n}", "INFO")
            elif arg.startswith("profiler."):
                # Instrumentation backend (Kineto/ITT) is owned by ThirdParty/Profiler
                # via its own PROFILER_BACKEND cache var — XSigma must not set it.
                print_status(
                    f"Ignoring '{arg}': Profiler instrumentation backend is configured "
                    "inside ThirdParty/Profiler (not an XSigma setup flag).",
                    "WARNING",
                )
            elif arg.startswith("project."):
                proj_key = arg.split(".", 1)[1].lower()
                # Logging/Parallel are pure third-party dependencies (ThirdParty/
                # submodules), not Library/* projects — like Profiler, they have no
                # --project.* scope of their own.
                valid_projects = (
                    "memory",
                    "vectorization",
                    "core",
                    "models",
                    "graph",
                )
                if proj_key not in valid_projects:
                    print_status(
                        f"Invalid --project value '{proj_key}'. "
                        f"Valid options: {', '.join(valid_projects)}",
                        "ERROR",
                    )
                    sys.exit(1)
                self.__value["library_project"] = proj_key.title()
                self.builder_suffix += f"_project_{proj_key}"
                print_status(
                    f"Limiting build to Library/{self.__value['library_project']} (and CMake deps)",
                    "INFO",
                )
            elif arg in logging_backend_list:
                # Set logging backend (NATIVE, LOGURU, GLOG, or SPDLOG)
                self.__value["logging_backend"] = arg.upper()
                self.builder_suffix += f"_logging_{arg}"
                print_status(f"Setting logging backend to {arg.upper()}", "INFO")
            elif arg in cache_type_list:
                # Set cache type (none, ccache, sccache, or buildcache)
                self.__value["cache_type"] = arg
                self.builder_suffix += f"_{arg}"
                print_status(f"Setting cache type to {arg}", "INFO")
            elif arg.startswith("parallel."):
                # Handle SMP backend selection (--parallel.std, --parallel.openmp, --parallel.tbb)
                # This flag controls which parallel processing backend is used:
                # - std:     Standard C++ threads (std_thread) - default, maximum compatibility
                # - openmp:  OpenMP parallel processing - optimized for OpenMP-aware code
                # - tbb:     Intel Threading Building Blocks - high-performance parallel execution
                # Only one backend can be active at a time. The selected backend affects:
                # - PROJECT_HAS_TBB compile definition (1 if tbb selected, 0 otherwise)
                # - PROJECT_HAS_OPENMP compile definition (1 if openmp selected, 0 otherwise)
                # - Build directory suffix (e.g., build_ninja_parallel_tbb)
                backend_value = arg.split(".", 1)[1].lower()
                if backend_value in parallel_backend_list:
                    self.__value["parallel_backend"] = backend_value
                    self.builder_suffix += f"_parallel_{backend_value}"
                    print_status(f"Selecting SMP backend: {backend_value}", "INFO")
                else:
                    print_status(
                        f"Invalid SMP backend '{backend_value}'. Valid options: {', '.join(parallel_backend_list)}",
                        "ERROR",
                    )
                    sys.exit(1)
            elif any(arg.lower() == item.lower() for item in cxx_std_list):
                # Extract the numeric part (e.g., "cxx17" -> "17")
                std_version = arg[3:]  # Remove "cxx" prefix
                self.__value["cxxstd"] = std_version
                # self.builder_suffix += f"_{arg.lower()}"
                print_status(f"Setting C++ standard to C++{std_version}", "INFO")
            elif re.match(r"^c\+\+(\d+)$", arg.lower()):
                # Handle "c++20" style syntax (alternative to "cxx20")
                std_version = re.match(r"^c\+\+(\d+)$", arg.lower()).group(1)
                self.__value["cxxstd"] = std_version
                print_status(f"Setting C++ standard to C++{std_version}", "INFO")
            elif arg.isdigit():
                self.__value["javasourceversion"] = arg
                self.__value["javatargetversion"] = arg
                self.builder_suffix += f"_java{arg}"
            elif arg in self.__key:
                # Implement inverse logic based on CMake defaults
                if arg in ["gtest", "magic_enum", "mimalloc", "cache"]:
                    # These have CMake default ON, so providing the arg turns them OFF
                    self.__value[arg] = self.OFF
                elif arg == "lto":
                    # bare 'lto' token → auto mode (compiler picks thin on Clang, ipo on GCC/MSVC)
                    self.__value["lto"] = "auto"
                    self.builder_suffix += "_lto_auto"
                else:
                    # These have CMake default OFF, so providing the arg turns them ON
                    self.__value[arg] = self.ON

                # Special handling for specific flags
                if arg == "mkl":
                    self.__value["dist"] = "mkl"

                # Add to builder suffix (except for certain flags)
                if arg not in ["test", "build", "benchmark"]:
                    self.builder_suffix += f"_{arg}"

    def __validate_flags(self):
        """Validate flag combinations and warn about potential issues."""
        if (
            self.__value.get("python") == self.ON
            and self.__value.get("java") == self.ON
        ):
            print_status(
                "Python and Java bindings enabled simultaneously - this may increase build time.",
                "WARNING",
            )

        if (
            self.__value.get("sanitizer") == self.ON
            and self.__value.get("valgrind") == self.ON
        ):
            print_status(
                "Both sanitizer and valgrind enabled - consider using only one.",
                "WARNING",
            )

        if (
            self.__value.get("coverage") == self.ON
            and self.__value.get("test") != self.ON
        ):
            print_status(
                "Coverage enabled but testing is disabled - enabling tests automatically.",
                "WARNING",
            )
            self.__value["test"] = self.ON

        if self.__value.get("coverage") == self.ON:
            try:
                import coverage_tool  # noqa: F401
            except ImportError:
                print_status(
                    "coverage-tool is not installed. The in-tree Tools/coverage "
                    "package was moved to PyPI. Install with: pip install coverage-tool",
                    "ERROR",
                )
                sys.exit(1)

        if self.__value.get("spell") == self.ON:
            print_status(
                "SPELL CHECKING ENABLED: Automatic spelling corrections will be applied during build!",
                "WARNING",
            )
            print_status(
                "Ensure you have committed your changes before building with this option.",
                "WARNING",
            )

        # Validate SMP backend selection
        parallel_backend = self.__value.get("parallel_backend", "std")
        valid_backends = ["std", "openmp", "tbb"]
        if parallel_backend not in valid_backends:
            print_status(
                f"Invalid SMP backend '{parallel_backend}'. Valid options: {', '.join(valid_backends)}",
                "ERROR",
            )
            sys.exit(1)

        # Validate C++ standard
        if self.__value.get("cxxstd"):
            std_version = self.__value["cxxstd"]
            try:
                version_num = int(std_version)
                if version_num < 11 or version_num > 26:  # Reasonable range check
                    print_status(
                        f"Warning: C++ standard {std_version} may not be supported by your compiler",
                        "WARNING",
                    )
                elif version_num >= 20:
                    print_status(
                        f"Using modern C++ standard C++{std_version} - ensure your compiler supports it",
                        "INFO",
                    )
            except ValueError:
                print_status(f"Invalid C++ standard format: {std_version}", "WARNING")

    @staticmethod
    def find_case_insensitive(element, lst):
        element_lower = element.lower()
        return next((item for item in lst if element_lower == item.lower()), None)

    def create_cmake_flags(self, cmake_cmd_flags, build_enum, system):
        debug_print("Create cmake flags")
        # First handle build type
        build_type = None
        if self.__value.get("wheel") == self.ON:
            cmake_cmd_flags.extend(["-DPython3_FIND_STRATEGY=LOCATION"])
            self.__value["test"] = self.OFF
            build_type = "RELEASE"
        elif (
            self.__value.get("valgrind") == self.ON
            or self.__value.get("sanitizer") == self.ON
            or self.__value.get("coverage") == self.ON
        ):
            print_status(
                "Enabling debug build for sanitizer, valgrind, or coverage analysis",
                "INFO",
            )
            build_type = "DEBUG"
        else:
            build_type = str(build_enum).capitalize()

        # Always set library scope so omitting --project.* clears a stale XSIGMA_LIBRARY_PROJECT
        # from an earlier configure (empty = full Library/* tree).
        _lp = self.__value.get("library_project") or ""
        cmake_cmd_flags.append(f"-DXSIGMA_LIBRARY_PROJECT={_lp}")
        # Empty means fan flags to every module.
        _lp_mod = _lp.upper()

        # ------------------------------------------------------------------ per-module fan-outs
        # Every flag in this section is propagated to all library modules so that a
        # single setup.py argument controls the entire project uniformly. When
        # --project.NAME is set, only that module's CMakeLists.txt is loaded, so
        # fanning CORE_*/MEMORY_*/… flags would produce CMake unused-variable
        # warnings.
        # NOTE: PROFILER, LOGGING, and PARALLEL are deliberately absent — they are
        # consumed as pure third-party dependencies (ThirdParty/ submodules, like
        # fmt/googletest): XSigma feature flags must not fan into them. They build
        # with their own defaults (tests/examples disabled — see xsigma_add_profiler()/
        # xsigma_add_logging()/xsigma_add_parallel() in ThirdParty/CMakeLists.txt).
        ALL_MODULES = [
            "CORE",
            "MEMORY",
            "VECTORIZATION",
            "MODELS",
            "GRAPH",
        ]
        if _lp_mod:
            ALL_MODULES = [mod for mod in ALL_MODULES if mod == _lp_mod]

        _GLOBAL_CMAKE_FLAGS = {
            "BUILD_SHARED_LIBS",
            "BUILD_TESTING",
            "XSIGMA_ENABLE_EXTERNAL",
            # Logging is a dependency of scoped modules such as Memory; Parallel is
            # pulled in by Graph. Their backend selectors stay user-facing and must
            # reach the third-party subprojects even in --project.* scoped builds.
            "LOGGING_BACKEND",
            "PARALLEL_BACKEND",
            "PARALLEL_ENABLE_OPENMP",
        }

        def _cmake_flag_in_scope(flag_name):
            if not _lp_mod:
                return True
            if flag_name in _GLOBAL_CMAKE_FLAGS:
                return True
            return flag_name.startswith(_lp_mod + "_")

        # Add all other CMake flags
        for key, value in self.__value.items():
            if key in self.__name:
                flag_name = self.__name[key]
                if isinstance(value, bool):
                    flag_value = "ON" if value else "OFF"
                else:
                    flag_value = str(value)

                # Add the flag if it has a meaningful value
                # Include OFF values for boolean flags to explicitly disable features
                if flag_value and flag_value != "" and _cmake_flag_in_scope(flag_name):
                    cmake_cmd_flags.append(f"-D{flag_name}={flag_value}")

        # `torch` maps to VECTORIZATION_ENABLE_LIBTORCH above, which is out of
        # scope for --project.memory. Memory has its own ENABLE_LIBTORCH option
        # keyed off the same token. (Profiler is pure third-party — no fan-out.)
        _torch_val = self.__value.get("torch")
        if _torch_val in [self.ON, self.OFF]:
            _torch_onoff = "ON" if _torch_val == self.ON else "OFF"
            for _torch_flag in ("MEMORY_ENABLE_LIBTORCH",):
                if _cmake_flag_in_scope(_torch_flag):
                    cmake_cmd_flags.append(f"-D{_torch_flag}={_torch_onoff}")

        # Fan C++ standard out to every in-scope module
        if self.__value.get("cxxstd"):
            std_value = self.__value["cxxstd"]
            for _mod in ALL_MODULES:
                cmake_cmd_flags.append(f"-D{_mod}_CXX_STANDARD={std_value}")

        def _fan_bool(key, cmake_suffix):
            val = self.__value.get(key)
            if val in [self.ON, self.OFF]:
                for mod in ALL_MODULES:
                    cmake_cmd_flags.append(f"-D{mod}_{cmake_suffix}={val}")

        def _fan_str(key, cmake_suffix):
            val = self.__value.get(key)
            if val and val != "" and val != self.OFF:
                for mod in ALL_MODULES:
                    cmake_cmd_flags.append(f"-D{mod}_{cmake_suffix}={val}")

        _fan_bool("benchmark", "ENABLE_BENCHMARK")
        _fan_bool("coverage", "ENABLE_COVERAGE")

        # Fan LTO mode to all modules only when the user explicitly set it.
        # When unset (empty string), CMake uses xsigma_lto_compute_default() — which
        # picks thin/ipo/off based on compiler and build type — so we don't override it.
        _lto_val = (self.__value.get("lto") or "").strip().lower()
        if _lto_val in ("on",):
            _lto_val = "auto"  # normalise legacy ON from __set_all_flags
        if _lto_val:
            for _mod in ALL_MODULES:
                cmake_cmd_flags.append(f"-D{_mod}_LTO_MODE={_lto_val}")
        _fan_bool("gtest", "ENABLE_GTEST")
        _fan_bool("clangtidy", "ENABLE_CLANGTIDY")
        _fan_bool("iwyu", "ENABLE_IWYU")
        _fan_bool("sanitizer", "ENABLE_SANITIZER")
        _fan_bool("valgrind", "ENABLE_VALGRIND")
        _fan_bool("spell", "ENABLE_SPELL")
        _fan_bool("fix", "ENABLE_FIX")
        _fan_bool("icecc", "ENABLE_ICECC")
        _fan_bool("examples", "ENABLE_EXAMPLES")
        # cppcheck runs via Scripts/helpers/cppcheck.py after the build. No library
        # CMakeLists.txt consumes *_ENABLE_CPPCHECK, so do not fan it (unused-var warning).
        _fan_str("sanitizer_enum", "SANITIZER_TYPE")
        _fan_str("cache_type", "CACHE_BACKEND")
        _fan_str("linker", "LINKER_CHOICE")

        if self.__value.get("cache") in [self.ON, self.OFF]:
            cv = self.__value.get("cache")
            for mod in ALL_MODULES:
                cmake_cmd_flags.append(f"-D{mod}_ENABLE_CACHE={cv}")

        # When the TBB parallel backend is selected, the Memory TBB allocator must
        # also be enabled. PARALLEL_ENABLE_TBB itself is derived from PARALLEL_BACKEND
        # by ThirdParty/Parallel's own Cmake/parallel_backend.cmake — XSigma only
        # passes PARALLEL_BACKEND (a global flag) and never sets PARALLEL_* directly.
        if self.__value.get("parallel_backend") == "tbb":
            if not _lp_mod or _lp_mod == "MEMORY":
                cmake_cmd_flags.append("-DMEMORY_ENABLE_TBB=ON")

        # MKL VML backend for the Vectorization expression evaluator.
        # CORE_ENABLE_MKL controls BLAS/LAPACK usage in Core; VECTORIZATION_ENABLE_MKL
        # controls the VML batch math path in the Vectorization expression evaluator.
        # Both are enabled together when the user passes the 'mkl' flag.
        # Forward INTEL_MKL_DIR / MKLROOT from the environment so FindMKL.cmake can
        # locate the installation without requiring a manual -DINTEL_MKL_DIR= flag.
        if not _lp_mod or _lp_mod == "VECTORIZATION":
            if self.__value.get("mkl") == self.ON:
                cmake_cmd_flags.append("-DVECTORIZATION_ENABLE_MKL=ON")
                mkl_root = os.environ.get("INTEL_MKL_DIR") or os.environ.get("MKLROOT")
                if mkl_root:
                    cmake_cmd_flags.append(f"-DINTEL_MKL_DIR={mkl_root}")
            else:
                cmake_cmd_flags.append("-DVECTORIZATION_ENABLE_MKL=OFF")
        elif self.__value.get("mkl") == self.ON:
            mkl_root = os.environ.get("INTEL_MKL_DIR") or os.environ.get("MKLROOT")
            if mkl_root:
                cmake_cmd_flags.append(f"-DINTEL_MKL_DIR={mkl_root}")

        # GPU backend — project-specific flags for the two GPU-aware modules.
        # Profiler CMakeLists reads MEMORY_GPU_BACKEND to set PROFILER_HAS_METAL.
        gpu_val = self.__value.get("gpu_backend")
        if gpu_val and gpu_val != "":
            # Vectorization Metal kernels bind MTLBuffers via Memory's metal
            # caching allocator, so MEMORY_GPU_BACKEND must match.
            if not _lp_mod or _lp_mod in ("MEMORY", "VECTORIZATION"):
                cmake_cmd_flags.append(f"-DMEMORY_GPU_BACKEND={gpu_val}")
            if not _lp_mod or _lp_mod == "VECTORIZATION":
                cmake_cmd_flags.append(f"-DVECTORIZATION_GPU_BACKEND={gpu_val}")

        # Tune generated code for the host CPU (Clang/GCC; see Library/Vectorization/Cmake/utils.cmake).
        if self.__value.get("native") == self.ON and (
            not _lp_mod or _lp_mod == "VECTORIZATION"
        ):
            cmake_cmd_flags.append("-DUSE_NATIVE_ARCH=ON")

        # Add compilation database generation flag
        cmake_cmd_flags.append("-DCMAKE_EXPORT_COMPILE_COMMANDS=ON")

        return build_type

    def helper(self):
        for key, description in zip(self.__key, self.__description):
            if key == "parallel":
                key = "std, openmp or tbb"
            elif key == "parallel_backend":
                key = "parallel.std, parallel.openmp, or parallel.tbb"
            elif key == "cpu_backend":
                key = "sse, avx, avx2, avx512, neon, or sve"
            elif key == "cxxstd":
                key = "cxx11, cxx14, cxx17, cxx20, cxx23"
            elif key == "logging_backend":
                key = "NATIVE, LOGURU, GLOG, or SPDLOG"
            elif key == "cache_type":
                key = "none, ccache, sccache, or buildcache"
            elif key == "sanitizer":
                key = "sanitizer (or --sanitizer.TYPE)"
            elif key == "sanitizer_enum":
                key = "address, undefined, thread, memory, leak"
            elif key == "lto":
                key = "lto | --lto.thin | --lto.full | --lto.ipo | --lto.auto"
            elif key == "linker":
                key = "linker.mold | linker.lld | linker.gold | linker.lld-link"
            elif key == "native":
                key = "native (with release.lto for aggressive runtime)"
            print(f"{key:<30}{description}")

    def enable_gtest(self):
        self.__value["gtest"] = self.ON

    def is_gtest(self):
        return self.__value["gtest"] == self.ON

    def is_coverage(self):
        return self.__value["coverage"] == self.ON

    def is_valgrind(self):
        return self.__value["valgrind"] == self.ON

    def is_cppcheck(self):
        return self.__value["cppcheck"] == self.ON

    def get_sanitizer_type(self):
        """Get the current sanitizer type if enabled, None otherwise."""
        if self.__value.get("sanitizer") == self.ON:
            return self.__value.get("sanitizer_enum")
        return None


class XSigmaConfiguration:
    def __init__(self, args_list):
        # Check dependencies first
        missing_deps = check_dependencies()
        if missing_deps:
            print_status("Missing required dependencies:", "ERROR")
            for dep in missing_deps:
                print_status(f"  - {dep}", "ERROR")
            print_status("Please install missing dependencies and try again.", "ERROR")
            sys.exit(1)

        # Initialize utilities
        self.error_logger = ErrorLogger()
        self.summary_reporter = SummaryReporter()

        self.__initialize_values()
        self.__xsigma_flags = XSigmaFlags(args_list)
        self.__fill_compilation_flags(args_list)

    def __initialize_values(self):
        # Set default compiler to Clang on all platforms
        default_cxx_compiler = "clang++"
        default_c_compiler = "clang"

        self.__value = {
            "system": platform.system(),
            "build_folder": "build_ninja",
            "builder": "ninja",
            "config": "",
            "build": "",
            "test": "",
            "analyze": "",
            "build_enum": "Release",
            "cmake_generator": "Ninja",
            "cmake_cxx_compiler": f"-DCMAKE_CXX_COMPILER={default_cxx_compiler}",
            "cmake_c_compiler": f"-DCMAKE_C_COMPILER={default_c_compiler}",
            "compiler_flags": "--debug-trycompile",
            "verbosity": "",
            "arg_cmake_verbose": "--loglevel=NOTICE",
        }
        self.__compiler_user_specified = False
        print(f"================= {self.__value['system']} platform =================")

    def __fill_compilation_flags(self, args_list):
        debug_print("Fill Compilation flags")
        for arg in args_list:
            self.__process_arg(arg)

    def __process_arg(self, arg):
        if arg == "ninja":
            self.__set_ninja_flags()
        elif arg == "xcode":
            self.__set_xcode_flags()
        elif self.__is_clang_compiler(arg):
            self.__set_clang_compiler(arg)
        elif arg == "clang-cl":
            self.__value["cmake_cxx_compiler"] = "-DCMAKE_GENERATOR_TOOLSET=ClangCL"
            self.__value["cmake_c_compiler"] = ""
            self.__compiler_user_specified = True
        elif self.__is_gcc_compiler(arg):
            self.__set_gcc_compiler(arg)
        elif self.__is_visual_studio(arg):
            self.__set_visual_studio(arg)
        elif arg in ["config", "build", "test", "analyze", "clean"]:
            self.__value[arg] = arg
        elif arg in ["release", "debug", "relwithdebinfo"]:
            self.__value["build_enum"] = arg.capitalize()
        elif arg in ["vv", "v"]:
            self.__set_verbose_flags()

        if (
            self.__xsigma_flags.is_coverage()
            and "clang" in self.__value["cmake_cxx_compiler"].lower()
        ):
            self.__xsigma_flags.enable_gtest()

    def __set_ninja_flags(self):
        self.__value["cmake_generator"] = "Ninja"
        self.__value["builder"] = "ninja"
        self.__value["build_folder"] = (
            f"build_ninja{self.__xsigma_flags.builder_suffix}"
        )

    def __set_xcode_flags(self):
        if self.__value["system"] == "Darwin":
            if check_xcode_availability():
                self.__value["cmake_generator"] = "Xcode"
                self.__value["builder"] = "xcodebuild"
                self.__value["build_folder"] = (
                    f"build_xcode{self.__xsigma_flags.builder_suffix}"
                )
                self.__value["compiler_flags"] = ""
                # Compilers and TOOLCHAINS both come from Cmake/tools/xcode_toolchain.cmake
                # (LLVM*.xctoolchain/usr/bin/clang) so compile and link use one toolchain.
                if not self.__compiler_user_specified:
                    self.__value["cmake_c_compiler"] = ""
                    self.__value["cmake_cxx_compiler"] = ""
                print_status("Using Xcode generator", "SUCCESS")
            else:
                print_status("Xcode not found, falling back to Ninja", "WARNING")
                # Check if Xcode is installed but not configured
                if check_xcode_installation():
                    print_status(
                        "Xcode appears to be installed but not configured properly",
                        "INFO",
                    )
                self.__set_ninja_flags()
        else:
            print_status("Xcode generator is only available on macOS", "WARNING")
            # Fall back to default generator for non-macOS systems
            self.__set_ninja_flags()

    def __is_clang_compiler(self, arg):
        return "clang" in arg and arg not in ["clang-cl", "clangtidy"]

    def __set_clang_compiler(self, arg):
        self.__value["cmake_c_compiler"] = f"-DCMAKE_C_COMPILER={arg}"
        self.__value["cmake_cxx_compiler"] = (
            f"-DCMAKE_CXX_COMPILER={arg.replace('clang', 'clang++')}"
        )
        self.__compiler_user_specified = True

    def __is_gcc_compiler(self, arg):
        """Check if argument is a GCC compiler specification (gcc, g++, gcc-11, g++-11, etc.)"""
        return ("gcc" in arg or "g++" in arg) and arg not in ["cppcheck"]

    def __set_gcc_compiler(self, arg):
        """Set GCC compiler for CMake configuration"""
        if "g++" in arg:
            # If it's g++ or g++-XX, use it as CXX and derive C compiler
            self.__value["cmake_cxx_compiler"] = f"-DCMAKE_CXX_COMPILER={arg}"
            # Replace g++ with gcc to get the C compiler
            c_compiler = arg.replace("g++", "gcc")
            self.__value["cmake_c_compiler"] = f"-DCMAKE_C_COMPILER={c_compiler}"
        else:
            # If it's gcc or gcc-XX, use it as C compiler and derive CXX compiler
            self.__value["cmake_c_compiler"] = f"-DCMAKE_C_COMPILER={arg}"
            # Replace gcc with g++ to get the CXX compiler
            cxx_compiler = arg.replace("gcc", "g++")
            self.__value["cmake_cxx_compiler"] = f"-DCMAKE_CXX_COMPILER={cxx_compiler}"
        self.__compiler_user_specified = True

    def __is_visual_studio(self, arg):
        return (
            arg in ["vs17", "vs19", "vs22", "vs26"]
            and self.__value["system"] == "Windows"
        )

    def __set_visual_studio(self, arg):
        vs_versions = {
            "vs17": ("Visual Studio 15 2017 Win64", "build_vs17"),
            "vs19": ("Visual Studio 16 2019", "build_vs19"),
            "vs22": ("Visual Studio 17 2022", "build_vs22"),
            "vs26": ("Visual Studio 18 2026", "build_vs26"),
        }
        self.__value["compiler_flags"] = "-A x64"
        self.__value["cmake_generator"], base_build_folder = vs_versions[arg]
        self.__value["builder"] = "cmake"
        self.__value["build_folder"] = (
            f"{base_build_folder}{self.__xsigma_flags.builder_suffix}"
        )
        if not self.__compiler_user_specified:
            # Let Visual Studio decide the native MSVC toolchain unless the user requested otherwise.
            self.__value["cmake_cxx_compiler"] = ""
            self.__value["cmake_c_compiler"] = ""

    def __set_verbose_flags(self):
        self.__value["arg_cmake_verbose"] = "--loglevel=VERBOSE"
        self.__value["verbosity"] = "-VV"

    def config(self, source_path, build_path):
        if self.__value["config"] != "config":
            return 0

        print_status("Configuring build...", "INFO")
        try:
            cmake_flags = []
            self.__value["build_enum"] = self.__xsigma_flags.create_cmake_flags(
                cmake_flags, self.__value["build_enum"], self.__value["system"]
            )
            print(f"build enum: {self.__value['build_enum']}")
            cmake_flags.append(f"-DCMAKE_BUILD_TYPE={self.__value['build_enum']}")

            generator_toolset = self.__value.get("generator_toolset")
            exit_code = config_helper.configure_build(
                source_path,
                build_path,
                self.__value["cmake_generator"],
                self.__value["cmake_cxx_compiler"],
                self.__value["cmake_c_compiler"],
                cmake_flags,
                self.__value["arg_cmake_verbose"],
                self.__shell_flag(),
                generator_toolset=generator_toolset,
            )

            if exit_code == 0:
                print_status("Build configured successfully", "SUCCESS")
                # If using Xcode, offer to open the project
                if self.__value["cmake_generator"] == "Xcode":
                    config_helper.handle_xcode_project_opening()
            else:
                print_status("Configuration failed", "ERROR")
                sys.exit(1)

        except subprocess.CalledProcessError as e:
            suggestions = [
                "Check if CMake is properly installed",
                "Verify all required dependencies are available",
                "Check if the generator is supported on your system",
                "Try a different build generator (e.g., ninja instead of make)",
            ]
            self.error_logger.log_error(
                "cmake", str(e), "Configuring the build system", suggestions
            )
            print_status(f"Configuration failed: {e}", "ERROR")
            print_status(
                f"Detailed error log saved to: {self.error_logger.get_log_file_path()}",
                "INFO",
            )
            sys.exit(1)

    def build(self):
        if self.__value["build"] != "build":
            return 0

        print_status("Building project...", "INFO")
        try:
            exit_code = build_helper.build_project(
                self.__value["builder"],
                self.__value["build_enum"],
                self.__value["system"],
                self.__shell_flag(),
            )
            if exit_code == 0:
                print_status("Build completed successfully", "SUCCESS")
            else:
                print_status("Build failed", "ERROR")
                sys.exit(1)
        except subprocess.CalledProcessError as e:
            suggestions = [
                "Check if all dependencies are installed",
                "Verify the build configuration is correct",
                "Try cleaning the build directory and reconfiguring",
                "Check for compiler errors in the output above",
            ]
            self.error_logger.log_error(
                "build", str(e), "Building the project", suggestions
            )
            print_status(f"Build failed: {e}", "ERROR")
            print_status(
                f"Detailed error log saved to: {self.error_logger.get_log_file_path()}",
                "INFO",
            )
            sys.exit(1)

    def cppcheck(self, source_path, build_path):
        """Run cppcheck static analysis with user-friendly interface."""
        if self.__value["build"] != "build" or not self.__xsigma_flags.is_cppcheck():
            return 0

        print_status("Starting static code analysis with cppcheck...", "INFO")

        # Check if cppcheck is installed
        try:
            version_result = subprocess.run(
                ["cppcheck", "--version"], capture_output=True, check=True, text=True
            )
            print_status(f"Found cppcheck: {version_result.stdout.strip()}", "SUCCESS")
        except (subprocess.CalledProcessError, FileNotFoundError):
            suggestions = [
                "Ubuntu/Debian: sudo apt-get install cppcheck",
                "CentOS/RHEL/Fedora: sudo dnf install cppcheck",
                "macOS: brew install cppcheck",
                "Windows: choco install cppcheck or winget install cppcheck",
            ]
            self.error_logger.log_error(
                "cppcheck --version",
                "cppcheck command not found",
                "Checking for cppcheck installation",
                suggestions,
            )
            print_status("cppcheck not found. Please install cppcheck:", "ERROR")
            for suggestion in suggestions:
                print_status(f"  - {suggestion}", "INFO")
            return 1

        # Prepare output directory and file
        os.makedirs(build_path, exist_ok=True)
        output_file = os.path.join(build_path, "cppcheck_output.log")

        # Build cppcheck command with optimized settings
        cppcheck_cmd = self._build_cppcheck_command(source_path, output_file)

        try:
            # Change to project root directory to run cppcheck
            original_dir = os.getcwd()
            os.chdir(source_path)

            print_status("Analyzing source code for potential issues...", "INFO")
            print_status("This may take a few minutes for large codebases", "INFO")

            result = subprocess.run(
                cppcheck_cmd, capture_output=True, text=True, check=False
            )

            # Change back to build directory
            os.chdir(original_dir)

            # Process and display results
            exit_code = self._process_cppcheck_results(result, output_file, source_path)

            # Add to summary report
            self.summary_reporter.add_cppcheck_report(output_file, exit_code)

            return exit_code

        except Exception as e:
            error_msg = f"Unexpected error during cppcheck execution: {e}"
            self.error_logger.log_error(
                " ".join(cppcheck_cmd),
                str(e),
                "Running cppcheck static analysis",
                [
                    "Check if the source directory is accessible",
                    "Verify cppcheck installation",
                ],
            )
            print_status(error_msg, "ERROR")
            # Change back to build directory in case of error
            try:
                os.chdir(original_dir)
            except Exception:  # noqa: E722
                pass
            return 1

    def _build_cppcheck_command(self, source_path: str, output_file: str) -> list[str]:
        """Build the cppcheck command with appropriate settings."""
        return cppcheck_helper.build_cppcheck_command(source_path, output_file)

    def _process_cppcheck_results(
        self, result: subprocess.CompletedProcess, output_file: str, source_path: str
    ) -> int:
        """Process cppcheck results and provide user-friendly feedback."""
        return cppcheck_helper.process_cppcheck_results(result, output_file)

    def test(self, source_path, build_path):
        if self.__value["test"] != "test":
            return 0

        if self.__xsigma_flags.is_valgrind():
            exit_code = test_helper.run_valgrind_test(
                source_path, build_path, self.__shell_flag()
            )
            # Add valgrind results to summary
            self.summary_reporter.add_valgrind_report(build_path, exit_code)
            return exit_code

        skip_reason = runtime_test_skip_reason(self.__value.get("cpu_backend", ""))
        if skip_reason:
            print_status(skip_reason, "WARNING")
            return 0

        return test_helper.run_ctest(
            self.__value["builder"],
            self.__value["build_enum"],
            self.__value["system"],
            self.__value["verbosity"],
            self.__shell_flag(),
            sanitizer_type=self.__xsigma_flags.get_sanitizer_type(),
            source_path=source_path,
        )

    def coverage(self, source_path, build_path):
        """Run code coverage analysis.

        Args:
            source_path: Path to source directory (project root).
            build_path: Path to build directory.

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        if self.__value["build"] != "build" or not self.__xsigma_flags.is_coverage():
            return 0

        print_status(
            "Starting code coverage collection and report generation...", "INFO"
        )

        try:
            from coverage_tool import get_coverage
        except ImportError:
            print_status(
                "coverage-tool is not installed. Install with: "
                "pip install coverage-tool",
                "ERROR",
            )
            return 1

        coverage_result = get_coverage(
            compiler="auto",
            build_folder=build_path,
            source_folder=os.path.join(source_path, "Library"),
            output_folder=os.path.join(build_path, "coverage_report"),
            summary=True,
            project_root=source_path,
        )
        if coverage_result == 0:
            print_status("Coverage collection completed successfully", "SUCCESS")
            self.summary_reporter.add_coverage_report(build_path, 0)

            # Display coverage summary automatically
            # self._display_coverage_summary(build_path)

            return 0
        else:
            print_status("Coverage collection failed", "ERROR")
            return 1

    def _display_coverage_summary(self, build_path):
        """Display coverage summary from JSON report.

        Args:
            build_path: Path to build directory containing coverage reports.
        """
        import json

        # Look for coverage summary JSON file
        coverage_json_paths = [
            os.path.join(build_path, "coverage_report", "coverage_summary.json"),
            os.path.join(build_path, "coverage_report", "coverage.json"),
        ]

        coverage_json = None
        for path in coverage_json_paths:
            if os.path.exists(path):
                coverage_json = path
                break

        if not coverage_json:
            print_status("Coverage summary file not found, skipping display", "WARNING")
            return

        try:
            with open(coverage_json, encoding="utf-8") as f:
                coverage_data = json.load(f)

            print_status("\n" + "=" * 80, "INFO")
            print_status("CODE COVERAGE SUMMARY", "INFO")
            print_status("=" * 80, "INFO")

            # Display global metrics if available
            if "global_metrics" in coverage_data:
                metrics = coverage_data["global_metrics"]
                total_lines = metrics.get("total_lines", 0)
                covered_lines = metrics.get("covered_lines", 0)
                coverage_percent = metrics.get("line_coverage_percent", 0.0)

                print_status(f"Total Lines:    {total_lines}", "INFO")
                print_status(f"Covered Lines:  {covered_lines}", "INFO")
                print_status(
                    f"Coverage:       {coverage_percent:.2f}%",
                    "SUCCESS"
                    if coverage_percent >= 95.0
                    else "WARNING"
                    if coverage_percent >= 80.0
                    else "ERROR",
                )

                # Display function coverage if available
                if metrics.get("total_functions", 0) > 0:
                    func_coverage = metrics.get("function_coverage_percent", 0.0)
                    print_status(f"Function Coverage: {func_coverage:.2f}%", "INFO")

                # Display region coverage if available
                if metrics.get("total_regions", 0) > 0:
                    region_coverage = metrics.get("region_coverage_percent", 0.0)
                    print_status(f"Region Coverage:   {region_coverage:.2f}%", "INFO")

            # Display summary metrics if available (alternative format)
            elif "summary" in coverage_data:
                summary = coverage_data["summary"]
                if "line_coverage" in summary:
                    line_cov = summary["line_coverage"]
                    total = line_cov.get("total", 0)
                    covered = line_cov.get("covered", 0)
                    percent = line_cov.get("percent", 0.0)

                    print_status(f"Total Lines:    {total}", "INFO")
                    print_status(f"Covered Lines:  {covered}", "INFO")
                    print_status(
                        f"Coverage:       {percent:.2f}%",
                        "SUCCESS"
                        if percent >= 95.0
                        else "WARNING"
                        if percent >= 80.0
                        else "ERROR",
                    )

                if "function_coverage" in summary:
                    func_cov = summary["function_coverage"]
                    func_percent = func_cov.get("percent", 0.0)
                    print_status(f"Function Coverage: {func_percent:.2f}%", "INFO")

            # Display HTML report location
            html_report_paths = [
                os.path.join(build_path, "coverage_report", "html", "index.html"),
                os.path.join(build_path, "coverage_report", "index.html"),
            ]

            for html_path in html_report_paths:
                if os.path.exists(html_path):
                    print_status(f"\nHTML Report: {html_path}", "INFO")
                    break

            print_status("=" * 80, "INFO")

        except Exception as e:
            print_status(f"Failed to display coverage summary: {e}", "WARNING")

    def __shell_flag(self):
        return self.__value["system"] == "Windows"

    def move_to_build_folder(self):
        os.chdir("..")
        build_folder = self.__value["build_folder"]

        if os.path.isdir(build_folder) and self.__value.get("config") == "config":
            shutil.rmtree(build_folder, ignore_errors=True)

        if not os.path.isdir(build_folder):
            os.mkdir(build_folder)

        os.chdir(build_folder)
        return os.getcwd()

    def find_build_directory_for_analysis(self, source_path: str) -> Optional[str]:
        """Find the most appropriate build directory for analysis tools."""
        # First try the current build folder if it exists
        current_build = self.__value.get("build_folder")
        if current_build and os.path.isdir(os.path.join(source_path, current_build)):
            return os.path.join(source_path, current_build)

        # Use the build directory detector to find alternatives
        build_dir = BuildDirectoryDetector.find_best_build_directory(
            source_path, current_build
        )
        if build_dir:
            return str(build_dir)

        return None


def parse_args(args):
    """Parse command line arguments, handling special flags first."""
    processed_args = []

    for arg in args:
        # Handle sanitizer flags with dot notation (e.g., --sanitizer.undefined)
        if arg.startswith("--sanitizer."):
            sanitizer_type = arg.split(".", 1)[1].lower()
            valid_sanitizers = ["address", "undefined", "thread", "memory", "leak"]
            if sanitizer_type in valid_sanitizers:
                processed_args.extend(["sanitizer", sanitizer_type])
            else:
                print_status(
                    f"Invalid sanitizer type: {sanitizer_type}. Valid options: {', '.join(valid_sanitizers)}",
                    "ERROR",
                )
                sys.exit(1)
        # Handle individual sanitizer enable flags
        elif arg.startswith("--logging="):
            backend_type = arg.split("=", 1)[1].upper()
            valid_backends = ["NATIVE", "LOGURU", "GLOG", "SPDLOG"]
            if backend_type in valid_backends:
                processed_args.append(backend_type.lower())
                print_status(f"Logging backend set to {backend_type}", "INFO")
            else:
                print_status(
                    f"Invalid logging backend: {backend_type}. Valid options: {', '.join(valid_backends)}",
                    "ERROR",
                )
                sys.exit(1)
        elif arg.startswith("--logging."):
            backend_type = arg.split(".", 1)[1].upper()
            valid_backends = ["NATIVE", "LOGURU", "GLOG", "SPDLOG"]
            if backend_type in valid_backends:
                processed_args.append(backend_type.lower())
                print_status(f"Logging backend set to {backend_type}", "INFO")
            else:
                print_status(
                    f"Invalid logging backend: {backend_type}. Valid options: {', '.join(valid_backends)}",
                    "ERROR",
                )
                sys.exit(1)
        elif arg.startswith("--profiler."):
            # Accepted only so old scripts fail softly; backend is Profiler's concern.
            print_status(
                f"Ignoring '{arg}': Profiler instrumentation backend is configured "
                "inside ThirdParty/Profiler (not an XSigma setup flag).",
                "WARNING",
            )
        elif arg in ("--mimalloc_stats", "--mimalloc-stats"):
            # Multi-word option: the dotted-token splitter treats '_' as a
            # delimiter (re.split(r"_|\.|\ ", ...)), so this needs an explicit
            # --flag form that passes through as a single token.
            processed_args.append("mimalloc_stats")
            print_status("mimalloc statistics enabled (MI_STAT=1)", "INFO")
        elif arg.startswith("--packet-size="):
            size_part = arg.split("=", 1)[1].strip()
            if not size_part.isdigit() or int(size_part) < 1:
                print_status(
                    f"Invalid --packet-size value: {size_part!r}. Expected a positive integer.",
                    "ERROR",
                )
                sys.exit(1)
            if int(size_part) > 256:
                print_status(
                    "packet size must be between 1 and 256 (inclusive)",
                    "ERROR",
                )
                sys.exit(1)
            processed_args.append(f"psize{size_part}")
            print_status(f"Packet size set to {size_part}", "INFO")
        elif arg.startswith("--project."):
            proj = arg.split(".", 1)[1].lower()
            # Logging/Parallel are pure third-party dependencies (ThirdParty/
            # submodules), not Library/* projects — no --project.* scope.
            valid_projects = (
                "memory",
                "vectorization",
                "core",
                "models",
                "graph",
            )
            if proj not in valid_projects:
                print_status(
                    f"Invalid --project value '{proj}'. "
                    f"Valid options: {', '.join(valid_projects)}",
                    "ERROR",
                )
                sys.exit(1)
            processed_args.append(f"project.{proj}")
            print_status(
                f"Library scope: {proj} (pass-through as project.{proj})",
                "INFO",
            )
        elif arg.startswith("--lto."):
            lto_mode = arg.split(".", 1)[1].lower()
            valid_lto_modes = ["off", "thin", "full", "ipo", "auto"]
            if lto_mode in valid_lto_modes:
                processed_args.append(f"lto.{lto_mode}")
                print_status(f"LTO mode set to {lto_mode}", "INFO")
            else:
                print_status(
                    f"Invalid LTO mode '{lto_mode}'. Valid options: {', '.join(valid_lto_modes)}",
                    "ERROR",
                )
                sys.exit(1)
        elif arg.startswith("--parallel."):
            # Parse SMP backend selection flag (--parallel.std, --parallel.openmp, --parallel.tbb)
            # This is the first stage of argument parsing that converts command-line flags
            # into internal argument format. The actual backend selection happens later
            # in XSigmaFlags.__process_arg_list() which sets CMake variables.
            #
            # Supported backends:
            # - --parallel.std:     Use standard C++ threads (std_thread)
            # - --parallel.openmp:  Use OpenMP for parallel processing
            # - --parallel.tbb:     Use Intel Threading Building Blocks
            #
            # The selected backend controls which CMake options are enabled:
            # - std:     PARALLEL_ENABLE_TBB=OFF, PARALLEL_ENABLE_OPENMP=OFF
            # - openmp:  PARALLEL_ENABLE_OPENMP=ON, PARALLEL_ENABLE_TBB=OFF
            # - tbb:     PARALLEL_ENABLE_TBB=ON, PARALLEL_ENABLE_OPENMP=OFF
            backend_value = arg.split(".", 1)[1].lower()
            valid_backends = ["std", "openmp", "tbb"]
            if backend_value in valid_backends:
                # Pass the backend selection to the next processing stage
                processed_args.append(f"parallel.{backend_value}")
                print_status(f"SMP backend set to {backend_value}", "INFO")
            else:
                print_status(
                    f"Invalid SMP backend: {backend_value}. Valid options: {', '.join(valid_backends)}",
                    "ERROR",
                )
                sys.exit(1)

        elif arg.startswith(("--gpu_backend.", "--gpu-backend.")):
            backend_value = arg.split(".", 1)[1].lower()
            valid_backends = ["none", "cuda", "hip", "metal"]
            if backend_value in valid_backends:
                processed_args.append(f"gpu_backend.{backend_value}")
            else:
                print_status(
                    f"Invalid GPU backend: {backend_value}. Valid options: {', '.join(valid_backends)}",
                    "ERROR",
                )
                sys.exit(1)

        elif re.search(r"[/\\]", arg) and re.search(
            r"[Cc]lang|[Gg][Cc][Cc]|[Gg]\+\+", arg
        ):
            # Compiler path argument: contains a directory separator and a compiler name.
            # Pass through verbatim — do NOT split on '.' or '_' or lowercase, as that
            # would destroy paths like C:/msys64/mingw64/bin/clang.exe.
            processed_args.append(arg)
        else:
            # Apply the original parsing logic, but split on '.'/space first so
            # registered multi-word flags survive as single tokens: splitting a
            # dotted arg containing "mimalloc_stats" on '_' would shred it into
            # "mimalloc" (inverse-logic: DISABLES mimalloc!) and "stats" (unknown,
            # ignored) — silently dropping mimalloc without enabling statistics.
            for part in re.split(r"\.|\ ", arg.lower()):
                if part == "mimalloc_stats":
                    processed_args.append(part)
                else:
                    processed_args.extend(re.split(r"_", part))

    return processed_args


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--help":
        print_status("PRETORIAN Build Configuration Helper", "INFO")
        print("\n" + "=" * 80)
        print("DEFAULT CONFIGURATION:")
        print("  Build System: Ninja (fast, cross-platform)")
        print("  Compiler:     Clang (clang/clang++)")
        print("=" * 80)
        print("\nUsage examples:")
        print("  1. Default build (Ninja + Clang):")
        print("     setup.py config.build.test")
        print("  2. Development build with Python:")
        print("     setup.py config.build.test.python")
        print("  3. Release build with Visual Studio 2022:")
        print("     setup.py config.build.test.vs22.release.python")
        print("  4. macOS build with Xcode:")
        print("     setup.py config.build.test.xcode")
        print("  5. Build with GCC compiler (Unix/Linux):")
        print("     setup.py config.build.test.gcc")
        print("  6. Build with coverage (analysis runs automatically):")
        print("     setup.py config.build.test.coverage")
        print("\nBuild system generators:")
        print("  ninja     - Ninja build system (DEFAULT, fast, cross-platform)")
        print("  xcode     - Xcode (macOS only, full IDE integration)")
        print("  vs17/19/22- Visual Studio (Windows only)")
        print("\nCompiler options:")
        print("  clang     - Clang compiler (DEFAULT)")
        print("  clang-XX  - Specific Clang version (e.g., clang-15)")
        print("  gcc       - GCC compiler (Unix/Linux)")
        print("  gcc-XX    - Specific GCC version (e.g., gcc-11)")
        print("  g++       - G++ compiler (Unix/Linux)")
        print("  g++-XX    - Specific G++ version (e.g., g++-11)")
        print("\nBuild commands:")
        print("  config    - Configure the build system")
        print("  build     - Build the project")
        print("  test      - Run tests")
        print("  coverage  - Enable coverage (automatically displays summary)")
        print("\nSpecial flags:")
        print(
            "  spell                      Enable check-only spell checking (skips ThirdParty)"
        )
        print(
            "  fix                        Enable clang-tidy fix-errors and fix options"
        )
        print("\nSingle-library build (CMake):")
        print(
            "  --project.NAME             Only add_subdirectory Library/NAME (+ deps where needed)."
        )
        print("                             memory = Memory only (Logging disabled).")
        print(
            "                             vectorization/core include their normal dependency chain."
        )
        print(
            "                             Example: python setup.py config.build.test --project.memory"
        )
        print("\nVectorization options:")
        print(
            "  sleef              Enable SLEEF math library for NEON/SVE transcendentals"
        )
        print(
            "                             (auto-enabled by CMake when Apple Accelerate vForce is unavailable)"
        )
        print(
            "                             Example: python setup.py config.build.test.neon.sleef"
        )
        print("\nVectorization packet size:")
        print(
            "  --packet-size=N    SIMD lane count (CMake VECTORIZATION_PACKET_SIZE; default 4)"
        )
        print("  psizeN             Same as --packet-size=N (e.g. psize8)")
        print("\nLogging backend flags:")
        print("  --logging=BACKEND  Set logging backend")
        print("                             Options: NATIVE, LOGURU, GLOG, SPDLOG")
        print("                             Default: LOGURU")
        print("\nSanitizer flags:")
        print("  --sanitizer.address        Enable AddressSanitizer")
        print("  --sanitizer.undefined      Enable UndefinedBehaviorSanitizer")
        print("  --sanitizer.thread         Enable ThreadSanitizer")
        print("  --sanitizer.memory         Enable MemorySanitizer (Clang only)")
        print("  --sanitizer.leak           Enable LeakSanitizer")
        print("  --enable-sanitizer         Enable sanitizer (requires type)")
        print("  --sanitizer-type=TYPE      Specify sanitizer type")
        print("                             Options: address, undefined,")
        print("                             thread, memory, leak")
        print("\nLogging backend examples:")
        print("  # Use GLOG backend")
        print("  python setup.py config.build.test.ninja.clang --logging=GLOG")
        print("  # Use NATIVE backend")
        print("  python setup.py config.build.test.ninja.clang --logging=NATIVE")
        print("  # Use LOGURU backend (default, no flag needed)")
        print("  python setup.py config.build.test.ninja.clang")
        print("  # Use SPDLOG backend")
        print("  python setup.py config.build.test.ninja.clang --logging=SPDLOG")
        print("\nSanitizer examples:")
        print("  python setup.py config.build.test.vs22 --sanitizer.undefined")
        print("  python setup.py config.build.test.ninja.clang --sanitizer.address")
        print("  python setup.py config.build.test.vs22 --sanitizer-type=thread")
        print("\nSpell checking examples:")
        print("  # Enable check-only spell checking (skips ThirdParty)")
        print("  python setup.py config.build.test.ninja.clang.spell")
        print("  python setup.py config.build.test.vs22.spell")
        print("\nCoverage analysis examples:")
        print("  # Build with coverage (analysis runs automatically)")
        print("  python setup.py config.build.test.ninja.clang.coverage")
        print()
        print("  # Re-analyze with verbose output")
        print("  python setup.py analyze.v")
        print()
        print("  # Note: Coverage analysis is automatic when 'coverage' is enabled")
        print("  #       No need to add '.analyze' to coverage builds")
        print("\nBenchmark examples:")
        print(
            "  # Google Benchmark is on by default; Release + explicit .benchmark is typical for numbers"
        )
        print("  python setup.py config.build.ninja.clang.release.benchmark")
        print("  python setup.py config.build.ninja.clang.release.lto.benchmark")
        print("  # Explicit ThinLTO (Clang) or IPO fallback (GCC/MSVC):")
        print("  python setup.py config.build.ninja.clang.release --lto.thin")
        print("  python setup.py config.build.ninja.clang.release --lto.full")
        print("  python setup.py config.build.ninja.gcc.release --lto.ipo")
        print()
        print(
            "  # Note: To disable, pass CMake defines such as -DCORE_ENABLE_BENCHMARK=OFF"
            " (and the same for other *_ENABLE_BENCHMARK options)."
        )
        print(
            "  #       Recommended to use with Release build for accurate performance results."
        )
        print("\nAvailable options:")
        XSigmaFlags([]).helper()
        return

    try:
        arg_list = parse_args(sys.argv[1:])
        if not arg_list:
            print_status(
                "No build configuration specified. Use --help for usage information.",
                "ERROR",
            )
            sys.exit(1)

        print_status(f"Starting build configuration for {platform.system()}", "INFO")
        compilation_calc = XSigmaConfiguration(arg_list)

        source_path = os.path.dirname(os.getcwd())
        build_path = compilation_calc.move_to_build_folder()

        print_status(f"Build directory: {build_path}", "INFO")

        # Execute build pipeline
        try:
            start = time.perf_counter()
            compilation_calc.config(source_path, build_path)
            config_end = time.perf_counter()

            build_start = time.perf_counter()
            compilation_calc.build()
            build_end = time.perf_counter()

            cppcheck_start = time.perf_counter()
            compilation_calc.cppcheck(source_path, build_path)
            cppcheck_end = time.perf_counter()

            test_start = time.perf_counter()
            compilation_calc.test(source_path, build_path)
            test_end = time.perf_counter()

            coverage_start = time.perf_counter()
            compilation_calc.coverage(source_path, build_path)
            end = time.perf_counter()

            print_status(f"Config time: {config_end - start:.4f} seconds", "INFO")
            print_status(f"Build time: {build_end - build_start:.4f} seconds", "INFO")
            print_status(
                f"Cppcheck time: {cppcheck_end - cppcheck_start:.4f} seconds", "INFO"
            )
            print_status(f"Test time: {test_end - test_start:.4f} seconds", "INFO")
            print_status(f"Coverage time: {end - coverage_start:.4f} seconds", "INFO")

            print_status(f"Total time: {end - start:.4f} seconds", "INFO")

            print_status("Build process completed successfully!", "SUCCESS")

            # Display comprehensive summary report
            compilation_calc.summary_reporter.display_summary()

            # Show error log location if there were any errors
            if compilation_calc.error_logger.has_errors():
                print_status(
                    f"Error log available at: {compilation_calc.error_logger.get_log_file_path()}",
                    "INFO",
                )
                print_status(
                    "Review the error log for detailed troubleshooting information",
                    "INFO",
                )

        except SystemExit:
            # Re-raise SystemExit to preserve exit codes from subprocess failures
            compilation_calc.summary_reporter.display_summary()
            if compilation_calc.error_logger.has_errors():
                print_status(
                    f"Error log available at: {compilation_calc.error_logger.get_log_file_path()}",
                    "ERROR",
                )
            raise

    except KeyboardInterrupt:
        print_status("\nBuild process interrupted by user", "WARNING")
        # Try to display summary even if interrupted
        try:
            if "compilation_calc" in locals():
                compilation_calc.summary_reporter.display_summary()
        except Exception:  # noqa: E722
            pass
        sys.exit(1)
    except Exception as e:
        print_status(f"An unexpected error occurred: {e}", "ERROR")
        # Try to display summary and error log info even on unexpected errors
        try:
            if "compilation_calc" in locals():
                compilation_calc.summary_reporter.display_summary()
                if compilation_calc.error_logger.has_errors():
                    print_status(
                        f"Error log available at: {compilation_calc.error_logger.get_log_file_path()}",
                        "ERROR",
                    )
        except Exception:  # noqa: E722
            pass
        if DEBUG_FLAG:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
