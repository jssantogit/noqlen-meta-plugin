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


def test_public_release_state_is_consistent() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    home = (ROOT / "site-docs/index.md").read_text(encoding="utf-8")
    release = (ROOT / "site-docs/project/release.md").read_text(encoding="utf-8")
    checklist = (ROOT / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    release_words = " ".join(release.split())
    combined = f"{readme}\n{home}\n{release}".casefold()

    assert len(readme.splitlines()) < 500
    assert "[MIT License](LICENSE)" in readme
    assert "João Pedro Rosa dos Santos" in readme
    assert "MIT licensed" in home
    assert "canonical license text" in home
    assert "GitHub repository is public" in home
    assert "MIT License" in release
    assert "public access has been confirmed" in release
    assert "[Read the Docs](https://noqlen-meta-plugin.readthedocs.io/)" in readme
    assert "canonical public documentation is live" in release_words
    assert "package has not been published to PyPI" in release_words
    assert "versioned Read the Docs `v1.0.0` build does not exist" in release_words
    assert "[x] MIT License selected and added" in checklist
    assert "[x] Repository visibility changed to public" in checklist
    assert "[ ] Repository visibility changed to public" not in checklist
    stale_phrases = (
        "public visibility remains unconfirmed",
        "not complete until GitHub reports",
        "publication remains gated on public repository confirmation",
        "until the owner imports the project",
        "read the docs project is intended",
        "read the docs is not considered live",
        "owner still needs to import",
        "public build remains pending",
    )
    assert not any(phrase in combined for phrase in stale_phrases)
    assert "package is published on pypi" not in combined
    assert "package has been published to pypi" not in combined
    assert "readthedocs.io/en/v1.0.0" not in combined
