#!/usr/bin/env python3
"""Validate UMD remote plugin metadata and API surface."""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

RE_METADATA = re.compile(r'^"""(.*?)"""', re.DOTALL | re.MULTILINE)
RE_CLASS = re.compile(r"class\s+(\w+)\s*\(\s*(BasePlugin|BaseConverter)")


def validate_metadata(content: str) -> list[str]:
    errors: list[str] = []
    match = RE_METADATA.search(content)
    if not match:
        errors.append("Missing metadata docstring")
        return errors

    required = ("Name:", "Author:", "Version:", "Description:")
    missing = [field for field in required if field not in match.group(1)]
    errors.extend(f"Metadata missing field: {field}" for field in missing)
    return errors


def validate_api(content: str) -> list[str]:
    errors: list[str] = []
    if not RE_CLASS.search(content):
        errors.append("No class inheriting BasePlugin/BaseConverter found")
    try:
        ast.parse(content)
    except SyntaxError as exc:  # pragma: no cover - ast already tested
        errors.append(f"Syntax error: {exc}")
    return errors


def validate_file(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    errors = validate_metadata(content)
    errors.extend(validate_api(content))
    if not content.startswith("from __future__ import annotations"):
        errors.append("File must start with 'from __future__ import annotations'")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a UMD remote plugin")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()

    issues = validate_file(args.file)
    if issues:
        print("Validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1
    print("Plugin valid!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
