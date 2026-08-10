"""Verified candidate-copy application for MusicBrainz identity tags."""

from __future__ import annotations

import os
import secrets
import tempfile
from dataclasses import dataclass
from enum import Enum

from beets import plugins, ui
from beets.dbcore.db import Transaction
from beets.library import Item, Library
from mediafile import MediaFile

from beetsplug.noqlenmeta.media_snapshot import digest_regular_file_without_atime

from .domain import canonical_mbid
from .tag_filesystem import (
    IdentityTagAtimeCopyError,
    IdentityTagFileFingerprint,
    IdentityTagFileSnapshot,
    IdentityTagFilesystemMetadata,
    copy_regular_file_without_source_atime,
    filesystem_metadata,
    fingerprint_identity_tag_file,
    freeze_media_value,
    snapshot_identity_tag_file,
    verify_candidate_metadata,
)
from .tag_mapping import IdentityTagFilePlan, map_identity_tag_file
from .tag_sync import (
    IDENTITY_TAG_FIELDS,
    IdentityTagPreparedDatabaseTarget,
    SelectedIdentityTagFile,
    verify_identity_tag_database_target,
)

_SAVEPOINT = "noqlen_identity_tag_mtime"
_SAVEPOINT_SQL = f"SAVEPOINT {_SAVEPOINT}"
_ROLLBACK_SQL = f"ROLLBACK TO SAVEPOINT {_SAVEPOINT}"
_RELEASE_SQL = f"RELEASE SAVEPOINT {_SAVEPOINT}"
_SELECT_MTIME_SQL = "SELECT mtime FROM items WHERE id=?"
_UPDATE_MTIME_SQL = "UPDATE items SET mtime=? WHERE id=?"


class _SafeMtimeFailure(RuntimeError):
    pass


class _IdentityTagCommitPhase(Enum):
    SOURCE_UNCHANGED = "source_unchanged"
    SOURCE_REPLACED = "source_replaced"
    MTIME_COMMITTED = "mtime_committed"


class IdentityTagApplicationError(RuntimeError, ui.UserError):
    def __init__(
        self,
        message: str,
        *,
        integrity_critical: bool = False,
        committed: bool = False,
        state_uncertain: bool = False,
        recovery_artifact_retained: bool = False,
    ) -> None:
        super().__init__(message)
        self.integrity_critical = integrity_critical
        self.committed = committed
        self.state_uncertain = state_uncertain
        self.recovery_artifact_retained = recovery_artifact_retained


@dataclass(frozen=True, slots=True)
class IdentityTagApplicationResult:
    item_id: int
    applied_fields: tuple[str, ...] = ()
    blocked_reason: str | None = None
    no_op: bool = False

    @property
    def has_applied_changes(self) -> bool:
        return bool(self.applied_fields)

    @property
    def is_blocked(self) -> bool:
        return self.blocked_reason is not None

    @property
    def is_noop(self) -> bool:
        return self.no_op


def verify_identity_tag_file_plan(
    library: Library,
    target: IdentityTagPreparedDatabaseTarget,
    plan: IdentityTagFilePlan,
) -> None:
    """Command-wide fresh database and exact-stat preflight."""
    _validate_plan(target, plan)
    if plan.blocked_reason is not None:
        return
    try:
        verify_identity_tag_database_target(library, target)
        if plan.file_snapshot is None:
            raise ValueError
        current = fingerprint_identity_tag_file(plan.database.selected.path)
        current_metadata = filesystem_metadata(plan.database.selected.path)
    except Exception as error:
        raise IdentityTagApplicationError(
            "identity tag source changed before synchronization"
        ) from error
    if (
        current != plan.file_snapshot.fingerprint
        or current_metadata != plan.file_snapshot.filesystem_metadata
    ):
        raise IdentityTagApplicationError("identity tag source changed before synchronization")


