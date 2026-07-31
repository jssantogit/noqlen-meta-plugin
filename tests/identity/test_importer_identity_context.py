from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.distance import Distance
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.importer.actions import Action
from beets.importer.tasks import ImportTask, SingletonImportTask
from beets.library import Item

from beetsplug.noqlenmeta.identity import (
    MISSING_ALBUM_ID_MARKER,
    MISSING_RELEASE_GROUP_ID_MARKER,
    IdentityAlbumContext,
    IdentityImportMatchKind,
    MusicBrainzReleaseIdentity,
    SelectedImportIdentity,
    audit_selected_import_identity,
    identity_context_from_selected_import,
    selected_import_identity,
)

from .helpers import candidate, candidate_track, mbid


def _track(number: int, **overrides: object) -> TrackInfo:
    values: dict[str, object] = {
        "artist": "Synthetic Artist",
        "title": f"Track {number}",
        "album": "Synthetic Album",
        "length": 180.0 + number,
        "medium": 1,
        "medium_index": number,
        "index": number,
    }
    values.update(overrides)
    return TrackInfo(**values)  # type: ignore[arg-type]


def _album_task(
    pairs: list[tuple[Item, TrackInfo]],
    *,
    album_overrides: dict[str, object] | None = None,
    extra_items: list[Item] | None = None,
    extra_tracks: list[TrackInfo] | None = None,
    action: Action = Action.APPLY,
) -> tuple[ImportTask, AlbumInfo]:
    extras = extra_tracks or []
    album_values: dict[str, object] = {
        "artist": "Synthetic Artist",
        "album": "Synthetic Album",
    }
    album_values.update(album_overrides or {})
    album = AlbumInfo([track for _, track in pairs] + extras, **album_values)
    match = AlbumMatch(
        Distance(),
        album,
        dict(pairs),
        extra_items or [],
        extras,
    )
    task = ImportTask(None, [], [item for item, _ in pairs] + (extra_items or []))
    task.choice_flag = action
    task.match = match
    return task, album


def _singleton_task(
    item: Item,
    track: TrackInfo,
    *,
    action: Action = Action.APPLY,
) -> SingletonImportTask:
    task = SingletonImportTask(None, item)
    task.choice_flag = action
    task.match = TrackMatch(Distance(), track, item)
    return task


def _selected_album(
    pairs: list[tuple[Item, TrackInfo]],
    *,
    album_overrides: dict[str, object] | None = None,
) -> tuple[SelectedImportIdentity, AlbumInfo]:
    task, album = _album_task(pairs, album_overrides=album_overrides)
    selected = selected_import_identity(task)
    assert selected is not None
    return selected, album


@dataclass
class _SyntheticSource:
    candidates: tuple[MusicBrainzReleaseIdentity, ...]
    contexts: list[IdentityAlbumContext] = field(default_factory=list)

    def candidates_for(
        self, context: IdentityAlbumContext
    ) -> tuple[MusicBrainzReleaseIdentity, ...]:
        self.contexts.append(context)
        return self.candidates


def test_album_match_retains_mapping_order_and_excludes_extras() -> None:
    first_item = Item(title="Local First")
    second_item = Item(title="Local Second")
    first_track = _track(1, title="Selected First")
    second_track = _track(2, title="Selected Second")
    extra_item = Item(title="Unmatched Item")
    extra_track = _track(3, title="Unmatched Track")
    task, album = _album_task(
        [(second_item, second_track), (first_item, first_track)],
        extra_items=[extra_item],
        extra_tracks=[extra_track],
    )

    selected = selected_import_identity(task)

    assert selected is not None
    assert selected.kind is IdentityImportMatchKind.ALBUM
    assert selected.album_info is album
    assert [track.local_key for track in selected.tracks] == ["track:0001", "track:0002"]
    assert [track.item for track in selected.tracks] == [second_item, first_item]
    assert [track.track_info for track in selected.tracks] == [second_track, first_track]
    assert all(track.item is not extra_item for track in selected.tracks)
    assert all(track.track_info is not extra_track for track in selected.tracks)


def test_track_match_retains_the_selected_item_and_track_info() -> None:
    item = Item(title="Local")
    track = _track(1, title="Selected")

    selected = selected_import_identity(_singleton_task(item, track))

    assert selected is not None
    assert selected.kind is IdentityImportMatchKind.TRACK
    assert selected.album_info is None
    assert len(selected.tracks) == 1
    assert selected.tracks[0].local_key == "track:0001"
    assert selected.tracks[0].item is item
    assert selected.tracks[0].track_info is track


