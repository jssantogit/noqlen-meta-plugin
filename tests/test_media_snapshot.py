import os
import shutil
from pathlib import Path

import pytest
from mediafile import MediaFile

from beetsplug.noqlenmeta.media_snapshot import freeze_media_value, snapshot_media_file

FIXTURE = Path(__file__).parent / "fixtures" / "identity_tags" / "silence.flac"


def test_snapshot_reads_requested_fields_and_filesystem_metadata(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    media = MediaFile(path)
    media.title = "Synthetic Title"
    media.artist = "Synthetic Artist"
    media.save()

    snapshot = snapshot_media_file(os.fsencode(path), fields=("title", "artist"))

    assert snapshot.path == os.fsencode(path)
    assert dict(snapshot.values)["title"] == "Synthetic Title"
    assert snapshot.filesystem_metadata.size == os.stat(path).st_size


def test_snapshot_rejects_symlink_and_non_regular_file(tmp_path: Path) -> None:
    source = tmp_path / "source.flac"
    shutil.copy2(FIXTURE, source)
    link = tmp_path / "link.flac"
    link.symlink_to(source)

    with pytest.raises(ValueError, match="regular file"):
        snapshot_media_file(os.fsencode(link), fields=("title",))
    with pytest.raises(ValueError, match="regular file"):
        snapshot_media_file(os.fsencode(tmp_path), fields=("title",))


def test_freeze_media_value_is_deterministic_for_sequences() -> None:
    assert freeze_media_value(["A", ("B", "C")]) == ("A", ("B", "C"))