def apply_identity_tag_file_plan(
    library: Library,
    target: IdentityTagPreparedDatabaseTarget,
    plan: IdentityTagFilePlan,
) -> IdentityTagApplicationResult:
    """Apply one changed file without ever opening the source for MediaFile save."""
    _validate_plan(target, plan)
    item_id = plan.database.selected.item_id
    if plan.blocked_reason is not None:
        return IdentityTagApplicationResult(item_id, blocked_reason=plan.blocked_reason)
    if not plan.changes:
        return IdentityTagApplicationResult(item_id, no_op=True)
    assert plan.file_snapshot is not None
    expected = plan.database.expected
    assert expected is not None
    if type(plan.database.selected) is not SelectedIdentityTagFile:
        raise IdentityTagApplicationError("identity tag write-eligible selection is invalid")
    path = plan.database.selected.path
    candidate: bytes | None = None
    backup: bytes | None = None
    backup_digest: bytes | None = None
    backup_source_fingerprint: IdentityTagFileFingerprint | None = None
    backup_source_metadata: IdentityTagFilesystemMetadata | None = None
    phase = _IdentityTagCommitPhase.SOURCE_UNCHANGED
    retain_backup = False
    try:
        _require_fresh(library, target, plan)
        candidate, candidate_descriptor = _candidate_path(path)
        copy_regular_file_without_source_atime(
            path,
            candidate,
            destination_exists=True,
            destination_descriptor=candidate_descriptor,
        )
        _require_source_snapshot(path, plan.file_snapshot)
        candidate_before = snapshot_identity_tag_file(candidate)
        if candidate_before.unrelated_values != plan.file_snapshot.unrelated_values:
            raise ValueError("candidate unrelated tags differ")
        media = MediaFile(os.fsdecode(candidate))
        for field, value in expected.as_tuple():
            setattr(media, field, value)
        media.save()
        candidate_after = snapshot_identity_tag_file(candidate)
        _verify_logical_snapshot(candidate_after, plan.file_snapshot, expected.as_tuple())
        _restore_atime(candidate, plan.file_snapshot.filesystem_metadata.atime_ns)
        verify_candidate_metadata(candidate, plan.file_snapshot.filesystem_metadata)
        _fsync_file(candidate)
        _require_fresh(library, target, plan)
        (
            backup,
            backup_digest,
            backup_source_fingerprint,
            backup_source_metadata,
        ) = _create_backup(path, plan.file_snapshot)
        _verify_source_with_backup(
            path,
            backup,
            plan.file_snapshot,
            backup_source_fingerprint,
            backup_source_metadata,
        )
        os.replace(candidate, path)
        candidate = None
        phase = _IdentityTagCommitPhase.SOURCE_REPLACED
        _fsync_directory(path)
        replaced_snapshot = snapshot_identity_tag_file(path)
        _verify_logical_snapshot(replaced_snapshot, plan.file_snapshot, expected.as_tuple())
        _restore_atime(path, plan.file_snapshot.filesystem_metadata.atime_ns)
        verify_candidate_metadata(path, plan.file_snapshot.filesystem_metadata)
        new_mtime = os.stat(path, follow_symlinks=False).st_mtime
        fresh_item = _store_operational_mtime(library, target, plan, new_mtime)
        phase = _IdentityTagCommitPhase.MTIME_COMMITTED
        try:
            plugins.send("after_write", item=fresh_item, path=path)
            plugins.send("database_change", lib=library, model=fresh_item)
        except Exception as error:
            raise IdentityTagApplicationError(
                "identity tag synchronization committed but notification failed",
                committed=True,
            ) from error
        if not _remove_artifact(backup):
            retain_backup = _artifact_exists(backup)
            raise IdentityTagApplicationError(
                "identity tag synchronization committed but artifact cleanup failed",
                committed=True,
                recovery_artifact_retained=retain_backup,
            )
        backup = None
        return IdentityTagApplicationResult(item_id, tuple(change.field for change in plan.changes))
    except IdentityTagApplicationError as error:
        if phase is _IdentityTagCommitPhase.SOURCE_REPLACED:
            if error.committed:
                if error.integrity_critical and error.state_uncertain:
                    retain_backup = _artifact_exists(backup)
                elif not _remove_artifact(backup):
                    retain_backup = _artifact_exists(backup)
                    raise IdentityTagApplicationError(
                        "identity tag synchronization committed but artifact cleanup failed",
                        committed=True,
                        recovery_artifact_retained=retain_backup,
                    ) from error
                else:
                    backup = None
                raise
            if error.integrity_critical or error.state_uncertain:
                retain_backup = _artifact_exists(backup)
                raise IdentityTagApplicationError(
                    "identity tag synchronization state is uncertain; original recovery "
                    "artifact was retained",
                    integrity_critical=True,
                    committed=True,
                    state_uncertain=True,
                    recovery_artifact_retained=retain_backup,
                ) from error
            try:
                _restore_original(path, backup, backup_digest, plan.file_snapshot)
                backup = None
            except Exception as restore_error:
                retain_backup = _artifact_exists(backup)
                raise IdentityTagApplicationError(
                    "identity tag restoration failed; committed state is uncertain",
                    integrity_critical=True,
                    committed=True,
                    state_uncertain=True,
                    recovery_artifact_retained=retain_backup,
                ) from restore_error
            return IdentityTagApplicationResult(
                item_id,
                blocked_reason="identity tag original restored after failed synchronization",
            )
        if phase is _IdentityTagCommitPhase.MTIME_COMMITTED:
            if error.recovery_artifact_retained:
                retain_backup = _artifact_exists(backup)
            elif error.integrity_critical and error.state_uncertain:
                retain_backup = _artifact_exists(backup)
            elif not _remove_artifact(backup):
                retain_backup = _artifact_exists(backup)
                raise IdentityTagApplicationError(
                    "identity tag synchronization committed but artifact cleanup failed",
                    committed=True,
                    recovery_artifact_retained=retain_backup,
                ) from error
            else:
                backup = None
            if error.committed:
                raise
            raise IdentityTagApplicationError(
                "identity tag synchronization committed but finalization failed",
                integrity_critical=error.integrity_critical,
                committed=True,
                state_uncertain=error.state_uncertain,
                recovery_artifact_retained=retain_backup,
            ) from error
        raise
    except Exception as error:
        if phase is _IdentityTagCommitPhase.SOURCE_REPLACED:
            try:
                _restore_original(path, backup, backup_digest, plan.file_snapshot)
                backup = None
            except Exception as restore_error:
                retain_backup = _artifact_exists(backup)
                raise IdentityTagApplicationError(
                    "identity tag restoration failed; committed state is uncertain",
                    integrity_critical=True,
                    committed=True,
                    state_uncertain=True,
                    recovery_artifact_retained=retain_backup,
                ) from restore_error
            return IdentityTagApplicationResult(
                item_id,
                blocked_reason="identity tag original restored after failed synchronization",
            )
        if phase is _IdentityTagCommitPhase.MTIME_COMMITTED:
            if not _remove_artifact(backup):
                retain_backup = _artifact_exists(backup)
                raise IdentityTagApplicationError(
                    "identity tag synchronization committed but artifact cleanup failed",
                    committed=True,
                    recovery_artifact_retained=retain_backup,
                ) from error
            backup = None
            raise IdentityTagApplicationError(
                "identity tag synchronization committed but finalization failed",
                committed=True,
            ) from error
        return IdentityTagApplicationResult(item_id, blocked_reason=_safe_blocked_reason(error))
    except BaseException as error:
        if phase is _IdentityTagCommitPhase.SOURCE_REPLACED:
            retain_backup = _artifact_exists(backup)
            raise IdentityTagApplicationError(
                "identity tag synchronization state is uncertain; original recovery "
                "artifact was retained",
                integrity_critical=True,
                committed=True,
                state_uncertain=True,
                recovery_artifact_retained=retain_backup,
            ) from error
        if phase is _IdentityTagCommitPhase.MTIME_COMMITTED:
            if not _remove_artifact(backup):
                retain_backup = _artifact_exists(backup)
                raise IdentityTagApplicationError(
                    "identity tag synchronization committed but artifact cleanup failed",
                    committed=True,
                    recovery_artifact_retained=retain_backup,
                ) from error
            backup = None
            raise IdentityTagApplicationError(
                "identity tag synchronization committed but finalization was interrupted",
                committed=True,
            ) from error
        raise
    finally:
        _remove_artifact(candidate)
        if not retain_backup:
            _remove_artifact(backup)


