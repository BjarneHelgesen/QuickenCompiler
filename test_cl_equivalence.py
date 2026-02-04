#!/usr/bin/env python3
"""
Integration tests verifying QuickenCL produces equivalent results to cl.exe.

These tests compile actual C++ code using both cl.exe directly and QuickenCL,
then compare the results (return codes, generated object files).
"""

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Get the QuickenCL.py path
QUICKENCL_PATH = Path(__file__).parent / "QuickenCL.py"


def get_cl_path():
    """Get the path to cl.exe from Quicken config or environment."""
    try:
        from quicken._cmd_tool import CmdTool
        return CmdTool._get_config()['cl']
    except Exception:
        # Fallback: assume cl.exe is in PATH
        return "cl.exe"


def get_msvc_env():
    """Get the MSVC environment variables."""
    try:
        from quicken._msvc import MsvcEnv
        return MsvcEnv.get()
    except Exception:
        # Fallback: use current environment
        return os.environ.copy()


def file_hash(filepath):
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def strip_obj_timestamps(obj_path):
    """
    Read object file content, excluding timestamp sections.

    COFF object files contain timestamps that differ between compilations.
    This function returns content suitable for comparison.
    """
    with open(obj_path, 'rb') as f:
        content = f.read()
    # For basic comparison, we'll check file size and key sections
    # Full binary comparison would require parsing COFF format
    return len(content)


