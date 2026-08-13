"""Safe ordinary metadata synchronization to media files."""

from __future__ import annotations

import os
import secrets
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any

from beets import plugins
from beets.library import Item, Library
from mediafile import MediaFile

from beetsplug.noqlenmeta.changeplan import PlannedChange
from beetsplug.noqlenmeta.field_contracts import IdentifierCollection, PartialDate
from beetsplug.noqlenmeta.media_snapshot import (
    MediaFileSnapshot,
    copy_regular_file_without_source_atime,
    digest_regular_file_without_atime,
    filesystem_metadata,
    fingerprint_media_file,
    freeze_media_value,
    snapshot_media_file,
    verify_candidate_metadata,
)
from beetsplug.noqlenmeta.release_catalog import ReleaseStatus, ReleaseType
from beetsplug.noqlenmeta.work_identity import WorkReference


class FileTagShape(Enum):
    STRING_LIST = "string_list"
    SCALAR_STRING = "scalar_string"
    SCALAR_INT = "scalar_int"
    SCALAR_FLOAT = "scalar_float"


@dataclass(frozen=True, slots=True)
class FileTagTarget:
    canonical_field: str
    media_field: str
    shape: FileTagShape


@dataclass(frozen=True, slots=True)
class FileTagChange:
    canonical_field: str
    media_field: str
    before: object
    after: object
    source: PlannedChange


@dataclass(frozen=True, slots=True)
class FileSyncBlocker:
    canonical_field: str
    reason: str
    source: PlannedChange


@dataclass(frozen=True, slots=True)
class FileSyncPlan:
    item_id: int
    path: bytes
    snapshot: MediaFileSnapshot
    item_mtime: float
    changes: tuple[FileTagChange, ...] = ()
    blockers: tuple[FileSyncBlocker, ...] = ()


@dataclass(frozen=True, slots=True)
class FileSyncResult:
    item_id: int
    applied_fields: tuple[str, ...] = ()
    blocked_reason: str | None = None
    blocker_count: int = 0
    committed: bool = False
    state_uncertain: bool = False
    recovery_artifact_retained: bool = False


class FileSyncApplicationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        committed: bool = False,
        state_uncertain: bool = False,
        recovery_artifact_retained: bool = False,
    ) -> None:
        super().__init__(message)
        self.committed = committed
        self.state_uncertain = state_uncertain
        self.recovery_artifact_retained = recovery_artifact_retained


_TARGETS = (
    FileTagTarget("genres", "genres", FileTagShape.STRING_LIST),
    FileTagTarget("styles", "styles", FileTagShape.STRING_LIST),
    FileTagTarget("moods", "moods", FileTagShape.STRING_LIST),
    FileTagTarget("lyrics_languages", "lyrics_languages", FileTagShape.STRING_LIST),
    FileTagTarget("artist_languages", "artist_languages", FileTagShape.STRING_LIST),
    FileTagTarget("artist_countries", "artist_countries", FileTagShape.STRING_LIST),
    FileTagTarget("artist_areas", "artist_areas", FileTagShape.STRING_LIST),
    FileTagTarget("labels", "label", FileTagShape.SCALAR_STRING),
    FileTagTarget("country", "country", FileTagShape.SCALAR_STRING),
    FileTagTarget("year", "year", FileTagShape.SCALAR_INT),
    FileTagTarget("lyrics", "lyrics", FileTagShape.SCALAR_STRING),
    FileTagTarget("bpm", "bpm", FileTagShape.SCALAR_FLOAT),
)
FILE_TAG_TARGETS: Mapping[str, FileTagTarget] = MappingProxyType(
    {target.canonical_field: target for target in _TARGETS}
)
_EXPANDED_FIELDS = frozenset(
    {"date", "original_date", "isrcs", "works", "release_type", "release_status"}
)
_RELATED_MEDIA_FIELDS: Mapping[str, frozenset[str]] = MappingProxyType(
    {"genres": frozenset({"genres", "genre"})}
)


def _all_media_fields() -> tuple[str, ...]:
    return tuple(sorted(MediaFile.fields()))


