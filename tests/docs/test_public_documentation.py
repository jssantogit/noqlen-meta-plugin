from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.configuration import default_config

ROOT = Path(__file__).parents[2]


def test_technical_reference_uses_canonical_paths() -> None:
    docs = ROOT / "site-docs"

    assert (docs / "technical-reference" / "configuration.md").is_file()
    assert (docs / "technical-reference" / "command-line.md").is_file()
    assert not (docs / "reference").exists()


def test_start_here_is_a_continuous_existing_library_tutorial() -> None:
    start = ROOT / "site-docs" / "start-here"
    required = {
        "index.md",
        "installation.md",
        "basic-configuration.md",
        "first-preview.md",
        "understanding-results.md",
        "apply-changes.md",
        "write-files.md",
    }

    assert required == {path.name for path in start.glob("*.md")}
    assert not (ROOT / "site-docs" / "getting-started").exists()
    assert 'beet nm album:"Discovery"' in (start / "first-preview.md").read_text()
    assert 'beet nm --apply album:"Discovery"' in (start / "apply-changes.md").read_text()
    assert 'beet nm --apply --write album:"Discovery"' in (
        start / "write-files.md"
    ).read_text()


def test_friendly_configuration_covers_mood_relationship() -> None:
    configuration = ROOT / "site-docs" / "configuration"
    required = {
        "index.md",
        "fields.md",
        "providers.md",
        "genres-styles.md",
        "moods.md",
        "artwork.md",
        "bpm.md",
        "lyrics-languages.md",
        "acoustid.md",
        "advanced-resolution.md",
        "full-example.md",
    }
    page = (configuration / "moods.md").read_text(encoding="utf-8")

    assert required == {path.name for path in configuration.glob("*.md")}
    assert "fields:" in page
    assert "moods: true" in page
    assert "max_moods: 1" in page
    assert "max_moods: 3" in page


def test_command_guides_cover_core_user_goals() -> None:
    docs = ROOT / "site-docs" / "commands"

    assert "beet nm QUERY" in (docs / "preview.md").read_text()
    assert "beet nm --apply QUERY" in (docs / "apply.md").read_text()
    assert "beet nm --apply --write QUERY" in (docs / "write-files.md").read_text()
    assert "beet nm --all" in (docs / "whole-library.md").read_text()
    assert "beet nm --identity QUERY" in (docs / "identity.md").read_text()
    assert "beet nm --acoustid QUERY" in (docs / "acoustid.md").read_text()


def test_recipes_replace_legacy_guides() -> None:
    recipes = ROOT / "site-docs" / "recipes"
    required = {
        "index.md",
        "existing-library.md",
        "import-enrichment.md",
        "artwork.md",
        "local-bpm.md",
        "lyrics-languages.md",
        "repair-musicbrainz-ids.md",
        "whole-library.md",
    }

    assert required == {path.name for path in recipes.glob("*.md")}
    assert not (ROOT / "site-docs" / "guides").exists()


def test_troubleshooting_routes_by_symptom() -> None:
    troubleshooting = ROOT / "site-docs" / "troubleshooting"
    required = {
        "index.md",
        "nothing-changed.md",
        "review-blocked.md",
        "providers.md",
        "file-writing.md",
        "acoustid.md",
    }
    index = (troubleshooting / "index.md").read_text(encoding="utf-8")

    assert required == {path.name for path in troubleshooting.glob("*.md")}
    for name in required - {"index.md"}:
        assert f"({name})" in index


def test_public_navigation_matches_v2_information_architecture() -> None:
    mkdocs = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    labels = [next(iter(entry)) for entry in mkdocs["nav"]]

    assert labels == [
        "Home",
        "Start Here",
        "Configuration",
        "Commands",
        "Recipes",
        "Troubleshooting",
        "Technical Reference",
        "Advanced",
        "Project",
    ]
    for legacy in ("getting-started", "concepts", "guides", "reference"):
        assert not (ROOT / "site-docs" / legacy).exists()


def test_default_config_is_fresh_and_complete() -> None:
    first = default_config()
    second = default_config()

    first["fields"]["genres"] = False

    assert second["fields"]["genres"] is True
    assert second["genres"] == {"num_genres": 1, "promote_styles": True}
    assert second["providers"]["discogs"]["user_token"] == ""
    assert second["fields"]["moods"] is True
    assert "mood" not in second["fields"]
    assert second["fields"]["artist_areas"] is False
    assert second["providers"]["musicbrainz"]["enabled"] is True
    assert second["providers"]["coverartarchive"]["enabled"] is True
    assert second["artwork"] == {"size": "original", "replace_existing": False}
    assert second["bpm"] == {
        "round": False,
        "recalculate_existing": False,
        "octave_normalization": False,
        "octave_range": {"min": 70, "max": 180},
    }
    assert second["local_analysis"] == {
        "bpm": {"enabled": False, "analysis_mode": "full", "window_seconds": 90},
        "mood": {"enabled": False},
    }