def _validate_plan(
    target: IdentityTagPreparedDatabaseTarget, plan: IdentityTagFilePlan
) -> None:
    if (
        type(target) is not IdentityTagPreparedDatabaseTarget
        or type(plan) is not IdentityTagFilePlan
    ):
        raise IdentityTagApplicationError("identity tag application plan is invalid")
    if plan.database.target_snapshot != target.snapshot or plan.database not in target.files:
        raise IdentityTagApplicationError("identity tag application target is inconsistent")
    try:
        canonical = map_identity_tag_file(
            plan.database, plan.file_snapshot, blocked_reason=plan.blocked_reason
        )
    except Exception as error:
        raise IdentityTagApplicationError(
            "identity tag application plan cannot be mapped"
        ) from error
    if canonical != plan:
        raise IdentityTagApplicationError("identity tag application plan is not canonical")
    seen: set[str] = set()
    for change in plan.changes:
        if change.field not in IDENTITY_TAG_FIELDS or change.field in seen:
            raise IdentityTagApplicationError("identity tag application field is invalid")
        if canonical_mbid(change.expected_value) != change.expected_value:
            raise IdentityTagApplicationError("identity tag application UUID is invalid")
        seen.add(change.field)
    if plan.blocked_reason is not None:
        return
    if type(plan.database.selected) is not SelectedIdentityTagFile:
        raise IdentityTagApplicationError("identity tag write-eligible selection is invalid")
    if plan.database.database_snapshot.path != plan.database.selected.path:
        raise IdentityTagApplicationError("identity tag application path relation is invalid")


