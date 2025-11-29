#!/usr/bin/env python3
"""Validate community plugin before accepting PR."""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
from pathlib import Path


def validate_plugin(file_path: Path) -> tuple[bool, list[str]]:
    """Validate plugin file structure and content."""
    errors = []

    if not file_path.exists():
        return False, [f"File not found: {file_path}"]

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    # Check Python syntax
    try:
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")

    # Check for future annotations
    if not content.startswith("from __future__ import annotations"):
        errors.append("Missing 'from __future__ import annotations' at top")

    # Check metadata docstring
    if not re.search(r'""".*?Name:.*?"""', content, re.DOTALL):
        errors.append("Missing metadata docstring with Name field")

    # Check base class
    has_base_plugin = "BasePlugin" in content
    has_base_converter = "BaseConverter" in content

    if not (has_base_plugin or has_base_converter):
        errors.append("Must import BasePlugin or BaseConverter")

    # Check class definition
    class_pattern = r"class\s+(\w+)\s*\(\s*(BasePlugin|BaseConverter)\s*\)"
    if not re.search(class_pattern, content):
        errors.append("No valid plugin class found")

    # Calculate checksum
    checksum = hashlib.sha256(content.encode()).hexdigest()
    print(f"✓ Checksum: sha256:{checksum}")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Validate UMD community plugin")
    parser.add_argument("file", type=Path, help="Plugin file to validate")
    args = parser.parse_args()

    print(f"Validating {args.file}...")
    is_valid, errors = validate_plugin(args.file)

    if is_valid:
        print("✅ Plugin is valid!")
        return 0
    else:
        print("\n❌ Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
