from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from beets.library import Album, Item, Library

from beetsplug.noqlenmeta.identity import (
    BlockedIdentityTagFile,
    IdentityTagDatabaseVerdict,
    LibraryIdentityTargetKind,
    prepare_identity_tag_database_target,
    select_library_identity_targets,
)

from .helpers import mbid


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return Library(str(tmp_path / "library.db"), set_music_dir=False)


def _album(library: Library, tmp_path: Path, count: int = 2) -> Album:
    items = [
        Item(
            path=str(tmp_path / f"track-{index}.flac").encode(),
            albumartist="Example Artist",
            album="Example Album",
            artist="Example Artist",
            title=f"Track {index}",
            disc=1,
            track=index,
            mb_albumid=mbid(10),
            mb_releasegroupid=mbid(11),
            mb_trackid=mbid(100 + index),
            mb_releasetrackid=mbid(200 + index),
        )
        for index in range(1, count + 1)
    ]
    album = library.add_album(items)
    album.mb_albumid = mbid(10)
    album.mb_releasegroupid = mbid(11)
    album.store(inherit=False)
    return album


def _singleton(library: Library, tmp_path: Path) -> Item:
    item = Item(
        path=str(tmp_path / "single.flac").encode(),
        artist="Example Artist",
        title="Single",
        mb_albumid=mbid(20),
        mb_releasegroupid=mbid(21),
        mb_trackid=mbid(22),
        mb_releasetrackid=mbid(23),
    )
    library.add(item)
    return item


def _prepare(library: Library, query: str | None = None):
    target = select_library_identity_targets(library, query)[0]
    return prepare_identity_tag_database_target(library, target)


def test_coherent_complete_album_and_singleton_are_ready(
    library: Library, tmp_path: Path
) -> None:
    album = _album(library, tmp_path)
    singleton = _singleton(library, tmp_path)

    album_target = _prepare(library, f"album_id:{album.id}")
    singleton_target = _prepare(library, f"id:{singleton.id}")

    assert album_target.kind is LibraryIdentityTargetKind.ALBUM
    assert singleton_target.kind is LibraryIdentityTargetKind.SINGLETON
    assert all(file.verdict is IdentityTagDatabaseVerdict.READY for file in album_target.files)
    assert singleton_target.files[0].expected is not None


@pytest.mark.parametrize(
    ("scope", "field", "value"),
    [
        ("album", "mb_albumid", ""),
        ("item", "mb_albumid", ""),
        ("item", "mb_albumid", mbid(999)),
        ("item", "mb_trackid", "not-a-uuid"),
        ("item", "mb_trackid", ""),
        ("item", "mb_releasetrackid", ""),
    ],
    ids=[
        "missing-album-row",
        "missing-item-album",
        "conflicting-album-copy",
        "malformed",
        "missing-track",
        "missing-release-track",
    ],
)
def test_incomplete_or_inconsistent_album_identity_is_blocked(
    library: Library,
    tmp_path: Path,
    scope: str,
    field: str,
    value: str,
) -> None:
    album = _album(library, tmp_path)
    if scope == "album":
        setattr(album, field, value)
        album.store(inherit=False)
    else:
        item = next(iter(album.items()))
        setattr(item, field, value)
        item.store()

    prepared = _prepare(library, f"album_id:{album.id}")

    assert prepared.blocked_reason == "database identity incomplete or inconsistent"
    assert all(file.expected is None for file in prepared.files)


def test_repeated_recording_is_allowed_but_repeated_release_track_is_blocked(
    library: Library, tmp_path: Path
) -> None:
    album = _album(library, tmp_path)
    first, second = tuple(album.items())
    second.mb_trackid = first.mb_trackid
    second.store()
    assert _prepare(library, f"album_id:{album.id}").blocked_reason is None

    second.mb_releasetrackid = first.mb_releasetrackid
    second.store()
    assert (
        _prepare(library, f"album_id:{album.id}").blocked_reason
        == "database release-track identity is duplicated"
    )


def test_preparation_refreshes_stale_query_objects_and_detects_path_changes(
    library: Library, tmp_path: Path
) -> None:
    singleton = _singleton(library, tmp_path)
    selected = select_library_identity_targets(library, f"id:{singleton.id}")[0]
    selected.items[0].item.path = b"private-stale-path.flac"
    fresh = library.get_item(singleton.id)
    assert fresh is not None
    fresh.path = str(tmp_path / "changed.flac").encode()
    fresh.store()

    prepared = prepare_identity_tag_database_target(library, selected)

    assert prepared.files[0].selected.path == fresh.path
    assert b"private-stale-path.flac" not in repr(prepared).encode()


def test_snapshots_are_immutable_and_hide_paths_and_raw_identity(
    library: Library, tmp_path: Path
) -> None:
    singleton = _singleton(library, tmp_path)
    prepared = _prepare(library, f"id:{singleton.id}")
    snapshot = prepared.snapshot.item_snapshots[0]

    with pytest.raises(FrozenInstanceError):
        snapshot.mtime = 9.0  # type: ignore[misc]
    rendered = repr(snapshot)
    assert str(tmp_path) not in rendered
    assert mbid(20) not in rendered


def test_empty_persisted_path_is_a_blocked_non_write_eligible_file(
    library: Library,
) -> None:
    item = Item(
        path=b"",
        artist="Example Artist",
        title="No Path",
        mb_albumid=mbid(30),
        mb_releasegroupid=mbid(31),
        mb_trackid=mbid(32),
        mb_releasetrackid=mbid(33),
    )
    library.add(item)

    prepared = _prepare(library, f"id:{item.id}")

    assert prepared.blocked_reason == "database file path is unavailable"
    assert len(prepared.files) == 1
    assert type(prepared.files[0].selected) is BlockedIdentityTagFile
    assert prepared.files[0].expected is None
    assert "path" not in repr(prepared.files[0].selected).lower()
