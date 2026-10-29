"""V3 .lrc sidecar safety: preview, no-clobber apply and stale checks."""

from pathlib import Path

import pytest
from beets.library import Item, Library

from beetsplug.noqlenmeta.changeplan import PlannedChange
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.lyrics_sidecar import (
    LyricsSidecarError,
    apply_lyrics_sidecar_plan,
    plan_lyrics_sidecar,
)


@pytest.fixture
def target(tmp_path: Path) -> tuple[Library, Item, Path]:
    path = tmp_path / "track.flac"
    path.write_bytes(b"synthetic audio")
    lib = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(path=str(path).encode(), artist="Artist", title="Title")
    lib.add(item)
    return lib, item, path.with_suffix(".lrc")


def candidate(text: str = "[00:01.20]Hello\n[00:04.00]World") -> PlannedChange:
    source = MetadataCandidate("synced_lyrics", text, "lrclib", 0.95, "123")
    return PlannedChange("synced_lyrics", None, source.value, source, "exact-track lyrics")


def test_preview_creates_nothing_and_apply_creates_lossless_utf8(
    target: tuple[Library, Item, Path],
) -> None:
    lib, item, sidecar = target
    change = candidate("[00:01.20]Olá\n[00:04.00]Música")
    plan = plan_lyrics_sidecar(item, change)

    assert plan.status == "PROPOSE"
    assert plan.source is change
    assert not sidecar.exists()

    result = apply_lyrics_sidecar_plan(lib, plan)
    assert result.created
    assert sidecar.read_bytes() == change.after.encode("utf-8")
    assert item.get_fresh_from_db().path == item.path


def test_existing_matching_lrc_keeps_without_modification(
    target: tuple[Library, Item, Path],
) -> None:
    lib, item, sidecar = target
    text = "[00:01.20]Hello\n[00:04.00]World"
    sidecar.write_text(text, encoding="utf-8")
    plan = plan_lyrics_sidecar(item, candidate(text))
    assert plan.status == "KEEP"
    assert not apply_lyrics_sidecar_plan(lib, plan).created
    assert sidecar.read_text(encoding="utf-8") == text


def test_different_existing_lrc_requires_review_and_is_never_overwritten(
    target: tuple[Library, Item, Path],
) -> None:
    lib, item, sidecar = target
    sidecar.write_text("[00:01.00]Existing", encoding="utf-8")
    plan = plan_lyrics_sidecar(item, candidate())
    assert plan.status == "REVIEW"
    assert not apply_lyrics_sidecar_plan(lib, plan).created
    assert sidecar.read_text(encoding="utf-8") == "[00:01.00]Existing"


def test_sidecar_created_after_preview_blocks_no_clobber_apply(
    target: tuple[Library, Item, Path],
) -> None:
    lib, item, sidecar = target
    plan = plan_lyrics_sidecar(item, candidate())
    sidecar.write_text("[00:03.00]Someone else", encoding="utf-8")

    with pytest.raises(LyricsSidecarError, match="changed|exists"):
        apply_lyrics_sidecar_plan(lib, plan)
    assert sidecar.read_text(encoding="utf-8") == "[00:03.00]Someone else"


def test_audio_path_changed_after_preview_is_stale(
    target: tuple[Library, Item, Path],
) -> None:
    lib, item, sidecar = target
    plan = plan_lyrics_sidecar(item, candidate())
    item.path = str(sidecar.with_suffix(".mp3")).encode()
    item.store()

    with pytest.raises(LyricsSidecarError, match="changed"):
        apply_lyrics_sidecar_plan(lib, plan)
    assert not sidecar.exists()


def test_symlink_target_is_not_followed_or_replaced(
    target: tuple[Library, Item, Path], tmp_path: Path
) -> None:
    lib, item, sidecar = target
    other = tmp_path / "sensitive.txt"
    other.write_text("Do not modify", encoding="utf-8")
    sidecar.symlink_to(other)
    plan = plan_lyrics_sidecar(item, candidate())
    assert plan.status == "REVIEW"
    assert not apply_lyrics_sidecar_plan(lib, plan).created
    assert other.read_text(encoding="utf-8") == "Do not modify"


@pytest.mark.parametrize("text", [
    "Plain lyrics with no timestamps",
    "[title:Song]\nNo timed lines",
    "[00:99.00]Invalid seconds",
    "[00:01.00]bad\\x00nul",
])
def test_invalid_or_untimed_lrc_is_blocked(
    target: tuple[Library, Item, Path], text: str
) -> None:
    lib, item, sidecar = target
    plan = plan_lyrics_sidecar(item, candidate(text))
    assert plan.status == "BLOCKED"
    assert not apply_lyrics_sidecar_plan(lib, plan).created
    assert not sidecar.exists()


def test_non_synced_change_is_rejected(target: tuple[Library, Item, Path]) -> None:
    _, item, _ = target
    source = MetadataCandidate("lyrics", "plain", "lrclib", 0.95, "123")
    change = PlannedChange("lyrics", None, "plain", source, "plain")
    with pytest.raises(ValueError, match="synced_lyrics"):
        plan_lyrics_sidecar(item, change)
