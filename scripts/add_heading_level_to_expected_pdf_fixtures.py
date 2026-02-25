#!/usr/bin/env python3
"""Add heading_level to Title elements in expected PDF JSON fixtures.

Our PDF partitioner now sets metadata.heading_level (1-6) on Title elements.
Expected fixtures were generated before that change. This script adds
heading_level: 1 to every Title's metadata in expected *.pdf.json files
so the ingest diff test matches current output.

Run from repo root:
  python scripts/add_heading_level_to_expected_pdf_fixtures.py
"""
from __future__ import annotations

import json
from pathlib import Path

EXPECTED_ROOT = Path(__file__).resolve().parent.parent / "test_unstructured_ingest" / "expected-structured-output"


def add_heading_level_to_file(path: Path) -> bool:
    """Add heading_level to each Title's metadata. Returns True if file was modified."""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, list):
        return False
    modified = False
    for item in data:
        if isinstance(item, dict) and item.get("type") == "Title":
            meta = item.get("metadata")
            if isinstance(meta, dict) and "heading_level" not in meta:
                meta["heading_level"] = 1
                modified = True
    if modified:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return modified


def main() -> None:
    count = 0
    for j in EXPECTED_ROOT.rglob("*.pdf.json"):
        if add_heading_level_to_file(j):
            print(j.relative_to(EXPECTED_ROOT))
            count += 1
    print(f"Updated {count} file(s).")


if __name__ == "__main__":
    main()
