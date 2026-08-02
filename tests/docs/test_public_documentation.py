from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.configuration import default_config

ROOT = Path(__file__).parents[2]


def test_default_config_is_fresh_and_complete() -> None:
    first = default_config()
    second = default_config()

    first["fields"]["genres"] = False

    assert second["fields"]["genres"] is True
    assert second["providers"]["discogs"]["user_token"] == ""


def test_public_documentation_gate() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_public_docs.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_command_help_explains_modes_and_write_boundaries() -> None:
    command = NoqlenMetaPlugin().commands()[0]
    help_text = command.parser.format_help()

    assert "--identity" in help_text
    assert "--identity-tags" in help_text
    assert "--apply" in help_text
    assert "never writes files" in help_text
    assert "ordinary metadata only" in help_text
    assert "--write" in help_text
    assert "all targets in the selected mode" in help_text


def test_public_license_and_visibility_statements_are_consistent() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    home = (ROOT / "site-docs/index.md").read_text(encoding="utf-8")
    release = (ROOT / "site-docs/project/release.md").read_text(encoding="utf-8")
    checklist = (ROOT / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert len(readme.splitlines()) < 500
    assert "[MIT License](LICENSE)" in readme
    assert "João Pedro Rosa dos Santos" in readme
    assert "MIT licensed" in home
    assert "canonical license text" in home
    assert "MIT License" in release
    assert "not complete until GitHub reports" in release
    assert "[x] MIT License selected and added" in checklist
    assert "[ ] Repository visibility changed to public" in checklist
    assert "[x] Repository visibility changed to public" not in checklist
