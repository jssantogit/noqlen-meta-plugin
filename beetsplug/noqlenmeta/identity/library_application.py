"""Savepoint-backed database-only application of library identity repairs."""

from __future__ import annotations

from dataclasses import dataclass

from beets import plugins
from beets.dbcore.db import Transaction
from beets.library import Album, Item, Library

from .domain import IdentityVerdict, canonical_mbid
from .library import (
    LibraryIdentityExactSnapshot,
    SelectedLibraryIdentityTarget,
    exact_snapshot_from_library_target,
    refresh_library_identity_target,
)
from .library_mapping import (
    LibraryIdentityMappingError,
    LibraryIdentityTargetChange,
    LibraryIdentityTargetPlan,
    LibraryIdentityWriteKind,
    map_library_identity_targets,
)

_SAVEPOINT = "noqlen_identity_target"
_SAVEPOINT_SQL = f"SAVEPOINT {_SAVEPOINT}"
_ROLLBACK_SQL = f"ROLLBACK TO SAVEPOINT {_SAVEPOINT}"
_RELEASE_SQL = f"RELEASE SAVEPOINT {_SAVEPOINT}"

_ALBUM_FIELDS = ("mb_albumid", "mb_releasegroupid")
_ITEM_FIELDS = (
    "mb_albumid",
    "mb_releasegroupid",
    "mb_trackid",
    "mb_releasetrackid",
)
_SELECT_SQL = {
    LibraryIdentityWriteKind.ALBUM_FIELD: (
        "SELECT mb_albumid, mb_releasegroupid FROM albums WHERE id=?"
    ),
    LibraryIdentityWriteKind.ITEM_FIELD: (
        "SELECT mb_albumid, mb_releasegroupid, mb_trackid, mb_releasetrackid "
        "FROM items WHERE id=?"
    ),
}
_UPDATE_SQL = {
    (LibraryIdentityWriteKind.ALBUM_FIELD, "mb_albumid"): (
        "UPDATE albums SET mb_albumid=? WHERE id=?"
    ),
    (LibraryIdentityWriteKind.ALBUM_FIELD, "mb_releasegroupid"): (
        "UPDATE albums SET mb_releasegroupid=? WHERE id=?"
    ),
    (LibraryIdentityWriteKind.ITEM_FIELD, "mb_albumid"): (
        "UPDATE items SET mb_albumid=? WHERE id=?"
    ),
    (LibraryIdentityWriteKind.ITEM_FIELD, "mb_releasegroupid"): (
        "UPDATE items SET mb_releasegroupid=? WHERE id=?"
    ),
    (LibraryIdentityWriteKind.ITEM_FIELD, "mb_trackid"): (
        "UPDATE items SET mb_trackid=? WHERE id=?"
    ),
    (LibraryIdentityWriteKind.ITEM_FIELD, "mb_releasetrackid"): (
        "UPDATE items SET mb_releasetrackid=? WHERE id=?"
    ),
}


class LibraryIdentityApplicationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        integrity_critical: bool = False,
        committed: bool = False,
    ) -> None:
        super().__init__(message)
        self.integrity_critical = integrity_critical
        self.committed = committed


@dataclass(frozen=True, slots=True)
class LibraryIdentityApplicationResult:
    verdict: IdentityVerdict
    applied_changes: tuple[LibraryIdentityTargetChange, ...] = ()
    blocked_reason: str | None = None

    @property
    def is_blocked(self) -> bool:
        return self.blocked_reason is not None

    @property
    def has_applied_changes(self) -> bool:
        return bool(self.applied_changes)

    @property
    def is_confirmed_noop(self) -> bool:
        return self.verdict is IdentityVerdict.CONFIRMED and not self.applied_changes


@dataclass(frozen=True, slots=True)
class _DatabaseRowPlan:
    write_kind: LibraryIdentityWriteKind
    row_id: int
    changes: tuple[LibraryIdentityTargetChange, ...]


