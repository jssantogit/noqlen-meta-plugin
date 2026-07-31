from __future__ import annotations

import shutil
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from beets.library import Item, Library
from mediafile import MediaFile

from beetsplug.noqlenmeta.identity import (
    IDENTITY_TAG_FIELDS,
    IdentityTagApplicationError,
    IdentityTagFieldStatus,
    apply_identity_tag_file_plan,
    identity_tag_field_status,
    map_identity_tag_file,
    prepare_identity_tag_database_target,
    select_library_identity_targets,
    snapshot_identity_tag_file,
)

from .helpers import mbid

FIXTURE = Path(__file__).parents[1] / "fixtures" / "identity_tags" / "silence.flac"


def _prepared(tmp_path: Path):
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(
        path=str(path).encode(),
        artist="Example Artist",
        title="Track",
        mb_albumid=mbid(1),
        mb_releasegroupid=mbid(2),
        mb_trackid=mbid(3),
        mb_releasetrackid=mbid(4),
    )
    library.add(item)
    selected = select_library_identity_targets(library, f"id:{item.id}")[0]
    return library, prepare_identity_tag_database_target(library, selected), path


def _set(path: Path, **values: object) -> None:
    media = MediaFile(path)
    for field, value in values.items():
        setattr(media, field, value)
    media.save()


def test_field_status_rules_and_deterministic_order(tmp_path: Path) -> None:
    assert identity_tag_field_status(mbid(1), mbid(1)) is IdentityTagFieldStatus.KEEP
    assert identity_tag_field_status(None, mbid(1)) is IdentityTagFieldStatus.MISSING
    assert identity_tag_field_status(mbid(2), mbid(1)) is IdentityTagFieldStatus.CONFLICT
    assert identity_tag_field_status("bad", mbid(1)) is IdentityTagFieldStatus.MALFORMED
    library, target, path = _prepared(tmp_path)
    del library

    plan = map_identity_tag_file(target.files[0], snapshot_identity_tag_file(str(path).encode()))

    assert tuple(change.field for change in plan.changes) == IDENTITY_TAG_FIELDS
    assert all(change.expected_value == mbid(index) for index, change in enumerate(plan.changes, 1))


def test_four_keep_is_an_immutable_noop(tmp_path: Path) -> None:
    _, target, path = _prepared(tmp_path)
    _set(path, **dict(target.files[0].expected.as_tuple()))  # type: ignore[union-attr]

    plan = map_identity_tag_file(target.files[0], snapshot_identity_tag_file(str(path).encode()))

    assert plan.is_noop
    with pytest.raises(FrozenInstanceError):
        plan.blocked_reason = "changed"  # type: ignore[misc]


def test_forged_field_duplicate_and_path_relation_are_rejected(tmp_path: Path) -> None:
    library, target, path = _prepared(tmp_path)
    plan = map_identity_tag_file(target.files[0], snapshot_identity_tag_file(str(path).encode()))
    forged_field = replace(plan, changes=(replace(plan.changes[0], field="title"),))
    duplicate = replace(plan, changes=(plan.changes[0], plan.changes[0]))
    forged_database = replace(
        plan.database,
        database_snapshot=replace(plan.database.database_snapshot, path=b"private-forged.flac"),
    )
    forged_path = replace(plan, database=forged_database)

    for forged in (forged_field, duplicate, forged_path):
        with pytest.raises(IdentityTagApplicationError):
            apply_identity_tag_file_plan(library, target, forged)


def test_blocked_database_target_maps_no_file_write(tmp_path: Path) -> None:
    _, target, path = _prepared(tmp_path)
    blocked_database = replace(
        target.files[0], expected=None, blocked_reason="database identity incomplete"
    )

    plan = map_identity_tag_file(blocked_database, snapshot_identity_tag_file(str(path).encode()))

    assert plan.changes == ()
    assert plan.blocked_reason == "database identity incomplete"
