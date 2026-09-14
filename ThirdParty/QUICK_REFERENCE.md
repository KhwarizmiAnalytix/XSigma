# Enhanced add_third_party_library() - Quick Reference

## TL;DR

```cmake
add_third_party_library(library_name
    [CONDITION variable]
    [LIBRARY_TYPE STATIC|SHARED|DEFAULT]
    [FILTER_FLAGS flag1 flag2 ...]
    [ALIASES alias1 alias2 ...]
)
```

## Common Patterns

### Basic
```cmake
add_third_party_library(fmt)
```

### With Condition
```cmake
add_third_party_library(mimalloc
    CONDITION MEMORY_ENABLE_MIMALLOC
    LIBRARY_TYPE STATIC
)
```

### Filter Exception Flags
```cmake
add_third_party_library(lib_needs_exceptions
    FILTER_FLAGS "-fno-exceptions"
)
```

### Filter Warning Flags
```cmake
add_third_party_library(legacy_lib
    FILTER_FLAGS "-Werror" "-Wall" "-Wextra"
)
```

### With Aliases
```cmake
add_third_party_library(fmt
    ALIASES "fmt::fmt"
)
```

### Complete Example
```cmake
add_third_party_library(mimalloc
    CONDITION MEMORY_ENABLE_MIMALLOC
    LIBRARY_TYPE STATIC
    LIBRARY_TYPE_VAR MI_BUILD_STATIC
    FILTER_FLAGS "-fno-exceptions" "-Werror"
    ALIASES "mimalloc::mimalloc"
)
```

## Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `name` | Required | Library name | - |
| `CONDITION` | Optional | CMake variable to check | - |
| `LIBRARY_TYPE` | Optional | STATIC/SHARED/DEFAULT | `XSIGMA_THIRDPARTY_TYPE` |
| `LIBRARY_TYPE_VAR` | Optional | Library-specific variable | - |
| `FILTER_FLAGS` | Optional | Flags to remove | - |
| `ALIASES` | Optional | Alias names to create | - |
| `AUTO_FOLDER` | Optional | Auto-set FOLDER property | `ON` |
| `EXTERNAL_NAME` | Optional | Name for find_package | `name` |

## What It Does Automatically

✅ Checks condition (early return if not met)  
✅ Checks for duplicates  
✅ Tries external package (if enabled)  
✅ Saves compiler/linker flags  
✅ Filters specified flags  
✅ Configures library type  
✅ Builds library  
✅ Sets FOLDER properties for all targets  
✅ Creates aliases  
✅ Restores all flags  

## Flags That Can Be Filtered

### Exception Handling
- `-fno-exceptions`
- `-fno-rtti`

### Warnings
- `-Werror`
- `-Wall`
- `-Wextra`
- `-pedantic`
- `-pedantic-errors`

### MSVC Warnings
- `/WX`
- `/W4`
- `/Wall`

### Optimization
- `-O3`
- `-march=native`
- `-mtune=native`

### Sanitizers
- `-fsanitize=address`
- `-fsanitize=undefined`
- `-fsanitize=thread`

### LTO
- `-flto`
- `-flto=thin`

## Before vs After

### Before Enhancement
```cmake
# 25+ lines of boilerplate
set(_saved_cxx_flags ${CMAKE_CXX_FLAGS})
set(_saved_build_shared_libs ${BUILD_SHARED_LIBS})
string(REPLACE "-fno-exceptions" "" CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
set(BUILD_SHARED_LIBS OFF)

if(XSIGMA_ENABLE_MY_LIB)
    add_third_party_library(my_lib)
    
    if(TARGET my_lib)
        set_target_properties(my_lib PROPERTIES FOLDER "ThirdParty/my_lib")
    endif()
    if(TARGET my_lib_internal)
        set_target_properties(my_lib_internal PROPERTIES FOLDER "ThirdParty/my_lib")
    endif()
endif()

set(BUILD_SHARED_LIBS ${_saved_build_shared_libs})
set(CMAKE_CXX_FLAGS ${_saved_cxx_flags})
```

### After Enhancement
```cmake
# 5 lines, clean and declarative
add_third_party_library(my_lib
    CONDITION XSIGMA_ENABLE_MY_LIB
    LIBRARY_TYPE STATIC
    FILTER_FLAGS "-fno-exceptions"
)
```

## Benefits

| Benefit | Impact |
|---------|--------|
| Code Reduction | ~70% less boilerplate |
| Maintainability | Centralized logic |
| Reliability | No forgotten cleanup |
| Readability | Self-documenting |
| IDE Support | Auto FOLDER organization |

## Common Use Cases

### 1. Library Needs Exceptions
```cmake
add_third_party_library(lib
    FILTER_FLAGS "-fno-exceptions"
)
```

### 2. Library Has Warnings
```cmake
add_third_party_library(lib
    FILTER_FLAGS "-Werror"
)
```

### 3. Conditional Library
```cmake
add_third_party_library(lib
    CONDITION XSIGMA_ENABLE_LIB
)
```

### 4. Force Static
```cmake
add_third_party_library(lib
    LIBRARY_TYPE STATIC
)
```

### 5. Create Namespace Alias
```cmake
add_third_party_library(lib
    ALIASES "lib::lib"
)
```

## Troubleshooting

### Targets Not Getting FOLDER Property
```cmake
# Disable auto-folder and set manually
add_third_party_library(lib
    AUTO_FOLDER OFF
)
if(TARGET special_target)
    set_target_properties(special_target PROPERTIES FOLDER "Custom/Path")
endif()
```

### Flag Filtering Not Working
Check which variables contain the flags:
- `CMAKE_CXX_FLAGS`
- `CMAKE_C_FLAGS`
- `CMAKE_EXE_LINKER_FLAGS`
- `CMAKE_SHARED_LINKER_FLAGS`
- `CMAKE_MODULE_LINKER_FLAGS`
- `CMAKE_STATIC_LINKER_FLAGS`

### Alias Already Exists
The function handles this gracefully - it will skip creating duplicate aliases.

## See Also

- [Full Documentation](README_ENHANCED_LIBRARY_MANAGEMENT.md)
- [Examples](../Docs/examples/EnhancedThirdPartyLibraryExamples.cmake)
- [Library Type Configuration](README_LIBRARY_TYPE.md)

