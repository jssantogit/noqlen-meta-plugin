from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from beets.library import Item, Library

from beetsplug.noqlenmeta.acoustid import (
    AcoustIDExistingValues,
    AcoustIDLibraryTargetKind,
    AcoustIDStoredValueState,
    SelectedAcoustIDItem,
    SelectedAcoustIDTarget,
    refresh_acoustid_target,
    select_acoustid_targets,
)


@pytest.fixture
def library(tmp_path) -> Library:
    return Library(str(tmp_path / "library.db"), set_music_dir=False)


def add_album(
    library: Library,
    title: str,
    positions: tuple[tuple[int, int], ...] = ((1, 1), (1, 2)),
):
    items = [
        Item(
            albumartist="Artist",
            album=title,
            artist="Artist",
            title=f"{title} {index}",
            length=100 + index,
            disc=disc,
            track=track,
            path=f"/private/{title}-{index}.flac".encode(),
        )
        for index, (disc, track) in enumerate(positions, 1)
    ]
    album = library.add_album(items)
    assert album.id is not None
    return album, items


def add_singleton(library: Library, title: str) -> Item:
    item = Item(
        artist="Artist",
        title=title,
        length=90,
        path=f"/private/{title}.flac".encode(),
    )
    library.add(item)
    assert item.id is not None
    return item


def test_matched_album_item_expands_to_complete_fresh_album(library: Library) -> None:
    album, stale_items = add_album(library, "Complete")

    targets = select_acoustid_targets(library, "title:Complete 2")

    assert len(targets) == 1
    assert targets[0].kind is AcoustIDLibraryTargetKind.ALBUM
    assert targets[0].album_id == album.id
    assert [item.item.title for item in targets[0].items] == ["Complete 1", "Complete 2"]
    assert all(item.item not in stale_items for item in targets[0].items)


def test_matched_singleton_remains_singleton(library: Library) -> None:
    item = add_singleton(library, "Loose")

    target = select_acoustid_targets(library, f"id:{item.id}")[0]

    assert target.kind is AcoustIDLibraryTargetKind.SINGLETON
    assert target.album_id is None
    assert len(target.items) == 1
    assert target.items[0].item_id == item.id
    assert target.items[0].item is not item


def test_mixed_target_order_is_album_then_singleton_by_database_id(library: Library) -> None:
    album_two, _ = add_album(library, "Album B", ((1, 1),))
    singleton_one = add_singleton(library, "Loose B")
    album_one, _ = add_album(library, "Album A", ((1, 1),))
    singleton_two = add_singleton(library, "Loose A")

    targets = select_acoustid_targets(library)

    assert [target.kind for target in targets] == [
        AcoustIDLibraryTargetKind.ALBUM,
        AcoustIDLibraryTargetKind.ALBUM,
        AcoustIDLibraryTargetKind.SINGLETON,
        AcoustIDLibraryTargetKind.SINGLETON,
    ]
    assert [target.album_id for target in targets[:2]] == sorted([album_two.id, album_one.id])
    assert [target.items[0].item_id for target in targets[2:]] == sorted(
        [singleton_one.id, singleton_two.id]
    )


def test_duplicate_query_matches_do_not_duplicate_target(library: Library, monkeypatch) -> None:
    _, items = add_album(library, "Duplicate", ((1, 1),))
    original_items = Library.items

    def duplicate_items(self, query=None):
        if query == "duplicate-query":
            fresh = self.get_item(items[0].id)
            assert fresh is not None
            return (fresh, fresh)
        return original_items(self, query)

    monkeypatch.setattr(Library, "items", duplicate_items)

    targets = select_acoustid_targets(library, "duplicate-query")

    assert len(targets) == 1


def test_album_items_order_positions_then_id_with_missing_last(library: Library) -> None:
    _, inserted = add_album(library, "Order", ((2, 1), (1, 2), (1, 1), (0, 3), (1, 0)))

    target = select_acoustid_targets(library, "album:Order")[0]

    assert [item.item_id for item in target.items] == [
        inserted[2].id,
        inserted[1].id,
        inserted[4].id,
        inserted[0].id,
        inserted[3].id,
    ]
    assert [item.local_key for item in target.items] == [
        f"library-item:{item.item_id}" for item in target.items
    ]


