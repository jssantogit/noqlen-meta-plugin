from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from beets.dbcore.db import Transaction
from beets.library import Album, Item, Library

import beetsplug.noqlenmeta.identity.library_application as application_module
from beetsplug.noqlenmeta.identity import (
    IdentityVerdict,
    LibraryIdentityApplicationError,
    LibraryIdentityAuditResult,
    LibraryIdentityTargetKind,
    SelectedLibraryIdentityTarget,
    apply_library_identity_plan,
    audit_musicbrainz_identity,
    identity_context_from_library_target,
    map_library_identity_targets,
    select_library_identity_targets,
)

from .helpers import candidate, mbid


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return Library(str(tmp_path / "library.db"), set_music_dir=False)


def _add_album(
    library: Library,
    *,
    tracks: int = 2,
    identity_state: str = "missing",
) -> SelectedLibraryIdentityTarget:
    items = []
    for index in range(1, tracks + 1):
        values: dict[str, object] = {
            "albumartist": "Example Artist",
            "album": "Example Album",
            "artist": "Example Artist",
            "title": f"Track {index}",
            "length": 180.0 + index,
            "disc": 1,
            "track": index,
            "path": f"album-{index}.flac".encode(),
        }
        if identity_state != "missing":
            offset = 0 if identity_state == "confirmed" else 800
            values.update(
                mb_albumid=mbid(100 + offset),
                mb_releasegroupid=mbid(200 + offset),
                mb_trackid=mbid(1000 + index + offset),
                mb_releasetrackid=mbid(2000 + index + offset),
            )
        items.append(Item(**values))
    album = library.add_album(items)
    assert album.id is not None
    return next(
        target
        for target in select_library_identity_targets(library)
        if target.kind is LibraryIdentityTargetKind.ALBUM and target.album_id == album.id
    )


def _add_singleton(library: Library) -> SelectedLibraryIdentityTarget:
    item = Item(
        album="Example Album",
        artist="Example Artist",
        title="Track 1",
        length=181.0,
        disc=1,
        track=1,
        path=b"singleton.flac",
    )
    library.add(item)
    assert item.id is not None
    return next(
        target
        for target in select_library_identity_targets(library)
        if target.kind is LibraryIdentityTargetKind.SINGLETON
        and target.items[0].item_id == item.id
    )


def _plan(
    target: SelectedLibraryIdentityTarget,
    *,
    candidates: object = None,
):
    context_result = identity_context_from_library_target(target)
    assert context_result is not None
    if candidates is None:
        candidates = (candidate(len(target.items), album=context_result.context.album),)
    audit = audit_musicbrainz_identity(context_result.context, candidates)
    source = LibraryIdentityAuditResult(context_result, audit)
    return map_library_identity_targets(source)


def _persisted_identity(
    library: Library, target: SelectedLibraryIdentityTarget
) -> tuple[tuple[str | None, ...], tuple[tuple[str | None, ...], ...]]:
    album_values: tuple[str | None, ...] = ()
    if target.album_id is not None:
        album = library.get_album(target.album_id)
        assert album is not None
        album_values = (album.mb_albumid, album.mb_releasegroupid)
    item_values = []
    for selected_item in target.items:
        item = library.get_item(selected_item.item_id)
        assert item is not None
        item_values.append(
            tuple(
                item.get(field, with_album=False)
                for field in (
                    "mb_albumid",
                    "mb_releasegroupid",
                    "mb_trackid",
                    "mb_releasetrackid",
                )
            )
        )
    return album_values, tuple(item_values)


def _reject_model_and_file_apis(monkeypatch: pytest.MonkeyPatch) -> None:
    for model, method in (
        (Album, "store"),
        (Item, "store"),
        (Item, "write"),
        (Album, "try_sync"),
        (Item, "try_sync"),
        (Album, "move"),
        (Item, "move"),
        (Item, "copy"),
    ):
        monkeypatch.setattr(
            model,
            method,
            lambda *args, method=method, **kwargs: pytest.fail(f"called {method}"),
        )


def test_beets_root_transaction_commits_when_context_exits_with_exception(
    library: Library,
) -> None:
    target = _add_singleton(library)
    item_id = target.items[0].item_id

    with pytest.raises(RuntimeError, match="root transaction exception"):
        with library.transaction() as tx:
            tx.mutate("UPDATE items SET mb_trackid=? WHERE id=?", (mbid(777), item_id))
            raise RuntimeError("root transaction exception")

    persisted = library.get_item(item_id)
    assert persisted is not None
    assert persisted.get("mb_trackid", with_album=False) == mbid(777)


