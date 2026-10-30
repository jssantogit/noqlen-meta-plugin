"""Integration safety for V3 DB-only measured audio proxies."""
from beets import config
from beets.autotag.hooks import TrackInfo
from beets.library import Item, Library

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.audio_features import (
    AudioFeatureObservation,
    AudioFeatureSettings,
    AudioMetric,
    LibrosaAudioFeatureAnalyzer,
)
from beetsplug.noqlenmeta.domain import TrackEnrichmentContext
from beetsplug.noqlenmeta.resolver import FieldRule, ResolutionPolicy
from beetsplug.noqlenmeta.semantic_enrichment import SemanticEnrichmentResult
from beetsplug.noqlenmeta.track_application import apply_track_target_plan
from beetsplug.noqlenmeta.track_integration import SelectedImportTrack

ENERGY = AudioMetric(0.61, 1.0, "rms-dbfs-v1")
DANCE = AudioMetric(0.78, 0.93, "beat-onset-regularity-v1")


def _stub(_self, _path, _settings):
    return AudioFeatureObservation(ENERGY, DANCE, "librosa")


def test_library_audio_proxies_preview_apply_and_method_are_typed(tmp_path, monkeypatch):
    config["timeout"].get()
    sources = list(config.sources)
    item_types = dict(Item._types)
    try:
        library = Library(str(tmp_path / "library.db"), set_music_dir=False)
        item = Item(
            path=str(tmp_path / "track.flac").encode(),
            artist="Synthetic", albumartist="Synthetic",
            album="Synthetic Album", title="Synthetic Track",
        )
        library.add(item)
        plugin = NoqlenMetaPlugin()
        # Direct plugin invocation bypasses beet CLI's normal plugin type setup.
        Item._types.update(plugin.item_types)
        plugin.config["fields"].set({
            **{key: False for key in plugin.config["fields"].keys()},
            "energy": True, "danceability": True,
        })
        settings = plugin.config["local_analysis"].get(dict)
        settings["audio_features"] = {
            "enabled": True, "analysis_mode": "window", "window_seconds": 90
        }
        plugin.config["local_analysis"].set(settings)
        monkeypatch.setattr(LibrosaAudioFeatureAnalyzer, "analyze", _stub)

        command = plugin.commands()[0]
        preview, args = command.parse_args(["--all"])
        command.func(library, preview, args)
        assert library.get_item(item.id).get("energy") is None

        # Explicit --write must not request file sync for DB-only V3 metrics.
        # The synthetic Item has no actual audio file on disk.
        apply, args = command.parse_args(["--apply", "--write", "--all"])
        command.func(library, apply, args)
        stored = library.get_item(item.id)
        assert stored.get("energy") == 0.61
        assert stored.get("danceability") == 0.78
        assert stored.get("energy_method") == "rms-dbfs-v1"
        assert stored.get("danceability_method") == "beat-onset-regularity-v1"

        # A second pass is a no-op: existing signal measurements are preserved.
        command.func(library, apply, args)
        reloaded = library.get_item(item.id)
        assert reloaded.get("energy") == 0.61
        assert reloaded.get("danceability") == 0.78
    finally:
        Item._types.clear()
        Item._types.update(item_types)
        config.sources[:] = sources


def test_selected_importer_audio_only_changes_selected_track_info(monkeypatch):
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_collect_track_candidates",
        lambda _self, *_args: SemanticEnrichmentResult((), {}),
    )
    monkeypatch.setattr(LibrosaAudioFeatureAnalyzer, "analyze", _stub)
    track = TrackInfo(
        artist="Synthetic", title="Track", album="Album",
        length=180.0, index=1, medium=1, medium_index=1,
    )
    item = Item(path=b"/synthetic.flac")
    selected = SelectedImportTrack(item, track, None)
    policy = ResolutionPolicy({
        "energy": FieldRule(True, (), 0.8),
        "danceability": FieldRule(True, (), 0.8),
    }, {})
    plugin = NoqlenMetaPlugin()

    plan = plugin._build_import_track_plan(
        selected,
        TrackEnrichmentContext("Synthetic", "Track"),
        from_scratch=False,
        policy=policy,
        local_bpm_settings=plugin._local_bpm_settings(),
        local_audio_settings=AudioFeatureSettings(enabled=True),
    )
    assert {v.target_field for v in plan.target_plan.mapped_changes} == {
        "energy", "danceability", "energy_method", "danceability_method",
    }
    assert track.get("energy") is None
    assert item.get("energy") is None

    applied = apply_track_target_plan(
        selected, plan.target_plan, from_scratch=False
    )
    assert not applied.is_blocked
    assert track.get("energy") == 0.61
    assert track.get("danceability_method") == "beat-onset-regularity-v1"
    assert item.get("energy") is None


def test_existing_audio_method_disagreement_cannot_be_silently_relabelled(monkeypatch):
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_collect_track_candidates",
        lambda _self, *_args: SemanticEnrichmentResult((), {}),
    )
    monkeypatch.setattr(LibrosaAudioFeatureAnalyzer, "analyze", _stub)
    track = TrackInfo(
        artist="Synthetic", title="Track", album="Album",
        energy_method="external-different-v1",
        length=180.0, index=1, medium=1, medium_index=1,
    )
    selected = SelectedImportTrack(Item(path=b"/synthetic.flac"), track, None)
    plugin = NoqlenMetaPlugin()
    plan = plugin._build_import_track_plan(
        selected,
        TrackEnrichmentContext("Synthetic", "Track"),
        from_scratch=False,
        policy=ResolutionPolicy({"energy": FieldRule(True, (), 0.8)}, {}),
        local_bpm_settings=plugin._local_bpm_settings(),
        local_audio_settings=AudioFeatureSettings(enabled=True),
    )
    assert not plan.target_plan.mapped_changes
    assert track.get("energy") is None
    assert track.get("energy_method") == "external-different-v1"
