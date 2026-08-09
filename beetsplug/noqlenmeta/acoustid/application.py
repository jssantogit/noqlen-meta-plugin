"""Verified, database-only application of prepared AcoustID target results."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field

from beets import plugins
from beets.dbcore.db import Transaction
from beets.library import Item, Library

from .backend import verify_source_snapshot
from .domain import (
    AcoustIDApplicationError,
    AcoustIDApplicationFailure,
    AcoustIDApplicationResult,
    AcoustIDDatabaseState,
    AcoustIDDatabaseTargetPlan,
    AcoustIDEvidenceReason,
    AcoustIDFieldPlan,
    AcoustIDFingerprintMaterial,
    AcoustIDFingerprintOrigin,
    AcoustIDGeneratedSourceSnapshot,
    AcoustIDPlanningItemSnapshot,
    AcoustIDPlanningSnapshot,
    AcoustIDTargetResult,
    AcoustIDTrackDatabasePlan,
    AcoustIDTrackOutcome,
    FingerprintPreparationResult,
    SelectedAcoustIDItem,
    SelectedAcoustIDTarget,
)
from .library import refresh_acoustid_target
from .mapping import canonical_acoustid_database_plan, snapshot_acoustid_target

_SAVEPOINT = "noqlen_acoustid_target"
_SAVEPOINT_SQL = f"SAVEPOINT {_SAVEPOINT}"
_ROLLBACK_SQL = f"ROLLBACK TO SAVEPOINT {_SAVEPOINT}"
_RELEASE_SQL = f"RELEASE SAVEPOINT {_SAVEPOINT}"
_SELECT_SQL = "SELECT acoustid_id, acoustid_fingerprint FROM items WHERE id=?"
_UPDATE_SQL = {
    "acoustid_id": "UPDATE items SET acoustid_id=? WHERE id=?",
    "acoustid_fingerprint": "UPDATE items SET acoustid_fingerprint=? WHERE id=?",
}


class _PreflightFailure(Exception):
    def __init__(self, reason: AcoustIDEvidenceReason | None = None) -> None:
        self.reason = reason


class _StaleTarget(_PreflightFailure):
    def __init__(self) -> None:
        super().__init__(AcoustIDEvidenceReason.STALE_TARGET)


class _StaleSource(_PreflightFailure):
    def __init__(self) -> None:
        super().__init__(AcoustIDEvidenceReason.STALE_SOURCE_FILE)


@dataclass(frozen=True, slots=True)
class _ItemRowPlan:
    item_id: int
    local_key: str
    changed_fields: tuple[str, ...]
    before_id: object = dataclass_field(repr=False)
    before_fingerprint: object = dataclass_field(repr=False)
    after_id: object = dataclass_field(repr=False)
    after_fingerprint: object = dataclass_field(repr=False)


@dataclass(frozen=True, slots=True)
class _PreparedTarget:
    result: AcoustIDTargetResult
    expected_after: AcoustIDPlanningSnapshot
    rows: tuple[_ItemRowPlan, ...]
    applied_field_count: int


def apply_acoustid_results(
    library: Library, results: Sequence[AcoustIDTargetResult]
) -> AcoustIDApplicationResult:
    """Preflight a complete unit, then commit each changed target independently."""
    if type(library) is not Library:
        raise AcoustIDApplicationError(AcoustIDApplicationFailure.BLOCKED_PREFLIGHT)
    try:
        values = tuple(results)
    except Exception:
        raise AcoustIDApplicationError(
            AcoustIDApplicationFailure.BLOCKED_PREFLIGHT
        ) from None
    try:
        prepared = _preflight(library, values)
    except _PreflightFailure as error:
        raise AcoustIDApplicationError(
            AcoustIDApplicationFailure.BLOCKED_PREFLIGHT,
            reason=error.reason,
        ) from None
    except Exception:
        raise AcoustIDApplicationError(
            AcoustIDApplicationFailure.BLOCKED_PREFLIGHT
        ) from None

    changed_targets = 0
    changed_items = 0
    applied_fields = 0
    for target in prepared:
        if not target.rows:
            continue
        try:
            target_items = _apply_target(library, target)
        except AcoustIDApplicationError as error:
            current_committed = 1 if error.committed else 0
            raise AcoustIDApplicationError(
                error.failure,
                reason=error.reason,
                integrity_critical=error.integrity_critical,
                committed=bool(changed_targets or current_committed),
                state_uncertain=error.state_uncertain,
                committed_target_count=changed_targets + current_committed,
                changed_item_count=changed_items + error.changed_item_count,
            ) from None
        changed_targets += 1
        changed_items += target_items
        applied_fields += target.applied_field_count
    return AcoustIDApplicationResult(
        len(values), changed_targets, changed_items, applied_fields
    )


def _preflight(
    library: Library, results: tuple[AcoustIDTargetResult, ...]
) -> tuple[_PreparedTarget, ...]:
    target_keys: set[tuple[object, ...]] = set()
    item_ids: set[int] = set()
    local_keys: set[str] = set()
    prepared = []
    for result in results:
        _validate_result_types(result)
        canonical = canonical_acoustid_database_plan(
            result.planning_snapshot, result.outcomes
        )
        if canonical != result.database_plan:
            raise _PreflightFailure
        if any(
            field.state in {AcoustIDDatabaseState.REVIEW, AcoustIDDatabaseState.BLOCKED}
            for track in result.database_plan.tracks
            for field in (track.acoustid_id, track.acoustid_fingerprint)
        ):
            raise _PreflightFailure
        target_key = _target_key(result)
        if target_key in target_keys:
            raise _PreflightFailure
        target_keys.add(target_key)
        for item in result.planning_snapshot.items:
            if item.item_id in item_ids or item.local_key in local_keys:
                raise _PreflightFailure
            item_ids.add(item.item_id)
            local_keys.add(item.local_key)
        try:
            if snapshot_acoustid_target(result.selected) != result.planning_snapshot:
                raise _StaleTarget
            fresh = refresh_acoustid_target(library, result.selected)
            if snapshot_acoustid_target(fresh) != result.planning_snapshot:
                raise _StaleTarget
        except _PreflightFailure:
            raise
        except Exception:
            raise _StaleTarget from None
        _require_generated_sources(result)
        prepared.append(_prepare_target(result))
    return tuple(prepared)


def _validate_result_types(result: AcoustIDTargetResult) -> None:
    if type(result) is not AcoustIDTargetResult:
        raise _PreflightFailure
    if (
        type(result.selected) is not SelectedAcoustIDTarget
        or type(result.planning_snapshot) is not AcoustIDPlanningSnapshot
        or type(result.database_plan) is not AcoustIDDatabaseTargetPlan
    ):
        raise _PreflightFailure
    if any(type(item) is not SelectedAcoustIDItem for item in result.selected.items):
        raise _PreflightFailure
    if any(
        type(item) is not AcoustIDPlanningItemSnapshot
        for item in result.planning_snapshot.items
    ):
        raise _PreflightFailure
    if any(type(outcome) is not AcoustIDTrackOutcome for outcome in result.outcomes):
        raise _PreflightFailure
    for outcome in result.outcomes:
        if type(outcome.preparation) is not FingerprintPreparationResult:
            raise _PreflightFailure
        material = outcome.preparation.material
        if material is not None and type(material) is not AcoustIDFingerprintMaterial:
            raise _PreflightFailure
    if any(
        type(track) is not AcoustIDTrackDatabasePlan
        or type(track.acoustid_id) is not AcoustIDFieldPlan
        or type(track.acoustid_fingerprint) is not AcoustIDFieldPlan
        for track in result.database_plan.tracks
    ):
        raise _PreflightFailure
    if any(
        type(source) is not AcoustIDGeneratedSourceSnapshot
        for source in result.generated_source_snapshots
    ):
        raise _PreflightFailure
    generated = tuple(
        AcoustIDGeneratedSourceSnapshot(outcome.local_key, material.source_snapshot)
        for outcome in result.outcomes
        if (material := outcome.preparation.material) is not None
        and material.origin is AcoustIDFingerprintOrigin.GENERATED
        and material.source_snapshot is not None
    )
    if generated != result.generated_source_snapshots:
        raise _PreflightFailure


def _target_key(result: AcoustIDTargetResult) -> tuple[object, ...]:
    snapshot = result.planning_snapshot
    identity = snapshot.album_id if snapshot.album_id is not None else snapshot.items[0].item_id
    return snapshot.kind, identity


def _require_generated_sources(result: AcoustIDTargetResult) -> None:
    paths = {item.local_key: item.media_path for item in result.planning_snapshot.items}
    for source in result.generated_source_snapshots:
        path = paths.get(source.local_key)
        if path is None:
            raise _StaleSource
        try:
            stable = verify_source_snapshot(path, source.snapshot)
        except Exception:
            stable = False
        if not stable:
            raise _StaleSource


def _prepare_target(result: AcoustIDTargetResult) -> _PreparedTarget:
    rows = []
    after_items = []
    applied_field_count = 0
    for snapshot, plan in zip(
        result.planning_snapshot.items, result.database_plan.tracks, strict=True
    ):
        after_id = snapshot.acoustid_id
        after_fingerprint = snapshot.acoustid_fingerprint
        changed_fields = []
        if plan.acoustid_id.state is AcoustIDDatabaseState.PROPOSE:
            after_id = plan.acoustid_id._value()
            changed_fields.append("acoustid_id")
        if plan.acoustid_fingerprint.state is AcoustIDDatabaseState.PROPOSE:
            after_fingerprint = plan.acoustid_fingerprint._value()
            changed_fields.append("acoustid_fingerprint")
        if changed_fields:
            rows.append(
                _ItemRowPlan(
                    snapshot.item_id,
                    snapshot.local_key,
                    tuple(changed_fields),
                    snapshot.acoustid_id,
                    snapshot.acoustid_fingerprint,
                    after_id,
                    after_fingerprint,
                )
            )
            applied_field_count += len(changed_fields)
        after_items.append(
            replace(
                snapshot,
                acoustid_id=after_id,
                acoustid_fingerprint=after_fingerprint,
            )
        )
    expected_after = replace(result.planning_snapshot, items=tuple(after_items))
    return _PreparedTarget(result, expected_after, tuple(rows), applied_field_count)


def _apply_target(library: Library, target: _PreparedTarget) -> int:
    try:
        with library.transaction() as tx:
            tx.mutate(_SAVEPOINT_SQL)
            try:
                _require_current_snapshot(
                    library, target.result, target.result.planning_snapshot
                )
                _require_generated_sources(target.result)
                _apply_and_verify_rows(tx, target.rows)
                _require_current_snapshot(library, target.result, target.expected_after)
                tx.mutate(_RELEASE_SQL)
            except Exception:
                _rollback_savepoint(tx)
    except AcoustIDApplicationError:
        raise
    except Exception:
        raise AcoustIDApplicationError(
            AcoustIDApplicationFailure.COMMIT_UNCERTAIN,
            integrity_critical=True,
            state_uncertain=True,
        ) from None

    try:
        fresh_items = _verify_after_commit(library, target)
    except AcoustIDApplicationError:
        raise
    except Exception:
        raise AcoustIDApplicationError(
            AcoustIDApplicationFailure.POST_COMMIT_FAILURE,
            integrity_critical=True,
            committed=True,
            state_uncertain=True,
            committed_target_count=1,
            changed_item_count=len(target.rows),
        ) from None
    try:
        for item in fresh_items:
            plugins.send("database_change", lib=library, model=item)
    except Exception:
        raise AcoustIDApplicationError(
            AcoustIDApplicationFailure.POST_COMMIT_FAILURE,
            committed=True,
            committed_target_count=1,
            changed_item_count=len(target.rows),
        ) from None
    return len(fresh_items)


def _require_current_snapshot(
    library: Library,
    result: AcoustIDTargetResult,
    expected: AcoustIDPlanningSnapshot,
) -> None:
    try:
        fresh = refresh_acoustid_target(library, result.selected)
        current = snapshot_acoustid_target(fresh)
    except Exception:
        raise _StaleTarget from None
    if current != expected:
        raise _StaleTarget


def _apply_and_verify_rows(tx: Transaction, rows: tuple[_ItemRowPlan, ...]) -> None:
    for row in rows:
        before_rows = tx.query(_SELECT_SQL, (row.item_id,))
        if len(before_rows) != 1 or tuple(before_rows[0]) != (
            row.before_id,
            row.before_fingerprint,
        ):
            raise _StaleTarget
        for field_name in row.changed_fields:
            value = row.after_id if field_name == "acoustid_id" else row.after_fingerprint
            tx.mutate(_UPDATE_SQL[field_name], (value, row.item_id))
        verified = tx.query(_SELECT_SQL, (row.item_id,))
        if len(verified) != 1 or tuple(verified[0]) != (
            row.after_id,
            row.after_fingerprint,
        ):
            raise _StaleTarget


def _rollback_savepoint(tx: Transaction) -> None:
    try:
        tx.mutate(_ROLLBACK_SQL)
        tx.mutate(_RELEASE_SQL)
    except Exception:
        raise AcoustIDApplicationError(
            AcoustIDApplicationFailure.ROLLBACK_FAILED,
            integrity_critical=True,
            state_uncertain=True,
        ) from None
    raise AcoustIDApplicationError(
        AcoustIDApplicationFailure.TARGET_ROLLED_BACK
    ) from None


def _verify_after_commit(
    library: Library, target: _PreparedTarget
) -> tuple[Item, ...]:
    try:
        fresh = refresh_acoustid_target(library, target.result.selected)
        if snapshot_acoustid_target(fresh) != target.expected_after:
            raise RuntimeError
        models = []
        for row in target.rows:
            item = library.get_item(row.item_id)
            if type(item) is not Item:
                raise RuntimeError
            fresh_item = item.get_fresh_from_db()
            if (
                fresh_item.get("acoustid_id", with_album=False) != row.after_id
                or fresh_item.get("acoustid_fingerprint", with_album=False)
                != row.after_fingerprint
            ):
                raise RuntimeError
            models.append(fresh_item)
        return tuple(models)
    except Exception:
        raise AcoustIDApplicationError(
            AcoustIDApplicationFailure.POST_COMMIT_FAILURE,
            integrity_critical=True,
            committed=True,
            state_uncertain=True,
            committed_target_count=1,
            changed_item_count=len(target.rows),
        ) from None
