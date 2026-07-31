from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from beets.library import Album, Item, Library

from beetsplug.noqlenmeta.identity import (
    IdentityAlbumContext,
    LibraryIdentityTargetKind,
    MusicBrainzReleaseIdentity,
    all_library_identity_targets,
    audit_library_identity_target,
    exact_snapshot_from_library_target,
    identity_context_from_library_target,
    refresh_library_identity_target,
    select_library_identity_targets,
)

from .helpers import candidate, mbid


@pytest.fixture
def library() -> Library:
    return Library(":memory:", set_music_dir=False)


def _add_album(
    library: Library,
    *,
    title: str = "Example Album",
    positions: tuple[tuple[int, int], ...] = ((1, 1), (1, 2), (1, 3)),
) -> Album:
    items = [
        Item(
            albumartist="Example Artist",
            album=title,
            artist="Example Artist",
            title=f"Track {track}",
            length=180.0 + track,
            disc=disc,
            track=track,
            path=f"private/{title}/{track:02}.flac".encode(),
        )
        for disc, track in positions
    ]
    album = library.add_album(items)
    assert album.id is not None
    fresh = library.get_album(album.id)
    assert fresh is not None
    return fresh


def _add_singleton(library: Library, *, title: str = "Loose Track") -> Item:
    item = Item(
        albumartist="",
        album="Loose Collection",
        artist="Example Artist",
        title=title,
        length=181.0,
        disc=1,
        track=1,
        year=2025,
        country="XE",
        label="Synthetic Label",
        path=f"private/{title}.flac".encode(),
    )
    library.add(item)
    assert item.id is not None
    return item


@dataclass
class _Source:
    candidates: tuple[MusicBrainzReleaseIdentity, ...]
    contexts: list[IdentityAlbumContext] = field(default_factory=list)

    def candidates_for(
        self, context: IdentityAlbumContext
    ) -> tuple[MusicBrainzReleaseIdentity, ...]:
        self.contexts.append(context)
        return self.candidates


def test_item_query_expands_complete_album_and_deduplicates_matches(
    library: Library,
) -> None:
    album = _add_album(library)

    one_match = select_library_identity_targets(library, "title:Track 2")
    all_matches = select_library_identity_targets(library, "album:Example Album")

    assert len(one_match) == len(all_matches) == 1
    assert one_match[0].kind is LibraryIdentityTargetKind.ALBUM
    assert one_match[0].album_id == album.id
    assert [item.item.title for item in one_match[0].items] == [
        "Track 1",
        "Track 2",
        "Track 3",
    ]
    assert [item.item_id for item in one_match[0].items] == [
        item.item_id for item in all_matches[0].items
    ]


def test_all_targets_include_albums_then_singletons_in_database_id_order(
    library: Library,
) -> None:
    second_album = _add_album(library, title="Album B", positions=((1, 1),))
    first_singleton = _add_singleton(library, title="Loose B")
    first_album = _add_album(library, title="Album A", positions=((1, 1),))
    second_singleton = _add_singleton(library, title="Loose A")

    targets = all_library_identity_targets(library)

    assert [target.kind for target in targets] == [
        LibraryIdentityTargetKind.ALBUM,
        LibraryIdentityTargetKind.ALBUM,
        LibraryIdentityTargetKind.SINGLETON,
        LibraryIdentityTargetKind.SINGLETON,
    ]
    assert [target.album_id for target in targets[:2]] == sorted([second_album.id, first_album.id])
    assert [target.items[0].item_id for target in targets[2:]] == sorted(
        [first_singleton.id, second_singleton.id]
    )


def test_selection_snapshot_is_fresh_and_omits_paths(library: Library) -> None:
    album = _add_album(library, positions=((1, 1),))
    stale_album = library.get_album(album.id)
    assert stale_album is not None
    stale_item = tuple(stale_album.items())[0]
    stale_album.album = "Dirty Album"
    stale_item.title = "Dirty Track"

    selected = all_library_identity_targets(library)[0]
    snapshot = exact_snapshot_from_library_target(selected)

    assert selected.album is not stale_album
    assert selected.items[0].item is not stale_item
    assert selected.album is not None
    assert selected.album.album == "Example Album"
    assert selected.items[0].item.title == "Track 1"
    assert dict(snapshot.album_fields)["album"] == "Example Album"
    assert dict(snapshot.item_snapshots[0].fields)["title"] == "Track 1"
    assert "path" not in dict(snapshot.album_fields)
    assert "path" not in dict(snapshot.item_snapshots[0].fields)