def _require_fresh(
    library: Library,
    target: IdentityTagPreparedDatabaseTarget,
    plan: IdentityTagFilePlan,
) -> None:
    try:
        verify_identity_tag_database_target(library, target)
        _require_source_snapshot(plan.database.selected.path, plan.file_snapshot)
    except Exception as error:
        raise ValueError("identity tag source changed before replacement") from error


def _require_source_fingerprint(path: bytes, snapshot: IdentityTagFileSnapshot) -> None:
    if fingerprint_identity_tag_file(path) != snapshot.fingerprint:
        raise ValueError("identity tag source changed before replacement")


def _require_source_snapshot(path: bytes, snapshot: IdentityTagFileSnapshot) -> None:
    _require_source_fingerprint(path, snapshot)
    if filesystem_metadata(path) != snapshot.filesystem_metadata:
        raise ValueError("identity tag source changed before replacement")


def _candidate_path(path: bytes) -> tuple[bytes, int]:
    parent = os.path.dirname(path) or os.fsencode(".")
    suffix = os.path.splitext(path)[1]
    descriptor, candidate = tempfile.mkstemp(
        prefix=b".noqlen-identity-candidate-", suffix=suffix, dir=parent
    )
    return candidate, descriptor


def _create_backup(
    path: bytes, snapshot: IdentityTagFileSnapshot
) -> tuple[
    bytes,
    bytes,
    IdentityTagFileFingerprint,
    IdentityTagFilesystemMetadata,
]:
    parent = os.path.dirname(path) or os.fsencode(".")
    backup = os.path.join(
        parent, os.fsencode(f".noqlen-identity-backup-{secrets.token_hex(12)}")
    )
    try:
        os.link(path, backup, follow_symlinks=False)
        source_stat = os.stat(path, follow_symlinks=False)
        backup_stat = os.stat(backup, follow_symlinks=False)
        if (source_stat.st_dev, source_stat.st_ino) != (backup_stat.st_dev, backup_stat.st_ino):
            raise ValueError("identity tag backup verification failed") from None
        fingerprint, metadata = _capture_source_state(path)
        return backup, _file_digest(path), fingerprint, metadata
    except OSError:
        _remove_artifact(backup)
        try:
            copy_regular_file_without_source_atime(
                path, backup, destination_exists=False
            )
            _require_source_snapshot(path, snapshot)
            source_digest = _file_digest(path)
            if _file_digest(backup) != source_digest:
                raise ValueError("identity tag backup verification failed") from None
            backup_snapshot = snapshot_identity_tag_file(backup)
            if (
                backup_snapshot.identity_values != snapshot.identity_values
                or backup_snapshot.unrelated_values != snapshot.unrelated_values
            ):
                raise ValueError("identity tag backup verification failed") from None
            verify_candidate_metadata(backup, snapshot.filesystem_metadata)
            fingerprint, metadata = _capture_source_state(path)
            return backup, source_digest, fingerprint, metadata
        except Exception:
            _remove_artifact(backup)
            raise
    except Exception:
        _remove_artifact(backup)
        raise


