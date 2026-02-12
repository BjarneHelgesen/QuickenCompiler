# QuickenCompiler
Replacements for compilers and other tools using Quicken for caching
* **QuickenCL** - Drop-in replacement for `cl.exe`.
* **QuickenClang** - Drop-in replacement for `clang.exe`. TDB
* **QuickenClangTidy** - Drop-in replacement for  `clang-tidy.exe`. TBD
* **QuickenMoc** - Drop-in replacement for QT `moc.exe`. TBD

The following is documentation for QuickenCL , as the oter tools are not made yet. 

# QuickenCL

QuickenCL is a wrapper script that accepts the exact same command-line arguments as `cl.exe` (MSVC compiler) and automatically routes them through Quicken for caching. This provides massive speedups for repeated compilations.

## Features

- Takes identical arguments to `cl.exe` (MSVC compiler)
- Automatically detects source files and output directories
- Transparent caching via Quicken
- Can be compiled to `QuickenCL.exe` using PyInstaller
- Drop-in replacement in build systems and makefiles

## Installation

### Prerequisites

- Python 3.7+
- [Quicken](../Quicken) library installed
- MSVC compiler (`cl.exe`) available in your system

### Setup

1. Clone this repository
2. Ensure Quicken is available (either installed via pip or located in sibling directory)
3. Create a `tools.json` configuration file (see Configuration section)

## Usage

### Command-line Usage

Use QuickenCL exactly like you would use `cl.exe`:

```bash
# Basic compilation
python QuickenCL.py /c /W4 myfile.cpp

# Multiple files
python QuickenCL.py /c /Foobj/ file1.cpp file2.cpp

# Source file at different position
python QuickenCL.py myfile.cpp /c /O2

# With output directory
python QuickenCL.py /c /Fooutput/ myfile.cpp
```

### Compilation to Executable

For easier integration, compile QuickenCL to a standalone executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Compile QuickenCL.py to executable
pyinstaller --onefile --name QuickenCL QuickenCL.py

# The executable will be in dist/QuickenCL.exe
# Copy it to your build directory or add to PATH
```

### Build System Integration

```bash
# In your build script, replace "cl" with path to QuickenCL
# Before: cl /c /W4 *.cpp
# After:  QuickenCL /c /W4 *.cpp

# Or set as environment variable
set CL=C:\path\to\QuickenCL.exe
```

## Configuration

QuickenCL requires a `tools.json` configuration file for Quicken. The file should be in the **installation directory** (the same directory as `QuickenCL.exe` or `QuickenCL.py`).

Example `tools.json`:

```json
{
  "cl": "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Tools\\MSVC\\14.39.33519\\bin\\Hostx64\\x64\\cl.exe",
  "vcvarsall": "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvarsall.bat",
  "msvc_arch": "x64"
}
```

## How It Works

1. **Argument Parsing**: QuickenCL parses `cl.exe` command-line arguments to extract:
   - Source files (`.cpp`, `.c`, `.cxx`, `.cc`, `.c++`)
   - Output directory (from `/Fo` flag)
   - Compiler arguments

2. **Quicken Integration**: For each source file:
   - Calls `quicken.run()` with the parsed arguments
   - Quicken checks cache for matching compilation
   - On cache hit: Returns cached output instantly
   - On cache miss: Runs actual compiler and caches result

3. **Exit Code**: Returns appropriate exit code for build system integration

## Implementation Details

- Parses cl.exe arguments to extract source files and compiler flags
- Detects output directory from `/Fo` flag if present
- Processes each source file through `quicken.run()`
- Returns appropriate exit codes for build system integration
- Supports all standard C/C++ file extensions

## Performance

**First compilation (cache miss):**
- Normal compilation time + ~200-300ms overhead

**Subsequent compilations (cache hit):**
- ~20-100ms total (50-200x faster!)

See [Quicken documentation](../Quicken/CLAUDE.md) for detailed performance characteristics.

## Testing

Run the test suite:

```bash
pytest test_quickencl.py -v
```

Tests cover:
- Basic compilation arguments
- Multiple source files
- Output directory detection (`/Fo` flag)
- Different file extensions
- Mixed argument order
- Quoted paths

## Limitations

- Requires `tools.json` configuration file
- Only works with MSVC `cl.exe` compiler
- Inherits all limitations from Quicken (see Quicken documentation)

# Contributing

This is a companion tool to Quicken. For issues or contributions, please coordinate with the main Quicken project.

# License

Same license as Quicken (to be determined).

---

*Part of the Quicken toolchain for C++ build acceleration*
