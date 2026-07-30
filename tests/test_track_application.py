from dataclasses import FrozenInstanceError, replace

import pytest
from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.distance import Distance
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.library import Item

import beetsplug.noqlenmeta.track_application as application_module
from beetsplug.noqlenmeta.domain import MetadataCandidate, TrackEnrichmentContext
from beetsplug.noqlenmeta.resolver import FieldRule, ResolutionPolicy
from beetsplug.noqlenmeta.track_application import (
    TrackApplicationError,
    TrackApplicationMode,
    apply_track_target_plan,
    parse_track_application_mode,
)
from beetsplug.noqlenmeta.track_integration import SelectedImportTrack
from beetsplug.noqlenmeta.track_mapping import TrackTargetPlan
from beetsplug.noqlenmeta.track_planning import build_import_track_planning_result

REMOTE_PLAIN = "Synthetic remote line one\nSynthetic remote line two"
REMOTE_SYNCED = "[00:01.00] Synthetic synchronized line"


def _track(**overrides: object) -> TrackInfo:
    values: dict[str, object] = {
        "artist": "Synthetic Artist",
        "title": "Synthetic Track",
        "album": "Synthetic Album",
        "length": 180.0,
        "index": 1,
        "medium": 1,
        "medium_index": 1,
    }
    values.update(overrides)
    return TrackInfo(**values)  # type: ignore[arg-type]


def _planning_result(
    selected: SelectedImportTrack,
    *fields: str,
    from_scratch: bool = False,
    preserve_existing: bool = True,
):
    values = {"lyrics": REMOTE_PLAIN, "synced_lyrics": REMOTE_SYNCED}
    return build_import_track_planning_result(
        selected,
        TrackEnrichmentContext(
            "Synthetic Artist",
            "Synthetic Track",
            album_title="Synthetic Album",
            duration=180.0,
        ),
        from_scratch=from_scratch,
        candidates=tuple(
            MetadataCandidate(field, values[field], "lrclib", 0.95, "42")
            for field in fields
        ),
        policy=ResolutionPolicy(
            {
                field: FieldRule(True, ("lrclib",), 0.8, preserve_existing)
                for field in fields
            },
            {"lrclib": True},
        ),
    )


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("strict", TrackApplicationMode.STRICT),
        (" STRICT ", TrackApplicationMode.STRICT),
        ("partial", TrackApplicationMode.PARTIAL),
    ],
)
def test_parse_track_application_mode(
    configured: str, expected: TrackApplicationMode
) -> None:
    assert parse_track_application_mode(configured) is expected


@pytest.mark.parametrize("configured", ["", "best-effort", object()])
def test_parse_track_application_mode_rejects_invalid_values(configured: object) -> None:
    with pytest.raises(TrackApplicationError, match="track application mode"):
        parse_track_application_mode(configured)  # type: ignore[arg-type]


def test_strict_clean_apply_mutates_only_selected_track_info() -> None:
    item = Item(lyrics="Local synthetic lyrics")
    track = _track()
    album = AlbumInfo([track], artist="Synthetic Artist", album="Synthetic Album")
    selected = SelectedImportTrack(item, track, album)
    result = _planning_result(selected, "lyrics", preserve_existing=False)
    item_before = dict(item)
    album_before = dict(album)

    applied = apply_track_target_plan(
        selected,
        result.target_plan,
        from_scratch=False,
    )

    assert track.lyrics == REMOTE_PLAIN
    assert dict(item) == item_before
    assert dict(album) == album_before
    assert applied.applied_changes == result.target_plan.mapped_changes
    assert applied.has_applied_changes
    assert not applied.has_withheld_fields
    with pytest.raises(FrozenInstanceError):
        applied.applied_changes = ()  # type: ignore[misc]


