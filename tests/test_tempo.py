import math

import pytest

from beetsplug.noqlenmeta.configuration import default_config
from beetsplug.noqlenmeta.tempo import (
    BpmPlanningResult,
    BpmSettings,
    LocalBpmSettings,
    TempoObservation,
    bpm_settings_from_config,
    local_bpm_settings_from_config,
    normalize_bpm,
    plan_bpm,
)


def test_bpm_public_defaults_are_exact() -> None:
    config = default_config()

    assert config["bpm"] == {
        "round": False,
        "recalculate_existing": False,
        "octave_normalization": False,
        "octave_range": {"min": 70, "max": 180},
    }
    assert config["local_analysis"]["bpm"] == {
        "enabled": False,
        "analysis_mode": "full",
        "window_seconds": 90,
    }
    assert bpm_settings_from_config(config["bpm"]) == BpmSettings()
    assert local_bpm_settings_from_config(config["local_analysis"]["bpm"]) == LocalBpmSettings()


@pytest.mark.parametrize(
    "value",
    [
        {
            "round": 0,
            "recalculate_existing": False,
            "octave_normalization": False,
            "octave_range": {"min": 70, "max": 180},
        },
        {
            "round": False,
            "recalculate_existing": False,
            "octave_normalization": False,
            "octave_range": {"min": 180, "max": 180},
        },
        {
            "round": False,
            "recalculate_existing": False,
            "octave_normalization": False,
            "octave_range": {"min": 181, "max": 180},
        },
        {
            "round": False,
            "recalculate_existing": False,
            "octave_normalization": False,
            "octave_range": {"min": math.nan, "max": 180},
        },
        {
            "round": False,
            "recalculate_existing": False,
            "octave_normalization": False,
            "octave_range": {"min": 70, "max": math.inf},
        },
    ],
)
def test_bpm_settings_reject_invalid_values(value: object) -> None:
    with pytest.raises(ValueError):
        bpm_settings_from_config(value)


@pytest.mark.parametrize(
    "value",
    [
        {"enabled": 0, "analysis_mode": "full", "window_seconds": 90},
        {"enabled": False, "analysis_mode": "start", "window_seconds": 90},
        {"enabled": False, "analysis_mode": "full", "window_seconds": 0},
        {"enabled": False, "analysis_mode": "full", "window_seconds": math.nan},
        {"enabled": False, "analysis_mode": "full", "window_seconds": math.inf},
        {"enabled": False, "analysis_mode": "full", "window_seconds": 90, "extra": True},
    ],
)
def test_local_bpm_settings_reject_invalid_values(value: object) -> None:
    with pytest.raises(ValueError):
        local_bpm_settings_from_config(value)


def test_tempo_observation_is_immutable() -> None:
    observation = TempoObservation(127.5, "librosa")

    with pytest.raises(AttributeError):
        observation.bpm = 128.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "raw,settings,expected",
    [
        (127.63, BpmSettings(), 127.63),
        (127.63, BpmSettings(round=True), 128.0),
        (55.0, BpmSettings(octave_normalization=True), 110.0),
        (210.0, BpmSettings(octave_normalization=True), 105.0),
        (72.0, BpmSettings(octave_normalization=True), 72.0),
        (144.0, BpmSettings(octave_normalization=True), 144.0),
        (
            55.3,
            BpmSettings(round=True, octave_normalization=True),
            111.0,
        ),
    ],
)
def test_normalize_bpm_applies_only_approved_policy(
    raw: float, settings: BpmSettings, expected: float
) -> None:
    assert normalize_bpm(TempoObservation(raw, "librosa"), settings) == expected


@pytest.mark.parametrize("raw", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_normalize_bpm_rejects_invalid_observation(raw: float) -> None:
    with pytest.raises(ValueError):
        normalize_bpm(TempoObservation(raw, "librosa"), BpmSettings())


class Analyzer:
    def __init__(self, result: TempoObservation | Exception) -> None:
        self.result = result
        self.calls = 0

    def analyze(self, path: bytes, settings: LocalBpmSettings) -> TempoObservation:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.parametrize(
    "field_enabled,existing,bpm_settings,local_settings,outcome,calls,canonical",
    [
        (False, None, BpmSettings(), LocalBpmSettings(enabled=True), "NO_EVIDENCE", 0, None),
        (True, 128.0, BpmSettings(), LocalBpmSettings(enabled=True), "PRESERVED", 0, 128.0),
        (True, None, BpmSettings(), LocalBpmSettings(), "NO_EVIDENCE", 0, None),
        (True, None, BpmSettings(), LocalBpmSettings(enabled=True), "RESOLVED", 1, 127.5),
        (
            True,
            128.0,
            BpmSettings(recalculate_existing=True),
            LocalBpmSettings(enabled=True),
            "RESOLVED",
            1,
            127.5,
        ),
        (
            True,
            128.0,
            BpmSettings(recalculate_existing=True),
            LocalBpmSettings(),
            "PRESERVED",
            0,
            128.0,
        ),
    ],
)
def test_plan_bpm_preservation_and_analysis_calls(
    field_enabled: bool,
    existing: object,
    bpm_settings: BpmSettings,
    local_settings: LocalBpmSettings,
    outcome: str,
    calls: int,
    canonical: float | None,
) -> None:
    analyzer = Analyzer(TempoObservation(127.5, "librosa"))

    result = plan_bpm(
        path=b"track.flac",
        existing_bpm=existing,
        field_enabled=field_enabled,
        bpm_settings=bpm_settings,
        local_settings=local_settings,
        analyzer=analyzer,
    )

    assert result.outcome == outcome
    assert result.canonical_bpm == canonical
    assert analyzer.calls == calls


def test_plan_bpm_unavailable_is_local() -> None:
    analyzer = Analyzer(RuntimeError("decoder failed"))

    result = plan_bpm(
        path=b"track.flac",
        existing_bpm=None,
        field_enabled=True,
        bpm_settings=BpmSettings(),
        local_settings=LocalBpmSettings(enabled=True),
        analyzer=analyzer,
    )

    assert result == BpmPlanningResult(
        "UNAVAILABLE",
        None,
        None,
        None,
        "local BPM analysis is unavailable",
    )
    assert analyzer.calls == 1
