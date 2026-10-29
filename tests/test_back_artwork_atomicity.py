"""Regression for multi-disc Back artwork creation failure.

A failed second write must not leave only one disc with new artwork.
"""
import os
from types import SimpleNamespace

import beetsplug.noqlenmeta.back_artwork as module
from beetsplug.noqlenmeta.back_artwork import (
    BackArtworkPlan,
    apply_back_artwork_plan,
)


def test_back_artwork_disc_failure_rolls_back_created_siblings(
    tmp_path, monkeypatch
) -> None:
    first = tmp_path / "Disc 1"
    second = tmp_path / "Disc 2"
    first.mkdir()
    second.mkdir()
    first_audio = os.fsencode(str(first / "track.flac"))
    second_audio = os.fsencode(str(second / "track.flac"))
    first_back = os.fsencode(str(first / "back.jpg"))
    second_back = os.fsencode(str(second / "back.jpg"))
    items = [SimpleNamespace(path=first_audio), SimpleNamespace(path=second_audio)]
    album = SimpleNamespace(id=42, items=lambda: items)
    library = SimpleNamespace(get_album=lambda _id: album)
    plan = BackArtworkPlan(
        album_id=42,
        item_paths=(first_audio, second_audio),
        destinations=(first_back, second_back),
        candidate=object(),
        status="PROPOSE",
        reason="verified exact-release back",
    )
    monkeypatch.setattr(module, "download_artwork", lambda *_args: b"jpeg")
    actual_link = module.os.link

    def fail_second(source: bytes, target: bytes) -> None:
        if target == second_back:
            raise OSError("simulated second disc write failure")
        actual_link(source, target)

    monkeypatch.setattr(module.os, "link", fail_second)
    result = apply_back_artwork_plan(library, album, plan)

    assert result.status == "BLOCKED"
    assert result.committed == ()
    assert not os.path.lexists(first_back)
    assert not os.path.lexists(second_back)