def test_readme_is_concise_project_landing_page() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    headings = [line for line in readme.splitlines() if line.startswith("#")]

    assert headings == ["# Noqlen Meta", "## Capabilities", "## Installation"]
    assert "## Documentation" not in readme
    assert "## First Preview" not in readme
    assert "## License" not in readme
    assert "Version `" not in readme
    assert "releases/tag/v" not in readme
    assert "pip install beets-noqlenmeta" in readme
    assert 'pip install "beets-noqlenmeta[discogs]"' in readme
    assert 'pip install "beets-noqlenmeta[audio]"' in readme
    assert "plugins:\n  - noqlenmeta" in readme
    assert "beet help noqlenmeta" in readme


def test_v2_0_1_release_checklist_is_present() -> None:
    checklist = (ROOT / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "## Version 2.0.1 Documentation Release" in checklist
    assert "Package version is `2.0.1`." in checklist
    assert (
        "README contains only the approved summary, Capabilities, and Installation structure."
        in checklist
    )
    assert "Create `v2.0.1` tag on a commit contained in `main`." in checklist
    assert "Publish `2.0.1` to PyPI through Trusted Publishing." in checklist
    assert "Create and verify the GitHub Release for `v2.0.1`." in checklist
    assert "Read the Docs builds `v2.0.1` successfully." in checklist
    assert "`/en/stable/` displays the redesigned Documentation v2" in checklist


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
    assert "ordinary file sync with --apply" in help_text
    assert "ordinary metadata only" in help_text
    assert "--write" in help_text
    assert "all targets in the selected mode" in help_text


def test_public_release_state_is_consistent() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    home = (ROOT / "site-docs/index.md").read_text(encoding="utf-8")
    release = (ROOT / "site-docs/project/release.md").read_text(encoding="utf-8")
    project_changelog = (ROOT / "site-docs/project/changelog.md").read_text(
        encoding="utf-8"
    )
    permissions = (ROOT / "site-docs/advanced/preview-apply-write.md").read_text(
        encoding="utf-8"
    )
    assert not (ROOT / "site-docs" / "concepts").exists()
    checklist = (ROOT / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    release_words = " ".join(release.split()).casefold()
    combined = " ".join(
        f"{readme}\n{home}\n{release}\n{permissions}".split()
    ).casefold()

    assert len(readme.splitlines()) < 500
    assert "MIT licensed" in home
    assert "canonical license text" in home
    assert "GitHub repository is public" in home
    assert "MIT License" in release
    assert "canonical public documentation is live" in release_words
    assert "https://pypi.org/project/beets-noqlenmeta/" in home
    assert (
        "https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v2.0.1"
        in release
    )
    assert "## Unreleased" in changelog
    assert "## 2.0.1 - 2026-08-12" in changelog
    assert "## 2.0.0 - 2026-08-11" in changelog
    assert (
        changelog.index("## Unreleased")
        < changelog.index("## 2.0.1 - 2026-08-12")
        < changelog.index("## 2.0.0 - 2026-08-11")
        < changelog.index("## 1.0.0 - 2026-08-02")
    )
    assert "Current stable release: `2.0.1` (2026-08-12)" in release
    assert "Noqlen Meta 2.0.1 is published on" in release
    assert "Version 2.0.1 is the current stable release." in project_changelog
    assert "The Read the Docs project slug is `noqlen-meta`." in release
    assert "verified `cover.jpg` sidecars may be written" in combined
    assert "audio files remain unchanged unless `--write`" in combined
    assert "adding `--write` never triggers another provider call" in combined
    assert "[x] MIT License selected and added" in checklist
    assert "[x] Repository visibility changed to public" in checklist
    assert "[x] PyPI project ownership established" in checklist
    assert "[x] `v1.0.0` tag created" in checklist
    assert "[x] Tag workflow built, checked, and published" in checklist
    assert "[x] GitHub Release `v1.0.0` was created" in checklist
    assert "[x] Read the Docs `stable`, `latest`, and `v1.0.0`" in checklist
    assert "[x] Create `v2.0.0` tag" in checklist
    assert "[x] Create and verify the GitHub Release for `v2.0.0`." in checklist
    assert "[x] Publish `2.0.0` to PyPI and verify its artifacts." in checklist
    assert (
        "[x] Confirm the canonical Read the Docs project at "
        "`noqlen-meta.readthedocs.io` and the public `stable` URL."
        in checklist
    )
    assert "[ ] Public wheel installs in a clean environment" in checklist
    assert "[ ] `beet nm --help` works after the public clean install." in checklist
    assert "[ ] Repository visibility changed to public" not in checklist
    assert "noqlen-meta-plugin.readthedocs.io" not in combined
    stale_phrases = (
        "public visibility remains unconfirmed",
        "not complete until GitHub reports",
        "publication remains gated on public repository confirmation",
        "until the owner imports the project",
        "read the docs project is intended",
        "read the docs is not considered live",
        "owner still needs to import",
        "public build remains pending",
        "ready for the release tag",
        "package has not been published to pypi",
        "first successful oidc publication will create",
        "versioned read the docs `v1.0.0` build does not exist",
        "repository release candidate: `2.0.0`",
        "currently published release: `1.0.0` (2026-08-02)",
        "main merge, tag, publication, and versioned documentation remain pending",
    )
    assert not any(phrase in combined for phrase in stale_phrases)