def test_existing_fields_are_read_only_from_fresh_items(library: Library) -> None:
    _, inserted = add_album(library, "Values", ((1, 1),))
    stale = inserted[0]
    stored = library.get_item(stale.id)
    assert stored is not None
    stored.acoustid_id = "00000001-0000-4000-8000-000000000001"
    stored.acoustid_fingerprint = "stored-private-fingerprint"
    stored.length = 123
    stored.store()
    stale.acoustid_id = "malformed-stale-id"
    stale.acoustid_fingerprint = "stale-private-fingerprint"

    selected = select_acoustid_targets(library, f"id:{stale.id}")[0].items[0]

    assert selected.item is not stale
    assert selected.existing_values.acoustid_id_state is AcoustIDStoredValueState.VALID
    assert selected.existing_values.fingerprint_state is AcoustIDStoredValueState.VALID
    assert selected.existing_values.duration_seconds == 123.0
    assert selected.media_path == selected.item.path
    assert selected.existing_values == AcoustIDExistingValues.from_stored(
        selected.item.acoustid_id,
        selected.item.acoustid_fingerprint,
        selected.item.length,
    )
    rendered = repr(selected)
    assert "/private" not in rendered
    assert "stored-private-fingerprint" not in rendered
    assert "stale-private-fingerprint" not in rendered
    assert "/private" not in repr(select_acoustid_targets(library)[0])


def test_selection_rejects_unsupported_library_and_query_item_types(
    library: Library, monkeypatch
) -> None:
    with pytest.raises(TypeError, match="supported Library"):
        select_acoustid_targets(object())  # type: ignore[arg-type]

    monkeypatch.setattr(Library, "items", lambda self, query=None: (object(),))
    with pytest.raises(TypeError, match="unsupported Item"):
        select_acoustid_targets(library, "bad")


def test_refresh_rejects_missing_album_and_singleton(library: Library, monkeypatch) -> None:
    add_album(library, "Missing", ((1, 1),))
    album_target = select_acoustid_targets(library, "album:Missing")[0]
    monkeypatch.setattr(Library, "get_album", lambda self, album_id: None)
    with pytest.raises(ValueError) as album_error:
        refresh_acoustid_target(library, album_target)
    assert "/private" not in str(album_error.value)

    monkeypatch.undo()
    singleton = add_singleton(library, "Gone")
    singleton_target = select_acoustid_targets(library, f"id:{singleton.id}")[0]
    monkeypatch.setattr(Library, "get_item", lambda self, item_id: None)
    with pytest.raises(ValueError) as singleton_error:
        refresh_acoustid_target(library, singleton_target)
    assert "/private" not in str(singleton_error.value)


def test_refresh_rejects_album_and_singleton_membership_changes(library: Library) -> None:
    album, _ = add_album(library, "Changing", ((1, 1),))
    album_target = select_acoustid_targets(library, "album:Changing")[0]
    extra = Item(
        album_id=album.id,
        album="Changing",
        artist="Artist",
        title="Added",
        path=b"/private/added.flac",
    )
    library.add(extra)
    with pytest.raises(ValueError, match="membership changed"):
        refresh_acoustid_target(library, album_target)

    singleton = add_singleton(library, "Moved")
    singleton_target = select_acoustid_targets(library, f"id:{singleton.id}")[0]
    moved = library.get_item(singleton.id)
    assert moved is not None
    moved.album_id = album.id
    moved.store()
    with pytest.raises(ValueError, match="membership changed"):
        refresh_acoustid_target(library, singleton_target)


def test_selection_has_no_filesystem_or_backend_boundary(library: Library, monkeypatch) -> None:
    add_singleton(library, "No Work")

    monkeypatch.setattr(
        "beetsplug.noqlenmeta.acoustid.backend.acquire_source_snapshot",
        lambda path: (_ for _ in ()).throw(AssertionError("snapshot called")),
    )

    assert len(select_acoustid_targets(library)) == 1