def test_selection_rejects_non_apply_unsupported_and_empty_album_boundaries() -> None:
    skipped, _ = _album_task([(Item(), _track(1))], action=Action.SKIP)
    unsupported = ImportTask(None, [], [Item()])
    unsupported.choice_flag = Action.APPLY
    unsupported.match = object()
    empty, _ = _album_task([])

    class AlbumMatchSubclass(AlbumMatch):
        pass

    class TrackMatchSubclass(TrackMatch):
        pass

    subclass_item = Item()
    subclass_track = _track(1)
    subclass_album = AlbumInfo(
        [subclass_track], artist="Synthetic Artist", album="Synthetic Album"
    )
    album_subclass_task = ImportTask(None, [], [subclass_item])
    album_subclass_task.choice_flag = Action.APPLY
    album_subclass_task.match = AlbumMatchSubclass(
        Distance(), subclass_album, {subclass_item: subclass_track}
    )
    track_subclass_task = SingletonImportTask(None, subclass_item)
    track_subclass_task.choice_flag = Action.APPLY
    track_subclass_task.match = TrackMatchSubclass(
        Distance(), subclass_track, subclass_item
    )

    assert selected_import_identity(skipped) is None
    assert selected_import_identity(unsupported) is None
    assert selected_import_identity(empty) is None
    assert selected_import_identity(album_subclass_task) is None
    assert selected_import_identity(track_subclass_task) is None
    assert selected_import_identity(object()) is None


@pytest.mark.parametrize("from_scratch", [False, True])
def test_selected_ids_override_item_ids_in_album_and_track_surfaces(
    from_scratch: bool,
) -> None:
    selected_release = mbid(101)
    selected_group = mbid(201)
    selected_recording = mbid(1001)
    selected_release_track = mbid(2001)
    item = Item(
        mb_albumid=mbid(901),
        mb_releasegroupid=mbid(902),
        mb_trackid=mbid(903),
        mb_releasetrackid=mbid(904),
    )
    track = _track(
        1,
        track_id=selected_recording,
        release_track_id=selected_release_track,
    )
    selected, _ = _selected_album(
        [(item, track)],
        album_overrides={
            "album_id": selected_release,
            "releasegroup_id": selected_group,
        },
    )

    context = identity_context_from_selected_import(selected, from_scratch=from_scratch)

    assert context is not None
    assert context.current_release_mbids == (selected_release,)
    assert context.current_release_group_mbids == (selected_group,)
    assert context.tracks[0].current_recording_mbid == selected_recording
    assert context.tracks[0].current_release_track_mbid == selected_release_track


@pytest.mark.parametrize("from_scratch", [False, True])
def test_omitted_selected_ids_preserve_item_ids_only_without_from_scratch(
    from_scratch: bool,
) -> None:
    item_ids = (mbid(111), mbid(211), mbid(1011), mbid(2011))
    item = Item(
        mb_albumid=item_ids[0],
        mb_releasegroupid=item_ids[1],
        mb_trackid=item_ids[2],
        mb_releasetrackid=item_ids[3],
    )
    selected, _ = _selected_album([(item, _track(1))])

    context = identity_context_from_selected_import(selected, from_scratch=from_scratch)

    assert context is not None
    if from_scratch:
        assert context.current_release_mbids == ()
        assert context.current_release_group_mbids == ()
        assert context.tracks[0].current_recording_mbid is None
        assert context.tracks[0].current_release_track_mbid is None
    else:
        assert context.current_release_mbids == (item_ids[0],)
        assert context.current_release_group_mbids == (item_ids[1],)
        assert context.tracks[0].current_recording_mbid == item_ids[2]
        assert context.tracks[0].current_release_track_mbid == item_ids[3]


@pytest.mark.parametrize("from_scratch", [False, True])
def test_singleton_selected_ids_override_item_ids(from_scratch: bool) -> None:
    selected_ids = (mbid(141), mbid(241), mbid(1041), mbid(2041))
    item = Item(
        artist="Item Artist",
        mb_albumid=mbid(941),
        mb_releasegroupid=mbid(942),
        mb_trackid=mbid(943),
        mb_releasetrackid=mbid(944),
    )
    track = _track(
        1,
        mb_albumid=selected_ids[0],
        mb_releasegroupid=selected_ids[1],
        track_id=selected_ids[2],
        release_track_id=selected_ids[3],
    )
    selected = selected_import_identity(_singleton_task(item, track))
    assert selected is not None

    context = identity_context_from_selected_import(selected, from_scratch=from_scratch)

    assert context is not None
    assert context.current_release_mbids == (selected_ids[0],)
    assert context.current_release_group_mbids == (selected_ids[1],)
    assert context.tracks[0].current_recording_mbid == selected_ids[2]
    assert context.tracks[0].current_release_track_mbid == selected_ids[3]


