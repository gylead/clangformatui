#!/usr/bin/env python3
"""
Parse FormatStyle struct from LLVM Format.h file.

This script reads a Format.h file and extracts the FormatStyle struct definition,
tracking comments and nested structures/enums.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import re


class FormatStyleParser:
    """Parser for extracting FormatStyle struct from Format.h."""
    
    def __init__(self, filename: str, quiet: bool = False):
        self.filename = filename
        self.comments: List[str] = []
        self.brace_count = 0
        self.parsing = False
        self.line_number = 0
        self.quiet = quiet
        self.entries: List[Dict[str, Any]] = []
        self.known_types: set = set()  # Track enum/struct types defined in FormatStyle
        self.enum_definitions: Dict[str, List[Dict[str, str]]] = {}  # Store enum values and descriptions
        self.current_enum_name: Optional[str] = None  # Track current enum being parsed
        self.parsing_enum: bool = False  # Flag to indicate we're inside an enum
        
    def parse(self) -> dict:
        """
        Parse the Format.h file and extract FormatStyle struct.
        
        Returns:
            Dictionary containing parsing results
        """
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except IOError as e:
            print(f"❌ Error reading file {self.filename}: {e}")
            sys.exit(1)
        
        print(f"📖 Reading file: {self.filename}")
        print(f"   Total lines: {len(lines):,}")
        
        for line_num, line in enumerate(lines, 1):
            self.line_number = line_num
            
            if not self.parsing:
                # Look for the start of FormatStyle struct
                if self._is_format_style_start(line):
                    print(f"🔍 Found FormatStyle struct at line {line_num}")
                    self.parsing = True
                    self.brace_count = 1  # Start with 1 to account for the opening brace
                    continue
            else:
                # We're inside FormatStyle struct
                if self._process_line(line):
                    # End of struct reached
                    break
        
        if not self.parsing:
            print("❌ FormatStyle struct not found in file")
            return {"success": False, "error": "FormatStyle struct not found"}
        
        print(f"✅ Parsing completed at line {self.line_number}")
        print(f"   Entries found: {len(self.entries)}")
        print(f"   Known types: {len(self.known_types)}")
        print(f"   Enum definitions: {len(self.enum_definitions)}")
        if self.enum_definitions and not self.quiet:
            total_enum_values = sum(len(values) for values in self.enum_definitions.values())
            print(f"   Total enum values: {total_enum_values}")
        
        return {
            "success": True,
            "start_line": self._find_start_line(),
            "end_line": self.line_number,
            "entries": self.entries,
            "known_types": list(self.known_types),
            "enum_definitions": self.enum_definitions,
            "total_lines_parsed": self.line_number - self._find_start_line() + 1
        }
    
    def _is_format_style_start(self, line: str) -> bool:
        """Check if line contains the start of FormatStyle struct."""
        stripped = line.strip()
        return stripped == "struct FormatStyle {"
    
    def _process_line(self, line: str) -> bool:
        """
        Process a line inside FormatStyle struct.
        
        Returns:
            True if end of struct is reached, False otherwise
        """
        stripped = line.strip()
        
        # Handle comments
        if stripped.startswith("///"):
            comment_text = stripped[3:]  # Remove "///" prefix
            # Strip exactly one space if it exists
            if comment_text.startswith(" "):
                comment_text = comment_text[1:]
            self.comments.append(comment_text)
            if not self.quiet:
                print(f"💬 Comment at line {self.line_number}: {comment_text}")
            return False
        
        # Skip empty lines and regular comments
        if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
            return False
        
        # Check for enum or struct definitions (to track types and skip processing)
        if self._is_enum_or_struct_definition(stripped):
            type_name = self._extract_type_name(stripped)
            if type_name:
                self.known_types.add(type_name)
                if not self.quiet:
                    print(f"📝 Found type definition: {type_name} at line {self.line_number}")
                
                # If it's an enum, start parsing enum values
                if stripped.startswith("enum "):
                    self.current_enum_name = type_name
                    self.parsing_enum = True
                    self.enum_definitions[type_name] = []
                    if not self.quiet:
                        print(f"🔍 Starting enum parsing: {type_name}")
            # We'll count braces but not process fields inside nested structures
        
        # Process enum values if we're inside an enum
        elif self.parsing_enum and self.brace_count >= 2:  # Inside enum body
            enum_value = self._extract_enum_value(stripped)
            if enum_value and self.current_enum_name:
                # Create enum value entry with collected comments
                value_entry = {
                    "name": enum_value,
                    "description": "\n".join(self.comments) if self.comments else "",
                    "line": self.line_number
                }
                self.enum_definitions[self.current_enum_name].append(value_entry)
                if not self.quiet:
                    print(f"🔍 Enum value found: {enum_value} in {self.current_enum_name} at line {self.line_number}")
                
                # Clear comments after creating entry
                self.comments.clear()
        
        # Process field definitions (only at the top level of FormatStyle)
        elif self.brace_count == 1:  # Only process at FormatStyle level
            field_info = self._extract_field_definition(stripped)
            if field_info:
                # Create entry with collected comments
                entry = {
                    "type": field_info["type"],
                    "name": field_info["name"],
                    "description": "\n".join(self.comments) if self.comments else "",
                    "line": self.line_number
                }
                self.entries.append(entry)
                if not self.quiet:
                    print(f"🔍 Field found: {field_info['type']} {field_info['name']} at line {self.line_number}")
                
                # Clear comments after creating entry
                self.comments.clear()
        
        # Count opening braces for nested structures
        opening_braces = line.count("{")
        if opening_braces > 0:
            if stripped.startswith("enum") or stripped.startswith("struct"):
                # Found nested enum or struct
                self.brace_count += opening_braces
                if not self.quiet:
                    print(f"🏗️  Nested structure at line {self.line_number}, brace count: {self.brace_count}")
            else:
                # Regular opening braces (could be functions, initializers, etc.)
                self.brace_count += opening_braces
                if opening_braces > 0 and not self.quiet:
                    print(f"🔧 Opening brace(s) at line {self.line_number}, brace count: {self.brace_count}")
        
        # Count closing braces
        closing_braces = line.count("}")
        if closing_braces > 0:
            self.brace_count -= closing_braces
            if not self.quiet:
                print(f"🔚 Closing brace(s) at line {self.line_number}, brace count: {self.brace_count}")
            
            # Check if we've finished parsing an enum
            if self.parsing_enum and self.brace_count == 1:
                self.parsing_enum = False
                if not self.quiet and self.current_enum_name:
                    enum_values_count = len(self.enum_definitions.get(self.current_enum_name, []))
                    print(f"✅ Finished parsing enum {self.current_enum_name} with {enum_values_count} values")
                self.current_enum_name = None
            
            # Check if we've exited the FormatStyle struct
            # When brace_count reaches 0, we've closed the main FormatStyle struct
            if self.brace_count == 0:
                if not self.quiet:
                    print(f"🎯 End of FormatStyle struct reached at line {self.line_number}")
                return True
        
        return False
    
    def _is_enum_or_struct_definition(self, line: str) -> bool:
        """Check if line starts an enum or struct definition."""
        return line.startswith("enum ") or line.startswith("struct ")
    
    def _extract_type_name(self, line: str) -> Optional[str]:
        """Extract the type name from enum or struct definition."""
        # Match: enum TypeName or struct TypeName
        match = re.match(r'(?:enum|struct)\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_enum_value(self, line: str) -> Optional[str]:
        """Extract enum value name from an enum value definition line."""
        # Skip lines that are not enum values
        if (line.startswith("enum ") or line.startswith("struct ") or 
            line.startswith("public:") or line.startswith("private:") or
            line.startswith("protected:") or line.startswith("//") or
            line.startswith("/*") or line.startswith("*") or
            "{" in line or "}" in line or
            line.startswith("#") or line.startswith("typedef") or
            not line.strip()):
            return None
        
        # Clean up the line - remove trailing comma, semicolon and extra whitespace
        cleaned = line.rstrip(",;").strip()
        if not cleaned:
            return None
        
        # Handle enum values with explicit values (e.g., "Value = 0")
        if "=" in cleaned:
            enum_name = cleaned.split("=")[0].strip()
        else:
            enum_name = cleaned
        
        # Validate enum name (should be a valid identifier)
        if enum_name and enum_name.replace("_", "").replace(":", "").isalnum():
            return enum_name
        
        return None
    
    def _extract_field_definition(self, line: str) -> Optional[Dict[str, str]]:
        """Extract field type and name from a field definition line."""
        # Skip lines that are clearly not field definitions
        if (line.startswith("enum ") or line.startswith("struct ") or 
            line.startswith("public:") or line.startswith("private:") or
            line.startswith("protected:") or line.startswith("//") or
            line.startswith("/*") or line.startswith("*") or
            "{" in line or "}" in line or
            line.startswith("#") or line.startswith("typedef")):
            return None
        
        # Clean up the line - remove trailing semicolon and extra whitespace
        cleaned = line.rstrip(";").strip()
        if not cleaned:
            return None
        
        # Skip InheritsParentConfig - it's not a real config setting
        if "InheritsParentConfig" in cleaned:
            return None
        
        # Try to match different field patterns
        patterns = [
            # Standard patterns: type name
            r'^(bool)\s+(\w+)(?:\s*=.*)?$',
            r'^(int|unsigned)\s+(\w+)(?:\s*=.*)?$',
            r'^(std::string)\s+(\w+)(?:\s*=.*)?$',
            r'^(std::vector<[^>]+>)\s+(\w+)(?:\s*=.*)?$',
            r'^(std::optional<[^>]+>)\s+(\w+)(?:\s*=.*)?$',
            # Custom type patterns (enum/struct names we've seen)
            r'^(\w+)\s+(\w+)(?:\s*=.*)?$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, cleaned)
            if match:
                field_type = match.group(1)
                field_name = match.group(2)
                
                # For custom types, verify it's a known type or basic type
                if field_type not in ["bool", "int", "unsigned", "std::string"] and not field_type.startswith("std::"):
                    if field_type not in self.known_types:
                        # Check if it looks like a type name (PascalCase or ends with common suffixes)
                        if not (field_type[0].isupper() or field_type.endswith(("Style", "Kind", "Type", "Mode", "Alignment"))):
                            continue
                
                return {
                    "type": field_type,
                    "name": field_name
                }
        
        return None
    
    def _find_start_line(self) -> int:
        """Find the line number where FormatStyle struct starts."""
        # This is a simplified approach - in a real implementation,
        # we'd track this during parsing
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if self._is_format_style_start(line):
                        return line_num
        except IOError:
            pass
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Parse FormatStyle struct from LLVM Format.h file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Parse default Format.h
  %(prog)s Format-19.h          # Parse specific file
  %(prog)s /path/to/Format.h    # Parse file with full path
        """
    )
    
    parser.add_argument(
        "filename",
        nargs="?",
        default="Format.h",
        help="Path to Format.h file to parse (default: Format.h)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output (only show summary)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file for field definitions (default: format_style_fields.json)"
    )
    
    args = parser.parse_args()
    
    # Validate file exists
    file_path = Path(args.filename)
    if not file_path.exists():
        print(f"❌ Error: File '{args.filename}' not found")
        print(f"   Current directory: {Path.cwd()}")
        if args.filename == "Format.h":
            print("   Hint: Download Format.h first using download_format_h.py")
        sys.exit(1)
    
    print(f"🚀 Starting FormatStyle parser")
    print(f"   File: {file_path.absolute()}")
    print(f"   Size: {file_path.stat().st_size:,} bytes")
    print()
    
    # Parse the file
    parser_instance = FormatStyleParser(args.filename, quiet=args.quiet)
    result = parser_instance.parse()
    
    if result["success"]:
        print("\n📊 Parsing Summary:")
        print(f"   Start line: {result['start_line']}")
        print(f"   End line: {result['end_line']}")
        print(f"   Lines parsed: {result['total_lines_parsed']}")
        print(f"   Field entries found: {len(result['entries'])}")
        print(f"   Known types discovered: {len(result['known_types'])}")
        print(f"   Enum definitions found: {len(result['enum_definitions'])}")
        if result['enum_definitions']:
            total_enum_values = sum(len(values) for values in result['enum_definitions'].values())
            print(f"   Total enum values: {total_enum_values}")
        
        # Save to JSON file
        output_file = args.output or "format_style_fields.json"
        try:
            output_data = {
                "metadata": {
                    "source_file": args.filename,
                    "start_line": result['start_line'],
                    "end_line": result['end_line'],
                    "total_lines_parsed": result['total_lines_parsed'],
                    "parsing_date": "2025-07-13",
                    "parser_version": "1.0"
                },
                "known_types": sorted(result['known_types']),
                "enum_definitions": result['enum_definitions'],
                "fields": result['entries']
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Field definitions saved to: {output_file}")
            
        except IOError as e:
            print(f"\n❌ Error saving JSON file: {e}")
        
        if args.verbose and result["entries"]:
            print("\n📋 Field entries found:")
            for i, entry in enumerate(result["entries"], 1):
                desc_preview = entry["description"][:50] + "..." if len(entry["description"]) > 50 else entry["description"]
                print(f"   {i:3d}. {entry['type']} {entry['name']} - {desc_preview}")
        
        print(f"\n✅ Successfully parsed FormatStyle struct from {args.filename}")
    else:
        print(f"\n❌ Failed to parse: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
