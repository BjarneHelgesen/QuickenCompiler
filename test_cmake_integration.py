import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_DIR = Path(__file__).parent
EXAMPLE_DIR = REPO_DIR / "example"
BUILD_DIR = EXAMPLE_DIR / "build"
TOOLS_JSON = REPO_DIR / "dist" / "QuickenCL.dist" / "tools.json"


def get_msvc_env():
    """Load MSVC environment by running vcvarsall.bat."""
    with open(TOOLS_JSON) as f:
        tools = json.load(f)

    vcvarsall = tools["vcvarsall"]
    arch = tools.get("msvc_arch", "x64")

    # Run vcvarsall and capture the resulting environment
    result = subprocess.run(
        f'"{vcvarsall}" {arch} && set',
        capture_output=True,
        text=True,
        shell=True,
    )
    assert result.returncode == 0, f"vcvarsall failed:\n{result.stderr}"

    env = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            env[key] = value
    return env


@pytest.fixture
def clean_build():
    """Clean build directory before test."""
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    yield


@pytest.fixture
def msvc_env():
    """Provide MSVC environment variables."""
    return get_msvc_env()


def test_cmake_integration(clean_build, msvc_env):
    """Test CMake integration using the example project."""
    # Configure with CMake preset
    result = subprocess.run(
        "cmake --preset quicken",
        cwd=EXAMPLE_DIR,
        capture_output=True,
        text=True,
        env=msvc_env,
        shell=True,
    )
    assert result.returncode == 0, f"CMake configure failed:\n{result.stdout}\n{result.stderr}"

    # Build
    result = subprocess.run(
        "cmake --build build",
        cwd=EXAMPLE_DIR,
        capture_output=True,
        text=True,
        env=msvc_env,
        shell=True,
    )
    assert result.returncode == 0, f"CMake build failed:\n{result.stdout}\n{result.stderr}"

    # Verify executable was created and runs
    hello_exe = BUILD_DIR / "hello.exe"
    assert hello_exe.exists(), f"Expected executable not found: {hello_exe}"

    result = subprocess.run([hello_exe], capture_output=True, text=True)
    assert result.returncode == 0, f"Executable failed:\n{result.stderr}"
    assert "Hello from QuickenCL!" in result.stdout, f"Unexpected output:\n{result.stdout}"