@pytest.mark.parametrize("from_scratch", [False, True])
def test_singleton_omitted_ids_preserve_item_ids_only_without_from_scratch(
    from_scratch: bool,
) -> None:
    item_ids = (mbid(151), mbid(251), mbid(1051), mbid(2051))
    item = Item(
        artist="Item Artist",
        mb_albumid=item_ids[0],
        mb_releasegroupid=item_ids[1],
        mb_trackid=item_ids[2],
        mb_releasetrackid=item_ids[3],
    )
    selected = selected_import_identity(_singleton_task(item, _track(1)))
    assert selected is not None

    context = identity_context_from_selected_import(selected, from_scratch=from_scratch)

    assert context is not None
    expected = item_ids if not from_scratch else (None, None, None, None)
    assert context.current_release_mbids == ((expected[0],) if expected[0] else ())
    assert context.current_release_group_mbids == ((expected[1],) if expected[1] else ())
    assert context.tracks[0].current_recording_mbid == expected[2]
    assert context.tracks[0].current_release_track_mbid == expected[3]


@pytest.mark.parametrize(
    ("items", "expected_releases", "expected_groups"),
    [
        ([Item(), Item()], (), ()),
        (
            [Item(mb_albumid=mbid(121), mb_releasegroupid=mbid(221)), Item()],
            (mbid(121), MISSING_ALBUM_ID_MARKER),
            (mbid(221), MISSING_RELEASE_GROUP_ID_MARKER),
        ),
        (
            [
                Item(mb_albumid=mbid(131), mb_releasegroupid=mbid(231)),
                Item(mb_albumid=mbid(132), mb_releasegroupid=mbid(232)),
            ],
            (mbid(131), mbid(132)),
            (mbid(231), mbid(232)),
        ),
    ],
    ids=["all-missing", "mixed-markers", "distinct-ids"],
)
def test_album_ids_preserve_all_missing_mixed_and_distinct_states(
    items: list[Item],
    expected_releases: tuple[str, ...],
    expected_groups: tuple[str, ...],
) -> None:
    selected, _ = _selected_album([(items[0], _track(1)), (items[1], _track(2))])

    context = identity_context_from_selected_import(selected, from_scratch=False)

    assert context is not None
    assert context.current_release_mbids == expected_releases
    assert context.current_release_group_mbids == expected_groups


def test_per_track_ids_follow_selected_mapping_order() -> None:
    first_ids = (mbid(1101), mbid(2101))
    second_ids = (mbid(1102), mbid(2102))
    first = Item(mb_trackid=first_ids[0], mb_releasetrackid=first_ids[1])
    second = Item(mb_trackid=second_ids[0], mb_releasetrackid=second_ids[1])
    selected, _ = _selected_album([(second, _track(2)), (first, _track(1))])

    context = identity_context_from_selected_import(selected, from_scratch=False)

    assert context is not None
    assert [track.current_recording_mbid for track in context.tracks] == [
        second_ids[0],
        first_ids[0],
    ]
    assert [track.current_release_track_mbid for track in context.tracks] == [
        second_ids[1],
        first_ids[1],
    ]


def test_album_context_uses_selected_structure_and_album_artist_fallback() -> None:
    track = _track(
        1,
        artist=" ",
        title="  Selected Title  ",
        length=float("nan"),
        medium=0,
        medium_index=True,
        index=-1,
    )
    selected, _ = _selected_album(
        [(Item(artist="Ignored Item Artist", title="Ignored Item Title"), track)],
        album_overrides={
            "artist": "  Album Artist  ",
            "album": "  Album Title  ",
            "year": 2024,
            "country": "  XE  ",
            "label": "  Synthetic Label  ",
        },
    )

    context = identity_context_from_selected_import(selected, from_scratch=False)

    assert context is not None
    assert context.album_artist == "Album Artist"
    assert context.album == "Album Title"
    assert context.year == 2024
    assert context.country == "XE"
    assert context.label == "Synthetic Label"
    assert context.tracks[0].artist == "Album Artist"
    assert context.tracks[0].title == "Selected Title"
    assert context.tracks[0].length is None
    assert context.tracks[0].medium is None
    assert context.tracks[0].medium_index is None
    assert context.tracks[0].index is None


