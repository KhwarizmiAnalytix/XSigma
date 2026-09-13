# Profiler

Implementation lives in [KhwarizmiAnalytix/Profiler](https://github.com/KhwarizmiAnalytix/Profiler),
vendored as the git submodule [`ThirdParty/Profiler`](../../ThirdParty/Profiler).

CMake `add_subdirectory`s that third party and exports `Profiler::Profiler`.
Bazel label `//Library/Profiler:Profiler` is an alias of `@profiler//:Profiler`.