def plan_file_sync(item: Item, changes: Sequence[PlannedChange]) -> FileSyncPlan:
    """Prepare one immutable file plan without mutating Item or media source."""
    if not isinstance(item, Item) or not isinstance(item.id, int):
        raise ValueError("file synchronization requires a persisted Item")
    path = item.path
    if not isinstance(path, bytes) or not path:
        raise ValueError("file synchronization requires an Item path")
    all_media_fields = _all_media_fields()
    missing_media_fields = {
        target.media_field for target in _TARGETS
    } - set(all_media_fields)
    if missing_media_fields:
        raise ValueError("declared file target is unavailable from MediaFile")

    snapshot = snapshot_media_file(path, fields=all_media_fields)
    snapshot_values = dict(snapshot.values)
    mapped: list[FileTagChange] = []
    blocked: list[FileSyncBlocker] = []
    seen: set[str] = set()
    for change in sorted(tuple(changes), key=lambda value: value.field):
        if change.field in seen:
            raise ValueError(f"duplicate canonical file field {change.field!r}")
        seen.add(change.field)
        if change.field in _EXPANDED_FIELDS:
            try:
                projections = _expanded_targets(change)
            except ValueError as error:
                blocked.append(FileSyncBlocker(change.field, str(error), change))
                continue
            for target, value in projections:
                before = snapshot_values[target.media_field]
                after = freeze_media_value(value)
                if before != after:
                    mapped.append(
                        FileTagChange(
                            change.field, target.media_field, before, value, change
                        )
                    )
            continue
        target = FILE_TAG_TARGETS.get(change.field)
        if target is None:
            blocked.append(
                FileSyncBlocker(
                    change.field,
                    "no supported lossless MediaFile target exists",
                    change,
                )
            )
            continue
        try:
            materialized = _materialize(target, change.after)
        except ValueError as error:
            blocked.append(FileSyncBlocker(change.field, str(error), change))
            continue
        before = snapshot_values[target.media_field]
        after = freeze_media_value(materialized)
        if before == after:
            continue
        mapped.append(
            FileTagChange(
                change.field,
                target.media_field,
                before,
                change.after,
                change,
            )
        )
    return FileSyncPlan(
        item.id,
        path,
        snapshot,
        float(item.mtime or 0.0),
        tuple(mapped),
        tuple(blocked),
    )


def verify_file_sync_plan(library: Library, plan: FileSyncPlan) -> None:
    """Verify a canonical plan against fresh database and exact source state."""
    _validate_plan(plan)
    fresh = library.get_item(plan.item_id)
    if (
        type(fresh) is not Item
        or fresh.path != plan.path
        or float(fresh.mtime or 0.0) != plan.item_mtime
    ):
        raise FileSyncApplicationError("ordinary metadata source changed before synchronization")
    try:
        fingerprint = fingerprint_media_file(plan.path)
        metadata = filesystem_metadata(plan.path)
    except Exception as error:
        raise FileSyncApplicationError(
            "ordinary metadata source changed before synchronization"
        ) from error
    if fingerprint != plan.snapshot.fingerprint or metadata != plan.snapshot.filesystem_metadata:
        raise FileSyncApplicationError("ordinary metadata source changed before synchronization")