def test_singleton_context_falls_back_to_item_artist_album_and_then_title() -> None:
    item_album = Item(artist="  Item Artist  ", album="  Item Album  ")
    selected_album = selected_import_identity(
        _singleton_task(item_album, _track(1, artist=None, album=None, title="  Title  "))
    )
    item_without_album = Item(artist="Item Artist")
    selected_title = selected_import_identity(
        _singleton_task(item_without_album, _track(1, artist=None, album=None, title="Title"))
    )
    assert selected_album is not None
    assert selected_title is not None

    album_context = identity_context_from_selected_import(selected_album, from_scratch=False)
    title_context = identity_context_from_selected_import(selected_title, from_scratch=False)

    assert album_context is not None
    assert album_context.album_artist == "Item Artist"
    assert album_context.album == "Item Album"
    assert album_context.tracks[0].artist == "Item Artist"
    assert title_context is not None
    assert title_context.album == "Title"


@pytest.mark.parametrize(
    ("kind", "album_artist", "album", "track_artist", "title"),
    [
        ("album", " ", "Album", "Artist", "Title"),
        ("album", "Artist", " ", "Artist", "Title"),
        ("album", "Artist", "Album", "Artist", " "),
        ("track", None, None, None, "Title"),
        ("track", None, None, "Artist", " "),
    ],
)
def test_structurally_incomplete_selected_metadata_returns_none(
    kind: str,
    album_artist: str | None,
    album: str | None,
    track_artist: str | None,
    title: str,
) -> None:
    item = Item()
    track = _track(1, artist=track_artist, album=album, title=title)
    if kind == "album":
        selected, _ = _selected_album(
            [(item, track)],
            album_overrides={"artist": album_artist, "album": album},
        )
    else:
        selected = selected_import_identity(_singleton_task(item, track))
        assert selected is not None

    assert identity_context_from_selected_import(selected, from_scratch=False) is None


def test_context_build_restores_cache_objects_and_original_presence() -> None:
    first = _track(1, track_id=mbid(1001))
    second = _track(2, track_id=mbid(1002))
    selected, album = _selected_album([(Item(), first), (Item(), second)])

    album_raw = album.raw_data
    album_item = album.item_data
    first_raw = first.raw_data
    first_item = first.item_data
    second_raw = second.raw_data
    assert "item_data" not in second.__dict__

    context = identity_context_from_selected_import(selected, from_scratch=False)

    assert context is not None
    assert album.__dict__["raw_data"] is album_raw
    assert album.__dict__["item_data"] is album_item
    assert first.__dict__["raw_data"] is first_raw
    assert first.__dict__["item_data"] is first_item
    assert second.__dict__["raw_data"] is second_raw
    assert "item_data" not in second.__dict__


def test_current_ids_do_not_affect_candidate_scores_or_ranking() -> None:
    correct = candidate(release=mbid(301), release_group=mbid(401))
    structurally_wrong = candidate(
        release=mbid(999),
        release_group=mbid(998),
        tracks=tuple(
            candidate_track(index, title=f"Unrelated {index}") for index in range(1, 4)
        ),
    )
    candidates = (structurally_wrong, correct)
    missing_pairs = [
        (Item(), _track(index, artist="Example Artist", album="Example Album"))
        for index in range(1, 4)
    ]
    wrong_pairs = [
        (
            Item(
                mb_albumid=structurally_wrong.release_mbid,
                mb_releasegroupid=structurally_wrong.release_group_mbid,
                mb_trackid=structurally_wrong.tracks[index - 1].recording_mbid,
                mb_releasetrackid=structurally_wrong.tracks[index - 1].release_track_mbid,
            ),
            _track(index, artist="Example Artist", album="Example Album"),
        )
        for index in range(1, 4)
    ]
    album_overrides = {"artist": "Example Artist", "album": "Example Album"}
    missing_selected, _ = _selected_album(
        missing_pairs, album_overrides=album_overrides
    )
    wrong_selected, _ = _selected_album(wrong_pairs, album_overrides=album_overrides)
    missing_source = _SyntheticSource(candidates)
    wrong_source = _SyntheticSource(candidates)

    missing = audit_selected_import_identity(
        missing_selected, missing_source, from_scratch=False
    )
    wrong = audit_selected_import_identity(wrong_selected, wrong_source, from_scratch=False)

    assert missing is not None
    assert wrong is not None
    assert missing_source.contexts[0].current_release_mbids == ()
    assert wrong_source.contexts[0].current_release_mbids == (
        structurally_wrong.release_mbid,
    ) * 3
    assert [evaluation.candidate for evaluation in missing.audit.evaluations] == [
        evaluation.candidate for evaluation in wrong.audit.evaluations
    ]
    assert [evaluation.score for evaluation in missing.audit.evaluations] == [
        evaluation.score for evaluation in wrong.audit.evaluations
    ]
    assert [evaluation.assignment for evaluation in missing.audit.evaluations] == [
        evaluation.assignment for evaluation in wrong.audit.evaluations
    ]
    assert missing.audit.selected_candidate == correct
    assert wrong.audit.selected_candidate == correct
