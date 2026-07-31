"""Immutable mapping from a library identity audit to exact database columns."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .domain import IdentityFieldStatus, IdentityVerdict, canonical_mbid
from .library import LibraryIdentityAuditResult, LibraryIdentityTargetKind


class LibraryIdentityMappingError(RuntimeError):
    pass


class LibraryIdentityWriteKind(Enum):
    ALBUM_FIELD = "album_field"
    ITEM_FIELD = "item_field"


@dataclass(frozen=True, slots=True)
class LibraryIdentityTargetChange:
    canonical_field: str
    scope_key: str | None
    write_kind: LibraryIdentityWriteKind
    row_id: int
    target_field: str
    before_value: object
    target_value: str


@dataclass(frozen=True, slots=True)
class LibraryIdentityTargetPlan:
    source: LibraryIdentityAuditResult
    changes: tuple[LibraryIdentityTargetChange, ...] = ()


def map_library_identity_targets(
    source: LibraryIdentityAuditResult,
) -> LibraryIdentityTargetPlan:
    """Map repair-ready findings to each differing fixed Album/Item column."""
    if type(source) is not LibraryIdentityAuditResult:
        raise LibraryIdentityMappingError("library identity mapping source is invalid")
    selected = source.selected
    snapshot = source.exact_snapshot
    if snapshot.kind is not selected.kind or snapshot.album_id != selected.album_id:
        raise LibraryIdentityMappingError("library identity snapshot target is inconsistent")
    item_ids = tuple(item.item_id for item in selected.items)
    snapshot_ids = tuple(item.item_id for item in snapshot.item_snapshots)
    context_keys = tuple(track.local_key for track in source.context.tracks)
    selected_keys = tuple(item.local_key for item in selected.items)
    if item_ids != snapshot_ids or selected_keys != context_keys:
        raise LibraryIdentityMappingError("library identity Item scopes are inconsistent")

    findings: dict[tuple[str, str | None], tuple[IdentityFieldStatus, str]] = {}
    for finding in source.audit.field_findings:
        key = (finding.field, finding.scope_key)
        if key in findings:
            raise LibraryIdentityMappingError("library identity finding is duplicated")
        if finding.field not in {
            "mb_albumid",
            "mb_releasegroupid",
            "mb_trackid",
            "mb_releasetrackid",
        }:
            raise LibraryIdentityMappingError("library identity finding field is unknown")
        if not isinstance(finding.status, IdentityFieldStatus):
            raise LibraryIdentityMappingError("library identity finding status is invalid")
        if canonical_mbid(finding.expected_value) != finding.expected_value:
            raise LibraryIdentityMappingError("library identity target is not a canonical UUID")
        if finding.field in {"mb_albumid", "mb_releasegroupid"}:
            if finding.scope_key is not None:
                raise LibraryIdentityMappingError("album identity finding has a track scope")
        elif finding.scope_key not in selected_keys:
            raise LibraryIdentityMappingError("track identity scope is unresolved")
        findings[key] = (finding.status, finding.expected_value)

    verdict = source.audit.verdict
    if verdict in {IdentityVerdict.AMBIGUOUS, IdentityVerdict.CONFIRMED}:
        return LibraryIdentityTargetPlan(source)
    if verdict not in {IdentityVerdict.MISSING, IdentityVerdict.CONFLICT}:
        raise LibraryIdentityMappingError("library identity verdict is unsupported")
    if not source.audit.repair_ready:
        return LibraryIdentityTargetPlan(source)

    for field in ("mb_albumid", "mb_releasegroupid"):
        if (field, None) not in findings:
            raise LibraryIdentityMappingError("repair-ready album identity finding is missing")
    for local_key in selected_keys:
        for field in ("mb_trackid", "mb_releasetrackid"):
            if (field, local_key) not in findings:
                raise LibraryIdentityMappingError("repair-ready track identity finding is missing")

    album_values = dict(snapshot.album_fields)
    item_values = {
        item.item_id: dict(item.fields) for item in snapshot.item_snapshots
    }
    changes: list[LibraryIdentityTargetChange] = []
    seen: set[tuple[LibraryIdentityWriteKind, int, str]] = set()

    if selected.kind is LibraryIdentityTargetKind.ALBUM:
        assert selected.album_id is not None
        for field in ("mb_albumid", "mb_releasegroupid"):
            _append_if_different(
                changes,
                seen,
                field,
                None,
                LibraryIdentityWriteKind.ALBUM_FIELD,
                selected.album_id,
                album_values[field],
                findings[(field, None)][1],
            )

    for selected_item in selected.items:
        values = item_values.get(selected_item.item_id)
        if values is None:
            raise LibraryIdentityMappingError("library identity Item row is missing")
        for field in ("mb_albumid", "mb_releasegroupid"):
            _append_if_different(
                changes,
                seen,
                field,
                None,
                LibraryIdentityWriteKind.ITEM_FIELD,
                selected_item.item_id,
                values[field],
                findings[(field, None)][1],
            )
        for field in ("mb_trackid", "mb_releasetrackid"):
            _append_if_different(
                changes,
                seen,
                field,
                selected_item.local_key,
                LibraryIdentityWriteKind.ITEM_FIELD,
                selected_item.item_id,
                values[field],
                findings[(field, selected_item.local_key)][1],
            )

    if not changes:
        raise LibraryIdentityMappingError(
            "repair-ready library identity result has no differing database row"
        )
    return LibraryIdentityTargetPlan(source, tuple(changes))


def _append_if_different(
    changes: list[LibraryIdentityTargetChange],
    seen: set[tuple[LibraryIdentityWriteKind, int, str]],
    canonical_field: str,
    scope_key: str | None,
    write_kind: LibraryIdentityWriteKind,
    row_id: int,
    before_value: object,
    target_value: str,
) -> None:
    if canonical_mbid(before_value) == target_value:
        return
    key = (write_kind, row_id, canonical_field)
    if key in seen:
        raise LibraryIdentityMappingError("library identity database target is duplicated")
    seen.add(key)
    changes.append(
        LibraryIdentityTargetChange(
            canonical_field,
            scope_key,
            write_kind,
            row_id,
            canonical_field,
            before_value,
            target_value,
        )
    )


# Compatibility names for the initial implementation draft.
IdentityLibraryMappingError = LibraryIdentityMappingError
IdentityLibraryTargetKind = LibraryIdentityWriteKind
IdentityLibraryTargetChange = LibraryIdentityTargetChange
IdentityLibraryTargetPlan = LibraryIdentityTargetPlan
map_identity_audit_to_library_targets = map_library_identity_targets
