#!/usr/bin/env python
"""
Script to automatically format Python code using autopep8.
Usage: python format_code.py <python_file>
"""

import sys
import subprocess
import os

def format_file(filename):
    """Format a Python file using autopep8."""
    try:
        # Check if autopep8 is installed
        try:
            import autopep8
        except ImportError:
            # Try to install autopep8 if it's not available
            print("Installing autopep8...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "autopep8"])
            import autopep8
        
        print(f"Formatting {filename}...")
        # Use autopep8 to format the file
        result = subprocess.run(
            [sys.executable, "-m", "autopep8", "--in-place", "--aggressive", "--aggressive", filename],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"Successfully formatted {filename}")
            return True
        else:
            print(f"Error formatting {filename}:")
            print(result.stderr)
            return False
    
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python format_code.py <python_file>")
        sys.exit(1)
    
    filename = sys.argv[1]
    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        sys.exit(1)
    
    success = format_file(filename)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 