#!/usr/bin/env python3
"""
Download Format.h from LLVM repository for a specific version.

This script downloads the Format.h file from the LLVM project repository
for a given major version number.
"""

import argparse
import requests
import sys
from pathlib import Path
from urllib.parse import urlparse


def download_format_h(version: str, output_path: str = None) -> str:
    """
    Download Format.h file from LLVM repository.
    
    Args:
        version: Major version number (e.g., "19", "18", "17")
        output_path: Optional path to save the file. If None, saves as Format.h
        
    Returns:
        Path to the downloaded file
        
    Raises:
        requests.RequestException: If download fails
        ValueError: If version format is invalid
    """
    # Validate version format
    try:
        major_version = int(version)
        if major_version < 10 or major_version > 20:
            print(f"Warning: Version {major_version} may not exist. Supported versions are typically 10-20.")
    except ValueError:
        raise ValueError(f"Invalid version format: {version}. Expected integer like '19'.")
    
    # Construct URL for the raw file
    base_url = "https://raw.githubusercontent.com/llvm/llvm-project"
    branch = f"release/{version}.x"
    file_path = "clang/include/clang/Format/Format.h"
    url = f"{base_url}/{branch}/{file_path}"
    
    print(f"Downloading Format.h for LLVM version {version}...")
    print(f"URL: {url}")
    
    try:
        # Download the file
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Determine output path
        if output_path is None:
            output_path = "Format.h"
        
        output_file = Path(output_path)
        
        # Write the content to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"✅ Successfully downloaded Format.h to {output_file}")
        print(f"   File size: {len(response.text):,} characters")
        
        return str(output_file)
        
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            print(f"❌ Error: Format.h not found for version {version}")
            print(f"   The branch 'release/{version}.x' may not exist.")
            print(f"   Available versions are typically: 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20")
        else:
            print(f"❌ HTTP Error {response.status_code}: {e}")
        sys.exit(1)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        sys.exit(1)
        
    except IOError as e:
        print(f"❌ File write error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Download Format.h from LLVM repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 19                    # Download LLVM 19.x Format.h
  %(prog)s 18 -o llvm18.h        # Download LLVM 18.x to custom file
  %(prog)s 17 --output Format-17.h
        """
    )
    
    parser.add_argument(
        "version",
        nargs='?',  # Make version optional
        help="LLVM major version number (e.g., 19, 18, 17)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: Format.h)"
    )
    
    parser.add_argument(
        "--list-versions",
        action="store_true",
        help="Show information about available versions"
    )
    
    args = parser.parse_args()
    
    if args.list_versions:
        print("LLVM Format.h versions typically available:")
        print("  LLVM 10.x: release/10.x branch")
        print("  LLVM 11.x: release/11.x branch") 
        print("  LLVM 12.x: release/12.x branch")
        print("  LLVM 13.x: release/13.x branch")
        print("  LLVM 14.x: release/14.x branch")
        print("  LLVM 15.x: release/15.x branch")
        print("  LLVM 16.x: release/16.x branch")
        print("  LLVM 17.x: release/17.x branch")
        print("  LLVM 18.x: release/18.x branch")
        print("  LLVM 19.x: release/19.x branch")
        print("  LLVM 20.x: release/20.x branch")
        print("\nNote: Version 21.x and higher are not yet available. Check LLVM repository for current branches.")
        return
    
    if not args.version:
        parser.error("version argument is required when not using --list-versions")
    
    try:
        downloaded_file = download_format_h(args.version, args.output)
        print(f"\n🎉 Format.h successfully downloaded: {downloaded_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
