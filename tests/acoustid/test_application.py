from __future__ import annotations

import os
import socket
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from beets.dbcore.db import Transaction
from beets.library import Item, Library

import beetsplug.noqlenmeta.acoustid.application as application_module
from beetsplug.noqlenmeta.acoustid import (
    AcoustIDApplicationError,
    AcoustIDApplicationFailure,
    AcoustIDDatabaseState,
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDFieldPlan,
    AcoustIDFingerprintMaterial,
    AcoustIDFingerprintOrigin,
    AcoustIDResultGroup,
    AcoustIDSourceSnapshot,
    AcoustIDTargetResult,
    AcoustIDTrackEvidence,
    AcoustIDTrackOutcome,
    FingerprintPreparationResult,
    apply_acoustid_results,
    canonical_acoustid_database_plan,
    classify_acoustid_evidence,
    select_acoustid_targets,
    snapshot_acoustid_target,
)

PRIVATE_PATH = b"/private/library/application.flac"
PRIVATE_FINGERPRINT = "private-application-fingerprint"
PRIVATE_KEY = "private-application-client-key"
ACOUSTID_ID = "00000001-0000-4000-8000-000000000001"
OTHER_ACOUSTID_ID = "00000002-0000-4000-8000-000000000002"
RECORDING_ID = "00000065-0000-4000-8000-000000000065"


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return Library(str(tmp_path / "library.db"), set_music_dir=False)


@pytest.fixture(autouse=True)
def stable_generated_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        application_module, "verify_source_snapshot", lambda path, expected: True
    )


def add_singleton(
    library: Library,
    number: int,
    *,
    acoustid_id: object = None,
    fingerprint: object = None,
    title: str | None = None,
):
    item = Item(
        artist="Original Artist",
        title=title or f"Track {number}",
        length=120,
        path=PRIVATE_PATH + str(number).encode(),
        acoustid_id=acoustid_id,
        acoustid_fingerprint=fingerprint,
        mb_trackid="00000090-0000-4000-8000-000000000090",
    )
    library.add(item)
    assert item.id is not None
    return select_acoustid_targets(library, f"id:{item.id}")[0]


def add_album(library: Library, number: int, *, tracks: int = 2):
    items = [
        Item(
            albumartist="Original Artist",
            album=f"Album {number}",
            artist="Original Artist",
            title=f"Album {number} Track {index}",
            length=120 + index,
            disc=1,
            track=index,
            path=PRIVATE_PATH + f"-{number}-{index}".encode(),
        )
        for index in range(1, tracks + 1)
    ]
    album = library.add_album(items)
    assert album.id is not None
    return next(
        target
        for target in select_acoustid_targets(library)
        if target.album_id == album.id
    )


def source_snapshot(number: int) -> AcoustIDSourceSnapshot:
    return AcoustIDSourceSnapshot(1, number, 100 + number, 200 + number)


def unavailable(local_key: str, origin: AcoustIDFingerprintOrigin):
    return AcoustIDTrackEvidence(
        local_key,
        origin,
        (),
        AcoustIDEvidenceVerdict.UNAVAILABLE,
        None,
        None,
        AcoustIDEvidenceReason.LOOKUP_DISABLED,
        None,
        None,
        None,
        0,
        0,
    )


def decisive(local_key: str, origin: AcoustIDFingerprintOrigin):
    return classify_acoustid_evidence(
        local_key,
        origin,
        (AcoustIDResultGroup(ACOUSTID_ID, 0.99, (RECORDING_ID,)),),
        AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
    )


def prepared_result(
    target,
    *,
    generated_fingerprint: str | None = None,
    decisive_lookup: bool = False,
) -> AcoustIDTargetResult:
    snapshot = snapshot_acoustid_target(target)
    outcomes = []
    for index, selected in enumerate(target.items, start=1):
        if generated_fingerprint is not None:
            material = AcoustIDFingerprintMaterial(
                selected.local_key,
                generated_fingerprint,
                120,
                AcoustIDFingerprintOrigin.GENERATED,
                source_snapshot(index),
            )
            reason = AcoustIDEvidenceReason.FINGERPRINT_GENERATED
        elif selected.existing_values.is_fingerprint_reusable:
            material = AcoustIDFingerprintMaterial(
                selected.local_key,
                selected.existing_values._reusable_fingerprint(),
                selected.existing_values.duration_seconds,
                AcoustIDFingerprintOrigin.EXISTING,
            )
            reason = AcoustIDEvidenceReason.FINGERPRINT_REUSED
        else:
            material = None
            reason = AcoustIDEvidenceReason.FINGERPRINT_MISSING
        preparation = FingerprintPreparationResult(selected.local_key, material, reason)
        evidence = None
        if material is not None:
            evidence = (
                decisive(selected.local_key, material.origin)
                if decisive_lookup
                else unavailable(selected.local_key, material.origin)
            )
        outcomes.append(AcoustIDTrackOutcome(preparation, evidence))
    immutable_outcomes = tuple(outcomes)
    plan = canonical_acoustid_database_plan(snapshot, immutable_outcomes)
    return AcoustIDTargetResult(target, snapshot, immutable_outcomes, plan)