def _restore_original(
    path: bytes,
    backup: bytes | None,
    expected_digest: bytes | None,
    expected: IdentityTagFileSnapshot,
) -> None:
    if backup is None or expected_digest is None:
        raise ValueError("identity tag backup is unavailable")
    os.replace(backup, path)
    _fsync_directory(path)
    restored = snapshot_identity_tag_file(path)
    if (
        _file_digest(path) != expected_digest
        or restored.fingerprint.size != expected.fingerprint.size
        or restored.fingerprint.mode != expected.fingerprint.mode
        or restored.fingerprint.mtime_ns != expected.fingerprint.mtime_ns
        or restored.fingerprint.link_count != 1
        or restored.identity_values != expected.identity_values
        or restored.unrelated_values != expected.unrelated_values
    ):
        raise ValueError("identity tag original restoration verification failed")
    _restore_atime(path, expected.filesystem_metadata.atime_ns)
    verify_candidate_metadata(path, expected.filesystem_metadata)


def _verify_source_with_backup(
    path: bytes,
    backup: bytes,
    expected: IdentityTagFileSnapshot,
    post_backup_fingerprint: IdentityTagFileFingerprint,
    post_backup_metadata: IdentityTagFilesystemMetadata,
) -> None:
    source = os.stat(path, follow_symlinks=False)
    backup_stat = os.stat(backup, follow_symlinks=False)
    fingerprint = expected.fingerprint
    if (
        source.st_dev != fingerprint.device
        or source.st_ino != fingerprint.inode
        or source.st_mode != fingerprint.mode
        or source.st_size != fingerprint.size
        or source.st_mtime_ns != fingerprint.mtime_ns
    ):
        raise ValueError("identity tag source changed before replacement")
    hard_link_backup = (source.st_dev, source.st_ino) == (
        backup_stat.st_dev,
        backup_stat.st_ino,
    )
    expected_links = 2 if hard_link_backup else 1
    if source.st_nlink != expected_links:
        raise ValueError("identity tag source changed before replacement")
    if (
        _stat_fingerprint(path) != post_backup_fingerprint
        or filesystem_metadata(path) != post_backup_metadata
        or post_backup_metadata != expected.filesystem_metadata
    ):
        raise ValueError("identity tag source changed before replacement")


def _verify_logical_snapshot(
    actual: IdentityTagFileSnapshot,
    original: IdentityTagFileSnapshot,
    expected_identity: tuple[tuple[str, str], ...],
) -> None:
    actual_identity = tuple(
        (field, freeze_media_value(canonical_mbid(value)))
        for field, value in actual.identity_values
    )
    if actual_identity != expected_identity:
        raise ValueError("identity tag candidate verification failed")
    if actual.unrelated_values != original.unrelated_values:
        raise ValueError("identity tag unrelated fields changed")


