from copy import deepcopy
from dataclasses import replace
from typing import Any, cast

import pytest
from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.distance import Distance
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.library import Item

from beetsplug.noqlenmeta.identity import (
    IdentityImportApplicationError,
    IdentityImportMatchKind,
    SelectedIdentityTrack,
    SelectedImportIdentity,
    apply_import_identity_plan,
    audit_musicbrainz_identity,
    identity_context_from_selected_import,
    map_identity_audit_to_import_targets,
)

from .helpers import candidate, mbid


@pytest.fixture(autouse=True)
def reject_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*args, **kwargs) -> None:
        pytest.fail("identity metadata application must not persist Items")

    monkeypatch.setattr(Item, "store", reject)
    monkeypatch.setattr(Item, "write", reject)


def _track(index: int, **overrides: object) -> TrackInfo:
    values: dict[str, object] = {
        "artist": "Example Artist",
        "title": f"Track {index}",
        "album": "Example Album",
        "length": 180.0 + index,
        "medium": 1,
        "medium_index": index,
        "index": index,
    }
    values.update(overrides)
    return TrackInfo(**values)  # type: ignore[arg-type]


def _selected(
    kind: IdentityImportMatchKind,
    *,
    state: str = "missing",
    count: int = 2,
) -> SelectedImportIdentity:
    correct = state == "confirmed"
    conflict = state == "conflict"
    album_id = mbid(100) if correct else mbid(900) if conflict else None
    group_id = mbid(200) if correct else mbid(901) if conflict else None
    tracks = []
    for index in range(1, count + 1):
        recording = mbid(1000 + index) if correct else mbid(1100 + index) if conflict else None
        release_track = (
            mbid(2000 + index) if correct else mbid(2100 + index) if conflict else None
        )
        extra: dict[str, object] = {
            "track_id": recording,
            "release_track_id": release_track,
        }
        if kind is IdentityImportMatchKind.TRACK:
            extra.update(mb_albumid=album_id, mb_releasegroupid=group_id)
        tracks.append(
            SelectedIdentityTrack(
                f"local-{index}",
                Item(
                    artist="Example Artist",
                    album="Example Album",
                    title=f"Local Item {index}",
                    mb_albumid=mbid(800),
                    mb_releasegroupid=mbid(801),
                    mb_trackid=mbid(802 + index),
                    mb_releasetrackid=mbid(812 + index),
                ),
                _track(index, **extra),
            )
        )
    album = None
    if kind is IdentityImportMatchKind.ALBUM:
        album = AlbumInfo(
            [track.track_info for track in tracks],
            artist="Example Artist",
            album="Example Album",
            album_id=album_id,
            releasegroup_id=group_id,
        )
    return SelectedImportIdentity(kind, tuple(tracks), album)


def _plan(selected: SelectedImportIdentity, *, from_scratch: bool = False, candidates=True):
    context = identity_context_from_selected_import(selected, from_scratch=from_scratch)
    assert context is not None
    audit = audit_musicbrainz_identity(
        context,
        (candidate(len(selected.tracks)),) if candidates else (),
    )
    return map_identity_audit_to_import_targets(audit, match_kind=selected.kind)


def _metadata_values(selected: SelectedImportIdentity) -> list[tuple[str | None, ...]]:
    values = []
    for selected_track in selected.tracks:
        track = selected_track.track_info
        values.append(
            (
                track.get("track_id"),
                track.get("release_track_id"),
                track.get("mb_albumid"),
                track.get("mb_releasegroupid"),
            )
        )
    return values


@pytest.mark.parametrize("kind", list(IdentityImportMatchKind))
@pytest.mark.parametrize("state", ["missing", "conflict"])
def test_applies_missing_and_conflicting_identity_atomically(kind, state) -> None:
    selected = _selected(kind, state=state, count=2 if kind is IdentityImportMatchKind.ALBUM else 1)
    plan = _plan(selected)
    items_before = [deepcopy(dict(track.item)) for track in selected.tracks]

    result = apply_import_identity_plan(selected, plan, from_scratch=False)

    assert result.has_applied_changes
    assert not result.is_blocked
    assert result.applied_changes == plan.changes
    assert [dict(track.item) for track in selected.tracks] == items_before
    if kind is IdentityImportMatchKind.ALBUM:
        assert selected.album_info is not None
        assert selected.album_info.album_id == mbid(100)
        assert selected.album_info.releasegroup_id == mbid(200)
    else:
        assert selected.tracks[0].track_info["mb_albumid"] == mbid(100)
        assert selected.tracks[0].track_info["mb_releasegroupid"] == mbid(200)
    actual_track_ids = [
        (track.track_info.track_id, track.track_info.release_track_id)
        for track in selected.tracks
    ]
    assert actual_track_ids == [
        (mbid(1000 + index), mbid(2000 + index))
        for index in range(1, len(selected.tracks) + 1)
    ]


