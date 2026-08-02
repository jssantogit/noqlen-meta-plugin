from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import pytest
from beets import ui
from beets.dbcore.db import Transaction
from beets.library import Item, Library
from mediafile import MediaFile

import beetsplug.noqlenmeta.identity.tag_application as application_module
import beetsplug.noqlenmeta.identity.tag_filesystem as filesystem_module
from beetsplug.noqlenmeta.identity import (
    IDENTITY_TAG_FIELDS,
    IdentityTagApplicationError,
    apply_identity_tag_file_plan,
    plan_identity_tag_targets,
    prepare_identity_tag_database_target,
    select_library_identity_targets,
    verify_identity_tag_file_plan,
)

from .helpers import mbid

FIXTURE = Path(__file__).parents[1] / "fixtures" / "identity_tags" / "silence.flac"


def _case(tmp_path: Path, *, synchronized: bool = False, old_atime: bool = False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    media = MediaFile(path)
    media.artist = "Unrelated Artist"
    media.title = "Unrelated Title"
    if synchronized:
        for index, field in enumerate(IDENTITY_TAG_FIELDS, 1):
            setattr(media, field, mbid(index))
    media.save()
    if old_atime:
        mtime_ns = time.time_ns() - 60 * 60 * 1_000_000_000
        atime_ns = mtime_ns - 48 * 60 * 60 * 1_000_000_000
        os.utime(path, ns=(atime_ns, mtime_ns))
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(
        path=str(path).encode(),
        artist="Example Artist",
        title="Track",
        mtime=17.0,
        mb_albumid=mbid(1),
        mb_releasegroupid=mbid(2),
        mb_trackid=mbid(3),
        mb_releasetrackid=mbid(4),
    )
    library.add(item)
    selected = select_library_identity_targets(library, f"id:{item.id}")[0]
    target = prepare_identity_tag_database_target(library, selected)
    target_plan = plan_identity_tag_targets((target,))[0]
    return library, target, target_plan.files[0], path


def _artifacts(tmp_path: Path) -> list[Path]:
    return list(tmp_path.glob(".noqlen-identity-*"))


def _read_without_atime(path: Path, opener: object = os.open) -> bytes:
    descriptor = opener(path, os.O_RDONLY | os.O_NOATIME)  # type: ignore[operator]
    chunks = []
    try:
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def test_preview_plan_creates_no_artifact_and_noop_writes_nothing(tmp_path: Path) -> None:
    library, target, plan, path = _case(tmp_path, synchronized=True)
    before = _read_without_atime(path)

    assert plan.is_noop
    assert _artifacts(tmp_path) == []
    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.is_noop
    assert _read_without_atime(path) == before
    assert _artifacts(tmp_path) == []


def test_success_replaces_candidate_writes_four_and_preserves_unrelated_tags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    old_inode = path.stat().st_ino
    saved: list[str] = []
    original_save = MediaFile.save

    def record_save(media: MediaFile, **kwargs: object) -> None:
        saved.append(str(media.filething.filename))
        original_save(media, **kwargs)

    monkeypatch.setattr(MediaFile, "save", record_save)

    result = apply_identity_tag_file_plan(library, target, plan)

    media = MediaFile(path)
    assert result.applied_fields == IDENTITY_TAG_FIELDS
    assert tuple(getattr(media, field) for field in IDENTITY_TAG_FIELDS) == tuple(
        mbid(index) for index in range(1, 5)
    )
    assert (media.artist, media.title) == ("Unrelated Artist", "Unrelated Title")
    assert path.stat().st_ino != old_inode
    assert saved and all(saved_path != str(path) for saved_path in saved)
    assert _artifacts(tmp_path) == []


def test_malformed_and_conflicting_tags_are_replaced(tmp_path: Path) -> None:
    library, target, plan, path = _case(tmp_path)
    media = MediaFile(path)
    media.mb_albumid = "malformed"
    media.mb_trackid = mbid(999)
    media.save()
    target_plan = plan_identity_tag_targets((target,))[0]

    result = apply_identity_tag_file_plan(library, target, target_plan.files[0])

    assert result.has_applied_changes
    assert MediaFile(path).mb_albumid == mbid(1)
    assert MediaFile(path).mb_trackid == mbid(3)


def test_symlink_and_existing_hard_link_are_blocked(tmp_path: Path) -> None:
    real = tmp_path / "real.flac"
    shutil.copy2(FIXTURE, real)
    symlink = tmp_path / "link.flac"
    symlink.symlink_to(real)
    hard = tmp_path / "hard.flac"
    os.link(real, hard)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    for index, path in enumerate((symlink, real), 1):
        library.add(
            Item(
                path=str(path).encode(),
                artist="Artist",
                title=f"Track {index}",
                mb_albumid=mbid(1),
                mb_releasegroupid=mbid(2),
                mb_trackid=mbid(10 + index),
                mb_releasetrackid=mbid(20 + index),
            )
        )

    targets = tuple(
        prepare_identity_tag_database_target(library, selected)
        for selected in select_library_identity_targets(library)
    )
    plans = plan_identity_tag_targets(targets)

    assert [plan.files[0].blocked_reason for plan in plans] == [
        "identity tag file is not a regular file",
        "identity tag file has multiple hard links",
    ]


def test_duplicate_selected_path_is_blocked(tmp_path: Path) -> None:
    path = tmp_path / "same.flac"
    shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    for index in range(2):
        library.add(
            Item(
                path=str(path).encode(),
                artist="Artist",
                title=str(index),
                mb_albumid=mbid(1),
                mb_releasegroupid=mbid(2),
                mb_trackid=mbid(10 + index),
                mb_releasetrackid=mbid(20 + index),
            )
        )
    targets = tuple(
        prepare_identity_tag_database_target(library, selected)
        for selected in select_library_identity_targets(library)
    )

    plans = plan_identity_tag_targets(targets)

    assert all(
        plan.files[0].blocked_reason == "duplicate identity tag file path" for plan in plans
    )


def test_stale_fingerprint_preflight_blocks_before_candidate(tmp_path: Path) -> None:
    library, target, plan, path = _case(tmp_path)
    path.touch()

    with pytest.raises(IdentityTagApplicationError, match="changed"):
        verify_identity_tag_file_plan(library, target, plan)

    assert _artifacts(tmp_path) == []


def test_candidate_save_failure_leaves_source_and_cleans_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    before = _read_without_atime(path)
    monkeypatch.setattr(MediaFile, "save", lambda *args, **kwargs: (_ for _ in ()).throw(OSError()))

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.is_blocked
    assert _read_without_atime(path) == before
    assert _artifacts(tmp_path) == []


def test_source_change_during_candidate_copy_blocks_before_replacement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    original_copy = application_module.copy_regular_file_without_source_atime

    def copy_then_change(source: bytes, destination: bytes, **kwargs: object) -> None:
        original_copy(source, destination, **kwargs)  # type: ignore[arg-type]
        with path.open("ab") as stream:
            stream.write(b"external-change")

    monkeypatch.setattr(
        application_module, "copy_regular_file_without_source_atime", copy_then_change
    )

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.blocked_reason == "identity tag source changed before replacement"
    assert _artifacts(tmp_path) == []


def test_replacement_failure_leaves_source_intact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    before = _read_without_atime(path)
    original_replace = os.replace

    def reject_candidate(source: object, destination: object) -> None:
        if b"candidate" in os.fsencode(source):
            raise OSError("private replacement failure")
        original_replace(source, destination)

    monkeypatch.setattr(application_module.os, "replace", reject_candidate)

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.is_blocked
    assert _read_without_atime(path) == before
    assert _artifacts(tmp_path) == []


def test_post_replacement_failure_restores_original(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    # Preserve the plan's exact source atime snapshot.
    before = _read_without_atime(path)
    original_verify = application_module._verify_logical_snapshot
    calls = 0

    def fail_second(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("private post replacement failure")
        original_verify(*args, **kwargs)

    monkeypatch.setattr(application_module, "_verify_logical_snapshot", fail_second)

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.blocked_reason == "identity tag original restored after failed synchronization"
    assert _read_without_atime(path) == before
    assert _artifacts(tmp_path) == []


def test_restore_failure_is_integrity_critical(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, _ = _case(tmp_path)
    original_verify = application_module._verify_logical_snapshot
    calls = 0

    def fail_second(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError
        original_verify(*args, **kwargs)

    monkeypatch.setattr(application_module, "_verify_logical_snapshot", fail_second)
    monkeypatch.setattr(
        application_module,
        "_restore_original",
        lambda *args: (_ for _ in ()).throw(OSError("private path")),
    )

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    assert captured.value.integrity_critical is True
    assert captured.value.committed is True
    assert "private" not in str(captured.value)


def test_mtime_update_failure_restores_original(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path, old_atime=True)
    before = _read_without_atime(path)
    before_stat = path.stat()
    events: list[str] = []
    original_mutate = Transaction.mutate

    def fail_update(
        transaction: Transaction, statement: str, subvals: object = ()
    ) -> object:
        if statement == application_module._UPDATE_MTIME_SQL:
            raise OSError("private database failure")
        return original_mutate(transaction, statement, subvals)

    monkeypatch.setattr(Transaction, "mutate", fail_update)
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda event, **kwargs: events.append(event),
    )

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.is_blocked
    assert _read_without_atime(path) == before
    after_stat = path.stat()
    assert after_stat.st_atime_ns == before_stat.st_atime_ns
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert after_stat.st_nlink == 1
    restored = filesystem_module.snapshot_identity_tag_file(str(path).encode())
    assert all(value is None for _, value in restored.identity_values)
    assert library.get_item(plan.database.selected.item_id).mtime == 17.0  # type: ignore[union-attr]
    assert events == []
    assert _artifacts(tmp_path) == []


def test_mtime_rollback_failure_retains_recovery_backup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    original_mutate = Transaction.mutate
    removed: list[bytes | None] = []
    original_remove = application_module._remove_artifact
    events: list[str] = []

    def fail_update_and_rollback(
        transaction: Transaction, statement: str, subvals: object = ()
    ) -> object:
        if statement == application_module._UPDATE_MTIME_SQL:
            raise OSError("private update failure")
        if statement == application_module._ROLLBACK_SQL:
            raise OSError("private rollback SQL failure")
        return original_mutate(transaction, statement, subvals)

    def record_remove(artifact: bytes | None) -> bool:
        removed.append(artifact)
        return original_remove(artifact)

    monkeypatch.setattr(Transaction, "mutate", fail_update_and_rollback)
    monkeypatch.setattr(application_module, "_remove_artifact", record_remove)
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda event, **kwargs: events.append(event),
    )

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    error = captured.value
    artifacts = _artifacts(tmp_path)
    assert error.integrity_critical is True
    assert error.committed is True
    assert error.state_uncertain is True
    assert error.recovery_artifact_retained is True
    assert MediaFile(path).mb_albumid == mbid(1)
    assert len(artifacts) == 1 and "backup" in artifacts[0].name
    assert str(artifacts[0]) not in str(error)
    assert mbid(1) not in str(error)
    assert "SQL" not in str(error)
    assert os.fsencode(artifacts[0]) not in tuple(entry for entry in removed if entry)
    assert events == []
    artifacts[0].unlink()


def test_root_transaction_commit_uncertainty_retains_recovery_backup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    original_transaction = library.transaction
    original_store = application_module._store_operational_mtime
    first = True

    class UncertainTransaction:
        def __init__(self) -> None:
            self.context = original_transaction()

        def __enter__(self):
            return self.context.__enter__()

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> object:
            result = self.context.__exit__(exc_type, exc, traceback)
            if exc_type is None:
                raise OSError("private root commit uncertainty")
            return result

    def transaction():
        nonlocal first
        if first:
            first = False
            return UncertainTransaction()
        return original_transaction()

    def uncertain_store(*args: object, **kwargs: object):
        monkeypatch.setattr(library, "transaction", transaction)
        return original_store(*args, **kwargs)

    monkeypatch.setattr(application_module, "_store_operational_mtime", uncertain_store)

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    error = captured.value
    artifacts = _artifacts(tmp_path)
    assert error.integrity_critical is True
    assert error.committed is True
    assert error.recovery_artifact_retained is True
    assert MediaFile(path).mb_albumid == mbid(1)
    assert len(artifacts) == 1
    artifacts[0].unlink()


def test_confirmed_post_commit_verification_failure_does_not_restore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    original_store = application_module._store_operational_mtime

    def fail_after_commit(*args: object, **kwargs: object):
        original_store(*args, **kwargs)
        raise IdentityTagApplicationError(
            "identity tag mtime committed but fresh verification failed",
            committed=True,
        )

    monkeypatch.setattr(application_module, "_store_operational_mtime", fail_after_commit)

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    assert captured.value.committed is True
    assert MediaFile(path).mb_albumid == mbid(1)
    assert _artifacts(tmp_path) == []


def test_post_replacement_interruption_retains_recovery_backup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    monkeypatch.setattr(
        application_module,
        "_store_operational_mtime",
        lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    error = captured.value
    artifacts = _artifacts(tmp_path)
    assert error.integrity_critical is True
    assert error.committed is True
    assert error.recovery_artifact_retained is True
    assert isinstance(error.__cause__, KeyboardInterrupt)
    assert MediaFile(path).mb_albumid == mbid(1)
    assert len(artifacts) == 1
    artifacts[0].unlink()


def test_backup_copy_fallback_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    monkeypatch.setattr(
        application_module.os,
        "link",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError()),
    )

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.has_applied_changes
    assert MediaFile(path).mb_albumid == mbid(1)
    assert _artifacts(tmp_path) == []


def test_candidate_copy_preserves_source_atime_before_safe_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path, old_atime=True)
    before = _read_without_atime(path)
    before_stat = path.stat()
    before_mtime = library.get_item(plan.database.selected.item_id).mtime  # type: ignore[union-attr]
    flags: list[int] = []
    events: list[str] = []
    original_open = filesystem_module.os.open

    def record_open(open_path: object, open_flags: int, *args: object, **kwargs: object):
        if os.fsencode(open_path) == os.fsencode(path):
            flags.append(open_flags)
        return original_open(open_path, open_flags, *args, **kwargs)

    monkeypatch.setattr(filesystem_module.os, "open", record_open)
    monkeypatch.setattr(
        application_module,
        "_verify_logical_snapshot",
        lambda *args: (_ for _ in ()).throw(ValueError("private forced failure")),
    )
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda event, **kwargs: events.append(event),
    )

    result = apply_identity_tag_file_plan(library, target, plan)

    after_stat = path.stat()
    assert result.is_blocked
    assert _read_without_atime(path) == before
    assert after_stat.st_atime_ns == before_stat.st_atime_ns
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    restored_snapshot = filesystem_module.snapshot_identity_tag_file(str(path).encode())
    assert all(value is None for _, value in restored_snapshot.identity_values)
    assert library.get_item(plan.database.selected.item_id).mtime == before_mtime  # type: ignore[union-attr]
    assert flags and all(flag & os.O_NOATIME for flag in flags)
    assert _artifacts(tmp_path) == []
    assert events == []


def test_success_preserves_planned_atime_and_commits_new_mtime(tmp_path: Path) -> None:
    library, target, plan, path = _case(tmp_path, old_atime=True)
    before_stat = path.stat()

    result = apply_identity_tag_file_plan(library, target, plan)

    after_stat = path.stat()
    fresh = library.get_item(plan.database.selected.item_id)
    assert fresh is not None
    assert result.has_applied_changes
    assert after_stat.st_atime_ns == before_stat.st_atime_ns
    assert after_stat.st_mtime_ns != before_stat.st_mtime_ns
    assert fresh.mtime == after_stat.st_mtime


def test_backup_copy_fallback_preserves_source_atime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path, old_atime=True)
    before_atime = path.stat().st_atime_ns
    original_backup = application_module._create_backup

    monkeypatch.setattr(
        application_module.os,
        "link",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError()),
    )

    def verify_fallback(*args: object, **kwargs: object):
        result = original_backup(*args, **kwargs)
        assert path.stat().st_atime_ns == before_atime
        return result

    monkeypatch.setattr(application_module, "_create_backup", verify_fallback)

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.has_applied_changes
    assert path.stat().st_atime_ns == before_atime
    assert _artifacts(tmp_path) == []