def apply_file_sync_plan(library: Library, plan: FileSyncPlan) -> FileSyncResult:
    """Apply one plan through verified candidate copy and replace."""
    verify_file_sync_plan(library, plan)
    if plan.blockers and not plan.changes:
        return FileSyncResult(
            plan.item_id,
            blocked_reason=plan.blockers[0].reason,
            blocker_count=len(plan.blockers),
        )
    if not plan.changes:
        return FileSyncResult(plan.item_id)

    candidate: bytes | None = None
    backup: bytes | None = None
    backup_digest: bytes | None = None
    replaced = False
    mtime_committed = False
    try:
        candidate, descriptor = _candidate_path(plan.path)
        copy_regular_file_without_source_atime(
            plan.path,
            candidate,
            destination_exists=True,
            destination_descriptor=descriptor,
        )
        _require_source_snapshot(plan)
        candidate_before = snapshot_media_file(candidate, fields=_all_media_fields())
        if candidate_before.values != plan.snapshot.values:
            raise ValueError("ordinary metadata candidate differs before save")

        media = MediaFile(os.fsdecode(candidate))
        for change in plan.changes:
            setattr(media, change.media_field, _file_change_value(change))
        media.save()
        candidate_after = snapshot_media_file(candidate, fields=_all_media_fields())
        _verify_candidate_snapshot(plan, candidate_after)
        _restore_atime(candidate, plan.snapshot.filesystem_metadata.atime_ns)
        verify_candidate_metadata(candidate, plan.snapshot.filesystem_metadata)
        _fsync_file(candidate)
        _require_source_snapshot(plan)

        backup = _backup_path(plan.path)
        copy_regular_file_without_source_atime(
            plan.path, backup, destination_exists=False
        )
        backup_digest = _verify_recovery_artifact(plan.path, backup, plan)
        _require_source_snapshot(plan)
        os.replace(candidate, plan.path)
        candidate = None
        replaced = True
        _fsync_directory(plan.path)
        final_snapshot = snapshot_media_file(plan.path, fields=_all_media_fields())
        _verify_candidate_snapshot(plan, final_snapshot)
        _restore_atime(plan.path, plan.snapshot.filesystem_metadata.atime_ns)
        verify_candidate_metadata(plan.path, plan.snapshot.filesystem_metadata)
        mtime = os.stat(plan.path, follow_symlinks=False).st_mtime
        fresh = _store_operational_mtime(library, plan, mtime)
        mtime_committed = True
        try:
            plugins.send("after_write", item=fresh, path=plan.path)
            plugins.send("database_change", lib=library, model=fresh)
        except Exception as error:
            raise FileSyncApplicationError(
                "ordinary metadata synchronization committed but notification failed",
                committed=True,
            ) from error
        if not _remove(backup):
            raise FileSyncApplicationError(
                "ordinary metadata synchronization committed but artifact cleanup failed",
                committed=True,
                recovery_artifact_retained=True,
            )
        backup = None
        return FileSyncResult(
            plan.item_id,
            tuple(change.canonical_field for change in plan.changes),
            blocked_reason=plan.blockers[0].reason if plan.blockers else None,
            blocker_count=len(plan.blockers),
            committed=True,
        )
    except FileSyncApplicationError as error:
        retained = backup is not None and os.path.exists(backup)
        if replaced and error.committed and not (
            error.state_uncertain or error.recovery_artifact_retained
        ):
            if _remove(backup):
                backup = None
                retained = False
            else:
                retained = backup is not None and os.path.exists(backup)
                raise FileSyncApplicationError(
                    "ordinary metadata synchronization committed but artifact cleanup failed",
                    committed=True,
                    recovery_artifact_retained=retained,
                ) from error
        if retained != error.recovery_artifact_retained:
            raise FileSyncApplicationError(
                str(error),
                committed=error.committed,
                state_uncertain=error.state_uncertain,
                recovery_artifact_retained=retained,
            ) from error
        raise
    except Exception as error:
        if replaced:
            if mtime_committed:
                retained = backup is not None and os.path.exists(backup)
                raise FileSyncApplicationError(
                    "ordinary metadata synchronization committed but finalization failed",
                    committed=True,
                    recovery_artifact_retained=retained,
                ) from error
            try:
                if backup is None or backup_digest is None:
                    raise ValueError("recovery artifact unavailable")
                _restore_original(plan, backup, backup_digest)
            except Exception as restore_error:
                retained = backup is not None and os.path.exists(backup)
                raise FileSyncApplicationError(
                    "ordinary metadata synchronization state is uncertain",
                    committed=True,
                    state_uncertain=True,
                    recovery_artifact_retained=retained,
                ) from restore_error
            retained = not _remove(backup)
            if not retained:
                backup = None
            return FileSyncResult(
                plan.item_id,
                blocked_reason="ordinary metadata original restored after failed synchronization",
                recovery_artifact_retained=retained,
            )
        return FileSyncResult(
            plan.item_id,
            blocked_reason=_safe_reason(error),
            blocker_count=len(plan.blockers),
        )
    except BaseException as error:
        if replaced:
            retained = backup is not None and os.path.exists(backup)
            raise FileSyncApplicationError(
                "ordinary metadata synchronization state is uncertain",
                committed=True,
                state_uncertain=True,
                recovery_artifact_retained=retained,
            ) from error
        raise
    finally:
        _remove(candidate)
        if not replaced:
            _remove(backup)


def _validate_plan(plan: FileSyncPlan) -> None:
    if not isinstance(plan, FileSyncPlan):
        raise FileSyncApplicationError("file synchronization plan is invalid")
    if plan.path != plan.snapshot.path:
        raise FileSyncApplicationError("file synchronization plan is not canonical")
    snapshot_values = dict(plan.snapshot.values)
    seen: set[str] = set()
    for change in plan.changes:
        target = FILE_TAG_TARGETS.get(change.canonical_field)
        if (
            change.canonical_field != change.source.field
            or change.before != snapshot_values.get(change.media_field)
            or change.media_field in seen
        ):
            raise FileSyncApplicationError("file synchronization plan is not canonical")
        seen.add(change.media_field)
        try:
            if target is not None:
                if change.media_field != target.media_field or change.after != change.source.after:
                    raise ValueError
                _materialize(target, change.after)
            elif change.canonical_field in _EXPANDED_FIELDS:
                expected = {
                    projected.media_field: value
                    for projected, value in _expanded_targets(change.source)
                }
                if expected.get(change.media_field) != change.after:
                    raise ValueError
            else:
                raise ValueError
        except ValueError as error:
            raise FileSyncApplicationError(
                "file synchronization plan is not canonical"
            ) from error


