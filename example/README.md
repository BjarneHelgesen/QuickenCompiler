# QuickenCL CMake Example

Minimal example using QuickenCL.exe as a drop-in replacement for cl.exe.

## Usage

From a Visual Studio Developer Command Prompt:

```bash
cmake --preset quicken
cmake --build build
```

## Key CMake Settings

- `CMAKE_CXX_COMPILER`: Path to QuickenCL.exe
- `CMAKE_CXX_COMPILER_FORCED`: TRUE (skips compiler detection)
