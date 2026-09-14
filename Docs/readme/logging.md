# XSigma Logging System

## Overview

Logging is consumed as a pure third-party dependency: the `ThirdParty/Logging`
submodule from
[KhwarizmiAnalytix/Logging](https://github.com/KhwarizmiAnalytix/Logging)
(CMake target `Logging::Logging`, Bazel `@logging//:Logging`). The public
C++ namespace is `logging`. Include:

```cpp
#include <logging/logging.h>
#include <logging/logger/logger.h>
#include <logging/util/exception.h>
```

Memory, Vectorization, and Core **always** link `Logging::Logging`. There is
no `MEMORY_HAS_LOGGING` / `VECTORIZATION_HAS_LOGGING` opt-out: Memory calls
`LOGGING_LOG_*` / `LOGGING_CHECK` directly, and `VECTORIZATION_LOGF` /
`VECTORIZATION_CHECK` / `VECTORIZATION_THROW` forward to the Logging macros.

The library is **host/CPU only**. Do not call these macros from `__device__` code.

XSigma compiles Logging product sources only. Work on Logging itself in the
standalone Logging repository.

## Logging levels

`logger_verbosity_enum`: `OFF`, `FATAL`, `ERROR`, `WARNING`, `INFO`, `TRACE`/`MAX`.
A message is emitted when its verbosity is less than or equal to the current cutoff
(`logger::get_current_verbosity_cutoff()`). Format arguments are not evaluated when
the level is disabled.

`LOGGING_LOG_FATAL` logs at `FATAL` and then calls `std::abort()`.

## Configuration

### Programmatic

```cpp
#include <logging/logging.h>

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
#include <logging/logging.h>

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

- [KhwarizmiAnalytix/Logging README](https://github.com/KhwarizmiAnalytix/Logging#readme)
- [Setup Guide](setup.md)
- [PROJECT_DEPENDENCIES.md](../PROJECT_DEPENDENCIES.md) — who links Logging
