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


def to_absolute(path_str):
    """Convert a path string to an absolute path string."""
    return str(Path(path_str).resolve())


def parse_cl_arguments(args):
    """
    Parse cl.exe command-line arguments into categories for Quicken.

    Categories:
    - source_files: Files to compile (.cpp, .c, etc.)
    - tool_args: General compilation flags (part of cache key)
    - output_args: Output path arguments (NOT part of cache key)
    - input_args: Input path arguments (part of cache key)

    Args:
        args: List of command-line arguments (excluding program name)

    Returns:
        Tuple of (source_files, tool_args, output_args, input_args)
    """
    source_files = []
    tool_args = []
    output_args = []
    input_args = []

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
                    output_args.append(prefix + to_absolute(path_part))
                else:
                    output_args.append(arg)
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
                input_args.append(arg)
                if i + 1 < len(args):
                    i += 1
                    input_args.append(to_absolute(args[i]))
                matched_input = True
                break
            if arg.startswith(prefix) and len(arg) > len(prefix):
                # Prefix with attached argument
                path_part = arg[len(prefix):]
                input_args.append(prefix + to_absolute(path_part))
                matched_input = True
                break
        if matched_input:
            i += 1
            continue

        # Check for /external:I (space before path)
        for prefix in EXTERNAL_I_PREFIXES:
            if arg == prefix:
                input_args.append(arg)
                if i + 1 < len(args):
                    i += 1
                    input_args.append(to_absolute(args[i]))
                matched_input = True
                break
            if arg.startswith(prefix) and len(arg) > len(prefix):
                path_part = arg[len(prefix):]
                input_args.append(prefix + to_absolute(path_part))
                matched_input = True
                break
        if matched_input:
            i += 1
            continue

        # Check for response file (@file) - treat as input dependency
        if arg.startswith('@'):
            response_file = arg[1:]
            input_args.append('@' + to_absolute(response_file))
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

    Returns:
        Tuple of (fo_value, is_directory, fo_index)
        - fo_value: The path after /Fo (None if not found)
        - is_directory: True if path ends with / or \\ (directory, not file)
        - fo_index: Index in output_args (-1 if not found)
    """
    for idx, arg in enumerate(output_args):
        if arg.startswith('/Fo') or arg.startswith('-Fo'):
            fo_path = arg[3:]
            # Handle colon syntax /Fo:path (newer MSVC)
            if fo_path.startswith(':'):
                fo_path = fo_path[1:]
            # Remove quotes if present
            if fo_path.startswith('"') and fo_path.endswith('"'):
                fo_path = fo_path[1:-1]
            is_dir = fo_path.endswith('/') or fo_path.endswith('\\')
            return fo_path, is_dir, idx
    return None, False, -1


def main():
    """Main entry point for QuickenCL."""
    args = sys.argv[1:]

    if not args:
        print("QuickenCL - cl.exe replacement with caching", file=sys.stderr)
        print("Usage: QuickenCL [cl.exe arguments]", file=sys.stderr)
        sys.exit(1)

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
        # Initialize Quicken with current working directory as repo
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
            # Handle /Fo edge case: if /Fo specifies a file (not directory),
            # only the first source file uses it (cl.exe behavior)
            current_output_args = output_args.copy()
            if fo_value and not fo_is_directory and file_idx > 0 and fo_index >= 0:
                # Remove /Fo for subsequent files - they use default naming
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
