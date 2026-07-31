"""Canonical immutable mapping from database identity to MediaFile fields."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .domain import canonical_mbid
from .tag_filesystem import IdentityTagFileSnapshot, snapshot_identity_tag_file
from .tag_sync import (
    IDENTITY_TAG_FIELDS,
    IdentityTagPreparedDatabaseFile,
    IdentityTagPreparedDatabaseTarget,
    SelectedIdentityTagFile,
)


class IdentityTagFieldStatus(Enum):
    KEEP = "keep"
    MISSING = "missing"
    CONFLICT = "conflict"
    MALFORMED = "malformed"


@dataclass(frozen=True, slots=True)
class IdentityTagFieldChange:
    field: str
    status: IdentityTagFieldStatus
    expected_value: str


@dataclass(frozen=True, slots=True)
class IdentityTagFilePlan:
    database: IdentityTagPreparedDatabaseFile
    file_snapshot: IdentityTagFileSnapshot | None
    changes: tuple[IdentityTagFieldChange, ...]
    blocked_reason: str | None = None

    @property
    def is_noop(self) -> bool:
        return self.blocked_reason is None and not self.changes


@dataclass(frozen=True, slots=True)
class IdentityTagTargetPlan:
    database: IdentityTagPreparedDatabaseTarget
    files: tuple[IdentityTagFilePlan, ...]


def map_identity_tag_file(
    database: IdentityTagPreparedDatabaseFile,
    file_snapshot: IdentityTagFileSnapshot | None,
    *,
    blocked_reason: str | None = None,
) -> IdentityTagFilePlan:
    if type(database) is not IdentityTagPreparedDatabaseFile:
        raise TypeError("identity tag database file is invalid")
    reason = database.blocked_reason or blocked_reason
    if reason is not None:
        return IdentityTagFilePlan(database, file_snapshot, (), reason)
    if database.expected is None or type(file_snapshot) is not IdentityTagFileSnapshot:
        raise ValueError("identity tag ready file requires snapshots")
    current = dict(file_snapshot.identity_values)
    if tuple(current) != IDENTITY_TAG_FIELDS:
        raise ValueError("identity tag file snapshot fields are invalid")
    changes = []
    for field, expected in database.expected.as_tuple():
        status = identity_tag_field_status(current[field], expected)
        if status is not IdentityTagFieldStatus.KEEP:
            changes.append(IdentityTagFieldChange(field, status, expected))
    return IdentityTagFilePlan(database, file_snapshot, tuple(changes))


def identity_tag_field_status(current: object, expected: str) -> IdentityTagFieldStatus:
    if canonical_mbid(expected) != expected:
        raise ValueError("identity tag expected UUID is invalid")
    if current is None or current == "":
        return IdentityTagFieldStatus.MISSING
    if not isinstance(current, str):
        return IdentityTagFieldStatus.MALFORMED
    canonical = canonical_mbid(current)
    if canonical is None:
        return IdentityTagFieldStatus.MALFORMED
    return IdentityTagFieldStatus.KEEP if canonical == expected else IdentityTagFieldStatus.CONFLICT


def plan_identity_tag_targets(
    targets: tuple[IdentityTagPreparedDatabaseTarget, ...],
) -> tuple[IdentityTagTargetPlan, ...]:
    """Read every eligible source and build all plans without creating artifacts."""
    path_counts: dict[bytes, int] = {}
    for target in targets:
        for database in target.files:
            if database.blocked_reason is not None:
                continue
            if type(database.selected) is not SelectedIdentityTagFile:
                raise ValueError("identity tag ready file selection is invalid")
            path = database.selected.path
            path_counts[path] = path_counts.get(path, 0) + 1
    planned_targets = []
    for target in targets:
        plans = []
        for database in target.files:
            if database.blocked_reason is not None:
                plans.append(map_identity_tag_file(database, None))
                continue
            if type(database.selected) is not SelectedIdentityTagFile:
                raise ValueError("identity tag ready file selection is invalid")
            if path_counts[database.selected.path] > 1:
                plans.append(
                    map_identity_tag_file(
                        database, None, blocked_reason="duplicate identity tag file path"
                    )
                )
                continue
            try:
                snapshot = snapshot_identity_tag_file(database.selected.path)
            except Exception as error:
                plans.append(
                    map_identity_tag_file(
                        database, None, blocked_reason=_snapshot_blocked_reason(error)
                    )
                )
                continue
            plans.append(map_identity_tag_file(database, snapshot))
        planned_targets.append(IdentityTagTargetPlan(target, tuple(plans)))
    return tuple(planned_targets)


def _snapshot_blocked_reason(error: Exception) -> str:
    message = str(error)
    name = type(error).__name__.lower()
    if "hard link" in message:
        return "identity tag file has multiple hard links"
    if "regular file" in message:
        return "identity tag file is not a regular file"
    if "filetype" in name or "unreadable" in name or "mutagen" in name:
        return "identity tag format unsupported"
    return "identity tag file unavailable"