def _materialize(target: FileTagTarget, value: object) -> Any:
    if target.shape is FileTagShape.STRING_LIST:
        if (
            not isinstance(value, tuple)
            or not value
            or any(
                not isinstance(entry, str) or not entry or entry != entry.strip()
                for entry in value
            )
        ):
            raise ValueError("canonical value is not a non-empty string list")
        return list(value)
    if target.shape is FileTagShape.SCALAR_STRING:
        if target.canonical_field == "labels":
            if not isinstance(value, tuple) or len(value) != 1:
                raise ValueError("canonical labels cannot be represented losslessly")
            value = value[0]
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError("canonical value is not a non-empty string")
        return value
    if target.shape is FileTagShape.SCALAR_INT:
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 9999:
            raise ValueError("canonical value is not a valid year")
        return value
    if target.shape is FileTagShape.SCALAR_FLOAT:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
        ):
            raise ValueError("canonical value is not a finite positive number")
        number = float(value)
        descriptor = MediaFile.__dict__.get(target.media_field)
        if getattr(descriptor, "out_type", None) is int:
            if not number.is_integer():
                raise ValueError(
                    "MediaFile cannot represent the fractional value losslessly"
                )
            return int(number)
        return number
    raise ValueError("unsupported file target shape")


def _file_change_value(change: FileTagChange) -> Any:
    target = FILE_TAG_TARGETS.get(change.canonical_field)
    return _materialize(target, change.after) if target is not None else change.after


def _expanded_targets(
    change: PlannedChange,
) -> tuple[tuple[FileTagTarget, object], ...]:
    value = change.after
    if change.field in {"date", "original_date"}:
        if not isinstance(value, PartialDate):
            raise ValueError("canonical date requires a partial date")
        prefix = "original_" if change.field == "original_date" else ""
        components = [(f"{prefix}year", value.year)]
        if value.month is not None:
            components.append((f"{prefix}month", value.month))
        if value.day is not None:
            components.append((f"{prefix}day", value.day))
        return tuple(
            (FileTagTarget(change.field, field, FileTagShape.SCALAR_INT), component)
            for field, component in components
        )
    if change.field == "release_type" and isinstance(value, ReleaseType):
        target = FileTagTarget(change.field, "albumtype", FileTagShape.SCALAR_STRING)
        return ((target, value.value),)
    if change.field == "release_status" and isinstance(value, ReleaseStatus):
        target = FileTagTarget(change.field, "albumstatus", FileTagShape.SCALAR_STRING)
        return ((target, value.value),)
    if change.field == "isrcs" and isinstance(value, IdentifierCollection):
        identifiers = tuple(identifier.value for identifier in value.values)
        if len(identifiers) != 1:
            raise ValueError("multiple ISRCs cannot be represented losslessly by MediaFile")
        return ((FileTagTarget(change.field, "isrc", FileTagShape.SCALAR_STRING), identifiers[0]),)
    if change.field == "works" and isinstance(value, tuple) and all(
        isinstance(reference, WorkReference) for reference in value
    ):
        if len(value) != 1:
            raise ValueError("multiple Works cannot be represented losslessly by MediaFile")
        target = FileTagTarget(change.field, "mb_workid", FileTagShape.SCALAR_STRING)
        return ((target, value[0].mbid),)
    raise ValueError("canonical value cannot be represented losslessly by MediaFile")


def _verify_candidate_snapshot(plan: FileSyncPlan, actual: MediaFileSnapshot) -> None:
    expected_before = dict(plan.snapshot.values)
    actual_values = dict(actual.values)
    allowed: set[str] = set()
    for change in plan.changes:
        expected = freeze_media_value(_file_change_value(change))
        if actual_values.get(change.media_field) != expected:
            raise ValueError("ordinary metadata candidate value verification failed")
        allowed.update(_RELATED_MEDIA_FIELDS.get(change.media_field, {change.media_field}))
    for media_field, before in expected_before.items():
        if media_field not in allowed and actual_values.get(media_field) != before:
            raise ValueError("ordinary metadata candidate changed an unrelated tag")
    if actual.format_name != plan.snapshot.format_name:
        raise ValueError("ordinary metadata candidate format changed")