def test_selected_values_reject_inconsistent_direct_construction() -> None:
    item = Item(id=1, album_id=None, path=b"private.flac")
    existing = AcoustIDExistingValues.from_stored(None, None, None)

    with pytest.raises(ValueError, match="local key"):
        SelectedAcoustIDItem("wrong:1", 1, None, item, item.path, existing)
    with pytest.raises(TypeError, match="Item"):
        SelectedAcoustIDItem(
            "library-item:1", 1, None, object(), b"private.flac", existing  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="membership"):
        SelectedAcoustIDItem("library-item:1", 1, 2, item, item.path, existing)
    with pytest.raises(ValueError, match="media path"):
        SelectedAcoustIDItem("library-item:1", 1, None, item, b"", existing)

    selected_item = SelectedAcoustIDItem(
        "library-item:1", 1, None, item, item.path, existing
    )
    with pytest.raises(ValueError, match="unrelated"):
        SelectedAcoustIDTarget(AcoustIDLibraryTargetKind.ALBUM, 2, (selected_item,))
    with pytest.raises(ValueError, match="duplicated"):
        SelectedAcoustIDTarget(
            AcoustIDLibraryTargetKind.SINGLETON, None, (selected_item, selected_item)
        )
    with pytest.raises(FrozenInstanceError):
        selected_item.item_id = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    "media_path",
    [b"different.flac", "private.flac"],
    ids=["different-path", "unequal-path-representation"],
)
def test_selected_item_requires_the_retained_items_exact_path(media_path: bytes | str) -> None:
    item = Item(id=1, album_id=None, path=b"private.flac")
    existing = AcoustIDExistingValues.from_stored(None, None, None)

    with pytest.raises(ValueError) as captured:
        SelectedAcoustIDItem("library-item:1", 1, None, item, media_path, existing)

    assert str(captured.value) == "selected AcoustID media path is invalid"
    assert "private.flac" not in str(captured.value)


@pytest.mark.parametrize("item_path", [None, b"", ""])
def test_selected_item_rejects_unsupported_or_empty_retained_path(item_path: object) -> None:
    item = Item(id=1, album_id=None, path=item_path)
    existing = AcoustIDExistingValues.from_stored(None, None, None)

    with pytest.raises(ValueError) as captured:
        SelectedAcoustIDItem(
            "library-item:1",
            1,
            None,
            item,
            item_path,  # type: ignore[arg-type]
            existing,
        )

    assert str(captured.value) == "selected AcoustID media path is invalid"
    assert repr(item) not in str(captured.value)


@pytest.mark.parametrize(
    "existing",
    [
        AcoustIDExistingValues.from_stored(None, "stored-fingerprint", 120),
        AcoustIDExistingValues.from_stored(
            "00000002-0000-4000-8000-000000000002", "stored-fingerprint", 120
        ),
        AcoustIDExistingValues.from_stored(
            "00000001-0000-4000-8000-000000000001", "different-fingerprint", 120
        ),
        AcoustIDExistingValues.from_stored(
            "00000001-0000-4000-8000-000000000001", "stored-fingerprint", 121
        ),
    ],
    ids=["acoustid-id-state", "acoustid-id-value", "fingerprint", "duration"],
)
def test_selected_item_requires_exact_fresh_existing_values(
    existing: AcoustIDExistingValues,
) -> None:
    item = Item(
        id=1,
        album_id=None,
        path=b"private.flac",
        acoustid_id="00000001-0000-4000-8000-000000000001",
        acoustid_fingerprint="stored-fingerprint",
        length=120,
    )

    with pytest.raises(ValueError) as captured:
        SelectedAcoustIDItem("library-item:1", 1, None, item, item.path, existing)

    assert str(captured.value) == "selected AcoustID existing values are invalid"
    rendered = str(captured.value)
    assert "private.flac" not in rendered
    assert "stored-fingerprint" not in rendered
    assert repr(item) not in rendered


def test_selected_item_mismatch_error_does_not_disclose_malformed_stored_id() -> None:
    malformed_id = "malformed-private-id"
    item = Item(
        id=1,
        album_id=None,
        path=b"private.flac",
        acoustid_id=malformed_id,
        acoustid_fingerprint="stored-fingerprint",
        length=120,
    )
    inconsistent = AcoustIDExistingValues.from_stored(None, "stored-fingerprint", 120)

    with pytest.raises(ValueError) as captured:
        SelectedAcoustIDItem("library-item:1", 1, None, item, item.path, inconsistent)

    assert str(captured.value) == "selected AcoustID existing values are invalid"
    assert malformed_id not in str(captured.value)
    assert repr(item) not in str(captured.value)


def test_refresh_rejects_an_inconsistent_private_refresh_source(library: Library) -> None:
    add_album(library, "First", ((1, 1),))
    add_album(library, "Second", ((1, 1),))
    first, second = select_acoustid_targets(library)
    inconsistent = SelectedAcoustIDTarget(
        first.kind,
        first.album_id,
        first.items,
        second._refresh_source,
    )

    with pytest.raises(ValueError, match="inconsistent"):
        refresh_acoustid_target(library, inconsistent)
