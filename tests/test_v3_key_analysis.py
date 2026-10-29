"""Conservative V3 Recording key detection and opt-in planning."""
import math

import pytest

from beetsplug.noqlenmeta.key_analysis import (
    KeyAnalysisUnavailable,
    KeyObservation,
    KeySettings,
    estimate_key,
    key_settings_from_config,
    plan_key,
)

MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)


def rotate(values: tuple[float, ...], semitones: int) -> tuple[float, ...]:
    return tuple(values[(i - semitones) % 12] for i in range(12))


@pytest.mark.parametrize("chroma,expected", [
    (MAJOR, "C major"),
    (rotate(MAJOR, 9), "A major"),
    (MINOR, "C minor"),
    (rotate(MINOR, 9), "A minor"),
])
def test_full_pitch_class_profile_recognizes_major_and_minor(chroma, expected):
    observation = estimate_key(chroma)
    assert observation is not None
    assert observation.key == expected
    assert observation.confidence >= 0.90


@pytest.mark.parametrize("chroma", [
    (0.0,) * 12,
    (1.0,) * 12,
    (math.nan,) + (1.0,) * 11,
    (math.inf,) + (1.0,) * 11,
    (-1.0,) + (1.0,) * 11,
    (1.0,) * 11,
])
def test_ambiguous_or_invalid_chroma_cannot_assert_key(chroma):
    assert estimate_key(chroma) is None


def test_key_config_is_strict_and_disabled_by_default():
    assert key_settings_from_config({
        "enabled": False, "analysis_mode": "full", "window_seconds": 90
    }) == KeySettings()
    for invalid in (
        {"enabled": 1, "analysis_mode": "full", "window_seconds": 90},
        {"enabled": False, "analysis_mode": "start", "window_seconds": 90},
        {"enabled": False, "analysis_mode": "full", "window_seconds": 0},
        {"enabled": False, "analysis_mode": "full", "window_seconds": float("nan")},
        {"enabled": False, "analysis_mode": "full", "window_seconds": 90, "other": 1},
    ):
        with pytest.raises(ValueError):
            key_settings_from_config(invalid)


class Analyzer:
    def __init__(self, observation):
        self.observation = observation
        self.calls = 0

    def analyze(self, path, settings):
        self.calls += 1
        if isinstance(self.observation, Exception):
            raise self.observation
        return self.observation


@pytest.mark.parametrize("enabled,existing,outcome,calls", [
    (False, None, "NO_EVIDENCE", 0),
    (True, "G minor", "PRESERVED", 0),
    (True, None, "RESOLVED", 1),
])
def test_opt_in_planning_never_overwrites_existing_key(enabled, existing, outcome, calls):
    analyzer = Analyzer(KeyObservation("C major", 0.95, "librosa"))
    result = plan_key(
        path=b"track.flac",
        existing_key=existing,
        field_enabled=enabled,
        settings=KeySettings(enabled=True),
        analyzer=analyzer,
    )
    assert result.outcome == outcome
    assert analyzer.calls == calls
    if outcome == "RESOLVED":
        assert result.canonical_key == "C major"


def test_unreliable_analyzer_does_not_create_metadata():
    analyzer = Analyzer(KeyAnalysisUnavailable("no chroma"))
    result = plan_key(
        path=b"track.flac",
        existing_key=None,
        field_enabled=True,
        settings=KeySettings(enabled=True),
        analyzer=analyzer,
    )
    assert result.outcome == "UNAVAILABLE"
    assert result.canonical_key is None


def test_key_analysis_is_opt_in_twice():
    analyzer = Analyzer(KeyObservation("C major", 0.95, "librosa"))
    result = plan_key(
        path=b"track.flac",
        existing_key=None,
        field_enabled=True,
        settings=KeySettings(),
        analyzer=analyzer,
    )
    assert result.outcome == "NO_EVIDENCE"
    assert analyzer.calls == 0