def _require_source_snapshot(plan: FileSyncPlan) -> None:
    if (
        fingerprint_media_file(plan.path) != plan.snapshot.fingerprint
        or filesystem_metadata(plan.path) != plan.snapshot.filesystem_metadata
    ):
        raise ValueError("ordinary metadata source changed")


def _verify_recovery_artifact(
    source: bytes, backup: bytes, plan: FileSyncPlan
) -> bytes:
    """Prove the recovery copy represents the still-current planned source."""
    _require_source_snapshot(plan)
    source_digest = digest_regular_file_without_atime(source)
    _verify_original_snapshot(backup, plan, source_digest)
    _require_source_snapshot(plan)
    return source_digest


def _verify_original_snapshot(path: bytes, plan: FileSyncPlan, digest: bytes) -> None:
    snapshot = snapshot_media_file(path, fields=_all_media_fields())
    fingerprint = snapshot.fingerprint
    expected = plan.snapshot
    if (
        digest_regular_file_without_atime(path) != digest
        or fingerprint.size != expected.fingerprint.size
        or fingerprint.mode != expected.fingerprint.mode
        or fingerprint.mtime_ns != expected.fingerprint.mtime_ns
        or fingerprint.link_count != 1
        or snapshot.values != expected.values
        or snapshot.format_name != expected.format_name
        or snapshot.filesystem_metadata != expected.filesystem_metadata
    ):
        raise ValueError("ordinary metadata recovery artifact verification failed")


def _restore_original(plan: FileSyncPlan, backup: bytes, digest: bytes) -> None:
    """Restore through a separately verified candidate, retaining the backup."""
    _verify_original_snapshot(backup, plan, digest)
    restore: bytes | None = None
    try:
        restore, descriptor = _candidate_path(plan.path)
        copy_regular_file_without_source_atime(
            backup,
            restore,
            destination_exists=True,
            destination_descriptor=descriptor,
        )
        _verify_original_snapshot(restore, plan, digest)
        os.replace(restore, plan.path)
        restore = None
        _fsync_directory(plan.path)
        _verify_original_snapshot(plan.path, plan, digest)
        _restore_atime(plan.path, plan.snapshot.filesystem_metadata.atime_ns)
        verify_candidate_metadata(plan.path, plan.snapshot.filesystem_metadata)
    finally:
        _remove(restore)


def _candidate_path(path: bytes) -> tuple[bytes, int]:
    parent = os.path.dirname(path) or os.fsencode(".")
    suffix = os.path.splitext(path)[1]
    descriptor, candidate = tempfile.mkstemp(
        prefix=b".noqlen-meta-candidate-", suffix=suffix, dir=parent
    )
    return candidate, descriptor


def _backup_path(path: bytes) -> bytes:
    parent = os.path.dirname(path) or os.fsencode(".")
    return os.path.join(parent, os.fsencode(f".noqlen-meta-backup-{secrets.token_hex(12)}"))


def _restore_atime(path: bytes, atime_ns: int) -> None:
    info = os.stat(path, follow_symlinks=False)
    os.utime(path, ns=(atime_ns, info.st_mtime_ns), follow_symlinks=False)


def _fsync_file(path: bytes) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: bytes) -> None:
    parent = os.path.dirname(path) or os.fsencode(".")
    descriptor = os.open(parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _store_operational_mtime(library: Library, plan: FileSyncPlan, mtime: float) -> Item:
    fresh = library.get_item(plan.item_id)
    if (
        type(fresh) is not Item
        or fresh.path != plan.path
        or float(fresh.mtime or 0.0) != plan.item_mtime
    ):
        raise ValueError("ordinary metadata Item changed before mtime update")
    fresh.mtime = mtime
    try:
        fresh.store(fields={"mtime"})
        verified = library.get_item(plan.item_id)
        if (
            type(verified) is not Item
            or verified.path != plan.path
            or verified.mtime != mtime
        ):
            raise ValueError("ordinary metadata mtime verification failed")
        return verified
    except Exception as error:
        raise FileSyncApplicationError(
            "ordinary metadata mtime commit state is uncertain",
            committed=True,
            state_uncertain=True,
        ) from error


def _remove(path: bytes | None) -> bool:
    if path is None:
        return True
    try:
        os.unlink(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def _safe_reason(error: Exception) -> str:
    if isinstance(error, (OSError, ValueError)):
        return "ordinary metadata candidate preparation failed"
    return "ordinary metadata synchronization unavailable"