class TestClEquivalence:
    """Tests verifying QuickenCL produces equivalent results to cl.exe."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for test files."""
        return tmp_path

    @pytest.fixture
    def simple_cpp(self, temp_dir):
        """Create a simple C++ source file."""
        source = temp_dir / "simple.cpp"
        source.write_text("""\
int add(int a, int b) {
    return a + b;
}
""")
        return source

    @pytest.fixture
    def hello_cpp(self, temp_dir):
        """Create a hello world C++ source file."""
        source = temp_dir / "hello.cpp"
        source.write_text("""\
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
""")
        return source

    @pytest.fixture
    def multi_func_cpp(self, temp_dir):
        """Create a C++ file with multiple functions."""
        source = temp_dir / "multi.cpp"
        source.write_text("""\
int multiply(int a, int b) {
    return a * b;
}

int divide(int a, int b) {
    if (b == 0) return 0;
    return a / b;
}

double average(int a, int b) {
    return (a + b) / 2.0;
}
""")
        return source

    @pytest.fixture
    def syntax_error_cpp(self, temp_dir):
        """Create a C++ file with a syntax error."""
        source = temp_dir / "error.cpp"
        source.write_text("""\
int broken( {
    return
}
""")
        return source

    def run_cl(self, args, cwd=None):
        """Run cl.exe directly with given arguments."""
        cl_path = get_cl_path()
        env = get_msvc_env()
        cmd = [cl_path] + args
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr

    def run_quickencl(self, args, cwd=None):
        """Run QuickenCL.py with given arguments."""
        env = get_msvc_env()
        cmd = [sys.executable, str(QUICKENCL_PATH)] + args
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr

    def test_compile_simple_file(self, temp_dir, simple_cpp):
        """Test compiling a simple C++ file produces same result."""
        cl_obj = temp_dir / "cl_simple.obj"
        qcl_obj = temp_dir / "qcl_simple.obj"

        # Compile with cl.exe
        cl_ret, cl_stdout, cl_stderr = self.run_cl(
            ["/c", "/nologo", f"/Fo{cl_obj}", str(simple_cpp)],
            cwd=temp_dir
        )

        # Compile with QuickenCL
        qcl_ret, qcl_stdout, qcl_stderr = self.run_quickencl(
            ["/c", "/nologo", f"/Fo{qcl_obj}", str(simple_cpp)],
            cwd=temp_dir
        )

        # Both should succeed
        assert cl_ret == 0, f"cl.exe failed: {cl_stderr}"
        assert qcl_ret == 0, f"QuickenCL failed: {qcl_stderr}"

        # Both should produce object files
        assert cl_obj.exists(), "cl.exe did not produce object file"
        assert qcl_obj.exists(), "QuickenCL did not produce object file"

        # Object files should be similar in size (timestamps differ)
        cl_size = strip_obj_timestamps(cl_obj)
        qcl_size = strip_obj_timestamps(qcl_obj)
        # Allow some variance due to timestamps and debug info
        assert abs(cl_size - qcl_size) < 100, \
            f"Object file sizes differ significantly: cl={cl_size}, qcl={qcl_size}"

    def test_compile_with_optimization(self, temp_dir, simple_cpp):
        """Test compiling with optimization flags."""
        cl_obj = temp_dir / "cl_opt.obj"
        qcl_obj = temp_dir / "qcl_opt.obj"

        args_base = ["/c", "/nologo", "/O2", "/W4"]

        cl_ret, _, cl_stderr = self.run_cl(
            args_base + [f"/Fo{cl_obj}", str(simple_cpp)],
            cwd=temp_dir
        )
        qcl_ret, _, qcl_stderr = self.run_quickencl(
            args_base + [f"/Fo{qcl_obj}", str(simple_cpp)],
            cwd=temp_dir
        )

        assert cl_ret == 0, f"cl.exe failed: {cl_stderr}"
        assert qcl_ret == 0, f"QuickenCL failed: {qcl_stderr}"
        assert cl_obj.exists()
        assert qcl_obj.exists()

    def test_compile_with_debug_info(self, temp_dir, simple_cpp):
        """Test compiling with debug information."""
        cl_obj = temp_dir / "cl_debug.obj"
        qcl_obj = temp_dir / "qcl_debug.obj"

        args_base = ["/c", "/nologo", "/Zi", "/Od"]

        cl_ret, _, cl_stderr = self.run_cl(
            args_base + [f"/Fo{cl_obj}", str(simple_cpp)],
            cwd=temp_dir
        )
        qcl_ret, _, qcl_stderr = self.run_quickencl(
            args_base + [f"/Fo{qcl_obj}", str(simple_cpp)],
            cwd=temp_dir
        )

        assert cl_ret == 0, f"cl.exe failed: {cl_stderr}"
        assert qcl_ret == 0, f"QuickenCL failed: {qcl_stderr}"
        assert cl_obj.exists()
        assert qcl_obj.exists()

    def test_compile_with_warnings(self, temp_dir, multi_func_cpp):
        """Test that warning levels produce same behavior."""
        cl_obj = temp_dir / "cl_warn.obj"
        qcl_obj = temp_dir / "qcl_warn.obj"

        args_base = ["/c", "/nologo", "/W4"]

        cl_ret, _, _ = self.run_cl(
            args_base + [f"/Fo{cl_obj}", str(multi_func_cpp)],
            cwd=temp_dir
        )
        qcl_ret, _, _ = self.run_quickencl(
            args_base + [f"/Fo{qcl_obj}", str(multi_func_cpp)],
            cwd=temp_dir
        )

        # Return codes should match
        assert cl_ret == qcl_ret, \
            f"Return codes differ: cl={cl_ret}, qcl={qcl_ret}"

    def test_syntax_error_same_return_code(self, temp_dir, syntax_error_cpp):
        """Test that syntax errors produce same return code."""
        cl_obj = temp_dir / "cl_error.obj"
        qcl_obj = temp_dir / "qcl_error.obj"

        cl_ret, _, _ = self.run_cl(
            ["/c", "/nologo", f"/Fo{cl_obj}", str(syntax_error_cpp)],
            cwd=temp_dir
        )
        qcl_ret, _, _ = self.run_quickencl(
            ["/c", "/nologo", f"/Fo{qcl_obj}", str(syntax_error_cpp)],
            cwd=temp_dir
        )

        # Both should fail
        assert cl_ret != 0, "cl.exe should fail on syntax error"
        assert qcl_ret != 0, "QuickenCL should fail on syntax error"

        # Neither should produce object file
        assert not cl_obj.exists()
        assert not qcl_obj.exists()

    def test_compile_cpp17(self, temp_dir):
        """Test compiling with C++17 standard."""
        source = temp_dir / "cpp17.cpp"
        source.write_text("""\
#include <optional>
#include <string_view>

std::optional<int> maybe_int(bool cond) {
    if (cond) return 42;
    return std::nullopt;
}
""")

        cl_obj = temp_dir / "cl_cpp17.obj"
        qcl_obj = temp_dir / "qcl_cpp17.obj"

        args_base = ["/c", "/nologo", "/std:c++17", "/EHsc"]

        cl_ret, _, cl_stderr = self.run_cl(
            args_base + [f"/Fo{cl_obj}", str(source)],
            cwd=temp_dir
        )
        qcl_ret, _, qcl_stderr = self.run_quickencl(
            args_base + [f"/Fo{qcl_obj}", str(source)],
            cwd=temp_dir
        )

        assert cl_ret == 0, f"cl.exe failed: {cl_stderr}"
        assert qcl_ret == 0, f"QuickenCL failed: {qcl_stderr}"

    def test_compile_with_include_path(self, temp_dir, simple_cpp):
        """Test compiling with include paths."""
        # Create an include directory with a header
        inc_dir = temp_dir / "include"
        inc_dir.mkdir()
        header = inc_dir / "myheader.h"
        header.write_text("#define MY_VALUE 42\n")

        source = temp_dir / "with_include.cpp"
        source.write_text("""\
#include "myheader.h"

int get_value() {
    return MY_VALUE;
}
""")

        cl_obj = temp_dir / "cl_inc.obj"
        qcl_obj = temp_dir / "qcl_inc.obj"

        args_base = ["/c", "/nologo", f"/I{inc_dir}"]

        cl_ret, _, cl_stderr = self.run_cl(
            args_base + [f"/Fo{cl_obj}", str(source)],
            cwd=temp_dir
        )
        qcl_ret, _, qcl_stderr = self.run_quickencl(
            args_base + [f"/Fo{qcl_obj}", str(source)],
            cwd=temp_dir
        )

        assert cl_ret == 0, f"cl.exe failed: {cl_stderr}"
        assert qcl_ret == 0, f"QuickenCL failed: {qcl_stderr}"
        assert cl_obj.exists()
        assert qcl_obj.exists()

    def test_compile_with_defines(self, temp_dir):
        """Test compiling with preprocessor defines."""
        source = temp_dir / "defines.cpp"
        source.write_text("""\
#ifndef MY_DEFINE
#error "MY_DEFINE not defined"
#endif

#if MY_VALUE != 100
#error "MY_VALUE incorrect"
#endif

int get_defined_value() {
    return MY_VALUE;
}
""")

        cl_obj = temp_dir / "cl_def.obj"
        qcl_obj = temp_dir / "qcl_def.obj"

        args_base = ["/c", "/nologo", "/DMY_DEFINE", "/DMY_VALUE=100"]

        cl_ret, _, cl_stderr = self.run_cl(
            args_base + [f"/Fo{cl_obj}", str(source)],
            cwd=temp_dir
        )
        qcl_ret, _, qcl_stderr = self.run_quickencl(
            args_base + [f"/Fo{qcl_obj}", str(source)],
            cwd=temp_dir
        )

        assert cl_ret == 0, f"cl.exe failed: {cl_stderr}"
        assert qcl_ret == 0, f"QuickenCL failed: {qcl_stderr}"

    def test_output_to_directory(self, temp_dir, simple_cpp):
        """Test output to directory with /Fo<dir>/."""
        obj_dir = temp_dir / "obj"
        obj_dir.mkdir()

        cl_ret, _, cl_stderr = self.run_cl(
            ["/c", "/nologo", f"/Fo{obj_dir}/", str(simple_cpp)],
            cwd=temp_dir
        )

        # Clean up cl output for QuickenCL test
        cl_obj = obj_dir / "simple.obj"
        if cl_obj.exists():
            cl_obj.unlink()

        qcl_ret, _, qcl_stderr = self.run_quickencl(
            ["/c", "/nologo", f"/Fo{obj_dir}/", str(simple_cpp)],
            cwd=temp_dir
        )

        assert cl_ret == 0, f"cl.exe failed: {cl_stderr}"
        assert qcl_ret == 0, f"QuickenCL failed: {qcl_stderr}"

        # QuickenCL should produce file in the directory
        qcl_obj = obj_dir / "simple.obj"
        assert qcl_obj.exists(), "QuickenCL did not produce object file in directory"


