"""V3 release gate: zero is a real measured score, never an absent value."""

import math

import pytest
from beets import plugins
from beets.autotag.hooks import TrackInfo
from beets.library import Item, Library
from beets.util import cached_classproperty

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.library_track_application import apply_library_track_plan
from beetsplug.noqlenmeta.track_application import apply_track_target_plan
from beetsplug.noqlenmeta.track_integration import SelectedImportTrack
from beetsplug.noqlenmeta.track_mapping import TrackMappingError, map_change_plan_to_track_info


def change(field: str, number: float) -> PlannedChange:
    candidate = MetadataCandidate(field, number, "local_audio", 1.0, "rms-dbfs-v1")
    return PlannedChange(field, None, number, candidate, "recorded measurement")


@pytest.mark.parametrize("field", ("energy", "danceability"))
@pytest.mark.parametrize("score", (0.0, 1.0))
def test_bounded_audio_score_maps_losslessly(field: str, score: float) -> None:
    plan = map_change_plan_to_track_info(ChangePlan(changes=(change(field, score),)))
    assert plan.blocked_changes == ()
    assert plan.mapped_changes[0].target_value == score


@pytest.mark.parametrize("field", ("energy", "danceability"))
@pytest.mark.parametrize("score", (-0.01, 1.01, float("nan"), float("inf")))
def test_out_of_range_audio_score_never_maps(field: str, score: float) -> None:
    # Non-finite values fail at candidate construction; finite out-of-range
    # values must fail at target mapping.
    expected_error = ValueError if not math.isfinite(score) else TrackMappingError
    with pytest.raises(expected_error):
        map_change_plan_to_track_info(ChangePlan(changes=(change(field, score),)))


def test_zero_bpm_still_cannot_map() -> None:
    with pytest.raises(TrackMappingError):
        map_change_plan_to_track_info(ChangePlan(changes=(change("bpm", 0.0),)))


@pytest.mark.parametrize("field", ("energy", "danceability"))
def test_importer_applies_zero_without_confusing_unknown(field: str) -> None:
    item = Item(path=b"synthetic.flac")
    track = TrackInfo(
        artist="Synthetic Artist", title="Synthetic Track",
        length=180.0, index=1, medium=1, medium_index=1,
    )
    selected = SelectedImportTrack(item, track, None)
    plan = map_change_plan_to_track_info(
        ChangePlan(changes=(change(field, 0.0),))
    )
    result = apply_track_target_plan(selected, plan, from_scratch=False)
    assert result.has_applied_changes
    assert track.get(field) == 0.0
    assert item.get(field) is None


@pytest.mark.parametrize("field", ("energy", "danceability"))
def test_existing_library_round_trips_zero_as_numeric_value(
    field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = NoqlenMetaPlugin()
    monkeypatch.setattr(plugins, "_instances", [plugin])
    monkeypatch.delitem(cached_classproperty.cache, (Item, "_types"), raising=False)
    lib = Library(":memory:", set_music_dir=False)
    item = Item(path=b"synthetic.flac", artist="Synthetic", title="Track")
    lib.add(item)
    fresh = lib.get_item(item.id)
    plan = map_change_plan_to_track_info(
        ChangePlan(changes=(change(field, 0.0),))
    )
    result = apply_library_track_plan(fresh, plan)
    assert result.stored
    assert lib.get_item(item.id).get(field) == 0.0