def test_atime_safe_copy_unsupported_blocks_without_source_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path, old_atime=True)
    before = _read_without_atime(path)
    before_stat = path.stat()
    events: list[str] = []
    original_open = filesystem_module.os.open

    def reject_noatime(open_path: object, flags: int, *args: object, **kwargs: object):
        if os.fsencode(open_path) == os.fsencode(path) and flags & os.O_NOATIME:
            raise PermissionError(13, "private permission failure", str(path))
        return original_open(open_path, flags, *args, **kwargs)

    monkeypatch.setattr(filesystem_module.os, "open", reject_noatime)
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda event, **kwargs: events.append(event),
    )

    result = apply_identity_tag_file_plan(library, target, plan)

    after_stat = path.stat()
    assert result.blocked_reason == "identity tag atime-safe file copy is unsupported"
    assert _read_without_atime(path) == before
    assert after_stat.st_atime_ns == before_stat.st_atime_ns
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert str(path) not in result.blocked_reason
    assert "permission" not in result.blocked_reason
    assert _artifacts(tmp_path) == []
    assert events == []


def test_production_never_uses_copy2_for_selected_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    original_copy2 = shutil.copy2

    def reject_source_copy(source: object, destination: object, **kwargs: object):
        if os.fsencode(source) == os.fsencode(path):
            pytest.fail("production used copy2 for selected source")
        return original_copy2(source, destination, **kwargs)

    monkeypatch.setattr(shutil, "copy2", reject_source_copy)
    monkeypatch.setattr(
        application_module.os,
        "link",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError()),
    )

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.has_applied_changes
    assert MediaFile(path).mb_albumid == mbid(1)


