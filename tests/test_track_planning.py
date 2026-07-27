import copy

import pytest
from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.distance import Distance
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.library import Item

from beetsplug.noqlenmeta.domain import MetadataCandidate, TrackEnrichmentContext
from beetsplug.noqlenmeta.resolver import FieldRule, ResolutionAction, ResolutionPolicy
from beetsplug.noqlenmeta.track_integration import (
    SelectedImportTrack,
    current_values_from_library_item,
)
from beetsplug.noqlenmeta.track_planning import (
    build_import_track_planning_result,
    effective_current_values_for_import_track,
    selected_metadata_current_values,
)


def _track_info(**overrides: object) -> TrackInfo:
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


def test_from_scratch_false_retains_local_canonical_values() -> None:
    selected = SelectedImportTrack(
        Item(lyrics="local plain", synced_lyrics="local synced"),
        _track_info(),
        None,
    )

    assert effective_current_values_for_import_track(selected, from_scratch=False) == {
        "lyrics": "local plain",
        "synced_lyrics": "local synced",
    }


def test_from_scratch_true_mirrors_field_specific_beets_clear() -> None:
    selected = SelectedImportTrack(
        Item(lyrics="local plain", synced_lyrics="local synced"),
        _track_info(),
        None,
    )

    assert "lyrics" in Item._media_tag_fields
    assert "synced_lyrics" not in Item._media_tag_fields
    assert effective_current_values_for_import_track(selected, from_scratch=True) == {
        "synced_lyrics": "local synced"
    }


@pytest.mark.parametrize("from_scratch", [False, True])
def test_selected_metadata_overrides_local_values_in_both_modes(
    from_scratch: bool,
) -> None:
    selected = SelectedImportTrack(
        Item(lyrics="local plain", synced_lyrics="local synced"),
        _track_info(lyrics=" selected plain ", synced_lyrics=" selected synced "),
        None,
    )

    assert effective_current_values_for_import_track(
        selected, from_scratch=from_scratch
    ) == {
        "lyrics": "selected plain",
        "synced_lyrics": "selected synced",
    }


def test_album_selected_metadata_uses_beets_merged_application_data() -> None:
    track = _track_info(artist=None, album=None)
    album = AlbumInfo(
        [track],
        artist="Album Artist",
        album="Merged Album",
        lyrics=" album supplied plain ",
        synced_lyrics=" album supplied synced ",
    )
    selected = SelectedImportTrack(Item(lyrics="local"), track, album)
    expected_data = track.merge_with_album(album)

    assert selected_metadata_current_values(selected) == {
        "lyrics": expected_data["lyrics"].strip(),
        "synced_lyrics": expected_data["synced_lyrics"].strip(),
    }


def test_effective_current_helpers_do_not_change_selected_data() -> None:
    item = Item(lyrics=" local ", synced_lyrics=" local synced ")
    track = _track_info(lyrics=" selected ")
    album = AlbumInfo([track], artist="Synthetic Artist", album="Synthetic Album")
    selected = SelectedImportTrack(item, track, album)
    snapshots = (
        copy.deepcopy(dict(item)),
        copy.deepcopy(dict(track)),
        copy.deepcopy(dict(album)),
    )

    selected_metadata_current_values(selected)
    effective_current_values_for_import_track(selected, from_scratch=False)
    effective_current_values_for_import_track(selected, from_scratch=True)

    assert (dict(item), dict(track), dict(album)) == snapshots
    assert selected.item is item
    assert selected.track_info is track
    assert selected.album_info is album


def test_from_scratch_changes_plain_but_not_flexible_synced_conflict() -> None:
    selected = SelectedImportTrack(
        Item(lyrics="local plain", synced_lyrics="local synced"),
        _track_info(),
        None,
    )
    context = TrackEnrichmentContext(
        "Synthetic Artist", "Synthetic Track", album_title="Synthetic Album", duration=180.0
    )
    candidates = (
        MetadataCandidate("lyrics", "remote plain", "lrclib", 0.95, "42"),
        MetadataCandidate("synced_lyrics", "remote synced", "lrclib", 0.95, "42"),
    )
    policy = ResolutionPolicy(
        {
            field: FieldRule(True, ("lrclib",), 0.8, True)
            for field in ("lyrics", "synced_lyrics")
        },
        {"lrclib": True},
    )

    retained = build_import_track_planning_result(
        selected,
        context,
        from_scratch=False,
        candidates=candidates,
        policy=policy,
    )
    cleared = build_import_track_planning_result(
        selected,
        context,
        from_scratch=True,
        candidates=candidates,
        policy=policy,
    )

    assert {decision.field: decision.action for decision in retained.decisions} == {
        "lyrics": ResolutionAction.REVIEW,
        "synced_lyrics": ResolutionAction.REVIEW,
    }
    assert {decision.field: decision.action for decision in cleared.decisions} == {
        "lyrics": ResolutionAction.PROPOSE,
        "synced_lyrics": ResolutionAction.REVIEW,
    }


@pytest.mark.parametrize("kind", ["album", "singleton"])
@pytest.mark.parametrize("from_scratch", [False, True])
@pytest.mark.parametrize("field", ["lyrics", "synced_lyrics"])
@pytest.mark.parametrize("selected_has_value", [False, True])
def test_effective_current_values_match_actual_beets_application(
    kind: str,
    from_scratch: bool,
    field: str,
    selected_has_value: bool,
) -> None:
    selected_values = {field: "selected synthetic text"} if selected_has_value else {}
    predicted_item = Item(**{field: "local synthetic text"})
    predicted_track = _track_info(**selected_values)
    actual_item = Item(**{field: "local synthetic text"})
    actual_track = _track_info(**selected_values)

    if kind == "album":
        predicted_album = AlbumInfo(
            [predicted_track], artist="Synthetic Artist", album="Synthetic Album"
        )
        actual_album = AlbumInfo(
            [actual_track], artist="Synthetic Artist", album="Synthetic Album"
        )
        selected = SelectedImportTrack(predicted_item, predicted_track, predicted_album)
        match = AlbumMatch(Distance(), actual_album, {actual_item: actual_track})
    else:
        selected = SelectedImportTrack(predicted_item, predicted_track, None)
        match = TrackMatch(Distance(), actual_track, actual_item)

    predicted = effective_current_values_for_import_track(
        selected,
        from_scratch=from_scratch,
    )
    match.apply_metadata(from_scratch=from_scratch)

    assert predicted == current_values_from_library_item(actual_item)
