"""Deterministic mapping from identity audit findings to selected metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .audit import IdentityAuditResult
from .domain import IdentityFieldStatus, IdentityVerdict, canonical_mbid
from .importer import IdentityImportMatchKind


class IdentityImportMappingError(RuntimeError):
    """Raised when an identity audit cannot be mapped safely."""


class IdentityImportTargetKind(Enum):
    ALBUM_INFO_ATTRIBUTE = "album_info_attribute"
    TRACK_INFO_ATTRIBUTE = "track_info_attribute"
    TRACK_INFO_ITEM_FIELD = "track_info_item_field"


@dataclass(frozen=True, slots=True)
class IdentityImportTargetChange:
    canonical_field: str
    scope_key: str | None
    target_kind: IdentityImportTargetKind
    target_field: str
    before_status: IdentityFieldStatus
    target_value: str


@dataclass(frozen=True, slots=True)
class IdentityImportTargetPlan:
    source: IdentityAuditResult
    match_kind: IdentityImportMatchKind
    changes: tuple[IdentityImportTargetChange, ...] = ()


def map_identity_audit_to_import_targets(
    source: IdentityAuditResult,
    *,
    match_kind: IdentityImportMatchKind,
) -> IdentityImportTargetPlan:
    """Map every repairable non-confirmed finding in deterministic audit order."""
    if type(source) is not IdentityAuditResult:
        raise IdentityImportMappingError("identity mapping source is invalid")
    if not isinstance(match_kind, IdentityImportMatchKind):
        raise IdentityImportMappingError("identity match kind is invalid")
    if source.verdict in (IdentityVerdict.AMBIGUOUS, IdentityVerdict.CONFIRMED):
        if source.repair_ready:
            raise IdentityImportMappingError("identity audit has inconsistent repair policy")
        return IdentityImportTargetPlan(source, match_kind)
    if source.verdict not in (IdentityVerdict.MISSING, IdentityVerdict.CONFLICT):
        raise IdentityImportMappingError("identity audit verdict is unsupported")
    if not source.repair_ready:
        return IdentityImportTargetPlan(source, match_kind)

    context_keys = tuple(track.local_key for track in source.context.tracks)
    changes: list[IdentityImportTargetChange] = []
    for finding in source.field_findings:
        if not isinstance(finding.status, IdentityFieldStatus):
            raise IdentityImportMappingError("identity finding status is unsupported")
        if finding.status is IdentityFieldStatus.CONFIRMED:
            continue
        if canonical_mbid(finding.expected_value) != finding.expected_value:
            raise IdentityImportMappingError("identity target value is not canonical")
        target_kind, target_field = _target_for(
            match_kind, finding.field, finding.scope_key, context_keys
        )
        changes.append(
            IdentityImportTargetChange(
                finding.field,
                finding.scope_key,
                target_kind,
                target_field,
                finding.status,
                finding.expected_value,
            )
        )
    if not changes:
        raise IdentityImportMappingError("repair-ready identity audit has no target changes")
    return IdentityImportTargetPlan(source, match_kind, tuple(changes))


def _target_for(
    match_kind: IdentityImportMatchKind,
    field: str,
    scope_key: str | None,
    context_keys: tuple[str, ...],
) -> tuple[IdentityImportTargetKind, str]:
    if field == "mb_albumid":
        if scope_key is not None:
            raise IdentityImportMappingError("album identity field has an invalid scope")
        if match_kind is IdentityImportMatchKind.ALBUM:
            return IdentityImportTargetKind.ALBUM_INFO_ATTRIBUTE, "album_id"
        return IdentityImportTargetKind.TRACK_INFO_ITEM_FIELD, field
    if field == "mb_releasegroupid":
        if scope_key is not None:
            raise IdentityImportMappingError("album identity field has an invalid scope")
        if match_kind is IdentityImportMatchKind.ALBUM:
            return IdentityImportTargetKind.ALBUM_INFO_ATTRIBUTE, "releasegroup_id"
        return IdentityImportTargetKind.TRACK_INFO_ITEM_FIELD, field
    if field in ("mb_trackid", "mb_releasetrackid"):
        if scope_key is None or context_keys.count(scope_key) != 1:
            raise IdentityImportMappingError("track identity scope does not resolve exactly once")
        target = "track_id" if field == "mb_trackid" else "release_track_id"
        return IdentityImportTargetKind.TRACK_INFO_ATTRIBUTE, target
    raise IdentityImportMappingError("identity field is unsupported")