def test_candidate_hard_link_swap_cannot_truncate_another_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    victim = tmp_path / "victim.bin"
    victim.write_bytes(b"unrelated-test-data")
    source_before = _read_without_atime(path)
    victim_before = victim.read_bytes()
    original_copy = application_module.copy_regular_file_without_source_atime

    def swap_candidate(
        source: bytes,
        destination: bytes,
        *,
        destination_exists: bool,
        destination_descriptor: int | None = None,
    ) -> None:
        os.unlink(destination)
        os.link(victim, destination)
        original_copy(
            source,
            destination,
            destination_exists=destination_exists,
            destination_descriptor=destination_descriptor,
        )

    monkeypatch.setattr(
        application_module, "copy_regular_file_without_source_atime", swap_candidate
    )

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.is_blocked
    assert _read_without_atime(path) == source_before
    assert victim.read_bytes() == victim_before
    assert _artifacts(tmp_path) == []


def test_corrupted_backup_mtime_makes_restoration_integrity_critical(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, _ = _case(tmp_path, old_atime=True)
    original_restore = application_module._restore_original

    def corrupt_mtime(
        path: bytes,
        backup: bytes | None,
        digest: bytes | None,
        snapshot: object,
    ) -> None:
        assert backup is not None
        info = os.stat(backup, follow_symlinks=False)
        os.utime(backup, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
        original_restore(path, backup, digest, snapshot)  # type: ignore[arg-type]

    monkeypatch.setattr(application_module, "_restore_original", corrupt_mtime)
    monkeypatch.setattr(
        application_module,
        "_store_operational_mtime",
        lambda *args: (_ for _ in ()).throw(ValueError()),
    )

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    assert captured.value.integrity_critical is True
    assert captured.value.committed is True
    assert captured.value.state_uncertain is True


def test_unexpected_restored_link_count_is_integrity_critical(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, _ = _case(tmp_path)
    extra_link = tmp_path / "test-extra-link"
    original_restore = application_module._restore_original

    def add_link(
        path: bytes,
        backup: bytes | None,
        digest: bytes | None,
        snapshot: object,
    ) -> None:
        assert backup is not None
        os.link(backup, extra_link)
        original_restore(path, backup, digest, snapshot)  # type: ignore[arg-type]

    monkeypatch.setattr(application_module, "_restore_original", add_link)
    monkeypatch.setattr(
        application_module,
        "_store_operational_mtime",
        lambda *args: (_ for _ in ()).throw(ValueError()),
    )

    try:
        with pytest.raises(IdentityTagApplicationError) as captured:
            apply_identity_tag_file_plan(library, target, plan)
        assert captured.value.integrity_critical is True
        assert captured.value.committed is True
        assert captured.value.state_uncertain is True
    finally:
        extra_link.unlink(missing_ok=True)


def test_committed_backup_cleanup_failure_retains_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    original_remove = application_module._remove_artifact

    def fail_backup_remove(artifact: bytes | None) -> bool:
        if artifact is not None and b"backup" in artifact:
            return False
        return original_remove(artifact)

    monkeypatch.setattr(application_module, "_remove_artifact", fail_backup_remove)

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    error = captured.value
    fresh = library.get_item(plan.database.selected.item_id)
    artifacts = _artifacts(tmp_path)
    assert error.committed is True
    assert error.integrity_critical is False
    assert error.state_uncertain is False
    assert error.recovery_artifact_retained is True
    assert MediaFile(path).mb_albumid == mbid(1)
    assert fresh is not None and fresh.mtime == path.stat().st_mtime
    assert len(artifacts) == 1
    assert str(artifacts[0]) not in str(error)
    original_remove(os.fsencode(artifacts[0]))


def test_confirmed_post_commit_error_cleanup_failure_retains_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    original_store = application_module._store_operational_mtime
    original_remove = application_module._remove_artifact

    def committed_failure(*args: object, **kwargs: object):
        original_store(*args, **kwargs)
        raise IdentityTagApplicationError(
            "identity tag mtime committed but fresh verification failed",
            committed=True,
        )

    def fail_backup_remove(artifact: bytes | None) -> bool:
        if artifact is not None and b"backup" in artifact:
            return False
        return original_remove(artifact)

    monkeypatch.setattr(application_module, "_store_operational_mtime", committed_failure)
    monkeypatch.setattr(application_module, "_remove_artifact", fail_backup_remove)

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    error = captured.value
    artifacts = _artifacts(tmp_path)
    assert error.committed is True
    assert error.recovery_artifact_retained is True
    assert MediaFile(path).mb_albumid == mbid(1)
    assert len(artifacts) == 1
    original_remove(os.fsencode(artifacts[0]))


def test_only_mtime_changes_and_events_follow_full_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    item_id = plan.database.selected.item_id
    before = library.get_item(item_id)
    assert before is not None
    identity_before = tuple(before.get(field, with_album=False) for field in IDENTITY_TAG_FIELDS)
    events: list[tuple[str, dict[str, object]]] = []
    source_verified = False
    mtime_verified = False
    verification_calls = 0
    original_verify = application_module._verify_logical_snapshot
    original_store = application_module._store_operational_mtime

    def verify(*args: object, **kwargs: object) -> None:
        nonlocal source_verified, verification_calls
        original_verify(*args, **kwargs)
        verification_calls += 1
        if verification_calls == 2:
            source_verified = True

    def store(*args: object, **kwargs: object):
        nonlocal mtime_verified
        fresh = original_store(*args, **kwargs)
        mtime_verified = True
        return fresh

    def send(event: str, **kwargs: object) -> None:
        assert source_verified
        assert mtime_verified
        persisted = library.get_item(item_id)
        assert persisted is not None and persisted.mtime != 17.0
        events.append((event, kwargs))

    monkeypatch.setattr(application_module, "_verify_logical_snapshot", verify)
    monkeypatch.setattr(application_module, "_store_operational_mtime", store)
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        send,
    )

    result = apply_identity_tag_file_plan(library, target, plan)

    after = library.get_item(item_id)
    assert after is not None
    assert result.has_applied_changes
    assert after.mtime != 17.0
    assert (
        tuple(after.get(field, with_album=False) for field in IDENTITY_TAG_FIELDS)
        == identity_before
    )
    assert [event for event, _ in events] == ["after_write", "database_change"]
    after_write = events[0][1]
    assert set(after_write) == {"item", "path"}
    assert after_write["path"] == str(path).encode()
    assert after_write["item"] is not plan.database.selected.item
    assert after_write["item"].mtime == after.mtime  # type: ignore[union-attr]
    assert "tags" not in after_write
    assert all(event != "write" for event, _ in events)


@pytest.mark.parametrize("failed_event", ["after_write", "database_change"])
def test_event_failure_reports_committed_without_restoring(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failed_event: str
) -> None:
    library, target, plan, path = _case(tmp_path)
    events: list[str] = []

    def fail_selected(event: str, **kwargs: object) -> None:
        events.append(event)
        if event == failed_event:
            raise RuntimeError(f"private listener at {path}")

    monkeypatch.setattr(
        application_module.plugins,
        "send",
        fail_selected,
    )

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    assert captured.value.committed is True
    assert isinstance(captured.value, ui.UserError)
    assert MediaFile(path).mb_albumid == mbid(1)
    assert "private" not in str(captured.value)
    assert str(path) not in str(captured.value)
    assert _artifacts(tmp_path) == []
    assert events == (["after_write"] if failed_event == "after_write" else [
        "after_write",
        "database_change",
    ])


def test_noop_blocked_and_restored_attempts_emit_no_events(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    noop_library, noop_target, noop_plan, _ = _case(tmp_path / "noop", synchronized=True)
    blocked_library, blocked_target, blocked_plan, _ = _case(tmp_path / "blocked")
    restored_library, restored_target, restored_plan, _ = _case(tmp_path / "restored")
    events: list[str] = []
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda event, **kwargs: events.append(event),
    )
    assert apply_identity_tag_file_plan(noop_library, noop_target, noop_plan).is_noop

    blocked_plan = type(blocked_plan)(
        blocked_plan.database,
        None,
        (),
        "identity tag file unavailable",
    )
    assert apply_identity_tag_file_plan(blocked_library, blocked_target, blocked_plan).is_blocked

    monkeypatch.setattr(
        application_module,
        "_store_operational_mtime",
        lambda *args: (_ for _ in ()).throw(ValueError()),
    )
    assert apply_identity_tag_file_plan(
        restored_library, restored_target, restored_plan
    ).is_blocked
    assert events == []