def test_strict_review_blocks_without_mutation() -> None:
    track = _track()
    selected = SelectedImportTrack(Item(lyrics="Local synthetic lyrics"), track, None)
    plan = _planning_result(selected, "lyrics")

    result = apply_track_target_plan(selected, plan.target_plan, from_scratch=False)

    assert track.get("lyrics") is None
    assert result.is_blocked
    assert result.resolution_review_count == 1
    assert result.applied_changes == ()


def test_strict_mapping_blocker_blocks_mapped_change() -> None:
    track = _track()
    selected = SelectedImportTrack(Item(), track, None)
    plan = _planning_result(selected, "lyrics", "synced_lyrics")

    result = apply_track_target_plan(selected, plan.target_plan, from_scratch=False)

    assert track.get("lyrics") is None
    assert result.is_blocked
    assert result.mapping_blocker_count == 1


def test_partial_applies_plain_and_withholds_synced() -> None:
    track = _track()
    selected = SelectedImportTrack(Item(), track, None)
    plan = _planning_result(selected, "lyrics", "synced_lyrics")

    result = apply_track_target_plan(
        selected,
        plan.target_plan,
        from_scratch=False,
        mode=TrackApplicationMode.PARTIAL,
    )

    assert track.lyrics == REMOTE_PLAIN
    assert track.get("synced_lyrics") is None
    assert result.is_partial_application
    assert result.mapping_blocker_count == 1


def test_partial_blocker_only_is_nonblocking_no_op() -> None:
    track = _track()
    selected = SelectedImportTrack(Item(), track, None)
    plan = _planning_result(selected, "synced_lyrics")

    result = apply_track_target_plan(
        selected,
        plan.target_plan,
        from_scratch=False,
        mode=TrackApplicationMode.PARTIAL,
    )

    assert track.get("lyrics") is None
    assert not result.has_applied_changes
    assert result.has_withheld_fields
    assert not result.is_blocked


def test_stale_local_item_state_aborts_without_track_mutation() -> None:
    item = Item(lyrics="Local before")
    track = _track()
    selected = SelectedImportTrack(item, track, None)
    plan = _planning_result(selected, "lyrics", preserve_existing=False)
    item.lyrics = "Local after"

    with pytest.raises(TrackApplicationError, match="'lyrics'.*no longer matches"):
        apply_track_target_plan(selected, plan.target_plan, from_scratch=False)

    assert track.get("lyrics") is None


def test_stale_selected_track_info_aborts_without_overwrite() -> None:
    track = _track(lyrics="Selected before")
    selected = SelectedImportTrack(Item(), track, None)
    plan = _planning_result(selected, "lyrics", preserve_existing=False)
    track.lyrics = "Selected after"

    with pytest.raises(TrackApplicationError, match="'lyrics'.*no longer matches"):
        apply_track_target_plan(selected, plan.target_plan, from_scratch=False)

    assert track.lyrics == "Selected after"


def test_forged_target_plan_is_rejected_without_mutation() -> None:
    track = _track()
    selected = SelectedImportTrack(Item(), track, None)
    plan = _planning_result(selected, "lyrics").target_plan
    forged_change = replace(plan.mapped_changes[0], target_value="Forged synthetic value")
    forged = replace(plan, mapped_changes=(forged_change,))

    with pytest.raises(TrackApplicationError, match="canonical source mapping"):
        apply_track_target_plan(selected, forged, from_scratch=False)

    assert track.get("lyrics") is None


def test_duplicate_target_is_rejected_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    track = _track()
    selected = SelectedImportTrack(Item(), track, None)
    plan = _planning_result(selected, "lyrics").target_plan
    duplicate = replace(plan, mapped_changes=plan.mapped_changes * 2)
    monkeypatch.setattr(
        application_module,
        "map_change_plan_to_track_info",
        lambda source: duplicate,
    )

    with pytest.raises(TrackApplicationError, match="duplicate TrackInfo target"):
        apply_track_target_plan(selected, duplicate, from_scratch=False)

    assert track.get("lyrics") is None