def apply_library_identity_plan(
    library: Library,
    target_or_plan: SelectedLibraryIdentityTarget | LibraryIdentityTargetPlan,
    plan: LibraryIdentityTargetPlan | None = None,
) -> LibraryIdentityApplicationResult:
    """Apply one complete target atomically inside a real SQLite savepoint."""
    if type(library) is not Library:
        raise LibraryIdentityApplicationError("library identity application library is invalid")
    if plan is None:
        if type(target_or_plan) is not LibraryIdentityTargetPlan:
            raise LibraryIdentityApplicationError("library identity target plan is invalid")
        resolved_plan = target_or_plan
        target = resolved_plan.source.selected
    else:
        if type(target_or_plan) is not SelectedLibraryIdentityTarget:
            raise LibraryIdentityApplicationError("library identity selected target is invalid")
        target = target_or_plan
        resolved_plan = plan
        if target != resolved_plan.source.selected:
            raise LibraryIdentityApplicationError(
                "library identity selected target is inconsistent"
            )
    _validate_plan(resolved_plan)

    verdict = resolved_plan.source.audit.verdict
    if verdict is IdentityVerdict.AMBIGUOUS:
        return LibraryIdentityApplicationResult(verdict, blocked_reason="ambiguous evidence")
    if verdict is IdentityVerdict.CONFIRMED:
        return LibraryIdentityApplicationResult(verdict)
    if verdict not in {IdentityVerdict.MISSING, IdentityVerdict.CONFLICT}:
        raise LibraryIdentityApplicationError("library identity verdict is unsupported")
    if not resolved_plan.source.audit.repair_ready:
        return LibraryIdentityApplicationResult(verdict, blocked_reason="repair not ready")
    if not resolved_plan.changes:
        raise LibraryIdentityApplicationError("repair-ready identity plan has no changes")

    rows = _database_rows(resolved_plan)
    _require_current_snapshot(library, target, resolved_plan.source.exact_snapshot)
    try:
        with library.transaction() as tx:
            tx.mutate(_SAVEPOINT_SQL)
            try:
                _apply_and_verify(tx, rows)
                tx.mutate(_RELEASE_SQL)
            except Exception as error:
                _rollback_savepoint(tx, error)
    except LibraryIdentityApplicationError:
        raise
    except Exception as error:
        raise LibraryIdentityApplicationError(
            "library identity root transaction failed; commit state is uncertain",
            integrity_critical=True,
        ) from error

    fresh_models = _verify_after_commit(library, rows)
    try:
        for model in fresh_models:
            plugins.send("database_change", lib=library, model=model)
    except Exception as error:
        raise LibraryIdentityApplicationError(
            "library identity repair committed but post-commit notification failed",
            committed=True,
        ) from error
    return LibraryIdentityApplicationResult(verdict, resolved_plan.changes)


def verify_library_identity_plan_snapshot(
    library: Library, plan: LibraryIdentityTargetPlan
) -> None:
    """Command-wide preflight used after all source and mapping work completes."""
    _validate_plan(plan)
    _require_current_snapshot(library, plan.source.selected, plan.source.exact_snapshot)


def _validate_plan(plan: LibraryIdentityTargetPlan) -> None:
    if type(plan) is not LibraryIdentityTargetPlan:
        raise LibraryIdentityApplicationError("library identity target plan is invalid")
    try:
        canonical = map_library_identity_targets(plan.source)
    except LibraryIdentityMappingError as error:
        raise LibraryIdentityApplicationError(
            "library identity plan source cannot be mapped safely"
        ) from error
    if canonical != plan:
        raise LibraryIdentityApplicationError(
            "library identity plan does not match its canonical source"
        )
    seen: set[tuple[LibraryIdentityWriteKind, int, str]] = set()
    for change in plan.changes:
        if type(change) is not LibraryIdentityTargetChange:
            raise LibraryIdentityApplicationError("library identity target change is invalid")
        if not isinstance(change.write_kind, LibraryIdentityWriteKind):
            raise LibraryIdentityApplicationError("library identity write kind is invalid")
        if (
            isinstance(change.row_id, bool)
            or not isinstance(change.row_id, int)
            or change.row_id <= 0
        ):
            raise LibraryIdentityApplicationError("library identity row ID is invalid")
        if canonical_mbid(change.target_value) != change.target_value:
            raise LibraryIdentityApplicationError("library identity target UUID is invalid")
        if (change.write_kind, change.target_field) not in _UPDATE_SQL:
            raise LibraryIdentityApplicationError("library identity target column is invalid")
        key = (change.write_kind, change.row_id, change.target_field)
        if key in seen:
            raise LibraryIdentityApplicationError("library identity database target is duplicated")
        seen.add(key)


