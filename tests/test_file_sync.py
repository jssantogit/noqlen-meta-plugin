import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from beets.library import Item, Library
from mediafile import MediaFile

import beetsplug.noqlenmeta.file_sync as file_sync_module
from beetsplug.noqlenmeta.changeplan import PlannedChange
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.file_sync import (
    FileSyncApplicationError,
    apply_file_sync_plan,
    plan_file_sync,
    verify_file_sync_plan,
)

FIXTURE = Path(__file__).parent / "fixtures" / "identity_tags" / "silence.flac"


@pytest.fixture
def media_item(tmp_path: Path) -> tuple[Library, Item, Path]:
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    media = MediaFile(path)
    media.title = "Synthetic Title"
    media.artist = "Synthetic Artist"
    media.save()
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(
        path=os.fsencode(path),
        artist="Synthetic Artist",
        title="Synthetic Title",
        mtime=17.0,
    )
    library.add(item)
    return library, library.get_item(item.id), path


def planned_change(field: str, value: object) -> PlannedChange:
    candidate = MetadataCandidate(field, value, "catalog", 0.95, "42")  # type: ignore[arg-type]
    return PlannedChange(field, None, candidate.value, candidate, f"resolved {field}")


def test_planner_maps_supported_values_without_mutating_item(media_item) -> None:
    _, item, _ = media_item
    snapshot = dict(item)

    plan = plan_file_sync(item, (planned_change("bpm", 126.0),))

    assert plan.blockers == ()
    assert plan.changes[0].media_field == "bpm"
    assert plan.changes[0].after == 126.0
    assert dict(item) == snapshot


def test_planner_blocks_unsupported_multivalue_field(media_item) -> None:
    _, item, _ = media_item

    plan = plan_file_sync(item, (planned_change("moods", ("Dark",)),))

    assert plan.changes == ()
    assert plan.blockers[0].canonical_field == "moods"


def test_planner_blocks_fractional_bpm_that_mediafile_would_round(media_item) -> None:
    _, item, _ = media_item

    plan = plan_file_sync(item, (planned_change("bpm", 126.4),))

    assert plan.changes == ()
    assert "fractional value losslessly" in plan.blockers[0].reason


def test_apply_writes_bpm_and_preserves_unrelated_tags(media_item) -> None:
    library, item, path = media_item
    plan = plan_file_sync(item, (planned_change("bpm", 126.0),))

    result = apply_file_sync_plan(library, plan)

    written = MediaFile(path)
    assert result.committed, result
    assert written.bpm == 126
    assert (written.title, written.artist) == ("Synthetic Title", "Synthetic Artist")
    assert result.committed


def test_apply_writes_synthetic_lyrics(media_item) -> None:
    library, item, path = media_item
    plan = plan_file_sync(item, (planned_change("lyrics", "Synthetic line"),))

    apply_file_sync_plan(library, plan)

    assert MediaFile(path).lyrics == "Synthetic line"


def test_preflight_rejects_source_change(media_item) -> None:
    library, item, path = media_item
    plan = plan_file_sync(item, (planned_change("bpm", 126.0),))
    path.write_bytes(path.read_bytes() + b"changed")

    with pytest.raises(FileSyncApplicationError, match="source changed"):
        verify_file_sync_plan(library, plan)


def test_forged_plan_is_rejected(media_item) -> None:
    library, item, _ = media_item
    plan = plan_file_sync(item, (planned_change("bpm", 126.0),))
    forged = replace(
        plan,
        changes=(replace(plan.changes[0], media_field="title"),),
    )

    with pytest.raises(FileSyncApplicationError, match="canonical"):
        apply_file_sync_plan(library, forged)


def test_candidate_save_failure_leaves_original(media_item, monkeypatch) -> None:
    library, item, path = media_item
    plan = plan_file_sync(item, (planned_change("bpm", 126.0),))
    before = path.read_bytes()
    monkeypatch.setattr(MediaFile, "save", lambda self: (_ for _ in ()).throw(OSError("save")))

    result = apply_file_sync_plan(library, plan)

    assert not result.committed
    assert path.read_bytes() == before


def test_post_replace_db_failure_restores_original(media_item, monkeypatch) -> None:
    library, item, path = media_item
    plan = plan_file_sync(item, (planned_change("bpm", 126.0),))
    before = path.read_bytes()
    monkeypatch.setattr(
        file_sync_module,
        "_store_operational_mtime",
        lambda *args: (_ for _ in ()).throw(OSError("database")),
    )

    result = apply_file_sync_plan(library, plan)

    assert not result.committed
    assert path.read_bytes() == before


def test_notification_failure_reports_committed_file(media_item, monkeypatch) -> None:
    library, item, path = media_item
    plan = plan_file_sync(item, (planned_change("bpm", 126.0),))
    original_send = file_sync_module.plugins.send

    def fail_after_write(event: str, **kwargs: object) -> None:
        if event == "after_write":
            raise OSError("notification")
        original_send(event, **kwargs)

    monkeypatch.setattr(file_sync_module.plugins, "send", fail_after_write)

    with pytest.raises(FileSyncApplicationError) as captured:
        apply_file_sync_plan(library, plan)

    assert captured.value.committed
    assert not captured.value.state_uncertain
    assert not captured.value.recovery_artifact_retained
    assert MediaFile(path).bpm == 126