def test_confirmed_is_noop_and_ambiguous_and_nonready_are_blocked() -> None:
    confirmed = _selected(IdentityImportMatchKind.ALBUM, state="confirmed")
    confirmed_plan = _plan(confirmed)
    ambiguous = _selected(IdentityImportMatchKind.ALBUM)
    ambiguous_plan = _plan(ambiguous, candidates=False)
    repairable_plan = _plan(ambiguous)
    nonready_plan = replace(
        repairable_plan,
        source=replace(repairable_plan.source, repair_ready=False),
        changes=(),
    )

    confirmed_result = apply_import_identity_plan(confirmed, confirmed_plan, from_scratch=False)
    ambiguous_result = apply_import_identity_plan(ambiguous, ambiguous_plan, from_scratch=False)
    nonready_result = apply_import_identity_plan(ambiguous, nonready_plan, from_scratch=False)

    assert confirmed_result.is_confirmed_noop
    assert not confirmed_result.has_applied_changes
    assert ambiguous_result.blocked_reason == "ambiguous_evidence"
    assert nonready_result.blocked_reason == "repair_not_ready"


def test_forged_and_stale_plans_are_rejected_without_mutation() -> None:
    selected = _selected(IdentityImportMatchKind.TRACK, count=1)
    plan = _plan(selected)
    before = _metadata_values(selected)
    forged = replace(
        plan,
        changes=(replace(plan.changes[0], target_field="track_id"),) + plan.changes[1:],
    )

    with pytest.raises(IdentityImportApplicationError, match="canonical source"):
        apply_import_identity_plan(selected, forged, from_scratch=False)
    assert _metadata_values(selected) == before

    selected.tracks[0].track_info.title = "Changed after audit"
    with pytest.raises(IdentityImportApplicationError, match="no longer matches"):
        apply_import_identity_plan(selected, plan, from_scratch=False)
    assert _metadata_values(selected) == before


def test_from_scratch_mismatch_and_invalid_contract_types_are_rejected() -> None:
    selected = _selected(IdentityImportMatchKind.TRACK, count=1)
    plan = _plan(selected, from_scratch=False)
    invalid = cast(Any, object())

    with pytest.raises(IdentityImportApplicationError, match="no longer matches"):
        apply_import_identity_plan(selected, plan, from_scratch=True)
    with pytest.raises(IdentityImportApplicationError, match="target is invalid"):
        apply_import_identity_plan(invalid, plan, from_scratch=False)
    with pytest.raises(IdentityImportApplicationError, match="plan is invalid"):
        apply_import_identity_plan(selected, invalid, from_scratch=False)
    with pytest.raises(IdentityImportApplicationError, match="must be a bool"):
        apply_import_identity_plan(selected, plan, from_scratch=cast(Any, 0))


def test_duplicate_canonical_targets_and_malformed_source_uuid_are_rejected() -> None:
    selected = _selected(IdentityImportMatchKind.TRACK, count=1)
    plan = _plan(selected)
    finding = plan.source.field_findings[0]
    duplicate_source = replace(plan.source, field_findings=(finding, finding))
    duplicate_plan = map_identity_audit_to_import_targets(
        duplicate_source, match_kind=IdentityImportMatchKind.TRACK
    )
    malformed_source = replace(
        plan.source,
        field_findings=(replace(finding, expected_value=mbid(0xABCDEF).upper()),),
    )
    malformed_plan = replace(plan, source=malformed_source, changes=())

    with pytest.raises(IdentityImportApplicationError, match="duplicated"):
        apply_import_identity_plan(selected, duplicate_plan, from_scratch=False)
    with pytest.raises(IdentityImportApplicationError, match="cannot be mapped canonically"):
        apply_import_identity_plan(selected, malformed_plan, from_scratch=False)


def test_application_invalidates_only_changed_metadata_caches() -> None:
    selected = _selected(IdentityImportMatchKind.ALBUM, state="confirmed")
    assert selected.album_info is not None
    selected.album_info.album_id = None
    plan = _plan(selected)
    album_cache = (selected.album_info.raw_data, selected.album_info.item_data)
    track = selected.tracks[0].track_info
    track_cache = (track.raw_data, track.item_data)

    apply_import_identity_plan(selected, plan, from_scratch=False)

    assert "raw_data" not in selected.album_info.__dict__
    assert "item_data" not in selected.album_info.__dict__
    assert selected.album_info.raw_data is not album_cache[0]
    assert selected.album_info.item_data is not album_cache[1]
    assert track.__dict__["raw_data"] is track_cache[0]
    assert track.__dict__["item_data"] is track_cache[1]


