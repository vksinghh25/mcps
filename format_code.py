#!/usr/bin/env python3
"""
Code formatting script for the MCPS project.
Formats all Python, HTML, and Markdown files.
"""

import subprocess
import sys
import os


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    """Format all code files in the project."""
    print("🎨 Starting code formatting...")
    
    # Format Python files with black
    success1 = run_command(
        "python3 -m black agents/ --line-length=88",
        "Formatting Python files with Black"
    )
    
    # Format HTML and Markdown files with Prettier
    success2 = run_command(
        "prettier --write index.html README.md",
        "Formatting HTML and Markdown files with Prettier"
    )
    
    if success1 and success2:
        print("\n🎉 All files formatted successfully!")
        print("✨ Your code is now beautifully formatted!")
    else:
        print("\n⚠️  Some formatting operations failed. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main() 