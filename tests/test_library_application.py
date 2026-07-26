from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from beets.library import Album, Item, Library

import beetsplug.noqlenmeta.library_application as application_module
from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.library_application import (
    LibraryApplicationError,
    apply_library_target_plan,
)
from beetsplug.noqlenmeta.library_mapping import (
    LibraryTargetPlan,
    map_change_plan_to_library_album,
)
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction


@pytest.fixture
def library() -> Library:
    return Library(":memory:", set_music_dir=False)


def add_album(lib: Library, *, tracks: int = 1, **overrides: object) -> Album:
    items = []
    for index in range(tracks):
        values: dict[str, object] = {
            "albumartist": "Gojira",
            "album": "From Mars to Sirius",
            "artist": "Gojira",
            "title": f"Track {index + 1}",
            "path": f"{index + 1:02}.flac".encode(),
        }
        values.update(overrides)
        items.append(Item(**values))
    album = lib.add_album(items)
    assert album.id is not None
    return lib.get_album(album.id)


def planned_change(field: str, after: object, before: object = None) -> PlannedChange:
    candidate = MetadataCandidate(
        field,
        after,  # type: ignore[arg-type]
        "discogs",
        0.95,
        "123456",
    )
    return PlannedChange(
        field,
        before,  # type: ignore[arg-type]
        candidate.value,
        candidate,
        f"resolved {field}",
    )


def target_plan(
    *changes: PlannedChange,
    reviews: tuple[FieldDecision, ...] = (),
) -> LibraryTargetPlan:
    return map_change_plan_to_library_album(ChangePlan(changes=changes, reviews=reviews))


def review() -> FieldDecision:
    return FieldDecision(
        "labels",
        None,
        None,
        ResolutionAction.REVIEW,
        "requires review",
    )


def test_genres_persist_and_inherit_as_a_fresh_list(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library, tracks=2)
    plan = target_plan(planned_change("genres", ("Rock", "Metal")))
    immutable_value = plan.mapped_changes[0].target_value
    original_store = Album.store
    store_calls: list[bool] = []

    def track_store(self: Album, fields: object = None, inherit: bool = True) -> None:
        store_calls.append(inherit)
        original_store(self, fields=fields, inherit=inherit)

    monkeypatch.setattr(Album, "store", track_store)

    result = apply_library_target_plan(album, plan)

    assert store_calls == [True]
    assert album.genres == ["Rock", "Metal"]
    assert isinstance(album.genres, list)
    assert album.genres is not immutable_value
    assert result.applied_changes == plan.mapped_changes
    assert result.has_applied_changes
    assert result.stored
    assert not result.is_blocked
    reloaded = library.get_album(album.id)
    assert reloaded.genres == ["Rock", "Metal"]
    assert [item.genres for item in reloaded.items()] == [
        ["Rock", "Metal"],
        ["Rock", "Metal"],
    ]
    with pytest.raises(FrozenInstanceError):
        result.stored = False  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value", "target", "expected"),
    [
        ("styles", ("Progressive Metal",), "style", "Progressive Metal"),
        ("labels", ("Roadrunner",), "label", "Roadrunner"),
        ("catalog_numbers", ("RR-123",), "catalognum", "RR-123"),
        ("barcodes", ("0123456789012",), "barcode", "0123456789012"),
        ("country", "DE", "country", "DE"),
        ("year", 2005, "year", 2005),
    ],
)
def test_scalar_fields_persist_and_inherit(
    library: Library,
    field: str,
    value: object,
    target: str,
    expected: object,
) -> None:
    album = add_album(library, tracks=2)

    result = apply_library_target_plan(album, target_plan(planned_change(field, value)))

    assert result.stored
    reloaded = library.get_album(album.id)
    assert getattr(reloaded, target) == expected
    assert [getattr(item, target) for item in reloaded.items()] == [expected, expected]


def test_empty_plan_does_not_store(monkeypatch: pytest.MonkeyPatch, library: Library) -> None:
    album = add_album(library)
    monkeypatch.setattr(Album, "store", lambda *args, **kwargs: pytest.fail("stored"))

    result = apply_library_target_plan(album, target_plan())

    assert not result.is_blocked
    assert not result.has_applied_changes
    assert not result.stored


@pytest.mark.parametrize(
    ("reviews", "blocked_values", "review_count", "blocker_count"),
    [
        ((review(),), None, 1, 0),
        ((), ("Label A", "Label B"), 0, 1),
        ((review(),), ("Label A", "Label B"), 1, 1),
    ],
)
def test_review_or_mapping_blocker_prevents_mutation_and_store(
    monkeypatch: pytest.MonkeyPatch,
    library: Library,
    reviews: tuple[FieldDecision, ...],
    blocked_values: tuple[str, ...] | None,
    review_count: int,
    blocker_count: int,
) -> None:
    album = add_album(library)
    changes = [planned_change("genres", ("Rock",))]
    if blocked_values is not None:
        changes.append(planned_change("labels", blocked_values))
    monkeypatch.setattr(Album, "store", lambda *args, **kwargs: pytest.fail("stored"))

    result = apply_library_target_plan(album, target_plan(*changes, reviews=reviews))

    assert album.genres == []
    assert result.is_blocked
    assert result.applied_changes == ()
    assert result.resolution_review_count == review_count
    assert result.mapping_blocker_count == blocker_count
    assert not result.stored


