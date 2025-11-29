#!/usr/bin/env python3
"""Generate index.json for the plugin market."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.json"
RE_METADATA = re.compile(r'^"""(.*?)"""', re.DOTALL | re.MULTILINE)


def parse_metadata(path: Path) -> dict[str, object]:
    content = path.read_text(encoding="utf-8")
    match = RE_METADATA.search(content)
    block = match.group(1) if match else ""
    data: dict[str, object] = {}
    for key in ("Name", "Author", "Version", "Description", "Repository", "License"):
        pattern = re.compile(rf"{key}:\s*(.+)")
        value_match = pattern.search(block)
        if value_match:
            data[key.lower()] = value_match.group(1).strip()
    deps_match = re.search(r"Dependencies:\s*(.+?)(?:\n\n|\Z)", block, re.DOTALL)
    if deps_match:
        deps = [dep.strip() for dep in re.split(r"[,\n]", deps_match.group(1)) if dep.strip()]
        data["dependencies"] = deps
    else:
        data["dependencies"] = []
    data["checksum"] = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
    data["source_url"] = f"https://raw.githubusercontent.com/umd-plugins/official/main/{path.relative_to(ROOT)}"
    return data


def collect_plugins() -> list[dict[str, object]]:
    plugins: list[dict[str, object]] = []
    for plugin_type in ("parsers", "converters"):
        for file in (ROOT / plugin_type).glob("*.py"):
            metadata = parse_metadata(file)
            plugins.append(
                {
                    "id": file.stem,
                    "name": metadata.get("name", file.stem.title()),
                    "type": "parser" if plugin_type == "parsers" else "converter",
                    "author": metadata.get("author", "Unknown"),
                    "version": metadata.get("version", "0.1.0"),
                    "description": metadata.get("description", ""),
                    "repository": metadata.get("repository", ""),
                    "license": metadata.get("license", "MIT"),
                    "dependencies": metadata.get("dependencies", []),
                    "source_url": metadata["source_url"],
                    "checksum": metadata["checksum"],
                    "downloads": 0,
                    "rating": 5.0,
                    "tags": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
    return plugins


def main() -> int:
    data = {
        "version": "1.0",
        "last_updated": datetime.utcnow().isoformat(),
        "plugins": collect_plugins(),
    }
    INDEX.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated {INDEX} with {len(data['plugins'])} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
