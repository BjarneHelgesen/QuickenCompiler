# Using QuickenCL with CMake

This guide explains how to configure CMake to use QuickenCL.exe as a drop-in replacement for cl.exe.

## Prerequisites

- Visual Studio 2022 (or compatible MSVC toolchain)
- CMake 3.15 or later
- QuickenCL.exe built and available

## Method 1: CMake Presets (Recommended)

Create a `CMakePresets.json` file in your project root:

```json
{
    "version": 6,
    "configurePresets": [
        {
            "name": "quicken",
            "generator": "NMake Makefiles",
            "binaryDir": "${sourceDir}/build",
            "cacheVariables": {
                "CMAKE_CXX_COMPILER": "/path/to/QuickenCL.exe",
                "CMAKE_CXX_COMPILER_FORCED": "TRUE"
            }
        }
    ]
}
```

Then configure and build:

```bash
cmake --preset quicken
cmake --build build
```

## Method 2: Command-Line Arguments

Pass the compiler settings directly to CMake:

```bash
cmake -G "NMake Makefiles" ^
    -DCMAKE_CXX_COMPILER=/path/to/QuickenCL.exe ^
    -DCMAKE_CXX_COMPILER_FORCED=TRUE ^
    -B build

cmake --build build
```

## Method 3: Toolchain File

Create a `quicken-toolchain.cmake` file:

```cmake
# quicken-toolchain.cmake
set(CMAKE_CXX_COMPILER "/path/to/QuickenCL.exe")
set(CMAKE_CXX_COMPILER_FORCED TRUE)

# Optional: Set C compiler if using QuickenCL for C as well
# set(CMAKE_C_COMPILER "/path/to/QuickenCL.exe")
# set(CMAKE_C_COMPILER_FORCED TRUE)
```

Then configure with the toolchain file:

```bash
cmake -G "NMake Makefiles" -DCMAKE_TOOLCHAIN_FILE=quicken-toolchain.cmake -B build
cmake --build build
```

## Key Settings Explained

| Setting | Value | Purpose |
|---------|-------|---------|
| `CMAKE_CXX_COMPILER` | Path to QuickenCL.exe | Tells CMake to use QuickenCL instead of cl.exe |
| `CMAKE_CXX_COMPILER_FORCED` | `TRUE` | Skips CMake's compiler detection tests |
| Generator | `NMake Makefiles` | Uses NMake for building (works well with MSVC-style compilers) |

### Why CMAKE_CXX_COMPILER_FORCED?

CMake normally runs compiler detection tests when configuring a project. Since QuickenCL is a wrapper around cl.exe, these tests may behave unexpectedly. Setting `CMAKE_CXX_COMPILER_FORCED=TRUE` tells CMake to trust that the compiler works and skip detection.

## Example CMakeLists.txt

Your CMakeLists.txt requires no special modifications to work with QuickenCL:

```cmake
cmake_minimum_required(VERSION 3.15)
project(MyProject LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(myapp main.cpp)
```

## Running from Developer Command Prompt

QuickenCL requires the Visual Studio environment to locate cl.exe. Run CMake from a **Visual Studio Developer Command Prompt**, or initialize the environment first:

```batch
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cmake --preset quicken
cmake --build build
```

## Ninja Generator Alternative

You can also use Ninja instead of NMake for faster parallel builds:

```json
{
    "version": 6,
    "configurePresets": [
        {
            "name": "quicken-ninja",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build",
            "cacheVariables": {
                "CMAKE_CXX_COMPILER": "/path/to/QuickenCL.exe",
                "CMAKE_CXX_COMPILER_FORCED": "TRUE"
            }
        }
    ]
}
```

## Troubleshooting

### "cl.exe not found"
Run from a Visual Studio Developer Command Prompt or call vcvars64.bat first.

### CMake compiler detection fails
Ensure `CMAKE_CXX_COMPILER_FORCED=TRUE` is set.

### Build errors about missing headers
The Visual Studio environment must be initialized before running CMake.
