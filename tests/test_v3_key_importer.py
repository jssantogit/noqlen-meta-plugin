"""V3 key evidence must respect selected importer metadata and preview boundaries."""

from beets.autotag.hooks import TrackInfo
from beets.library import Item

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.domain import TrackEnrichmentContext
from beetsplug.noqlenmeta.key_analysis import (
    KeyObservation,
    KeySettings,
    LibrosaKeyAnalyzer,
)
from beetsplug.noqlenmeta.resolver import FieldRule, ResolutionPolicy
from beetsplug.noqlenmeta.semantic_enrichment import SemanticEnrichmentResult
from beetsplug.noqlenmeta.track_application import apply_track_target_plan
from beetsplug.noqlenmeta.track_integration import SelectedImportTrack
from beetsplug.noqlenmeta.track_planning import effective_current_values_for_import_track


def _track(**kwargs):
    values = {
        "artist": "Synthetic Artist",
        "title": "Synthetic Track",
        "album": "Synthetic Album",
        "length": 180.0,
        "index": 1,
        "medium": 1,
        "medium_index": 1,
    }
    return TrackInfo(**(values | kwargs))


def test_selected_import_key_has_precedence_over_existing_item_key():
    selected = SelectedImportTrack(
        Item(initial_key="Am"), _track(initial_key="D"), None
    )
    for from_scratch in (True, False):
        current = effective_current_values_for_import_track(
            selected, from_scratch=from_scratch
        )
        assert current["key"] == "D"


def test_absent_selected_import_key_preserves_existing_item_without_clear():
    selected = SelectedImportTrack(Item(initial_key="Am"), _track(), None)
    assert effective_current_values_for_import_track(
        selected, from_scratch=False
    )["key"] == "Am"
    assert "key" not in effective_current_values_for_import_track(
        selected, from_scratch=True
    )


def test_importer_key_preview_then_apply_changes_only_selected_track(monkeypatch):
    plugin = NoqlenMetaPlugin()
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_collect_track_candidates",
        lambda _self, *_args: SemanticEnrichmentResult((), {}),
    )
    monkeypatch.setattr(
        LibrosaKeyAnalyzer,
        "analyze",
        lambda _self, _path, _settings: KeyObservation("Am", 0.96, "librosa"),
    )
    item = Item(path=b"/synthetic/track.flac")
    track_info = _track()
    selected = SelectedImportTrack(item, track_info, None)
    policy = ResolutionPolicy({"key": FieldRule(True, (), 0.8)}, {})

    result = plugin._build_import_track_plan(
        selected,
        TrackEnrichmentContext("Synthetic Artist", "Synthetic Track"),
        from_scratch=False,
        policy=policy,
        local_bpm_settings=plugin._local_bpm_settings(),
        local_key_settings=KeySettings(enabled=True),
    )
    assert len(result.target_plan.mapped_changes) == 1
    mapped = result.target_plan.mapped_changes[0]
    assert mapped.canonical_field == "key"
    assert mapped.target_field == "initial_key"
    assert track_info.initial_key is None
    assert item.initial_key is None

    application = apply_track_target_plan(
        selected, result.target_plan, from_scratch=False
    )
    assert not application.is_blocked
    assert track_info.initial_key == "Am"
    assert item.initial_key is None