class TestClEquivalenceMultipleFiles:
    """Tests for compiling multiple files."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        return tmp_path

    def run_cl(self, args, cwd=None):
        cl_path = get_cl_path()
        env = get_msvc_env()
        result = subprocess.run(
            [cl_path] + args,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr

    def run_quickencl(self, args, cwd=None):
        env = get_msvc_env()
        result = subprocess.run(
            [sys.executable, str(QUICKENCL_PATH)] + args,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr

    def test_compile_multiple_files(self, temp_dir):
        """Test compiling multiple source files."""
        # Create multiple source files
        file1 = temp_dir / "file1.cpp"
        file1.write_text("int func1() { return 1; }\n")

        file2 = temp_dir / "file2.cpp"
        file2.write_text("int func2() { return 2; }\n")

        obj_dir = temp_dir / "obj"
        obj_dir.mkdir()

        # Compile with cl.exe
        cl_ret, _, cl_stderr = self.run_cl(
            ["/c", "/nologo", f"/Fo{obj_dir}/", str(file1), str(file2)],
            cwd=temp_dir
        )

        cl_obj1 = obj_dir / "file1.obj"
        cl_obj2 = obj_dir / "file2.obj"

        assert cl_ret == 0, f"cl.exe failed: {cl_stderr}"
        assert cl_obj1.exists(), "cl.exe did not produce file1.obj"
        assert cl_obj2.exists(), "cl.exe did not produce file2.obj"

        # Clean up for QuickenCL
        cl_obj1.unlink()
        cl_obj2.unlink()

        # Compile with QuickenCL
        qcl_ret, _, qcl_stderr = self.run_quickencl(
            ["/c", "/nologo", f"/Fo{obj_dir}/", str(file1), str(file2)],
            cwd=temp_dir
        )

        assert qcl_ret == 0, f"QuickenCL failed: {qcl_stderr}"
        assert cl_obj1.exists(), "QuickenCL did not produce file1.obj"
        assert cl_obj2.exists(), "QuickenCL did not produce file2.obj"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
