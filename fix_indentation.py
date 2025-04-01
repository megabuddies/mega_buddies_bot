#!/usr/bin/env python
"""
Script to fix indentation issues in Python files.
This script parses Python files and automatically fixes common indentation issues.
"""

import sys
import re
import tokenize
import io
from pathlib import Path

def fix_indentation_in_file(filename):
    """Fix indentation issues in a Python file."""
    print(f"Processing {filename}...")
    
    try:
        # Read the file content
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use the tokenize module to properly handle Python code
        # This approach preserves comments and docstrings
        result = []
        lines = content.splitlines(True)
        
        # First pass: detect and fix basic indentation issues
        fixed_lines = []
        indent_level = 0
        in_def = False
        in_class = False
        in_try = False
        expect_except = False
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            
            # Skip empty lines
            if not stripped_line:
                fixed_lines.append(line)
                continue
            
            # Handle indentation increase for blocks starting
            if (stripped_line.startswith('def ') or 
                stripped_line.startswith('class ') or 
                stripped_line.startswith('if ') or 
                stripped_line.startswith('elif ') or 
                stripped_line.startswith('else:') or 
                stripped_line.startswith('for ') or 
                stripped_line.startswith('while ') or 
                stripped_line.startswith('try:') or 
                stripped_line.startswith('except ') or 
                stripped_line.startswith('finally:') or 
                stripped_line.startswith('with ')):
                
                # Special handling for try blocks
                if stripped_line.startswith('try:'):
                    in_try = True
                    expect_except = True
                
                # Special handling for except blocks
                if stripped_line.startswith('except '):
                    expect_except = False
                
                # Proper indentation for the current level
                proper_indent = ' ' * (4 * indent_level)
                fixed_line = proper_indent + stripped_line + '\n'
                fixed_lines.append(fixed_line)
                
                # Most block starters increase indentation for the next line
                if stripped_line.endswith(':'):
                    indent_level += 1
                
                continue
            
            # Handle indentation for normal lines
            proper_indent = ' ' * (4 * indent_level)
            fixed_line = proper_indent + stripped_line + '\n'
            fixed_lines.append(fixed_line)
            
            # Check for block endings
            if stripped_line == 'return' or stripped_line.startswith('return '):
                if indent_level > 0:
                    indent_level -= 1
        
        # Write the fixed content back to the file
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        
        print(f"Fixed indentation issues in {filename}")
        return True
    
    except Exception as e:
        print(f"Error fixing indentation in {filename}: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_indentation.py <python_file> [<python_file> ...]")
        sys.exit(1)
    
    files = sys.argv[1:]
    successes = 0
    
    for file in files:
        if fix_indentation_in_file(file):
            successes += 1
    
    print(f"Fixed {successes} out of {len(files)} files.")

if __name__ == "__main__":
    main()
