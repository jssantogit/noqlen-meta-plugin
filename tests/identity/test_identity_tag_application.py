from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from beets import ui
from beets.library import Item, Library
from mediafile import MediaFile

import beetsplug.noqlenmeta.identity.tag_application as application_module
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


def _case(tmp_path: Path, *, synchronized: bool = False):
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    media = MediaFile(path)
    media.artist = "Unrelated Artist"
    media.title = "Unrelated Title"
    if synchronized:
        for index, field in enumerate(IDENTITY_TAG_FIELDS, 1):
            setattr(media, field, mbid(index))
    media.save()
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


def test_preview_plan_creates_no_artifact_and_noop_writes_nothing(tmp_path: Path) -> None:
    library, target, plan, path = _case(tmp_path, synchronized=True)
    before = path.read_bytes()

    assert plan.is_noop
    assert _artifacts(tmp_path) == []
    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.is_noop
    assert path.read_bytes() == before
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
    before = path.read_bytes()
    monkeypatch.setattr(MediaFile, "save", lambda *args, **kwargs: (_ for _ in ()).throw(OSError()))

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.is_blocked
    assert path.read_bytes() == before
    assert _artifacts(tmp_path) == []


def test_source_change_during_candidate_copy_blocks_before_replacement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    original_copy = shutil.copy2

    def copy_then_change(source: object, destination: object, **kwargs: object):
        result = original_copy(source, destination, **kwargs)
        with path.open("ab") as stream:
            stream.write(b"external-change")
        return result

    monkeypatch.setattr(application_module.shutil, "copy2", copy_then_change)

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.blocked_reason == "identity tag source changed before replacement"
    assert _artifacts(tmp_path) == []


def test_replacement_failure_leaves_source_intact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    before = path.read_bytes()
    original_replace = os.replace

    def reject_candidate(source: object, destination: object) -> None:
        if b"candidate" in os.fsencode(source):
            raise OSError("private replacement failure")
        original_replace(source, destination)

    monkeypatch.setattr(application_module.os, "replace", reject_candidate)

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.is_blocked
    assert path.read_bytes() == before
    assert _artifacts(tmp_path) == []


def test_post_replacement_failure_restores_original(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    before = path.read_bytes()
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
    assert path.read_bytes() == before
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
    assert "private" not in str(captured.value)


def test_mtime_update_failure_restores_original(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(
        application_module,
        "_store_operational_mtime",
        lambda *args: (_ for _ in ()).throw(ValueError("private database failure")),
    )

    result = apply_identity_tag_file_plan(library, target, plan)

    assert result.is_blocked
    assert path.read_bytes() == before
    assert library.get_item(plan.database.selected.item_id).mtime == 17.0  # type: ignore[union-attr]


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


def test_only_mtime_changes_and_events_follow_full_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, _ = _case(tmp_path)
    item_id = plan.database.selected.item_id
    before = library.get_item(item_id)
    assert before is not None
    identity_before = tuple(before.get(field, with_album=False) for field in IDENTITY_TAG_FIELDS)
    events: list[str] = []
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda event, **kwargs: events.append(event),
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
    assert events == ["write", "database_change"]


def test_event_failure_reports_committed_without_restoring(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library, target, plan, path = _case(tmp_path)
    monkeypatch.setattr(
        application_module.plugins,
        "send",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("private listener")),
    )

    with pytest.raises(IdentityTagApplicationError) as captured:
        apply_identity_tag_file_plan(library, target, plan)

    assert captured.value.committed is True
    assert isinstance(captured.value, ui.UserError)
    assert MediaFile(path).mb_albumid == mbid(1)
    assert "private" not in str(captured.value)
    assert _artifacts(tmp_path) == []