def test_album_repair_updates_fixed_columns_and_assigned_item_fields(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    target = _add_album(library)
    plan = _plan(target)
    planning_values = (
        deepcopy(dict(target.album)) if target.album is not None else None,
        tuple(deepcopy(dict(item.item)) for item in target.items),
    )
    source_before = plan.source
    snapshot_before = plan.source.exact_snapshot
    changes_before = plan.changes
    _reject_model_and_file_apis(monkeypatch)

    result = apply_library_identity_plan(library, target, plan)

    assert result.applied_changes == plan.changes
    assert _persisted_identity(library, target) == (
        (mbid(100), mbid(200)),
        (
            (mbid(100), mbid(200), mbid(1001), mbid(2001)),
            (mbid(100), mbid(200), mbid(1002), mbid(2002)),
        ),
    )
    assert plan.source is source_before
    assert plan.source.exact_snapshot is snapshot_before
    assert plan.changes is changes_before
    assert dict(target.album) == planning_values[0]
    assert tuple(dict(item.item) for item in target.items) == planning_values[1]


def test_singleton_repair_updates_its_four_fixed_item_columns(library: Library) -> None:
    target = _add_singleton(library)
    plan = _plan(target)

    result = apply_library_identity_plan(library, plan)

    assert result.has_applied_changes
    assert _persisted_identity(library, target) == (
        (),
        ((mbid(100), mbid(200), mbid(1001), mbid(2001)),),
    )


def test_confirmed_ambiguous_and_nonready_plans_do_not_open_a_transaction(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    confirmed = _plan(_add_album(library, identity_state="confirmed"))
    ambiguous_target = _add_singleton(library)
    ambiguous = _plan(ambiguous_target, candidates=())
    ready = _plan(_add_album(library))
    nonready_source = replace(ready.source, audit=replace(ready.source.audit, repair_ready=False))
    nonready = map_library_identity_targets(nonready_source)
    before = tuple(
        _persisted_identity(library, plan.source.selected)
        for plan in (confirmed, ambiguous, nonready)
    )
    mutations: list[str] = []
    original_mutate = Transaction.mutate

    def record_mutate(self: Transaction, statement: str, *args, **kwargs):
        mutations.append(statement)
        return original_mutate(self, statement, *args, **kwargs)

    monkeypatch.setattr(Transaction, "mutate", record_mutate)

    confirmed_result = apply_library_identity_plan(library, confirmed)
    ambiguous_result = apply_library_identity_plan(library, ambiguous)
    nonready_result = apply_library_identity_plan(library, nonready)

    assert confirmed_result.is_confirmed_noop
    assert ambiguous_result.verdict is IdentityVerdict.AMBIGUOUS
    assert ambiguous_result.is_blocked
    assert nonready_result.blocked_reason == "repair not ready"
    assert tuple(
        _persisted_identity(library, plan.source.selected)
        for plan in (confirmed, ambiguous, nonready)
    ) == before
    assert mutations == []


def test_forged_plan_is_rejected_without_writes(library: Library) -> None:
    target = _add_album(library)
    plan = _plan(target)
    forged = replace(
        plan,
        changes=(replace(plan.changes[0], target_value=mbid(9999)), *plan.changes[1:]),
    )
    before = _persisted_identity(library, target)

    with pytest.raises(LibraryIdentityApplicationError, match="canonical source"):
        apply_library_identity_plan(library, forged)

    assert _persisted_identity(library, target) == before


def test_stale_plan_is_rejected_without_identity_writes(library: Library) -> None:
    target = _add_album(library)
    plan = _plan(target)
    item_id = target.items[0].item_id
    with library.transaction() as tx:
        tx.mutate("UPDATE items SET title=? WHERE id=?", ("Changed concurrently", item_id))
    before = _persisted_identity(library, target)

    with pytest.raises(LibraryIdentityApplicationError, match="stale"):
        apply_library_identity_plan(library, plan)

    assert _persisted_identity(library, target) == before


def test_deleted_target_is_rejected_without_writes(library: Library) -> None:
    target = _add_album(library)
    plan = _plan(target)
    assert target.album_id is not None
    with library.transaction() as tx:
        tx.mutate("DELETE FROM albums WHERE id=?", (target.album_id,))
    after_delete = tuple(
        tuple(
            library.get_item(item.item_id).get(field, with_album=False)
            for field in ("mb_albumid", "mb_releasegroupid", "mb_trackid", "mb_releasetrackid")
        )
        for item in target.items
    )

    with pytest.raises(LibraryIdentityApplicationError, match="unavailable or structurally stale"):
        apply_library_identity_plan(library, plan)

    assert tuple(
        tuple(
            library.get_item(item.item_id).get(field, with_album=False)
            for field in ("mb_albumid", "mb_releasegroupid", "mb_trackid", "mb_releasetrackid")
        )
        for item in target.items
    ) == after_delete


def test_item_moved_out_of_album_is_rejected_without_identity_writes(library: Library) -> None:
    target = _add_album(library)
    plan = _plan(target)
    moved_id = target.items[-1].item_id
    with library.transaction() as tx:
        tx.mutate("UPDATE items SET album_id=NULL WHERE id=?", (moved_id,))
    before = _persisted_identity(library, target)

    with pytest.raises(LibraryIdentityApplicationError, match="structurally stale"):
        apply_library_identity_plan(library, plan)

    assert _persisted_identity(library, target) == before


def test_application_uses_named_savepoint_transaction_apis_and_verifies_before_release(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    plan = _plan(_add_album(library))
    calls: list[tuple[str, str]] = []
    original_mutate = Transaction.mutate
    original_query = Transaction.query

    def record_mutate(self: Transaction, statement: str, *args, **kwargs):
        calls.append(("mutate", statement))
        return original_mutate(self, statement, *args, **kwargs)

    def record_query(self: Transaction, statement: str, *args, **kwargs):
        calls.append(("query", statement))
        return original_query(self, statement, *args, **kwargs)

    monkeypatch.setattr(Transaction, "mutate", record_mutate)
    monkeypatch.setattr(Transaction, "query", record_query)

    apply_library_identity_plan(library, plan)

    savepoint = calls.index(("mutate", "SAVEPOINT noqlen_identity_target"))
    release = calls.index(("mutate", "RELEASE SAVEPOINT noqlen_identity_target"))
    in_savepoint = calls[savepoint : release + 1]
    assert in_savepoint[0] == ("mutate", "SAVEPOINT noqlen_identity_target")
    assert in_savepoint[-1] == ("mutate", "RELEASE SAVEPOINT noqlen_identity_target")
    assert any(
        kind == "mutate" and sql.startswith("UPDATE albums SET")
        for kind, sql in in_savepoint
    )
    assert any(
        kind == "mutate" and sql.startswith("UPDATE items SET")
        for kind, sql in in_savepoint
    )
    assert any(kind == "query" and sql.startswith("SELECT ") for kind, sql in in_savepoint)
    last_update = max(
        index
        for index, (kind, sql) in enumerate(calls)
        if kind == "mutate" and sql.startswith("UPDATE ")
    )
    assert any(kind == "query" for kind, _sql in calls[last_update + 1 : release])


def test_mid_update_failure_rolls_back_actual_database_changes_and_sends_no_events(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    target = _add_album(library)
    plan = _plan(target)
    before = _persisted_identity(library, target)
    original_mutate = Transaction.mutate
    update_count = 0
    failed = False
    events: list[object] = []

    def fail_after_mutation(self: Transaction, statement: str, *args, **kwargs):
        nonlocal failed, update_count
        result = original_mutate(self, statement, *args, **kwargs)
        if statement.startswith("UPDATE "):
            update_count += 1
            if update_count == 7:
                failed = True
                raise RuntimeError("injected after database mutation")
        return result

    monkeypatch.setattr(Transaction, "mutate", fail_after_mutation)
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda *args, **kwargs: events.append((args, kwargs)),
    )

    with pytest.raises(LibraryIdentityApplicationError, match="rolled back"):
        apply_library_identity_plan(library, plan)

    assert failed
    assert update_count == 7
    assert _persisted_identity(library, target) == before
    assert events == []


def test_postcommit_events_contain_fresh_changed_models(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    target = _add_album(library)
    plan = _plan(target)
    planning_models = {id(target.album), *(id(item.item) for item in target.items)}
    events: list[tuple[str, Library, Album | Item]] = []

    def capture(event: str, *, lib: Library, model: Album | Item) -> None:
        events.append((event, lib, model))

    monkeypatch.setattr(application_module.plugins, "send", capture)

    apply_library_identity_plan(library, plan)

    assert len(events) == 1 + len(target.items)
    assert all(event == "database_change" and lib is library for event, lib, _ in events)
    assert all(id(model) not in planning_models for _, _, model in events)
    assert all(not model._dirty for _, _, model in events)
    assert [type(model) for _, _, model in events] == [Album, Item, Item]
    assert [model.id for _, _, model in events] == [
        target.album_id,
        *(item.item_id for item in target.items),
    ]
