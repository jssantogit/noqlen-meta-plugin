"""Atomic identity repair on already-selected beets metadata objects."""

from __future__ import annotations

from dataclasses import dataclass

from beets.autotag.hooks import AlbumInfo, TrackInfo

from .domain import IdentityVerdict, canonical_mbid
from .importer import (
    IdentityImportMatchKind,
    SelectedImportIdentity,
    identity_context_from_selected_import,
)
from .importer_mapping import (
    IdentityImportMappingError,
    IdentityImportTargetChange,
    IdentityImportTargetKind,
    IdentityImportTargetPlan,
    map_identity_audit_to_import_targets,
)

_CACHE_FIELDS = ("raw_data", "item_data")


class IdentityImportApplicationError(RuntimeError):
    """Raised when selected identity metadata cannot be changed safely."""


@dataclass(frozen=True, slots=True)
class IdentityImportApplicationResult:
    verdict: IdentityVerdict
    applied_changes: tuple[IdentityImportTargetChange, ...] = ()
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
class _Assignment:
    target: AlbumInfo | TrackInfo
    field: str
    value: str
    change: IdentityImportTargetChange


@dataclass(frozen=True, slots=True)
class _FieldSnapshot:
    target: AlbumInfo | TrackInfo
    field: str
    existed: bool
    value: object


@dataclass(frozen=True, slots=True)
class _CacheSnapshot:
    target: AlbumInfo | TrackInfo
    values: tuple[tuple[str, object], ...]


def apply_import_identity_plan(
    selected: SelectedImportIdentity,
    plan: IdentityImportTargetPlan,
    *,
    from_scratch: bool,
) -> IdentityImportApplicationResult:
    """Validate and atomically mutate only selected AlbumInfo/TrackInfo objects."""
    if type(selected) is not SelectedImportIdentity:
        raise IdentityImportApplicationError("identity application target is invalid")
    if type(plan) is not IdentityImportTargetPlan:
        raise IdentityImportApplicationError("identity application plan is invalid")
    if type(from_scratch) is not bool:
        raise IdentityImportApplicationError("from_scratch must be a bool")
    try:
        expected = map_identity_audit_to_import_targets(
            plan.source, match_kind=plan.match_kind
        )
    except IdentityImportMappingError as error:
        raise IdentityImportApplicationError(
            "identity target plan source cannot be mapped canonically"
        ) from error
    if plan != expected or selected.kind is not plan.match_kind:
        raise IdentityImportApplicationError(
            "identity target plan does not match its canonical source"
        )

    current = identity_context_from_selected_import(selected, from_scratch=from_scratch)
    if current is None or current != plan.source.context:
        raise IdentityImportApplicationError("selected identity context no longer matches the plan")

    verdict = plan.source.verdict
    if verdict is IdentityVerdict.AMBIGUOUS:
        return IdentityImportApplicationResult(verdict, blocked_reason="ambiguous_evidence")
    if verdict is IdentityVerdict.CONFIRMED:
        return IdentityImportApplicationResult(verdict)
    if verdict not in (IdentityVerdict.MISSING, IdentityVerdict.CONFLICT):
        raise IdentityImportApplicationError("identity audit verdict is unsupported")
    if not plan.source.repair_ready or not plan.changes:
        return IdentityImportApplicationResult(verdict, blocked_reason="repair_not_ready")

    assignments = _materialize_assignments(selected, plan)
    field_snapshots = tuple(
        _FieldSnapshot(
            item.target,
            item.field,
            item.field in item.target,
            item.target.get(item.field),
        )
        for item in assignments
    )
    changed_targets: tuple[AlbumInfo | TrackInfo, ...] = ()
    seen_target_ids: set[int] = set()
    for item in assignments:
        if id(item.target) not in seen_target_ids:
            changed_targets += (item.target,)
            seen_target_ids.add(id(item.target))
    cache_snapshots = tuple(
        _CacheSnapshot(
            target,
            tuple((key, target.__dict__[key]) for key in _CACHE_FIELDS if key in target.__dict__),
        )
        for target in changed_targets
    )
    try:
        for assignment in assignments:
            assignment.target[assignment.field] = assignment.value
        for target in changed_targets:
            for key in _CACHE_FIELDS:
                target.__dict__.pop(key, None)
    except Exception as error:
        _rollback(field_snapshots, cache_snapshots)
        raise IdentityImportApplicationError(
            "selected identity metadata application failed safely"
        ) from error
    return IdentityImportApplicationResult(verdict, plan.changes)