def test_all_changed_target_caches_are_invalidated_and_items_remain_unchanged() -> None:
    selected = _selected(IdentityImportMatchKind.ALBUM)
    assert selected.album_info is not None
    targets = (selected.album_info,) + tuple(track.track_info for track in selected.tracks)
    for target in targets:
        _ = target.raw_data
        _ = target.item_data
    items_before = [deepcopy(dict(track.item)) for track in selected.tracks]

    apply_import_identity_plan(selected, _plan(selected), from_scratch=False)

    assert all("raw_data" not in target.__dict__ for target in targets)
    assert all("item_data" not in target.__dict__ for target in targets)
    assert [dict(track.item) for track in selected.tracks] == items_before


def test_assignment_failure_restores_all_fields_and_exact_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _selected(IdentityImportMatchKind.ALBUM)
    assert selected.album_info is not None
    targets = (selected.album_info,) + tuple(track.track_info for track in selected.tracks)
    fields_before = _metadata_values(selected)
    album_fields_before = (
        selected.album_info.get("album_id"),
        selected.album_info.get("releasegroup_id"),
    )
    caches_before = []
    for target in targets:
        caches_before.append((target.raw_data, target.item_data))

    original = TrackInfo.__setitem__
    failed = False

    def fail_once(target: TrackInfo, key: str, value: object) -> None:
        nonlocal failed
        if target is selected.tracks[0].track_info and key == "release_track_id" and not failed:
            failed = True
            raise RuntimeError("synthetic assignment failure")
        original(target, key, value)

    monkeypatch.setattr(TrackInfo, "__setitem__", fail_once)

    with pytest.raises(IdentityImportApplicationError, match="failed safely"):
        apply_import_identity_plan(selected, _plan(selected), from_scratch=False)

    assert failed
    assert _metadata_values(selected) == fields_before
    assert (
        selected.album_info.get("album_id"),
        selected.album_info.get("releasegroup_id"),
    ) == album_fields_before
    for target, (raw_data, item_data) in zip(targets, caches_before, strict=True):
        assert target.__dict__["raw_data"] is raw_data
        assert target.__dict__["item_data"] is item_data


@pytest.mark.parametrize("from_scratch", [False, True])
def test_real_album_match_apply_metadata_receives_all_repaired_identity(from_scratch) -> None:
    selected = _selected(IdentityImportMatchKind.ALBUM)
    assert selected.album_info is not None
    targets = (selected.album_info,) + tuple(track.track_info for track in selected.tracks)
    for track in selected.tracks:
        _ = track.track_info.raw_data
        _ = track.track_info.item_data
        _ = track.track_info.merge_with_album(selected.album_info)
    _ = selected.album_info.raw_data
    _ = selected.album_info.item_data
    assert all("raw_data" in target.__dict__ for target in targets)
    assert all("item_data" in target.__dict__ for target in targets)
    items_before = [deepcopy(dict(track.item)) for track in selected.tracks]
    match = AlbumMatch(
        Distance(),
        selected.album_info,
        {track.item: track.track_info for track in selected.tracks},
    )

    apply_import_identity_plan(
        selected,
        _plan(selected, from_scratch=from_scratch),
        from_scratch=from_scratch,
    )

    assert [dict(track.item) for track in selected.tracks] == items_before
    assert all("raw_data" not in target.__dict__ for target in targets)
    assert all("item_data" not in target.__dict__ for target in targets)
    match.apply_metadata(from_scratch=from_scratch)  # type: ignore[call-arg]

    for index, track in enumerate(selected.tracks, start=1):
        assert track.item.mb_albumid == mbid(100)
        assert track.item.mb_releasegroupid == mbid(200)
        assert track.item.mb_trackid == mbid(1000 + index)
        assert track.item.mb_releasetrackid == mbid(2000 + index)


@pytest.mark.parametrize("from_scratch", [False, True])
def test_real_track_match_apply_metadata_receives_flexible_album_keys(from_scratch) -> None:
    selected = _selected(IdentityImportMatchKind.TRACK, count=1)
    track = selected.tracks[0]
    _ = track.track_info.raw_data
    _ = track.track_info.item_data
    assert "raw_data" in track.track_info.__dict__
    assert "item_data" in track.track_info.__dict__
    item_before = deepcopy(dict(track.item))
    match = TrackMatch(Distance(), track.track_info, track.item)

    apply_import_identity_plan(
        selected,
        _plan(selected, from_scratch=from_scratch),
        from_scratch=from_scratch,
    )

    assert dict(track.item) == item_before
    assert "raw_data" not in track.track_info.__dict__
    assert "item_data" not in track.track_info.__dict__
    assert track.track_info.item_data["mb_albumid"] == mbid(100)
    assert track.track_info.item_data["mb_releasegroupid"] == mbid(200)
    match.apply_metadata(from_scratch=from_scratch)  # type: ignore[call-arg]
    assert track.item.mb_albumid == mbid(100)
    assert track.item.mb_releasegroupid == mbid(200)
    assert track.item.mb_trackid == mbid(1001)
    assert track.item.mb_releasetrackid == mbid(2001)
