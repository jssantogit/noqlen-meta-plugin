"""V3 release gate: real pre-V3 beets DB and media-format preservation."""
import os
import shutil
from pathlib import Path

import pytest
from beets import config
from beets.dbcore import types as db_types
from beets.library import Item, Library

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.audio_features import (
    AudioFeatureObservation,
    AudioMetric,
    LibrosaAudioFeatureAnalyzer,
)
from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.field_contracts import V2_ITEM_FLEXIBLE_FIELDS
from beetsplug.noqlenmeta.library_track_application import apply_library_track_plan
from beetsplug.noqlenmeta.track_mapping import map_change_plan_to_track_info

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "identity_tags"
MEDIA_FORMATS = ("flac", "mp3", "m4a", "ogg", "opus")


def _mock_audio(_self, _path, _settings):
    return AudioFeatureObservation(
        AudioMetric(0.0, 1.0, "rms-dbfs-v1"), None, "librosa"
    )


def test_v2_multivalue_database_reopens_with_new_v3_types_and_preserves_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Upgrade an existing V2-typed library without deleting original metadata."""
    from beets import plugins
    from beets.util import cached_classproperty

    monkeypatch.setattr(plugins, "_instances", [])
    monkeypatch.delitem(cached_classproperty.cache, (Item, "_types"), raising=False)
    original_types = dict(Item._types)
    try:
        # Simulate V2 persisted flexible type schema, before V3 was installed.
        Item._types.update({
            field: db_types.MULTI_VALUE_DSV for field in V2_ITEM_FLEXIBLE_FIELDS
        })
        database = str(tmp_path / "v2-library.db")
        legacy = Library(database, set_music_dir=False)
        track = Item(
            path=os.fsencode(tmp_path / "before.flac"),
            artist="Legacy Artist", title="Legacy Title", album="Legacy Album",
            lyrics="Existing lyric text", bpm=122, genre="Downtempo",
            moods=["Gentle", "Warm"], lyrics_languages=["eng"],
        )
        legacy.add(track)
        legacy_id = track.id
        assert legacy.get_item(legacy_id).get("moods") == ["Gentle", "Warm"]

        # The V3 plugin extends types, but must not reinterpret/delete V2 data.
        plugin = NoqlenMetaPlugin()
        monkeypatch.setattr(plugins, "_instances", [plugin])
        monkeypatch.delitem(cached_classproperty.cache, (Item, "_types"), raising=False)
        upgraded = Library(database, set_music_dir=False)
        fresh = upgraded.get_item(legacy_id)
        assert fresh.title == "Legacy Title"
        assert fresh.lyrics == "Existing lyric text"
        assert fresh.bpm == 122
        assert fresh.get("moods") == ["Gentle", "Warm"]
        assert fresh.get("lyrics_languages") == ["eng"]

        for field, value in (
            ("energy", 0.0), ("energy_method", "rms-dbfs-v1")
        ):
            evidence = MetadataCandidate(
                field, value, "local_audio", 1.0, "rms-dbfs-v1"
            )
            change = PlannedChange(field, None, value, evidence, "validated local evidence")
            plan = map_change_plan_to_track_info(ChangePlan(changes=(change,)))
            result = apply_library_track_plan(fresh, plan)
            assert result.stored

        reopened = Library(database, set_music_dir=False).get_item(legacy_id)
        assert reopened.get("energy") == 0.0
        assert reopened.get("energy_method") == "rms-dbfs-v1"
        assert reopened.get("moods") == ["Gentle", "Warm"]
        assert reopened.get("lyrics_languages") == ["eng"]
        assert reopened.title == "Legacy Title"
        assert reopened.bpm == 122
    finally:
        Item._types.clear()
        Item._types.update(original_types)
        monkeypatch.delitem(cached_classproperty.cache, (Item, "_types"), raising=False)


@pytest.mark.parametrize("extension", MEDIA_FORMATS)
def test_db_only_audio_apply_write_is_byte_identical_across_formats(
    extension: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never rewrite existing audio when every change is a DB-only proxy."""
    config["timeout"].get()
    original_sources = list(config.sources)
    original_types = dict(Item._types)
    try:
        source = FIXTURE_DIRECTORY / f"silence.{extension}"
        assert source.is_file()
        path = tmp_path / f"recording.{extension}"
        shutil.copy2(source, path)
        original_bytes = path.read_bytes()

        library = Library(str(tmp_path / "library.db"), set_music_dir=False)
        track = Item(
            path=os.fsencode(path),
            artist="Synthetic Artist", albumartist="Synthetic Artist",
            album="Synthetic Album", title="Synthetic Track",
        )
        library.add(track)
        plugin = NoqlenMetaPlugin()
        Item._types.update(plugin.item_types)
        plugin.config["fields"].set({
            **{field: False for field in plugin.config["fields"].keys()},
            "energy": True,
        })
        local = plugin.config["local_analysis"].get(dict)
        local["audio_features"] = {
            "enabled": True, "analysis_mode": "window", "window_seconds": 90
        }
        plugin.config["local_analysis"].set(local)
        monkeypatch.setattr(LibrosaAudioFeatureAnalyzer, "analyze", _mock_audio)

        command = plugin.commands()[0]
        preview, args = command.parse_args(["--all"])
        command.func(library, preview, args)
        assert library.get_item(track.id).get("energy") is None
        assert path.read_bytes() == original_bytes

        apply, args = command.parse_args(["--apply", "--write", "--all"])
        command.func(library, apply, args)
        result = library.get_item(track.id)
        assert result.get("energy") == 0.0
        assert result.get("energy_method") == "rms-dbfs-v1"
        assert path.read_bytes() == original_bytes
    finally:
        Item._types.clear()
        Item._types.update(original_types)
        config.sources[:] = original_sources
