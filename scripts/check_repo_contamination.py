#!/usr/bin/env python3
"""Fail on common local-tooling artifacts and obvious sensitive path/secret leakage."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


FORBIDDEN_PATHS = {
    "opencode.json",
    "RTK.md",
    ".opencode",
    ".serena",
    ".mcp",
    ".claude",
    ".cursor",
    ".windsurf",
}

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
}

PERSONAL_PATH_PATTERNS = (
    re.compile(r"/home/[^/\s]+/"),
    re.compile(r"/Users/[^/\s]+/"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\"),
)

SECRET_ASSIGNMENT = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[\"'][^\"']{8,}[\"']"
)
PRIVATE_KEY_MARKER = "BEGIN " + "PRIVATE KEY"


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line]


def main() -> int:
    failures: list[str] = []

    for path in tracked_files():
        parts = set(path.parts)
        if path.name in FORBIDDEN_PATHS or parts & FORBIDDEN_PATHS:
            failures.append(f"forbidden tracked artifact: {path}")
            continue

        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"AGENTS.md", ".gitignore"}:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for pattern in PERSONAL_PATH_PATTERNS:
            if pattern.search(text):
                failures.append(f"personal path pattern found: {path}")
                break

        if SECRET_ASSIGNMENT.search(text):
            failures.append(f"possible hard-coded secret found: {path}")

        if PRIVATE_KEY_MARKER in text:
            failures.append(f"private-key marker found: {path}")

    if failures:
        print("FAIL: repository contamination detected")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: no obvious repository contamination detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
