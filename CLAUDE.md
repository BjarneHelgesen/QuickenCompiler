  # QuickenCompiler
This project contains minimal python files that use Quicken and are proxies for a cached compiler or similar C++ tools. 

Example:
* QuickenCL.exe is a compiled version of Quicken.py, and is a drop-in replacement for cl.exe (Microsoft's compiler). All requests are forwarded to the Quicken library, which either returns the artifacts (e.g. the object file) from cache or forwards the request to Microsoft cl.exe. 

## Technical overview
* The Quicken tool will be installed before compiling and running Quicken. 
* The code for each tool in QuickenCompiler should be absolutely minimal. If possible, each tool should be reduced to a single line. 
* We will create QuickenCL.py, QuickenClang++.py, QuickenClang-tidy.py, QuickenMoc.py, and others. We will call these "compilers", even if some or them are not strictly in the category of compilers. 
* We will use PyInstaller or Nuitka to create .exe files (e.g. QuickenCL.exe) from the compiler python sources. E.g. "pyinstaller --onefile --name QuickenCL QuickenCL.py"
* The compilers will be put in the same folder and share any python run-time, etc. 
* Suggested parameters
  nuitka --standalone --onefile \
         --enable-plugin=numpy \
         --follow-imports \
         --prefer-source-code \
         compile_one_file.py

QuickenCL is a wrapper script that accepts the exact same command-line arguments as `cl.exe` (MSVC compiler) and automatically routes them through Quicken for caching. This provides massive speedups for repeated compilations.
### Setup

1. Clone this repository
2. Ensure Quicken is available (either installed via pip or located in sibling directory)
3. Create a `tools.json` configuration file (see Configuration section)

## Usage

### Command-line Usage

Use QuickenCL exactly like you would use `cl.exe`:



# The executable will be in dist/QuickenCL.exe
# Copy it to your build directory or add to PATH
```

## Configuration

QuickenCL requires a `tools.json` configuration file for Quicken. Documentation for the format is in the Quicken repo. 

## Testing
pytest is used for unit tests. 
