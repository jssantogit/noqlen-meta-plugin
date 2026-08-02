#!/usr/bin/env python3
"""Inspect release archives for expected identity and safe contents."""

from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from email import message_from_bytes
from email.message import Message
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by the Python 3.10 CI job
    import tomli as tomllib

EXPECTED_NAME = "beets-noqlenmeta"
EXPECTED_VERSION = "1.0.0"
EXPECTED_REQUIRES_PYTHON = SpecifierSet(">=3.10,<3.15")
CLAIMED_PYTHON_VERSIONS = tuple(Version(f"3.{minor}") for minor in range(10, 15))
FORBIDDEN_PARTS = {
    ".github",
    ".opencode",
    ".serena",
    "build",
    "dist",
    "docs",
    "site",
    "site-docs",
    "tests",
}
FORBIDDEN_NAMES = {"AGENTS.md", "RELEASE_CHECKLIST.md", "opencode.json", "RTK.md"}


def _wheel_metadata(path: Path) -> tuple[Message, set[str]]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ValueError("wheel must contain exactly one METADATA file")
        metadata = message_from_bytes(archive.read(metadata_names[0]))
    return metadata, names


def _sdist_names(path: Path) -> set[str]:
    with tarfile.open(path, "r:gz") as archive:
        return set(archive.getnames())


def _requires_python_failures(
    metadata: Message, pyproject_path: Path
) -> list[str]:
    """Return release-boundary failures for wheel and source Python metadata."""
    failures: list[str] = []
    wheel_value = metadata.get("Requires-Python")
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project_value = project.get("project", {}).get("requires-python")

    parsed: dict[str, SpecifierSet] = {}
    for source, value in (("wheel", wheel_value), ("pyproject.toml", project_value)):
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{source} Requires-Python is missing")
            continue
        try:
            specifier = SpecifierSet(value)
        except InvalidSpecifier:
            failures.append(f"{source} Requires-Python is invalid: {value!r}")
            continue
        parsed[source] = specifier
        if specifier != EXPECTED_REQUIRES_PYTHON:
            failures.append(
                f"{source} Requires-Python {value!r} does not equal >=3.10,<3.15"
            )
        if Version("3.15") in specifier:
            failures.append(f"{source} Requires-Python incorrectly admits Python 3.15")
        for version in CLAIMED_PYTHON_VERSIONS:
            if version not in specifier:
                failures.append(f"{source} Requires-Python rejects claimed Python {version}")

    if len(parsed) == 2 and parsed["wheel"] != parsed["pyproject.toml"]:
        failures.append("wheel Requires-Python differs from pyproject.toml")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    wheels = sorted(args.directory.glob("*.whl"))
    sdists = sorted(args.directory.glob("*.tar.gz"))
    failures: list[str] = []
    if len(wheels) != 1:
        failures.append(f"expected one wheel, found {len(wheels)}")
    if len(sdists) != 1:
        failures.append(f"expected one sdist, found {len(sdists)}")

    if len(wheels) == 1:
        try:
            metadata, names = _wheel_metadata(wheels[0])
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            failures.append(f"invalid wheel: {error}")
        else:
            if metadata.get("Name") != EXPECTED_NAME:
                failures.append(f"wheel name is {metadata.get('Name')!r}")
            if metadata.get("Version") != EXPECTED_VERSION:
                failures.append(f"wheel version is {metadata.get('Version')!r}")
            failures.extend(_requires_python_failures(metadata, Path("pyproject.toml")))
            if not any(name.startswith("beetsplug/noqlenmeta/") for name in names):
                failures.append("wheel omits beetsplug.noqlenmeta")
            for name in names:
                parts = set(Path(name).parts)
                if parts & FORBIDDEN_PARTS or Path(name).name in FORBIDDEN_NAMES:
                    failures.append(f"wheel contains forbidden release content: {name}")

    if len(sdists) == 1:
        try:
            names = _sdist_names(sdists[0])
        except (OSError, tarfile.TarError) as error:
            failures.append(f"invalid sdist: {error}")
        else:
            required_suffixes = (
                "/pyproject.toml",
                "/README.md",
                "/beetsplug/noqlenmeta/__init__.py",
            )
            for suffix in required_suffixes:
                if not any(name.endswith(suffix) for name in names):
                    failures.append(f"sdist omits required file: {suffix[1:]}")
            for name in names:
                relative_parts = Path(name).parts[1:]
                if set(relative_parts) & FORBIDDEN_PARTS or Path(name).name in FORBIDDEN_NAMES:
                    failures.append(f"sdist contains forbidden release content: {name}")

    if failures:
        print("FAIL: distribution validation")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: wheel and sdist identity and contents validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
