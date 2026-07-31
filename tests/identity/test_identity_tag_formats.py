from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
from beets.library import Item, Library
from mediafile import MediaFile

from beetsplug.noqlenmeta.identity import (
    IDENTITY_TAG_FIELDS,
    apply_identity_tag_file_plan,
    plan_identity_tag_targets,
    prepare_identity_tag_database_target,
    select_library_identity_targets,
)

from .helpers import mbid

FIXTURES = Path(__file__).parents[1] / "fixtures" / "identity_tags"


@pytest.mark.parametrize(
    "filename",
    ["silence.flac", "silence.mp3", "silence.m4a", "silence.ogg", "silence.opus"],
)
def test_real_mediafile_candidate_round_trip(filename: str, tmp_path: Path) -> None:
    fixture = FIXTURES / filename
    fixture_digest = hashlib.sha256(fixture.read_bytes()).digest()
    path = tmp_path / filename
    shutil.copy2(fixture, path)
    media = MediaFile(path)
    media.artist = "Synthetic Artist"
    media.title = "Synthetic Silence"
    media.album = "Synthetic Album"
    media.save()
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(
        path=str(path).encode(),
        artist="Synthetic Artist",
        title="Synthetic Silence",
        mb_albumid=mbid(1),
        mb_releasegroupid=mbid(2),
        mb_trackid=mbid(3),
        mb_releasetrackid=mbid(4),
    )
    library.add(item)
    selected = select_library_identity_targets(library, f"id:{item.id}")[0]
    target = prepare_identity_tag_database_target(library, selected)
    plan = plan_identity_tag_targets((target,))[0].files[0]

    result = apply_identity_tag_file_plan(library, target, plan)

    written = MediaFile(path)
    assert result.has_applied_changes
    assert tuple(getattr(written, field) for field in IDENTITY_TAG_FIELDS) == tuple(
        mbid(index) for index in range(1, 5)
    )
    assert (written.artist, written.title, written.album) == (
        "Synthetic Artist",
        "Synthetic Silence",
        "Synthetic Album",
    )
    assert hashlib.sha256(fixture.read_bytes()).digest() == fixture_digest
    assert list(tmp_path.glob(".noqlen-identity-*")) == []
