#!/usr/bin/env python3
"""
Script to format all C/C++ files in a directory using clang-format.

This script recursively finds all .c, .cpp, .cxx, .cc, .c++, and .h files
in the specified directory and formats them using clang-format.

The script assumes there is a valid .clang-format file in the target directory
or any of its parent directories.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def find_cpp_files(directory):
    """Find all C/C++ source and header files in the directory recursively."""
    extensions = {'.c', '.cpp', '.cxx', '.cc', '.c++', '.h', '.hpp', '.hxx', '.hh', '.h++'}
    cpp_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in extensions:
                cpp_files.append(os.path.join(root, file))
    
    return sorted(cpp_files)


def check_clang_format_executable(clang_format_path):
    """Check if the clang-format executable is available and working."""
    try:
        result = subprocess.run([clang_format_path, '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"Using clang-format: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def format_file(file_path, clang_format_path, dry_run=False):
    """Format a single file using clang-format."""
    try:
        if dry_run:
            # Just check if the file would be changed
            result = subprocess.run([clang_format_path, '--dry-run', '--Werror', file_path],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Would format: {file_path}")
            return result.returncode == 0
        else:
            # Format the file in-place
            result = subprocess.run([clang_format_path, '-i', file_path],
                                  capture_output=True, text=True, check=True)
            print(f"Formatted: {file_path}")
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error formatting {file_path}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Format all C/C++ files in a directory using clang-format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project
  %(prog)s /path/to/project --clang-format /usr/bin/clang-format-15
  %(prog)s /path/to/project --dry-run
  %(prog)s . --verbose
        """
    )
    
    parser.add_argument('directory', 
                       help='Directory to format (searches recursively)')
    
    parser.add_argument('--clang-format', 
                       default='clang-format',
                       help='Path to clang-format executable (default: clang-format from PATH)')
    
    parser.add_argument('--dry-run', 
                       action='store_true',
                       help='Show which files would be formatted without actually formatting them')
    
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Show verbose output')
    
    args = parser.parse_args()
    
    # Validate directory
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a valid directory", file=sys.stderr)
        sys.exit(1)
    
    # Check clang-format executable
    if not check_clang_format_executable(args.clang_format):
        print(f"Error: clang-format executable '{args.clang_format}' not found or not working", 
              file=sys.stderr)
        print("Make sure clang-format is installed and in your PATH, or specify a valid path with --clang-format", 
              file=sys.stderr)
        sys.exit(1)
    
    # Find all C/C++ files
    cpp_files = find_cpp_files(args.directory)
    
    if not cpp_files:
        print(f"No C/C++ files found in '{args.directory}'")
        return
    
    if args.verbose:
        print(f"Found {len(cpp_files)} C/C++ files:")
        for file in cpp_files:
            print(f"  {file}")
        print()
    
    if args.dry_run:
        print(f"Dry run mode - checking {len(cpp_files)} files...")
    else:
        print(f"Formatting {len(cpp_files)} files...")
    
    # Format files
    formatted_count = 0
    error_count = 0
    
    for file_path in cpp_files:
        if format_file(file_path, args.clang_format, args.dry_run):
            if not args.dry_run:
                formatted_count += 1
        else:
            if args.dry_run:
                formatted_count += 1  # Would be formatted
            else:
                error_count += 1
    
    # Summary
    print()
    if args.dry_run:
        if formatted_count > 0:
            print(f"Summary: {formatted_count} files would be formatted")
        else:
            print("Summary: All files are already properly formatted")
    else:
        print(f"Summary: {formatted_count} files formatted successfully", end="")
        if error_count > 0:
            print(f", {error_count} errors")
        else:
            print()
    
    if error_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