def _store_operational_mtime(
    library: Library,
    target: IdentityTagPreparedDatabaseTarget,
    plan: IdentityTagFilePlan,
    mtime: float,
) -> Item:
    item_id = plan.database.selected.item_id
    try:
        with library.transaction() as tx:
            tx.mutate(_SAVEPOINT_SQL)
            try:
                verify_identity_tag_database_target(library, target)
                rows = tx.query(_SELECT_MTIME_SQL, (item_id,))
                if (
                    len(rows) != 1
                    or float(rows[0][0] or 0.0)
                    != plan.database.database_snapshot.mtime
                ):
                    raise ValueError("identity tag mtime row changed")
                tx.mutate(_UPDATE_MTIME_SQL, (mtime, item_id))
                verified = tx.query(_SELECT_MTIME_SQL, (item_id,))
                if len(verified) != 1 or float(verified[0][0]) != mtime:
                    raise ValueError("identity tag mtime verification failed")
                tx.mutate(_RELEASE_SQL)
            except Exception as error:
                _rollback_mtime(tx, error)
    except _SafeMtimeFailure as error:
        raise ValueError("identity tag mtime update failed") from error
    except IdentityTagApplicationError:
        raise
    except Exception as error:
        raise IdentityTagApplicationError(
            "identity tag mtime transaction failed; commit state is uncertain",
            integrity_critical=True,
            state_uncertain=True,
        ) from error
    item = library.get_item(item_id)
    if type(item) is not Item:
        raise IdentityTagApplicationError(
            "identity tag mtime committed but fresh verification failed", committed=True
        )
    fresh = item.get_fresh_from_db()
    if fresh.path != plan.database.selected.path or float(fresh.mtime) != mtime:
        raise IdentityTagApplicationError(
            "identity tag mtime committed but fresh verification failed", committed=True
        )
    expected = plan.database.expected
    assert expected is not None
    if tuple(fresh.get(field, with_album=False) for field in IDENTITY_TAG_FIELDS) != tuple(
        value for _, value in expected.as_tuple()
    ):
        raise IdentityTagApplicationError(
            "identity tag mtime committed but fresh verification failed", committed=True
        )
    return fresh


def _rollback_mtime(tx: Transaction, original_error: Exception) -> None:
    try:
        tx.mutate(_ROLLBACK_SQL)
        tx.mutate(_RELEASE_SQL)
    except Exception as rollback_error:
        raise IdentityTagApplicationError(
            "identity tag mtime rollback failed; database integrity is uncertain",
            integrity_critical=True,
            state_uncertain=True,
        ) from rollback_error
    raise _SafeMtimeFailure("identity tag mtime update failed") from original_error


def _safe_blocked_reason(error: Exception) -> str:
    if isinstance(error, IdentityTagAtimeCopyError):
        return "identity tag atime-safe file copy is unsupported"
    message = str(error)
    if "hard link" in message:
        return "identity tag file has multiple hard links"
    if "regular file" in message:
        return "identity tag file is not a regular file"
    if "metadata" in message:
        return "filesystem metadata cannot be preserved safely"
    if "changed" in message:
        return "identity tag source changed before replacement"
    return "identity tag candidate verification failed"


def _fsync_file(path: bytes) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _restore_atime(path: bytes, atime_ns: int) -> None:
    current = os.stat(path, follow_symlinks=False)
    os.utime(path, ns=(atime_ns, current.st_mtime_ns), follow_symlinks=False)


def _file_digest(path: bytes) -> bytes:
    return digest_regular_file_without_atime(path)


def _stat_fingerprint(path: bytes) -> IdentityTagFileFingerprint:
    info = os.stat(path, follow_symlinks=False)
    return IdentityTagFileFingerprint(
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_nlink,
    )


def _capture_source_state(
    path: bytes,
) -> tuple[IdentityTagFileFingerprint, IdentityTagFilesystemMetadata]:
    before = _stat_fingerprint(path)
    metadata = filesystem_metadata(path)
    after = _stat_fingerprint(path)
    if after != before:
        raise ValueError("identity tag source changed before replacement")
    return before, metadata


def _fsync_directory(path: bytes) -> None:
    parent = os.path.dirname(path) or os.fsencode(".")
    descriptor = os.open(parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _remove_artifact(path: bytes | None) -> bool:
    if path is None:
        return True
    try:
        os.unlink(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def _artifact_exists(path: bytes | None) -> bool:
    return path is not None and os.path.lexists(path)
