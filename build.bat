@echo off
REM Build script for QuickenCompiler - compiles Python files to .exe using Nuitka

REM Read version from VERSION file
set /p VERSION=<VERSION
echo Building QuickenCompiler v%VERSION%...

REM Check if Nuitka is installed
pip show nuitka >nul 2>&1
if errorlevel 1 (
    echo Nuitka not found. Installing...
    pip install nuitka
)

REM Clean previous build
if exist dist\QuickenCL.dist (
    echo Cleaning previous build...
    rmdir /s /q dist\QuickenCL.dist
)
if exist dist\QuickenCL.build (
    rmdir /s /q dist\QuickenCL.build
)
if exist dist\QuickenCleanup.dist (
    rmdir /s /q dist\QuickenCleanup.dist
)
if exist dist\QuickenCleanup.build (
    rmdir /s /q dist\QuickenCleanup.build
)
if exist dist\QuickenToolsConfig.dist (
    rmdir /s /q dist\QuickenToolsConfig.dist
)
if exist dist\QuickenToolsConfig.build (
    rmdir /s /q dist\QuickenToolsConfig.build
)

REM Create dist directory if it doesn't exist
if not exist dist mkdir dist

REM Build QuickenCL.exe
echo Building QuickenCL.exe...
python -m nuitka ^
    --standalone ^
    --lto=yes ^
    --python-flag=no_site ^
    --python-flag=no_docstrings ^
    --follow-imports ^
    --prefer-source-code ^
    --noinclude-pytest-mode=nofollow ^
    --noinclude-setuptools-mode=nofollow ^
    --no-deployment-flag=self-execution ^
    --output-dir=dist ^
    --product-name=QuickenCL ^
    --product-version=%VERSION% ^
    --file-description="Quicken Compiler Cache Wrapper" ^
    --copyright="QuickenCompiler Project" ^
    -o QuickenCL.exe ^
    QuickenCL.py

if errorlevel 1 (
    echo Build failed for QuickenCL.exe
    exit /b 1
)

REM Build QuickenCleanup.exe
echo Building QuickenCleanup.exe...
python -m nuitka ^
    --standalone ^
    --lto=yes ^
    --python-flag=no_site ^
    --python-flag=no_docstrings ^
    --follow-imports ^
    --prefer-source-code ^
    --noinclude-pytest-mode=nofollow ^
    --noinclude-setuptools-mode=nofollow ^
    --no-deployment-flag=self-execution ^
    --output-dir=dist ^
    --product-name=QuickenCleanup ^
    --product-version=%VERSION% ^
    --file-description="Quicken Cache Cleanup Tool" ^
    --copyright="QuickenCompiler Project" ^
    -o QuickenCleanup.exe ^
    QuickenCleanup.py

if errorlevel 1 (
    echo Build failed for QuickenCleanup.exe
    exit /b 1
)

REM Build QuickenToolsConfig.exe
echo Building QuickenToolsConfig.exe...
python -m nuitka ^
    --standalone ^
    --lto=yes ^
    --python-flag=no_site ^
    --python-flag=no_docstrings ^
    --follow-imports ^
    --prefer-source-code ^
    --noinclude-pytest-mode=nofollow ^
    --noinclude-setuptools-mode=nofollow ^
    --no-deployment-flag=self-execution ^
    --output-dir=dist ^
    --product-name=QuickenToolsConfig ^
    --product-version=%VERSION% ^
    --file-description="Quicken Visual Studio Auto-Setup" ^
    --copyright="QuickenCompiler Project" ^
    -o QuickenToolsConfig.exe ^
    QuickenToolsConfig.py

if errorlevel 1 (
    echo Build failed for QuickenToolsConfig.exe
    exit /b 1
)

REM Copy QuickenCleanup.exe into the shared QuickenCL distribution folder
echo Copying QuickenCleanup.exe into shared distribution...
copy /Y dist\QuickenCleanup.dist\QuickenCleanup.exe dist\QuickenCL.dist\QuickenCleanup.exe >nul

REM Copy QuickenToolsConfig.exe into the shared QuickenCL distribution folder
echo Copying QuickenToolsConfig.exe into shared distribution...
copy /Y dist\QuickenToolsConfig.dist\QuickenToolsConfig.exe dist\QuickenCL.dist\QuickenToolsConfig.exe >nul

echo.
echo Build complete! Executables are in dist\QuickenCL.dist\

REM Test with CMake example project
echo.
echo Testing CMake integration...

REM Set up MSVC environment
echo Setting up MSVC environment...
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul
if errorlevel 1 (
    echo Failed to set up MSVC environment!
    exit /b 1
)

REM Clean example build directory
if exist example\build (
    echo Cleaning example build directory...
    rmdir /s /q example\build
)

REM Configure with CMake
echo Configuring example project...
cmake --preset quicken -S example
if errorlevel 1 (
    echo CMake configure failed!
    exit /b 1
)

REM Build
echo Building example project...
cmake --build example\build
if errorlevel 1 (
    echo CMake build failed!
    exit /b 1
)

REM Run and verify output
echo Running example...
example\build\hello.exe > example\build\output.txt
if errorlevel 1 (
    echo Example executable failed!
    exit /b 1
)

findstr /C:"Hello from QuickenCL!" example\build\output.txt >nul
if errorlevel 1 (
    echo Unexpected output from example executable!
    type example\build\output.txt
    exit /b 1
)

echo.
echo CMake integration test passed!

REM Build installer if Inno Setup is available
where iscc >nul 2>&1
if errorlevel 1 (
    echo.
    echo Inno Setup not found - skipping installer creation.
    echo To create installer, install Inno Setup and ensure iscc.exe is in PATH.
) else (
    echo.
    echo Creating installer...
    iscc setup.iss
    if errorlevel 1 (
        echo Failed to create installer
        exit /b 1
    )
    echo Installer created: QuickenCL_Setup.exe (v%VERSION%)
)
