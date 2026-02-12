#!/usr/bin/env python3
"""
QuickenCL - Drop-in replacement for cl.exe with caching

This script takes the exact same parameters as cl.exe (MSVC compiler) and calls
Quicken to either return results from cache or forward the call to cl.exe.

Can be compiled to an .exe to act as a cl.exe replacement in build systems.

Usage:
    python QuickenCL.py [cl.exe arguments]
    QuickenCL.exe [cl.exe arguments]

Examples:
    QuickenCL.py /c /W4 myfile.cpp
    QuickenCL.py /c /Foobj/ file1.cpp file2.cpp
    QuickenCL.py myfile.cpp /c /O2
"""

import subprocess
import sys
from pathlib import Path
from quicken import Quicken


# Output path prefixes (argument attached directly, no space allowed)
OUTPUT_PREFIXES = (
    '/Fo', '-Fo', '/Fe', '-Fe', '/Fd', '-Fd', '/Fa', '-Fa',
    '/Fi', '-Fi', '/Fm', '-Fm', '/Fp', '-Fp', '/FR', '-FR',
    '/Fr', '-Fr', '/Ft', '-Ft', '/ifcOutput', '-ifcOutput'
)

# Input path prefixes that ALLOW space before argument
INPUT_PREFIXES_WITH_SPACE = ('/I', '-I', '/AI', '-AI', '/FI', '-FI', '/FU', '-FU')

# /external:I variants (space before path)
EXTERNAL_I_PREFIXES = ('/external:I', '-external:I')

# Source file extensions
SOURCE_EXTENSIONS = {'.cpp', '.cxx', '.cc', '.c', '.c++'}


def find_repo_path(start_path):
    """Find git repository root by walking up from start_path.

    Args:
        start_path: Path to start searching from (file or directory)

    Returns:
        Path to git root, or None if not found
    """
    p = Path(start_path).resolve()
    if p.is_file():
        p = p.parent
    for parent in [p] + list(p.parents):
        if (parent / '.git').exists():
            return parent
    return None


def find_input_file(args):
    """Find the first input file path from command-line arguments.

    Looks for arguments that are not flags (don't start with / - @)
    and exist as files on disk.

    Args:
        args: List of command-line arguments

    Returns:
        Path to first input file found, or None
    """
    for arg in args:
        if not arg.startswith('/') and not arg.startswith('-') and not arg.startswith('@'):
            p = Path(arg)
            if p.exists() and p.is_file():
                return p.resolve()
    return None


def parse_cl_arguments(args):
    """
    Parse cl.exe command-line arguments into categories for Quicken.

    Categories:
    - source_files: Files to compile (.cpp, .c, etc.)
    - tool_args: General compilation flags (part of cache key)
    - output_args: Output path arguments as PathArg tuples (NOT part of cache key)
    - input_args: Input path arguments as PathArg tuples (part of cache key)

    PathArg format: Tuple[str, str, Path] = (prefix, separator, path)
    - prefix: The option prefix (e.g., '/Fo', '/I')
    - separator: '' for attached args, ' ' for space-separated args
    - path: The path as a Path object

    Args:
        args: List of command-line arguments (excluding program name)

    Returns:
        Tuple of (source_files, tool_args, output_args, input_args)
    """
    source_files = []
    tool_args = []
    output_args = []  # List of (prefix, separator, Path) tuples
    input_args = []   # List of (prefix, separator, Path) tuples

    i = 0
    while i < len(args):
        arg = args[i]

        # Check if it's a source file by extension (not starting with / or - or @)
        if not arg.startswith('/') and not arg.startswith('-') and not arg.startswith('@'):
            path = Path(arg)
            if path.suffix.lower() in SOURCE_EXTENSIONS:
                source_files.append(path.resolve())
                i += 1
                continue

        # Check for output path prefixes (no space allowed)
        matched_output = False
        for prefix in OUTPUT_PREFIXES:
            if arg.startswith(prefix):
                path_part = arg[len(prefix):]
                if path_part:
                    # Use trailing slash as separator to indicate directory path
                    # This preserves the info that cl.exe should auto-name the output
                    if path_part.endswith('/') or path_part.endswith('\\'):
                        separator = path_part[-1]
                        output_args.append((prefix, separator, Path(path_part).resolve()))
                    else:
                        output_args.append((prefix, '', Path(path_part).resolve()))
                else:
                    # No path provided - pass through to cl.exe (error condition)
                    tool_args.append(arg)
                matched_output = True
                break
        if matched_output:
            i += 1
            continue

        # Check for input path prefixes (space allowed)
        matched_input = False
        for prefix in INPUT_PREFIXES_WITH_SPACE:
            if arg == prefix:
                # Bare prefix, next arg is the path
                if i + 1 < len(args):
                    i += 1
                    input_args.append((prefix, ' ', Path(args[i]).resolve()))
                matched_input = True
                break
            if arg.startswith(prefix) and len(arg) > len(prefix):
                # Prefix with attached argument
                path_part = arg[len(prefix):]
                input_args.append((prefix, '', Path(path_part).resolve()))
                matched_input = True
                break
        if matched_input:
            i += 1
            continue

        # Check for /external:I (space before path)
        for prefix in EXTERNAL_I_PREFIXES:
            if arg == prefix:
                if i + 1 < len(args):
                    i += 1
                    input_args.append((prefix, ' ', Path(args[i]).resolve()))
                matched_input = True
                break
            if arg.startswith(prefix) and len(arg) > len(prefix):
                path_part = arg[len(prefix):]
                input_args.append((prefix, '', Path(path_part).resolve()))
                matched_input = True
                break
        if matched_input:
            i += 1
            continue

        # Check for response file (@file) - treat as input dependency
        if arg.startswith('@'):
            response_file = arg[1:]
            input_args.append(('@', '', Path(response_file).resolve()))
            i += 1
            continue

        # Everything else goes to tool_args
        tool_args.append(arg)
        i += 1

    return source_files, tool_args, output_args, input_args


