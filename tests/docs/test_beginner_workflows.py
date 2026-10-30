"""Check that beginner-facing, copyable examples match real configuration contracts."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from beetsplug.noqlenmeta.configuration import default_config

DOCS = Path(__file__).resolve().parents[2] / "site-docs"

BEGINNER_PAGES = (
    "start-here/quickstart.md",
    "concepts/mental-model.md",
    "recipes/lyrics-synced.md",
    "recipes/audio-analysis.md",
    "recipes/recording-credits.md",
    "recipes/configuration-profiles.md",
)

PROFILE_FILES = (
    "lyrics-config.yaml",
    "audio-config.yaml",
    "credits-config.yaml",
)


def _blocks(relative: str) -> list[dict]:
    body = (DOCS / relative).read_text(encoding="utf-8")
    fenced = re.findall(r"^\x60\x60\x60yaml\n(.*?)^\x60\x60\x60\s*$", body, flags=re.M | re.S)
    return [yaml.safe_load(fragment) for fragment in fenced]


def _validate_example(doc: dict, source: str) -> None:
    assert isinstance(doc, dict), source
    assert set(doc) <= {"plugins", "noqlenmeta"}, source
    assert "noqlenmeta" in doc or "plugins" in doc, source
    if "plugins" in doc:
        assert "noqlenmeta" in doc["plugins"], source

    cfg = doc.get("noqlenmeta")
    if cfg is None:
        return
    assert isinstance(cfg, dict), source
    defaults = default_config()
    assert set(cfg) <= set(defaults), source
    if "fields" in cfg:
        assert isinstance(cfg["fields"], dict), source
        assert all(type(v) is bool for v in cfg["fields"].values()), source
        optional_v3 = {
            "vocal_languages", "instrumental", "explicitness",
            "alternate_titles", "transliterations", "track_version",
            "back_artwork", "key", "energy", "danceability",
        }
        assert set(cfg["fields"]) <= set(defaults["fields"]) | optional_v3, source
    if "providers" in cfg:
        assert set(cfg["providers"]) <= set(defaults["providers"]), source
        for provider, settings in cfg["providers"].items():
            assert isinstance(settings, dict), source
            assert set(settings) <= set(defaults["providers"][provider]), source
    if "local_analysis" in cfg:
        assert set(cfg["local_analysis"]) <= {"bpm", "mood", "key", "audio_features"}, source
        for settings in cfg["local_analysis"].values():
            assert isinstance(settings, dict), source
            assert type(settings.get("enabled")) is bool, source
    fields = cfg.get("fields", {})
    analysis = cfg.get("local_analysis", {})
    if fields.get("key"):
        assert analysis.get("key", {}).get("enabled") is True, source
    if fields.get("energy") or fields.get("danceability"):
        assert analysis.get("audio_features", {}).get("enabled") is True, source


@pytest.mark.parametrize("relative", BEGINNER_PAGES)
def test_every_beginner_yaml_block_has_valid_root_and_feature_dependencies(
    relative: str,
) -> None:
    blocks = _blocks(relative)
    assert blocks, relative
    for block in blocks:
        _validate_example(block, relative)


@pytest.mark.parametrize(
    ("recipe", "profile"),
    [
        ("recipes/lyrics-synced.md", "lyrics-config.yaml"),
        ("recipes/audio-analysis.md", "audio-config.yaml"),
        ("recipes/recording-credits.md", "credits-config.yaml"),
    ],
)
def test_downloadable_profiles_match_their_recipe_exactly(
    recipe: str, profile: str
) -> None:
    sample = yaml.safe_load((DOCS / "examples" / profile).read_text(encoding="utf-8"))
    _validate_example(sample, profile)
    blocks = _blocks(recipe)
    assert len(blocks) == 1, recipe
    assert blocks[0]["noqlenmeta"] == sample["noqlenmeta"]


def test_first_use_explains_safety_and_linked_paths() -> None:
    quickstart = (DOCS / "start-here" / "quickstart.md").read_text(encoding="utf-8")
    readme = (DOCS.parent / "README.md").read_text(encoding="utf-8")
    mental = (DOCS / "concepts" / "mental-model.md").read_text(encoding="utf-8")
    storage = (DOCS / "concepts" / "data-destinations.md").read_text(encoding="utf-8")
    assert 'beet nm album:"Discovery"' in quickstart
    assert 'beet nm --apply album:"Discovery"' in quickstart
    assert 'beet nm --apply --write album:"Discovery"' in quickstart
    assert "does not alter" in quickstart.replace("**", "")
    assert "noqlen-meta.readthedocs.io/en/latest/start-here/quickstart/" in readme
    for term in ("fields", "providers", "local_analysis", "--apply", "--write"):
        assert term in mental
    for term in ("cover.jpg", "back.jpg", ".lrc", "database-only"):
        assert term in storage


def test_all_friendly_configuration_yaml_snippets_have_correct_root() -> None:
    """A user must never be told to paste an orphan top-level fields: key."""
    for page in sorted((DOCS / "configuration").glob("*.md")):
        blocks = _blocks(str(page.relative_to(DOCS)))
        for example in blocks:
            assert isinstance(example, dict), str(page)
            assert set(example) <= {"noqlenmeta", "plugins"}, str(page)
            assert "noqlenmeta" in example, str(page)


def test_reference_distinguishes_lrc_from_unsupported_sylt() -> None:
    reference = (DOCS / "technical-reference" / "configuration.md").read_text(
        encoding="utf-8"
    )
    assert "no-clobber `.lrc` sidecar" in reference
    assert "No lossless synchronized-lyrics target is delivered" not in reference