def _materialize_assignments(
    selected: SelectedImportIdentity,
    plan: IdentityImportTargetPlan,
) -> tuple[_Assignment, ...]:
    by_scope = {track.local_key: track.track_info for track in selected.tracks}
    materialized: list[_Assignment] = []
    seen: set[tuple[int, str]] = set()
    for change in plan.changes:
        if type(change) is not IdentityImportTargetChange:
            raise IdentityImportApplicationError("identity target change is invalid")
        if canonical_mbid(change.target_value) != change.target_value:
            raise IdentityImportApplicationError("identity target value is invalid")
        target, expected_fields = _resolve_target(selected, by_scope, change)
        if change.target_field not in expected_fields:
            raise IdentityImportApplicationError("identity target field is invalid")
        key = (id(target), change.target_field)
        if key in seen:
            raise IdentityImportApplicationError("identity target is duplicated")
        seen.add(key)
        materialized.append(_Assignment(target, change.target_field, change.target_value, change))
    return tuple(materialized)


def _resolve_target(
    selected: SelectedImportIdentity,
    by_scope: dict[str, TrackInfo],
    change: IdentityImportTargetChange,
) -> tuple[AlbumInfo | TrackInfo, frozenset[str]]:
    if change.target_kind is IdentityImportTargetKind.ALBUM_INFO_ATTRIBUTE:
        if (
            selected.kind is not IdentityImportMatchKind.ALBUM
            or type(selected.album_info) is not AlbumInfo
        ):
            raise IdentityImportApplicationError("identity AlbumInfo target is invalid")
        if change.scope_key is not None:
            raise IdentityImportApplicationError("identity AlbumInfo scope is invalid")
        return selected.album_info, frozenset(("album_id", "releasegroup_id"))
    if change.target_kind is IdentityImportTargetKind.TRACK_INFO_ATTRIBUTE:
        if change.scope_key is None or change.scope_key not in by_scope:
            raise IdentityImportApplicationError("identity TrackInfo scope is invalid")
        target = by_scope[change.scope_key]
        if type(target) is not TrackInfo:
            raise IdentityImportApplicationError("identity TrackInfo target is invalid")
        return target, frozenset(("track_id", "release_track_id"))
    if change.target_kind is IdentityImportTargetKind.TRACK_INFO_ITEM_FIELD:
        if selected.kind is not IdentityImportMatchKind.TRACK or change.scope_key is not None:
            raise IdentityImportApplicationError("identity singleton target is invalid")
        target = selected.tracks[0].track_info
        if type(target) is not TrackInfo:
            raise IdentityImportApplicationError("identity singleton TrackInfo is invalid")
        return target, frozenset(("mb_albumid", "mb_releasegroupid"))
    raise IdentityImportApplicationError("identity target kind is unsupported")


def _rollback(
    fields: tuple[_FieldSnapshot, ...], caches: tuple[_CacheSnapshot, ...]
) -> None:
    try:
        for snapshot in reversed(fields):
            if snapshot.existed:
                snapshot.target[snapshot.field] = snapshot.value
            else:
                snapshot.target.pop(snapshot.field, None)
        for snapshot in caches:
            for key in _CACHE_FIELDS:
                snapshot.target.__dict__.pop(key, None)
            snapshot.target.__dict__.update(snapshot.values)
    except Exception as error:
        raise IdentityImportApplicationError(
            "selected identity metadata rollback failed safely"
        ) from error