def test_fresh_persisted_state_prevents_concurrent_overwrite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database = str(tmp_path / "library.db")
    planning_library = Library(database, set_music_dir=False)
    original = add_album(planning_library, genres=["Rock"])
    plan = target_plan(
        planned_change("genres", ("Metal",), ("Rock",)),
        planned_change("year", 2005),
    )

    concurrent_library = Library(database, set_music_dir=False)
    concurrent = concurrent_library.get_album(original.id)
    concurrent.genres = ["Jazz"]
    concurrent.store(inherit=True)
    monkeypatch.setattr(Album, "store", lambda *args, **kwargs: pytest.fail("stored"))

    with pytest.raises(LibraryApplicationError, match="no longer matches"):
        apply_library_target_plan(original, plan)

    assert original.genres == ["Rock"]
    assert original.year == 0
    persisted = concurrent_library.get_album(original.id)
    assert persisted.genres == ["Jazz"]
    assert persisted.year == 0
    assert [item.genres for item in persisted.items()] == [["Jazz"]]


def test_deleted_album_is_reported_as_library_application_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database = str(tmp_path / "library.db")
    planning_library = Library(database, set_music_dir=False)
    original = add_album(planning_library)
    plan = target_plan(planned_change("genres", ("Metal",)))

    concurrent_library = Library(database, set_music_dir=False)
    concurrent_library.get_album(original.id).remove(with_items=False)
    monkeypatch.setattr(Album, "store", lambda *args, **kwargs: pytest.fail("stored"))

    with pytest.raises(LibraryApplicationError, match="no longer exists in the database"):
        apply_library_target_plan(original, plan)

    assert original.genres == []


def test_preexisting_dirty_album_is_rejected_before_noqlen_mutation(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library)
    album.album = "Owned by another operation"
    monkeypatch.setattr(Album, "store", lambda *args, **kwargs: pytest.fail("stored"))
    monkeypatch.setattr(
        Album,
        "get_fresh_from_db",
        lambda *args, **kwargs: pytest.fail("discarded dirty state by refreshing"),
    )

    with pytest.raises(LibraryApplicationError, match="pre-existing dirty"):
        apply_library_target_plan(album, target_plan(planned_change("genres", ("Rock",))))

    assert album.genres == []
    assert album.album == "Owned by another operation"


def test_forged_plan_is_rejected_without_mutation_or_store(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library)
    plan = target_plan(planned_change("genres", ("Rock",)))
    forged_change = replace(plan.mapped_changes[0], target_value=("Jazz",))
    forged = replace(plan, mapped_changes=(forged_change,))
    monkeypatch.setattr(Album, "store", lambda *args, **kwargs: pytest.fail("stored"))

    with pytest.raises(LibraryApplicationError, match="canonical source mapping"):
        apply_library_target_plan(album, forged)

    assert album.genres == []


def test_duplicate_target_is_rejected_before_mutation(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library)
    plan = target_plan(
        planned_change("genres", ("Rock",)),
        planned_change("year", 2005),
    )
    duplicate = replace(plan.mapped_changes[1], target_field="genres")
    forged = replace(plan, mapped_changes=(plan.mapped_changes[0], duplicate))
    monkeypatch.setattr(
        application_module,
        "map_change_plan_to_library_album",
        lambda source: forged,
    )
    monkeypatch.setattr(Album, "store", lambda *args, **kwargs: pytest.fail("stored"))

    with pytest.raises(LibraryApplicationError, match="duplicate Album target"):
        apply_library_target_plan(album, forged)

    assert album.genres == []
    assert album.year == 0


def test_malformed_target_shape_is_rejected_before_mutation(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library)
    plan = target_plan(planned_change("genres", ("Rock",)))
    malformed_change = replace(plan.mapped_changes[0], target_value="Rock")
    malformed = replace(plan, mapped_changes=(malformed_change,))
    monkeypatch.setattr(
        application_module,
        "map_change_plan_to_library_album",
        lambda source: malformed,
    )
    monkeypatch.setattr(Album, "store", lambda *args, **kwargs: pytest.fail("stored"))

    with pytest.raises(LibraryApplicationError, match="string-list target"):
        apply_library_target_plan(album, malformed)

    assert album.genres == []


def test_database_application_never_invokes_file_operations(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library)
    for model, method in (
        (Item, "write"),
        (Item, "try_sync"),
        (Album, "try_sync"),
        (Album, "move"),
        (Item, "move"),
    ):
        monkeypatch.setattr(
            model,
            method,
            lambda *args, method=method, **kwargs: pytest.fail(f"called {method}"),
        )

    result = apply_library_target_plan(
        album,
        target_plan(planned_change("genres", ("Rock", "Metal"))),
    )

    assert result.stored
    assert library.get_album(album.id).genres == ["Rock", "Metal"]