def test_malformed_target_value_is_rejected_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    track = _track()
    selected = SelectedImportTrack(Item(), track, None)
    plan = _planning_result(selected, "lyrics").target_plan
    malformed_change = replace(plan.mapped_changes[0], target_value="")
    malformed = replace(plan, mapped_changes=(malformed_change,))
    monkeypatch.setattr(
        application_module,
        "map_change_plan_to_track_info",
        lambda source: malformed,
    )

    with pytest.raises(TrackApplicationError, match="non-empty string"):
        apply_track_target_plan(selected, malformed, from_scratch=False)

    assert track.get("lyrics") is None


def test_successful_application_invalidates_track_info_caches() -> None:
    track = _track()
    selected = SelectedImportTrack(Item(), track, None)
    plan = _planning_result(selected, "lyrics")
    before_raw = track.raw_data
    before_item_data = track.item_data

    apply_track_target_plan(selected, plan.target_plan, from_scratch=False)

    assert "raw_data" not in track.__dict__
    assert "item_data" not in track.__dict__
    assert track.item_data["lyrics"] == REMOTE_PLAIN
    assert track.raw_data is not before_raw
    assert track.item_data is not before_item_data


@pytest.mark.parametrize("from_scratch", [False, True])
def test_real_track_match_applies_selected_track_later(from_scratch: bool) -> None:
    item = Item(lyrics="Local synthetic lyrics")
    track = _track()
    selected = SelectedImportTrack(item, track, None)
    plan = _planning_result(
        selected,
        "lyrics",
        from_scratch=from_scratch,
        preserve_existing=False,
    )
    match = TrackMatch(Distance(), track, item)

    apply_track_target_plan(selected, plan.target_plan, from_scratch=from_scratch)

    assert track.lyrics == REMOTE_PLAIN
    assert item.lyrics == "Local synthetic lyrics"
    match.apply_metadata(from_scratch=from_scratch)
    assert item.lyrics == REMOTE_PLAIN


@pytest.mark.parametrize("from_scratch", [False, True])
def test_real_album_match_applies_selected_track_later(from_scratch: bool) -> None:
    item = Item(lyrics="Local synthetic lyrics")
    track = _track()
    album = AlbumInfo([track], artist="Synthetic Artist", album="Synthetic Album")
    selected = SelectedImportTrack(item, track, album)
    plan = _planning_result(
        selected,
        "lyrics",
        from_scratch=from_scratch,
        preserve_existing=False,
    )
    match = AlbumMatch(Distance(), album, {item: track})
    track.merge_with_album(album)

    apply_track_target_plan(selected, plan.target_plan, from_scratch=from_scratch)

    assert track.lyrics == REMOTE_PLAIN
    assert item.lyrics == "Local synthetic lyrics"
    match.apply_metadata(from_scratch=from_scratch)
    assert item.lyrics == REMOTE_PLAIN


@pytest.mark.parametrize(
    ("selected", "plan", "from_scratch", "mode"),
    [
        (object(), TrackTargetPlan, False, TrackApplicationMode.STRICT),
        (None, object(), False, TrackApplicationMode.STRICT),
        (None, TrackTargetPlan, None, TrackApplicationMode.STRICT),
        (None, TrackTargetPlan, False, object()),
    ],
)
def test_invalid_application_contract_types_raise(
    selected: object,
    plan: object,
    from_scratch: object,
    mode: object,
) -> None:
    valid_selected = SelectedImportTrack(Item(), _track(), None)
    valid_plan = _planning_result(valid_selected, "lyrics").target_plan
    selected_value = valid_selected if selected is None else selected
    plan_value = valid_plan if plan is TrackTargetPlan else plan

    with pytest.raises(TrackApplicationError):
        apply_track_target_plan(
            selected_value,  # type: ignore[arg-type]
            plan_value,  # type: ignore[arg-type]
            from_scratch=from_scratch,  # type: ignore[arg-type]
            mode=mode,  # type: ignore[arg-type]
        )