def test_refresh_reads_new_rows_without_mutating_the_original_snapshot(
    library: Library,
) -> None:
    _add_album(library, positions=((1, 1),))
    selected = all_library_identity_targets(library)[0]
    original = exact_snapshot_from_library_target(selected)
    item = library.get_item(selected.items[0].item_id)
    assert item is not None
    item.title = "Stored New Title"
    item.store()

    refreshed = refresh_library_identity_target(library, selected)
    refreshed_snapshot = exact_snapshot_from_library_target(refreshed)

    assert dict(original.item_snapshots[0].fields)["title"] == "Track 1"
    assert dict(refreshed_snapshot.item_snapshots[0].fields)["title"] == ("Stored New Title")


@pytest.mark.parametrize(
    ("positions", "expected_order", "expected_indexes"),
    [
        (((2, 1), (1, 2), (1, 1)), ["Track 1", "Track 2", "Track 1"], [1, 2, 3]),
        (((1, 1), (1, 1), (0, 3)), ["Track 1", "Track 1", "Track 3"], [None] * 3),
    ],
    ids=["complete-unique", "incomplete-or-duplicate"],
)
def test_album_order_and_ordinal_index_rules(
    library: Library,
    positions: tuple[tuple[int, int], ...],
    expected_order: list[str],
    expected_indexes: list[int | None],
) -> None:
    _add_album(library, positions=positions)

    result = identity_context_from_library_target(all_library_identity_targets(library)[0])

    assert result is not None
    assert [track.title for track in result.context.tracks] == expected_order
    assert [track.index for track in result.context.tracks] == expected_indexes


def test_album_current_ids_aggregate_album_and_every_item_in_order(
    library: Library,
) -> None:
    _add_album(library, positions=((1, 1), (1, 2)))
    selected = all_library_identity_targets(library)[0]
    assert selected.album is not None
    selected.album.mb_albumid = mbid(101)
    selected.album.mb_releasegroupid = mbid(201)
    selected.album.store()
    for index, selected_item in enumerate(selected.items, start=1):
        item = library.get_item(selected_item.item_id)
        assert item is not None
        item.mb_albumid = mbid(101 + index)
        item.mb_releasegroupid = mbid(201 + index)
        item.mb_trackid = mbid(1000 + index)
        item.mb_releasetrackid = mbid(2000 + index)
        item.store()

    result = identity_context_from_library_target(all_library_identity_targets(library)[0])

    assert result is not None
    assert result.context.current_release_mbids == (mbid(101), mbid(102), mbid(103))
    assert result.context.current_release_group_mbids == (
        mbid(201),
        mbid(202),
        mbid(203),
    )
    assert [track.current_recording_mbid for track in result.context.tracks] == [
        mbid(1001),
        mbid(1002),
    ]
    assert [track.current_release_track_mbid for track in result.context.tracks] == [
        mbid(2001),
        mbid(2002),
    ]


def test_singleton_context_carries_all_metadata_and_identity_fields(
    library: Library,
) -> None:
    item = _add_singleton(library)
    item.mb_albumid = mbid(100)
    item.mb_releasegroupid = mbid(200)
    item.mb_trackid = mbid(1001)
    item.mb_releasetrackid = mbid(2001)
    item.store()

    result = identity_context_from_library_target(all_library_identity_targets(library)[0])

    assert result is not None
    assert result.selected.kind is LibraryIdentityTargetKind.SINGLETON
    assert result.context.album_artist == "Example Artist"
    assert result.context.album == "Loose Collection"
    assert result.context.year == 2025
    assert result.context.country == "XE"
    assert result.context.label == "Synthetic Label"
    assert result.context.current_release_mbids == (mbid(100),)
    assert result.context.current_release_group_mbids == (mbid(200),)
    assert result.context.tracks[0].current_recording_mbid == mbid(1001)
    assert result.context.tracks[0].current_release_track_mbid == mbid(2001)


def test_audit_passes_the_pure_context_once_to_a_fake_block024_source(
    library: Library,
) -> None:
    _add_album(library)
    source = _Source((candidate(),))
    selected = all_library_identity_targets(library)[0]

    result = audit_library_identity_target(selected, source)

    assert result is not None
    assert source.contexts == [result.context]
    assert result.selected is selected
    assert result.exact_snapshot == exact_snapshot_from_library_target(selected)
    assert result.audit.selected_candidate == candidate()
