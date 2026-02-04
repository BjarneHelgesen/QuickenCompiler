@echo off
REM Build script for QuickenCompiler - compiles Python files to .exe using Nuitka

echo Building QuickenCompiler executables...

REM Check if Nuitka is installed
pip show nuitka >nul 2>&1
if errorlevel 1 (
    echo Nuitka not found. Installing...
    pip install nuitka
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
    --output-dir=dist ^
    -o QuickenCL.exe ^
    QuickenCL.py

if errorlevel 1 (
    echo Build failed for QuickenCL.exe
    exit /b 1
)

echo.
echo Build complete! Executable is in dist\QuickenCL.dist\QuickenCL.exe
