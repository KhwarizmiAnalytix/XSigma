# XSigma Logging System

## Overview

Logging is a compile-time pluggable logging facade, consumed as a pure
third-party dependency: the `ThirdParty/Logging` submodule from
[KhwarizmiAnalytix/Logging](https://github.com/KhwarizmiAnalytix/Logging)
(CMake target `Logging::Logging`, Bazel `@logging//:Logging`). The public
C++ namespace is `logging`. Include paths are relative to the Logging repo
root (`logger/logger.h`, `util/exception.h`).

Select a backend at configure time with `setup.py --logging=SPDLOG|LOGURU|GLOG|NATIVE`
(default **LOGURU**). Application source does not change when you switch backends.

Memory, Vectorization, and Core **always** link `Logging::Logging`. There is
no `MEMORY_HAS_LOGGING` / `VECTORIZATION_HAS_LOGGING` opt-out: Memory calls
`LOGGING_LOG_*` / `LOGGING_CHECK` directly, and `VECTORIZATION_LOGF` /
`VECTORIZATION_CHECK` / `VECTORIZATION_THROW` forward to the Logging macros.

The library is **host/CPU only**. Do not call these macros from `__device__` code.

## Backends

| Backend | When to use | Notes |
|---------|-------------|--------|
| **LOGURU** (default) | Development and full-featured diagnostics | Scopes, callbacks, files, optional signal traces |
| **SPDLOG** | Fast sinks, colored stderr, file + callback | Best throughput in the comparison below. No process signal handlers |
| **GLOG** | Google-style severity logging | Callbacks are not supported; signal handlers honor `enable_unsafe_signal_handler` |
| **NATIVE** | Minimal dependency (fmt only) | stderr + files + callbacks; `LOGGING_LOG_FATAL` still aborts |

```bash
cd Scripts
python3 setup.py config.build.ninja.clang                  # LOGURU (default)
python3 setup.py config.build.ninja.clang --logging=SPDLOG
python3 setup.py config.build.ninja.clang --logging=GLOG
python3 setup.py config.build.ninja.clang --logging=NATIVE
```

## Performance comparison

Backends are exclusive at compile time, so the comparison is four Release
binaries of the same `benchmark_logging_logger` target. Logging's tests and
benchmarks build in the standalone repo, not in XSigma — source:
`Testing/Cxx/BenchmarkLogger.cpp` in
[KhwarizmiAnalytix/Logging](https://github.com/KhwarizmiAnalytix/Logging).

```bash
git clone https://github.com/KhwarizmiAnalytix/Logging.git
cd Logging && cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --target benchmark_logging_logger
# binary: build/bin/benchmark_logging_logger
# then reconfigure with -DLOGGING_BACKEND=SPDLOG|GLOG|NATIVE (separate build dirs)
```

Run the binary **without** `--benchmark_min_time=0.01s` (that filter is only
for ctest). Suggested: `--benchmark_min_time=0.5s`.

### What is measured

| Benchmark | Meaning |
|-----------|---------|
| `DisabledInfo` | `VERBOSITY_OFF` + `LOGGING_LOG_INFO` — cost of the cutoff check (no emit) |
| `FileLiteral` | Enabled `INFO` to a temp file, literal string (stderr redirected to `/dev/null`) |
| `FileFormatted` | Enabled `INFO` to a temp file, two format arguments |
| `CallbackDiscard` | Enabled `INFO` to a no-op callback (not available on glog) |

### Results

Apple Silicon (14-core), Clang 22.1.2, Release, `--benchmark_min_time=0.5s`,
26 Aug 2026. Values are **CPU ns / log** (lower is better). Re-run locally
before treating this as a ranking on your hardware.

| Benchmark | SPDLOG | NATIVE | GLOG | LOGURU |
|-----------|--------|--------|------|--------|
| DisabledInfo (1 thread) | 1.22 | 0.94 | 1.04 | 1.15 |
| FileLiteral | **561** | 594 | 1006 | 2155 |
| FileFormatted | **622** | 712 | 1069 | 2267 |
| CallbackDiscard | **560** | 596 | n/a | 1017 |

**SPDLOG** is fastest on every enabled path (file and callback), which is why
it is the default. Disabled-path cost is ~1 ns for all backends because
`LOGGING_LOG` checks `get_current_verbosity_cutoff()` before formatting.
Glog has no callback sink; that row is skipped. Loguru pays extra for
preamble/scopes on the emit path.

## Logging levels

`logger_verbosity_enum`: `OFF`, `FATAL`, `ERROR`, `WARNING`, `INFO`, `TRACE`/`MAX`.
A message is emitted when its verbosity is less than or equal to the current cutoff
(`logger::get_current_verbosity_cutoff()`). Format arguments are not evaluated when
the level is disabled.

`LOGGING_LOG_FATAL` logs at `FATAL` and then calls `std::abort()`.

## Configuration

### Programmatic

```cpp
#include "logger/logger.h"

int main(int argc, char* argv[])
{
    logging::logger::set_enable_unsafe_signal_handler(false);  // optional
    logging::logger::init(argc, argv);  // parses -v <level>
    logging::logger::set_stderr_verbosity(logging::logger_verbosity_enum::VERBOSITY_INFO);
    logging::logger::set_thread_name("main");
    logging::logger::log_to_file(
        "/tmp/xsigma.log",
        logging::logger::file_mode::truncate,
        logging::logger_verbosity_enum::VERBOSITY_INFO);
}
```

### Environment

| Variable | Values | Effect |
|----------|--------|--------|
| `LOGGING_EXCEPTION_MODE` | `THROW` (default) or `LOG_FATAL` | `LOGGING_THROW` / `LOGGING_CHECK` either throw `logging::exception` or log FATAL and abort |

There is no YAML config file and no `XSIGMA_LOG_*` environment variables.

## Usage

```cpp
#include "logger/logger.h"
#include "util/exception.h"

LOGGING_LOG_INFO("Application started");
LOGGING_LOG_DEBUG(INFO, "debug only in non-NDEBUG builds");
LOGGING_LOG_WARNING("Low memory: {} MB remaining", free_mb);
LOGGING_LOG_ERROR("Failed to open file: {}", filename);

LOGGING_LOG_IF(ERROR, ptr == nullptr, "Pointer is null");

{
    LOGGING_LOG_SCOPE_FUNCTION(INFO);
    LOGGING_LOG_INFO("Inside function");
}

LOGGING_CHECK(x > 0, "x must be positive, got {}", x);
LOGGING_THROW("Invalid state: {}", state_name);
```

Consumers:

```cpp
// Memory
LOGGING_LOG_INFO("allocated {} bytes", n);

// Vectorization (host only)
VECTORIZATION_LOGF(INFO, "packet size {}", VECTORIZATION_PACKET_SIZE);
VECTORIZATION_CHECK(ok, "eval failed");
```

## Exception backtraces

`logging::exception` captures a stack trace unless
`logging::back_trace::set_stack_trace_on_error(0)` was called. Construction
does not log; the catcher decides whether to print `e.what()`.

## Related documentation

- [KhwarizmiAnalytix/Logging README](https://github.com/KhwarizmiAnalytix/Logging#readme) — CMake/Bazel flags
- [Setup Guide](setup.md) — configuring the backend during build
- [PROJECT_DEPENDENCIES.md](../PROJECT_DEPENDENCIES.md) — who links Logging