def blocked_result(target) -> AcoustIDTargetResult:
    snapshot = snapshot_acoustid_target(target)
    preparation = FingerprintPreparationResult(
        target.items[0].local_key,
        None,
        AcoustIDEvidenceReason.STALE_SOURCE_FILE,
    )
    outcomes = (AcoustIDTrackOutcome(preparation, None),)
    return AcoustIDTargetResult(
        target,
        snapshot,
        outcomes,
        canonical_acoustid_database_plan(snapshot, outcomes),
    )


def persisted(library: Library, item_id: int) -> tuple[object, object]:
    item = library.get_item(item_id)
    assert item is not None
    return (
        item.get("acoustid_id", with_album=False),
        item.get("acoustid_fingerprint", with_album=False),
    )


def acoustid_updates(statements: list[str]) -> list[str]:
    return [
        statement
        for statement in statements
        if statement.startswith("UPDATE items SET acoustid_")
    ]


def test_later_stale_target_blocks_every_write_in_global_preflight(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    first = prepared_result(
        add_singleton(library, 1),
        generated_fingerprint=PRIVATE_FINGERPRINT,
    )
    second = prepared_result(
        add_singleton(library, 2),
        generated_fingerprint=PRIVATE_FINGERPRINT,
    )
    second_id = second.planning_snapshot.items[0].item_id
    with library.transaction() as tx:
        tx.mutate("UPDATE items SET length=? WHERE id=?", (999, second_id))
    statements = []
    original_mutate = Transaction.mutate

    def record(self, statement, *args, **kwargs):
        statements.append(statement)
        return original_mutate(self, statement, *args, **kwargs)

    monkeypatch.setattr(Transaction, "mutate", record)

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (first, second))

    assert captured.value.failure is AcoustIDApplicationFailure.BLOCKED_PREFLIGHT
    assert captured.value.reason is AcoustIDEvidenceReason.STALE_TARGET
    assert acoustid_updates(statements) == []
    assert persisted(library, first.planning_snapshot.items[0].item_id) == ("", "")


@pytest.mark.parametrize(
    ("statement", "value"),
    [
        ("UPDATE items SET path=? WHERE id=?", b"/changed/private.flac"),
        ("UPDATE items SET length=? WHERE id=?", 121),
        ("UPDATE items SET acoustid_id=? WHERE id=?", "changed-raw-id"),
        (
            "UPDATE items SET acoustid_fingerprint=? WHERE id=?",
            "changed-private-fingerprint",
        ),
    ],
)
def test_exact_item_snapshot_changes_block_before_writes(
    statement: str,
    value: object,
    monkeypatch: pytest.MonkeyPatch,
    library: Library,
) -> None:
    result = prepared_result(add_singleton(library, 1))
    item_id = result.planning_snapshot.items[0].item_id
    with library.transaction() as tx:
        tx.mutate(statement, (value, item_id))
    writes = []
    original_mutate = Transaction.mutate

    def record(self, sql, *args, **kwargs):
        if sql.startswith("UPDATE items SET acoustid_"):
            writes.append(sql)
        return original_mutate(self, sql, *args, **kwargs)

    monkeypatch.setattr(Transaction, "mutate", record)

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    assert captured.value.reason is AcoustIDEvidenceReason.STALE_TARGET
    assert writes == []


@pytest.mark.parametrize("field_name", ["acoustid_id", "acoustid_fingerprint"])
def test_malformed_raw_value_change_is_detected_exactly(
    field_name: str, library: Library
) -> None:
    values = (
        {"acoustid_id": "bad-a"}
        if field_name == "acoustid_id"
        else {"fingerprint": " bad-a "}
    )
    result = prepared_result(add_singleton(library, 1, **values))
    item_id = result.planning_snapshot.items[0].item_id
    with library.transaction() as tx:
        tx.mutate(f"UPDATE items SET {field_name}=? WHERE id=?", (" bad-b ", item_id))

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    assert captured.value.reason is AcoustIDEvidenceReason.STALE_TARGET
    assert "bad-b" in persisted(library, item_id)[field_name == "acoustid_fingerprint"]


