#!/usr/bin/env python3
"""
Tests for QuickenCL argument parsing
"""

import pytest
from pathlib import Path
from QuickenCL import parse_cl_arguments, get_fo_path, has_language_override

# Helper to get absolute path for test comparisons
CWD = Path.cwd()


def abs_path(p):
    """Convert a relative path string to absolute Path."""
    return (CWD / p).resolve()


def abs_str(p):
    """Convert a relative path string to absolute path string."""
    return str(abs_path(p))


class TestParseClArguments:
    """Tests for parse_cl_arguments function."""

    def test_parse_basic_compilation(self):
        """Test basic compilation: cl /c file.cpp"""
        args = ["/c", "test.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        assert source_files[0] == abs_path("test.cpp")
        assert "/c" in tool_args
        assert len(output_args) == 0
        assert len(input_args) == 0

    def test_parse_multiple_files(self):
        """Test multiple files: cl /c file1.cpp file2.cpp"""
        args = ["/c", "file1.cpp", "file2.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 2
        assert source_files[0] == abs_path("file1.cpp")
        assert source_files[1] == abs_path("file2.cpp")
        assert "/c" in tool_args

    def test_parse_output_directory(self):
        """Test output directory: cl /c /Foobj/ file.cpp"""
        args = ["/c", "/Foobj/", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        assert source_files[0] == abs_path("file.cpp")
        assert "/Fo" + abs_str("obj/") in output_args
        assert "/Foobj/" not in tool_args

    def test_parse_output_directory_backslash(self):
        """Test output directory with backslash: cl /c /Foobj\\ file.cpp"""
        args = ["/c", "/Foobj\\", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        assert "/Fo" + abs_str("obj\\") in output_args

    def test_parse_output_file(self):
        """Test output file: cl /c /Fooutput/file.obj file.cpp"""
        args = ["/c", "/Fooutput/file.obj", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        assert "/Fo" + abs_str("output/file.obj") in output_args

    def test_parse_complex_arguments(self):
        """Test complex arguments: cl /c /W4 /O2 /EHsc file.cpp"""
        args = ["/c", "/W4", "/O2", "/EHsc", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        assert "/W4" in tool_args
        assert "/O2" in tool_args
        assert "/EHsc" in tool_args

    def test_parse_file_at_beginning(self):
        """Test file at beginning: cl file.cpp /c /W4"""
        args = ["file.cpp", "/c", "/W4"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        assert source_files[0] == abs_path("file.cpp")

    def test_parse_different_extensions(self):
        """Test different C/C++ extensions"""
        test_cases = [
            (["test.cpp"], ".cpp"),
            (["test.cxx"], ".cxx"),
            (["test.cc"], ".cc"),
            (["test.c"], ".c"),
            (["test.c++"], ".c++"),
        ]

        for args, expected_ext in test_cases:
            source_files, _, _, _ = parse_cl_arguments(args)
            assert len(source_files) == 1
            assert source_files[0].suffix.lower() == expected_ext

    def test_parse_quoted_output_directory(self):
        """Test quoted output directory: cl /c /Fo"output dir/" file.cpp"""
        # Note: In real usage, shell would strip quotes. This tests that quotes in
        # the path string are preserved when converting to absolute.
        args = ["/c", '/Fo"output dir/"', "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        # The path portion (including quotes) is converted to absolute
        assert len(output_args) == 1
        assert output_args[0].startswith('/Fo')

    def test_parse_no_source_files(self):
        """Test no source files: cl /help"""
        args = ["/help"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 0
        assert "/help" in tool_args

    def test_parse_mixed_order(self):
        """Test mixed order: cl /W4 file1.cpp /O2 file2.cpp /c"""
        args = ["/W4", "file1.cpp", "/O2", "file2.cpp", "/c"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 2
        assert source_files[0] == abs_path("file1.cpp")
        assert source_files[1] == abs_path("file2.cpp")
        assert "/W4" in tool_args
        assert "/O2" in tool_args
        assert "/c" in tool_args


class TestOutputArgsParsing:
    """Tests for output argument categorization."""

    def test_fo_to_output_args(self):
        """Test /Fo goes to output_args"""
        args = ["/c", "/Fooutput.obj", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/Fo" + abs_str("output.obj") in output_args
        assert "/Fooutput.obj" not in tool_args

    def test_fe_to_output_args(self):
        """Test /Fe goes to output_args"""
        args = ["/Feprogram.exe", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/Fe" + abs_str("program.exe") in output_args

    def test_fd_to_output_args(self):
        """Test /Fd goes to output_args"""
        args = ["/c", "/Zi", "/Fddebug.pdb", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/Fd" + abs_str("debug.pdb") in output_args
        assert "/Zi" in tool_args

    def test_fa_to_output_args(self):
        """Test /Fa goes to output_args, but /FA (flag) goes to tool_args"""
        args = ["/c", "/FAcs", "/Falisting.asm", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        # /FAcs is a flag (assembly listing format: c=machine code, s=source)
        assert "/FAcs" in tool_args
        # /Fa<file> specifies the output filename
        assert "/Fa" + abs_str("listing.asm") in output_args

    def test_fp_to_output_args(self):
        """Test /Fp (precompiled header file) goes to output_args"""
        args = ["/c", "/Yustdafx.h", "/Fpprecomp.pch", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/Fp" + abs_str("precomp.pch") in output_args
        assert "/Yustdafx.h" in tool_args

    def test_multiple_output_args(self):
        """Test multiple output path arguments"""
        args = ["/c", "/Foobj/", "/Fdpdb/", "/Zi", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/Fo" + abs_str("obj/") in output_args
        assert "/Fd" + abs_str("pdb/") in output_args
        assert "/Zi" in tool_args
        assert len(output_args) == 2

    def test_dash_prefix_output_args(self):
        """Test output args with dash prefix"""
        args = ["/c", "-Fooutput.obj", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "-Fo" + abs_str("output.obj") in output_args


class TestInputArgsParsing:
    """Tests for input argument categorization."""

    def test_include_path_attached(self):
        """Test /I with attached path goes to input_args"""
        args = ["/c", "/Iinclude/", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/I" + abs_str("include/") in input_args
        assert "/Iinclude/" not in tool_args

    def test_include_path_with_space(self):
        """Test /I with space before path"""
        args = ["/c", "/I", "include/", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/I" in input_args
        assert abs_str("include/") in input_args

    def test_multiple_include_paths(self):
        """Test multiple /I arguments"""
        args = ["/c", "/Iinclude1/", "/I", "include2/", "/Iinclude3/", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/I" + abs_str("include1/") in input_args
        assert "/I" in input_args
        assert abs_str("include2/") in input_args
        assert "/I" + abs_str("include3/") in input_args

    def test_force_include(self):
        """Test /FI (force include) goes to input_args"""
        args = ["/c", "/FIstdafx.h", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/FI" + abs_str("stdafx.h") in input_args

    def test_force_include_with_space(self):
        """Test /FI with space"""
        args = ["/c", "/FI", "stdafx.h", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/FI" in input_args
        assert abs_str("stdafx.h") in input_args

    def test_response_file(self):
        """Test @file (response file) goes to input_args"""
        args = ["/c", "@response.rsp", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "@" + abs_str("response.rsp") in input_args

    def test_external_include(self):
        """Test /external:I goes to input_args"""
        args = ["/c", "/external:I", "external/", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/external:I" in input_args
        assert abs_str("external/") in input_args

    def test_ai_using_path(self):
        """Test /AI (#using path) goes to input_args"""
        args = ["/c", "/clr", "/AIassemblies/", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/AI" + abs_str("assemblies/") in input_args
        assert "/clr" in tool_args

    def test_fu_force_using(self):
        """Test /FU (force #using) goes to input_args"""
        args = ["/c", "/clr", "/FUmscorlib.dll", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/FU" + abs_str("mscorlib.dll") in input_args


class TestGetFoPath:
    """Tests for get_fo_path function."""

    def test_fo_directory(self):
        """Test /Fo with directory (ends with /)"""
        output_args = ["/Foobj/"]
        fo_value, is_dir, fo_index = get_fo_path(output_args)

        assert fo_value == "obj/"
        assert is_dir is True
        assert fo_index == 0

    def test_fo_directory_backslash(self):
        """Test /Fo with directory (ends with \\)"""
        output_args = ["/Foobj\\"]
        fo_value, is_dir, fo_index = get_fo_path(output_args)

        assert fo_value == "obj\\"
        assert is_dir is True
        assert fo_index == 0

    def test_fo_file(self):
        """Test /Fo with specific file"""
        output_args = ["/Fooutput.obj"]
        fo_value, is_dir, fo_index = get_fo_path(output_args)

        assert fo_value == "output.obj"
        assert is_dir is False
        assert fo_index == 0

    def test_fo_colon_syntax(self):
        """Test /Fo:path colon syntax"""
        output_args = ["/Fo:output.obj"]
        fo_value, is_dir, fo_index = get_fo_path(output_args)

        assert fo_value == "output.obj"
        assert is_dir is False

    def test_fo_quoted(self):
        """Test /Fo with quoted path"""
        output_args = ['/Fo"output dir/"']
        fo_value, is_dir, fo_index = get_fo_path(output_args)

        assert fo_value == "output dir/"
        assert is_dir is True

    def test_fo_not_found(self):
        """Test when /Fo is not present"""
        output_args = ["/Feprogram.exe"]
        fo_value, is_dir, fo_index = get_fo_path(output_args)

        assert fo_value is None
        assert is_dir is False
        assert fo_index == -1

    def test_fo_among_other_args(self):
        """Test /Fo among other output args"""
        output_args = ["/Fdpdb/", "/Foobj/", "/Feprogram.exe"]
        fo_value, is_dir, fo_index = get_fo_path(output_args)

        assert fo_value == "obj/"
        assert is_dir is True
        assert fo_index == 1

    def test_dash_prefix(self):
        """Test with dash prefix"""
        output_args = ["-Foobj/"]
        fo_value, is_dir, fo_index = get_fo_path(output_args)

        assert fo_value == "obj/"
        assert is_dir is True


class TestHasLanguageOverride:
    """Tests for has_language_override function."""

    def test_no_language_override(self):
        """Test command without /Tc or /Tp"""
        args = ["/c", "/W4", "file.cpp"]
        assert has_language_override(args) is False

    def test_tc_with_file(self):
        """Test /Tc with attached filename"""
        args = ["/c", "/Tcfile.txt"]
        assert has_language_override(args) is True

    def test_tp_with_file(self):
        """Test /Tp with attached filename"""
        args = ["/c", "/Tpfile.c"]
        assert has_language_override(args) is True

    def test_tc_bare(self):
        """Test bare /Tc (invalid, but shouldn't trigger)"""
        args = ["/c", "/Tc"]
        assert has_language_override(args) is False

    def test_tp_bare(self):
        """Test bare /Tp (invalid, but shouldn't trigger)"""
        args = ["/c", "/Tp"]
        assert has_language_override(args) is False

    def test_tc_global_flag(self):
        """Test /TC (global flag, different from /Tc)"""
        args = ["/c", "/TC", "file.cpp"]
        assert has_language_override(args) is False

    def test_tp_global_flag(self):
        """Test /TP (global flag, different from /Tp)"""
        args = ["/c", "/TP", "file.c"]
        assert has_language_override(args) is False

    def test_dash_prefix(self):
        """Test with dash prefix"""
        args = ["/c", "-Tcfile.txt"]
        assert has_language_override(args) is True


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_args(self):
        """Test empty argument list"""
        args = []
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 0
        assert len(tool_args) == 0
        assert len(output_args) == 0
        assert len(input_args) == 0

    def test_only_flags(self):
        """Test only flags, no source files"""
        args = ["/c", "/W4", "/O2"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 0
        assert "/c" in tool_args
        assert "/W4" in tool_args
        assert "/O2" in tool_args

    def test_uppercase_extension(self):
        """Test uppercase file extension"""
        args = ["/c", "FILE.CPP"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        assert source_files[0] == abs_path("FILE.CPP")

    def test_define_macro(self):
        """Test /D (define macro) goes to tool_args"""
        args = ["/c", "/DDEBUG", "/DVERSION=2", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/DDEBUG" in tool_args
        assert "/DVERSION=2" in tool_args

    def test_std_version(self):
        """Test /std: goes to tool_args"""
        args = ["/c", "/std:c++17", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/std:c++17" in tool_args

    def test_precompiled_header_flags(self):
        """Test PCH flags go to tool_args"""
        args = ["/c", "/Yustdafx.h", "/Ycstdafx.h", "file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert "/Yustdafx.h" in tool_args
        assert "/Ycstdafx.h" in tool_args

    def test_path_with_dots(self):
        """Test source file path with dots is resolved to absolute"""
        args = ["/c", "../src/file.cpp"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        # Path is resolved to absolute, eliminating the ..
        assert source_files[0].is_absolute()
        assert "src" in str(source_files[0])
        assert str(source_files[0]).endswith("file.cpp")

    def test_non_source_file(self):
        """Test non-source file is not picked up"""
        args = ["/c", "file.cpp", "resource.rc", "file.obj"]
        source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

        assert len(source_files) == 1
        assert source_files[0] == abs_path("file.cpp")
        # Non-source files go to tool_args as they might be linker inputs
        assert "resource.rc" in tool_args
        assert "file.obj" in tool_args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