def has_language_override(args):
    """Check if args contain /Tc or /Tp (per-file language override).

    These options embed the filename in the argument itself, which is
    incompatible with Quicken's API that passes the file separately.
    Commands with these options bypass Quicken for compatibility.
    """
    for arg in args:
        if arg.startswith('/Tc') or arg.startswith('-Tc'):
            if len(arg) > 3:  # Has attached filename
                return True
        if arg.startswith('/Tp') or arg.startswith('-Tp'):
            if len(arg) > 3:  # Has attached filename
                return True
    return False


def run_cl_directly(args):
    """Run cl.exe directly without Quicken caching.

    Used for commands that are incompatible with Quicken's API.
    """
    from quicken._cmd_tool import CmdTool
    from quicken._msvc import MsvcEnv

    tool_path = CmdTool._get_config()['cl']
    env = MsvcEnv.get()

    cmd = [tool_path] + args
    result = subprocess.run(cmd, env=env, capture_output=False)
    return result.returncode


def get_fo_path(output_args):
    """Extract /Fo path information from output_args.

    Args:
        output_args: List of PathArg tuples (prefix, separator, path)

    Returns:
        Tuple of (fo_path, is_directory, fo_index)
        - fo_path: The Path object (None if not found)
        - is_directory: True if separator indicates directory (/ or \\)
        - fo_index: Index in output_args (-1 if not found)
    """
    for idx, (prefix, separator, path) in enumerate(output_args):
        if prefix in ('/Fo', '-Fo'):
            # separator of '/' or '\\' indicates directory path
            is_dir = separator in ('/', '\\')
            return path, is_dir, idx
    return None, False, -1


def main():
    """Main entry point for QuickenCL."""
    args = sys.argv[1:]

    if not args:
        # Pass through to cl.exe for version info (needed by CMake detection)
        returncode = run_cl_directly(args)
        sys.exit(returncode)

    # Check for /Tc or /Tp - these require direct cl.exe invocation
    # because they embed the filename in the argument itself
    if has_language_override(args):
        returncode = run_cl_directly(args)
        sys.exit(returncode)

    # Parse arguments into categories
    source_files, tool_args, output_args, input_args = parse_cl_arguments(args)

    if not source_files:
        # No source files found - might be /help, link-only, or error
        # Pass through to cl.exe directly
        returncode = run_cl_directly(args)
        sys.exit(returncode)

    try:
        # Find git repo from input file path, fall back to CWD
        input_file = find_input_file(args)
        repo_dir = find_repo_path(input_file) if input_file else None
        if repo_dir is None:
            repo_dir = Path.cwd()
        quicken = Quicken(repo_dir)

        # Get /Fo information for handling the edge case:
        # If /Fo specifies a specific filename (not directory) and there are
        # multiple source files, cl.exe only uses that filename for the first file.
        fo_value, fo_is_directory, fo_index = get_fo_path(output_args)

        overall_returncode = 0
        all_stdout = []
        all_stderr = []

        for file_idx, source_file in enumerate(source_files):
            # Handle /Fo edge cases
            current_output_args = output_args.copy()
            if fo_value is not None and fo_index >= 0:
                if fo_is_directory:
                    # /Fo specifies a directory - compute actual output filename
                    # e.g., /Fo{dir}/ + source.cpp -> /Fo{dir}/source.obj
                    obj_name = source_file.stem + '.obj'
                    actual_path = fo_value / obj_name
                    prefix, _, _ = output_args[fo_index]
                    current_output_args[fo_index] = (prefix, '', actual_path)
                elif file_idx > 0:
                    # /Fo specifies a specific file - only first source uses it
                    current_output_args.pop(fo_index)

            # Create tool and execute
            tool = quicken.cl(tool_args, current_output_args, input_args)
            stdout, stderr, returncode = tool(source_file)

            if stdout:
                all_stdout.append(stdout)
            if stderr:
                all_stderr.append(stderr)

            if returncode != 0:
                overall_returncode = returncode

        # Output collected stdout/stderr
        if all_stdout:
            sys.stdout.write('\n'.join(all_stdout))
            if not all_stdout[-1].endswith('\n'):
                sys.stdout.write('\n')
        if all_stderr:
            sys.stderr.write('\n'.join(all_stderr))
            if not all_stderr[-1].endswith('\n'):
                sys.stderr.write('\n')

        sys.exit(overall_returncode)

    except Exception as e:
        print(f"QuickenCL: Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