def test_album_membership_and_order_changes_block(library: Library) -> None:
    membership_result = prepared_result(add_album(library, 1))
    moved_id = membership_result.planning_snapshot.items[-1].item_id
    with library.transaction() as tx:
        tx.mutate("UPDATE items SET album_id=NULL WHERE id=?", (moved_id,))
    with pytest.raises(AcoustIDApplicationError):
        apply_acoustid_results(library, (membership_result,))

    order_result = prepared_result(add_album(library, 2))
    first_id, second_id = (
        item.item_id for item in order_result.planning_snapshot.items
    )
    with library.transaction() as tx:
        tx.mutate("UPDATE items SET track=2 WHERE id=?", (first_id,))
        tx.mutate("UPDATE items SET track=1 WHERE id=?", (second_id,))
    with pytest.raises(AcoustIDApplicationError):
        apply_acoustid_results(library, (order_result,))


def test_missing_target_blocks_before_writes(library: Library) -> None:
    result = prepared_result(add_singleton(library, 1))
    item_id = result.planning_snapshot.items[0].item_id
    with library.transaction() as tx:
        tx.mutate("DELETE FROM items WHERE id=?", (item_id,))

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    assert captured.value.reason is AcoustIDEvidenceReason.STALE_TARGET


@pytest.mark.parametrize("verifier", [lambda path, expected: False, lambda path, expected: 1 / 0])
def test_changed_or_unavailable_generated_source_blocks(
    verifier, monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    monkeypatch.setattr(application_module, "verify_source_snapshot", verifier)

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    assert captured.value.reason is AcoustIDEvidenceReason.STALE_SOURCE_FILE
    assert not captured.value.committed


def test_generated_source_verification_receives_exact_private_path_and_snapshot(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    calls = []

    def verify(path, expected):
        calls.append((path, expected))
        return True

    monkeypatch.setattr(application_module, "verify_source_snapshot", verify)

    apply_acoustid_results(library, (result,))

    expected = result.generated_source_snapshots[0]
    assert calls == [
        (result.planning_snapshot.items[0].media_path, expected.snapshot),
        (result.planning_snapshot.items[0].media_path, expected.snapshot),
    ]


def test_duplicate_target_item_id_and_local_key_are_rejected(library: Library) -> None:
    first = prepared_result(add_singleton(library, 1))
    with pytest.raises(AcoustIDApplicationError):
        apply_acoustid_results(library, (first, first))

    second = prepared_result(add_singleton(library, 2))
    object.__setattr__(
        second.planning_snapshot.items[0],
        "item_id",
        first.planning_snapshot.items[0].item_id,
    )
    with pytest.raises(AcoustIDApplicationError):
        apply_acoustid_results(library, (first, second))

    third = prepared_result(add_singleton(library, 3))
    duplicate_key = first.planning_snapshot.items[0].local_key
    object.__setattr__(third.planning_snapshot.items[0], "local_key", duplicate_key)
    object.__setattr__(third.outcomes[0].preparation, "local_key", duplicate_key)
    object.__setattr__(third.database_plan.tracks[0], "local_key", duplicate_key)
    with pytest.raises(AcoustIDApplicationError):
        apply_acoustid_results(library, (first, third))


def test_review_blocked_and_noncanonical_plans_cause_zero_writes(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    safe = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    review = prepared_result(
        add_singleton(
            library,
            2,
            acoustid_id=OTHER_ACOUSTID_ID,
            fingerprint="stored-private",
        ),
        decisive_lookup=True,
    )
    blocked = blocked_result(add_singleton(library, 3))
    original_track = safe.database_plan.tracks[0]
    tampered = replace(
        safe,
        database_plan=replace(
            safe.database_plan,
            tracks=(
                replace(
                    original_track,
                    acoustid_fingerprint=AcoustIDFieldPlan(AcoustIDDatabaseState.KEEP),
                ),
            ),
        ),
    )
    statements = []
    original_mutate = Transaction.mutate

    def record(self, statement, *args, **kwargs):
        statements.append(statement)
        return original_mutate(self, statement, *args, **kwargs)

    monkeypatch.setattr(Transaction, "mutate", record)

    for unsafe in (review, blocked, tampered):
        with pytest.raises(AcoustIDApplicationError):
            apply_acoustid_results(library, (safe, unsafe))

    assert acoustid_updates(statements) == []


def test_all_keep_is_true_noop_without_transaction_update_store_or_notification(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(add_singleton(library, 1))
    events = []
    mutations = []
    original_mutate = Transaction.mutate

    def record_mutate(self, statement, *args, **kwargs):
        mutations.append(statement)
        return original_mutate(self, statement, *args, **kwargs)

    monkeypatch.setattr(Transaction, "mutate", record_mutate)
    monkeypatch.setattr(Item, "store", lambda *args, **kwargs: pytest.fail("store called"))
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda *args, **kwargs: events.append((args, kwargs)),
    )

    applied = apply_acoustid_results(library, (result,))

    assert applied.is_confirmed_noop
    assert not applied.has_applied_changes
    assert applied.changed_item_count == 0
    assert mutations == []
    assert events == []


@pytest.mark.parametrize("mode", ["id", "fingerprint", "both"])
def test_precise_fields_persist_reload_and_query(
    mode: str, monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    target = add_singleton(
        library,
        1,
        fingerprint=PRIVATE_FINGERPRINT if mode == "id" else None,
    )
    result = prepared_result(
        target,
        generated_fingerprint=(PRIVATE_FINGERPRINT if mode != "id" else None),
        decisive_lookup=mode in {"id", "both"},
    )
    item_id = result.planning_snapshot.items[0].item_id
    original = library.get_item(item_id)
    assert original is not None
    before_mb = original.mb_trackid
    before_title = original.title
    before_mtime = original.mtime
    monkeypatch.setattr(Item, "store", lambda *args, **kwargs: pytest.fail("store called"))
    monkeypatch.setattr(Item, "write", lambda *args, **kwargs: pytest.fail("write called"))

    applied = apply_acoustid_results(library, (result,))

    expected_id = ACOUSTID_ID if mode in {"id", "both"} else ""
    expected_fingerprint = PRIVATE_FINGERPRINT
    assert persisted(library, item_id) == (expected_id, expected_fingerprint)
    fresh = library.get_item(item_id)
    assert fresh is not None
    assert fresh.mb_trackid == before_mb
    assert fresh.title == before_title
    assert fresh.mtime == before_mtime
    query_field = "acoustid_id" if mode in {"id", "both"} else "acoustid_fingerprint"
    query_value = expected_id if query_field == "acoustid_id" else expected_fingerprint
    assert [item.id for item in library.items(f'{query_field}:"{query_value}"')] == [item_id]
    assert applied.changed_item_count == 1
    assert applied.applied_field_count == (2 if mode == "both" else 1)


def test_unrelated_dirty_model_state_does_not_leak(library: Library) -> None:
    target = add_singleton(library, 1, title="Persisted Title")
    result = prepared_result(
        target, generated_fingerprint=PRIVATE_FINGERPRINT
    )
    result.selected.items[0].item.title = "Dirty Unstored Title"

    apply_acoustid_results(library, (result,))

    fresh = library.get_item(result.planning_snapshot.items[0].item_id)
    assert fresh is not None
    assert fresh.title == "Persisted Title"
    assert fresh.acoustid_fingerprint == PRIVATE_FINGERPRINT


def test_mid_target_failure_rolls_back_every_field_and_sends_no_notification(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1),
        generated_fingerprint=PRIVATE_FINGERPRINT,
        decisive_lookup=True,
    )
    item_id = result.planning_snapshot.items[0].item_id
    original_mutate = Transaction.mutate
    events = []

    def fail_after_first_update(self, statement, *args, **kwargs):
        value = original_mutate(self, statement, *args, **kwargs)
        if statement.startswith("UPDATE items SET acoustid_id"):
            raise RuntimeError("private raw injected failure")
        return value

    monkeypatch.setattr(Transaction, "mutate", fail_after_first_update)
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda *args, **kwargs: events.append((args, kwargs)),
    )

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    assert captured.value.failure is AcoustIDApplicationFailure.TARGET_ROLLED_BACK
    assert not captured.value.committed
    assert persisted(library, item_id) == ("", "")
    assert events == []
    assert "private raw" not in str(captured.value)


def test_current_row_mismatch_inside_savepoint_rolls_back(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    item_id = result.planning_snapshot.items[0].item_id
    original_apply = application_module._apply_and_verify_rows

    def inject_mismatch(tx, rows):
        tx.mutate("UPDATE items SET acoustid_id=? WHERE id=?", ("bad-race", item_id))
        return original_apply(tx, rows)

    monkeypatch.setattr(application_module, "_apply_and_verify_rows", inject_mismatch)

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    assert captured.value.failure is AcoustIDApplicationFailure.TARGET_ROLLED_BACK
    assert persisted(library, item_id) == ("", "")


def test_rollback_failure_is_integrity_critical_and_state_uncertain(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1),
        generated_fingerprint=PRIVATE_FINGERPRINT,
        decisive_lookup=True,
    )
    original_mutate = Transaction.mutate
    events = []

    def fail_update_and_rollback(self, statement, *args, **kwargs):
        if statement == "ROLLBACK TO SAVEPOINT noqlen_acoustid_target":
            raise RuntimeError("private rollback output")
        value = original_mutate(self, statement, *args, **kwargs)
        if statement.startswith("UPDATE items SET acoustid_id"):
            raise RuntimeError("private update output")
        return value

    monkeypatch.setattr(Transaction, "mutate", fail_update_and_rollback)
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda *args, **kwargs: events.append((args, kwargs)),
    )

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    error = captured.value
    assert error.failure is AcoustIDApplicationFailure.ROLLBACK_FAILED
    assert error.integrity_critical
    assert error.state_uncertain
    assert not error.committed
    assert "private" not in str(error)
    assert events == []


def test_root_exit_failure_after_release_reports_committed_state(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    original_preflight = application_module._preflight
    original_exit = Transaction.__exit__
    original_mutate = Transaction.mutate
    released_transactions = set()

    def arm_failure_after_preflight(*args, **kwargs):
        prepared = original_preflight(*args, **kwargs)

        def record_release(self, statement, *mutate_args, **mutate_kwargs):
            value = original_mutate(self, statement, *mutate_args, **mutate_kwargs)
            if statement == "RELEASE SAVEPOINT noqlen_acoustid_target":
                released_transactions.add(id(self))
            return value

        def fail_during_exit(self, *exit_args, **exit_kwargs):
            value = original_exit(self, *exit_args, **exit_kwargs)
            if id(self) in released_transactions:
                raise RuntimeError("private commit output")
            return value

        monkeypatch.setattr(Transaction, "mutate", record_release)
        monkeypatch.setattr(Transaction, "__exit__", fail_during_exit)
        return prepared

    monkeypatch.setattr(application_module, "_preflight", arm_failure_after_preflight)

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    error = captured.value
    assert error.failure is AcoustIDApplicationFailure.POST_COMMIT_FAILURE
    assert error.integrity_critical
    assert error.state_uncertain
    assert error.committed
    assert error.committed_target_count == 1
    assert error.changed_item_count == 1
    assert persisted(library, result.planning_snapshot.items[0].item_id)[1] == PRIVATE_FINGERPRINT
    assert "private" not in str(error)


def test_transaction_boundary_failure_before_release_reports_uncertain_uncommitted(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    original_mutate = Transaction.mutate

    def fail_savepoint(self, statement, *args, **kwargs):
        if statement == "SAVEPOINT noqlen_acoustid_target":
            raise RuntimeError("private transaction output")
        return original_mutate(self, statement, *args, **kwargs)

    monkeypatch.setattr(Transaction, "mutate", fail_savepoint)

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    error = captured.value
    assert error.failure is AcoustIDApplicationFailure.COMMIT_UNCERTAIN
    assert error.integrity_critical
    assert error.state_uncertain
    assert not error.committed
    assert error.committed_target_count == 0
    assert error.changed_item_count == 0
    assert "private" not in str(error)


def test_savepoint_verifies_before_release_and_notifies_after_commit(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    events = []
    original_mutate = Transaction.mutate
    original_require = application_module._require_current_snapshot

    def record_mutate(self, statement, *args, **kwargs):
        events.append(statement)
        return original_mutate(self, statement, *args, **kwargs)

    def record_snapshot(*args, **kwargs):
        events.append("snapshot verified")
        return original_require(*args, **kwargs)

    def record_notification(event, **kwargs):
        events.append(event)

    monkeypatch.setattr(Transaction, "mutate", record_mutate)
    monkeypatch.setattr(application_module, "_require_current_snapshot", record_snapshot)
    monkeypatch.setattr(application_module.plugins, "send", record_notification)

    apply_acoustid_results(library, (result,))

    savepoint = events.index("SAVEPOINT noqlen_acoustid_target")
    update = next(index for index, value in enumerate(events) if value.startswith("UPDATE "))
    release = events.index("RELEASE SAVEPOINT noqlen_acoustid_target")
    notifications = [index for index, value in enumerate(events) if value == "database_change"]
    snapshots = [index for index, value in enumerate(events) if value == "snapshot verified"]
    assert savepoint < snapshots[0] < update < snapshots[1] < release
    assert notifications and release < notifications[0]


def test_notifications_include_only_fresh_changed_items(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    target = add_album(library, 1)
    result = prepared_result(target, generated_fingerprint=PRIVATE_FINGERPRINT)
    first_track = result.database_plan.tracks[0]
    second_track = result.database_plan.tracks[1]
    mixed_plan = replace(
        result.database_plan,
        tracks=(
            first_track,
            replace(
                second_track,
                acoustid_fingerprint=AcoustIDFieldPlan(AcoustIDDatabaseState.KEEP),
            ),
        ),
    )
    # Keep the source canonical by removing material from the second outcome.
    second_preparation = FingerprintPreparationResult(
        result.outcomes[1].local_key,
        None,
        AcoustIDEvidenceReason.FINGERPRINT_MISSING,
    )
    outcomes = (
        result.outcomes[0],
        AcoustIDTrackOutcome(second_preparation, None),
    )
    canonical = canonical_acoustid_database_plan(result.planning_snapshot, outcomes)
    assert canonical == mixed_plan
    result = replace(result, outcomes=outcomes, database_plan=mixed_plan)
    events = []

    def capture(event, *, lib, model):
        events.append((event, lib, model))

    monkeypatch.setattr(application_module.plugins, "send", capture)

    apply_acoustid_results(library, (result,))

    assert len(events) == 1
    event, event_library, model = events[0]
    assert event == "database_change"
    assert event_library is library
    assert type(model) is Item
    assert model.id == result.planning_snapshot.items[0].item_id
    assert not model._dirty


@pytest.mark.parametrize("failure_point", ["verification", "notification"])
def test_postcommit_failure_reports_committed_state(
    failure_point: str, monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    if failure_point == "verification":
        monkeypatch.setattr(
            application_module,
            "_verify_after_commit",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("raw private")),
        )
    else:
        monkeypatch.setattr(
            application_module.plugins,
            "send",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("raw private")),
        )

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (result,))

    error = captured.value
    assert error.failure is AcoustIDApplicationFailure.POST_COMMIT_FAILURE
    assert error.committed
    assert error.committed_target_count == 1
    assert error.changed_item_count == 1
    assert error.integrity_critical is (failure_point == "verification")
    assert error.state_uncertain is (failure_point == "verification")
    assert persisted(library, result.planning_snapshot.items[0].item_id)[1] == PRIVATE_FINGERPRINT
    assert "raw private" not in str(error)
    assert error.__cause__ is None


def test_later_target_failure_reports_earlier_commit(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    first = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    second = prepared_result(
        add_singleton(library, 2), generated_fingerprint=PRIVATE_FINGERPRINT
    )
    original_apply = application_module._apply_target
    calls = 0

    def fail_second(target_library, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise AcoustIDApplicationError(
                AcoustIDApplicationFailure.TARGET_ROLLED_BACK
            )
        return original_apply(target_library, target)

    monkeypatch.setattr(application_module, "_apply_target", fail_second)

    with pytest.raises(AcoustIDApplicationError) as captured:
        apply_acoustid_results(library, (first, second))

    error = captured.value
    assert error.failure is AcoustIDApplicationFailure.TARGET_ROLLED_BACK
    assert error.committed
    assert error.committed_target_count == 1
    assert error.changed_item_count == 1
    assert persisted(library, first.planning_snapshot.items[0].item_id)[1] == PRIVATE_FINGERPRINT
    assert persisted(library, second.planning_snapshot.items[0].item_id) == ("", "")


def test_application_has_no_backend_network_environment_or_audio_authority(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    result = prepared_result(
        add_singleton(library, 1), generated_fingerprint=PRIVATE_FINGERPRINT
    )

    def forbidden(*args, **kwargs):
        pytest.fail("forbidden Stage 04B boundary called")

    monkeypatch.setattr(Item, "write", forbidden)
    monkeypatch.setattr(Item, "store", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)

    applied = apply_acoustid_results(library, (result,))

    assert applied.has_applied_changes
    rendered = repr(applied)
    assert "/private" not in rendered
    assert PRIVATE_FINGERPRINT not in rendered
    assert PRIVATE_KEY not in rendered
    assert "mb_" not in repr(result.database_plan)