def _database_rows(plan: LibraryIdentityTargetPlan) -> tuple[_DatabaseRowPlan, ...]:
    grouped: dict[
        tuple[LibraryIdentityWriteKind, int], list[LibraryIdentityTargetChange]
    ] = {}
    for change in plan.changes:
        grouped.setdefault((change.write_kind, change.row_id), []).append(change)
    ordered = sorted(
        grouped.items(),
        key=lambda entry: (
            entry[0][0] is LibraryIdentityWriteKind.ITEM_FIELD,
            entry[0][1],
        ),
    )
    return tuple(
        _DatabaseRowPlan(kind, row_id, tuple(changes))
        for (kind, row_id), changes in ordered
    )


def _require_current_snapshot(
    library: Library,
    target: SelectedLibraryIdentityTarget,
    expected: LibraryIdentityExactSnapshot,
) -> None:
    try:
        fresh = refresh_library_identity_target(library, target)
        current = exact_snapshot_from_library_target(fresh)
    except Exception as error:
        raise LibraryIdentityApplicationError(
            "library identity target is unavailable or structurally stale"
        ) from error
    if current != expected:
        raise LibraryIdentityApplicationError("library identity target is stale")


def _apply_and_verify(tx: Transaction, rows: tuple[_DatabaseRowPlan, ...]) -> None:
    for row in rows:
        fields = (
            _ALBUM_FIELDS
            if row.write_kind is LibraryIdentityWriteKind.ALBUM_FIELD
            else _ITEM_FIELDS
        )
        before_rows = tx.query(_SELECT_SQL[row.write_kind], (row.row_id,))
        if len(before_rows) != 1:
            raise LibraryIdentityApplicationError("library identity database row is missing")
        before = dict(zip(fields, tuple(before_rows[0]), strict=True))
        if any(before[change.target_field] != change.before_value for change in row.changes):
            raise LibraryIdentityApplicationError("library identity row changed before update")
        expected = dict(before)
        for change in row.changes:
            tx.mutate(
                _UPDATE_SQL[(change.write_kind, change.target_field)],
                (change.target_value, change.row_id),
            )
            expected[change.target_field] = change.target_value
        verified = tx.query(_SELECT_SQL[row.write_kind], (row.row_id,))
        if len(verified) != 1 or tuple(verified[0]) != tuple(expected[field] for field in fields):
            raise LibraryIdentityApplicationError(
                "library identity in-savepoint verification failed"
            )


def _rollback_savepoint(tx: Transaction, original_error: Exception) -> None:
    try:
        tx.mutate(_ROLLBACK_SQL)
        tx.mutate(_RELEASE_SQL)
    except Exception as rollback_error:
        raise LibraryIdentityApplicationError(
            "library identity rollback failed; database integrity is uncertain",
            integrity_critical=True,
        ) from rollback_error
    raise LibraryIdentityApplicationError(
        "library identity application failed and the target was rolled back"
    ) from original_error


def _verify_after_commit(
    library: Library, rows: tuple[_DatabaseRowPlan, ...]
) -> tuple[Album | Item, ...]:
    models: list[Album | Item] = []
    for row in rows:
        model = (
            library.get_album(row.row_id)
            if row.write_kind is LibraryIdentityWriteKind.ALBUM_FIELD
            else library.get_item(row.row_id)
        )
        if type(model) is Album:
            fresh_model: Album | Item = model.get_fresh_from_db()
        elif type(model) is Item:
            fresh_model = model.get_fresh_from_db()
        else:
            raise LibraryIdentityApplicationError(
                "library identity repair committed but a changed row is unavailable",
                committed=True,
            )
        for change in row.changes:
            value = (
                fresh_model.get(change.target_field, with_album=False)
                if type(fresh_model) is Item
                else fresh_model.get(change.target_field)
            )
            if value != change.target_value:
                raise LibraryIdentityApplicationError(
                    "library identity repair committed but fresh verification failed",
                    committed=True,
                )
        models.append(fresh_model)
    return tuple(models)


# Compatibility aliases for the initial implementation draft.
IdentityLibraryApplicationError = LibraryIdentityApplicationError
IdentityLibraryApplicationResult = LibraryIdentityApplicationResult
