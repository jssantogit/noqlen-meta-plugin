"""Conservative V3 track-version evidence from dedicated Recording description."""

from pathlib import Path

import pytest
from beets import config
from beets.library import Item, Library

from beetsplug.noqlenmeta.track_version import (
    TrackVersion,
    apply_track_version_plan,
    parse_recording_version,
    plan_track_version,
)

RECORDING = "11111111-1111-4111-8111-111111111111"


@pytest.fixture(autouse=True)
def restore_beets_configuration() -> object:
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


@pytest.fixture
def target(tmp_path: Path) -> tuple[Library, Item]:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(
        path=str(tmp_path / "track.flac").encode(),
        artist="Synthetic Artist", title="A Song (Radio Edit)",
        mb_trackid=RECORDING,
    )
    library.add(item)
    return library, item


@pytest.mark.parametrize(("comment", "expected_kind"), [
    ("radio edit", "radio_edit"),
    ("extended mix", "extended_mix"),
    ("instrumental version", "instrumental"),
    ("live version", "live"),
    ("demo version", "demo"),
])
def test_explicit_recording_disambiguation_has_typed_version(
    comment: str, expected_kind: str
) -> None:
    version = parse_recording_version(
        {"id": RECORDING, "disambiguation": comment}, RECORDING
    )
    assert version == TrackVersion(expected_kind, comment, RECORDING)


@pytest.mark.parametrize("comment", [
    "2019 remaster of the album", "some other mix", "", "a different artist",
])
def test_free_text_cannot_guess_a_track_version(comment: str) -> None:
    assert parse_recording_version(
        {"id": RECORDING, "disambiguation": comment}, RECORDING
    ) is None


def test_title_keywords_alone_never_assert_version() -> None:
    assert parse_recording_version(
        {"id": RECORDING, "title": "A Song (Radio Edit)"}, RECORDING
    ) is None


def test_version_preview_and_apply_store_both_typed_components(
    target: tuple[Library, Item],
) -> None:
    library, item = target
    evidence = TrackVersion("radio_edit", "radio edit", RECORDING)
    plan = plan_track_version(item, evidence)
    assert plan.status == "PROPOSE"
    assert item.get("track_version_type") is None

    result = apply_track_version_plan(library, plan)
    assert result.applied
    fresh = library.get_item(item.id)
    assert fresh["track_version_type"] == "radio_edit"
    assert fresh["track_version_description"] == "radio edit"
    assert plan_track_version(fresh, evidence).status == "KEEP"


def test_conflicting_existing_version_needs_review(
    target: tuple[Library, Item],
) -> None:
    library, item = target
    item["track_version_type"] = "live"
    item["track_version_description"] = "live version"
    item.store()
    evidence = TrackVersion("radio_edit", "radio edit", RECORDING)
    plan = plan_track_version(item, evidence)
    assert plan.status == "REVIEW"
    assert not apply_track_version_plan(library, plan).applied
    assert library.get_item(item.id)["track_version_type"] == "live"


def test_identity_changes_after_preview_block_version_application(
    target: tuple[Library, Item],
) -> None:
    library, item = target
    plan = plan_track_version(item, TrackVersion("radio_edit", "radio edit", RECORDING))
    item.mb_trackid = "22222222-2222-4222-8222-222222222222"
    item.store()

    assert apply_track_version_plan(library, plan).status == "BLOCKED"
    assert library.get_item(item.id).get("track_version_type") is None


def test_track_version_only_cli_preview_and_apply(
    target: tuple[Library, Item], monkeypatch: pytest.MonkeyPatch
) -> None:
    from beetsplug.noqlenmeta import NoqlenMetaPlugin
    from beetsplug.noqlenmeta.semantic_enrichment import SemanticEnrichmentResult

    library, item = target
    plugin = NoqlenMetaPlugin()
    plugin.config["fields"].set({
        **{field: False for field in plugin.config["fields"].keys()},
        "track_version": True,
    })
    version = TrackVersion("radio_edit", "radio edit", RECORDING)
    monkeypatch.setattr(
        plugin, "_collect_track_candidates",
        lambda *_: SemanticEnrichmentResult((), {}, version=version),
    )
    command = plugin.commands()[0]
    opts, args = command.parse_args(["--all"])
    command.func(library, opts, args)
    assert library.get_item(item.id).get("track_version_type") is None

    opts, args = command.parse_args(["--apply", "--all"])
    command.func(library, opts, args)
    assert library.get_item(item.id)["track_version_type"] == "radio_edit"
    assert library.get_item(item.id)["track_version_description"] == "radio edit"
