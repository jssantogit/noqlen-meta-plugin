"""V3 audio proxies: deterministic, nullable and explicitly methodology-versioned."""
import math

import pytest

from beetsplug.noqlenmeta.audio_features import (
    AudioFeatureObservation,
    AudioFeatureSettings,
    AudioFeatureUnavailable,
    estimate_danceability,
    estimate_energy,
    audio_feature_settings_from_config,
    plan_audio_features,
    score_level,
    tempo_range,
)


def test_proxy_settings_are_strict_disabled_and_nonmutable():
    assert audio_feature_settings_from_config({
        "enabled": False, "analysis_mode": "full", "window_seconds": 90
    }) == AudioFeatureSettings()
    for candidate in (
        {"enabled": 1, "analysis_mode": "full", "window_seconds": 90},
        {"enabled": True, "analysis_mode": "other", "window_seconds": 90},
        {"enabled": True, "analysis_mode": "full", "window_seconds": math.nan},
        {"enabled": True, "analysis_mode": "full", "window_seconds": 0},
        {"enabled": True, "analysis_mode": "full", "window_seconds": 90, "other": 2},
    ):
        with pytest.raises(ValueError):
            audio_feature_settings_from_config(candidate)


def test_energy_is_amplitude_proxy_not_perceptual_loudness():
    assert estimate_energy((0.0,) * 50) is None
    quiet = estimate_energy((0.01,) * 50)
    loud = estimate_energy((0.15,) * 50)
    assert quiet is not None and loud is not None
    assert 0 <= quiet.value < loud.value <= 1
    assert quiet.method == loud.method == "rms-dbfs-v1"
    assert quiet.confidence == loud.confidence == 1.0


@pytest.mark.parametrize("frames", [
    (), (math.nan, 0.2), (math.inf, 0.2), (-0.1, 0.2), (1.2, 0.2)
])
def test_energy_invalid_or_suspicious_signal_abstains(frames):
    assert estimate_energy(frames) is None


def test_danceability_requires_rhythmic_structure_not_just_bpm():
    onset = [0.0] * 120
    beats = tuple(float(i) for i in range(1, 11))
    for second in beats:
        onset[int(second * 10)] = 3.0
    value = estimate_danceability(beats, tuple(onset), hop_seconds=0.1)
    assert value is not None
    assert 0.0 <= value.value <= 1.0
    assert value.value >= 0.70
    assert value.method == "beat-onset-regularity-v1"
    assert estimate_danceability(beats, (1.0,) * 120, hop_seconds=0.1) is None


def test_danceability_abstains_on_missing_or_unstable_beat_evidence():
    onsets = tuple(3.0 if i % 10 == 0 else 0.0 for i in range(140))
    assert estimate_danceability((), onsets, hop_seconds=0.1) is None
    assert estimate_danceability((1.0, 2.0) * 5, onsets, hop_seconds=0.1) is None
    assert estimate_danceability(tuple(range(1, 11)), onsets, hop_seconds=0.0) is None
    unstable = (1., 1.2, 2., 4., 4.1, 5.3, 5.8, 7., 9.1, 11.)
    assert estimate_danceability(unstable, onsets, hop_seconds=0.1) is None


def test_versioned_observation_and_explicit_preservation_with_one_analysis():
    class Analyzer:
        calls = 0

        def analyze(self, path, settings):
            self.calls += 1
            return AudioFeatureObservation(
                energy=estimate_energy((0.10,) * 50),
                danceability=None,
                backend="librosa",
            )

    analyzer = Analyzer()
    result = plan_audio_features(
        path=b"track.flac",
        current_values={"energy": 0.75, "energy_method": "older-calibration"},
        field_enabled={"energy": True, "danceability": True},
        settings=AudioFeatureSettings(enabled=True),
        analyzer=analyzer,
    )
    assert result.outcomes["energy"] == "PRESERVED"
    assert result.outcomes["danceability"] == "NO_EVIDENCE"
    assert result.proposals == {}
    assert analyzer.calls == 1


def test_disabled_or_unavailable_audio_does_not_mutate_or_invent_zero():
    class Broken:
        def analyze(self, _path, _settings):
            raise AudioFeatureUnavailable("unreadable")

    for settings, expected in (
        (AudioFeatureSettings(), "NO_EVIDENCE"),
        (AudioFeatureSettings(enabled=True), "UNAVAILABLE"),
    ):
        result = plan_audio_features(
            path=b"track.flac",
            current_values={},
            field_enabled={"energy": True, "danceability": True},
            settings=settings,
            analyzer=Broken(),
        )
        assert result.proposals == {}
        assert set(result.outcomes.values()) == {expected}


@pytest.mark.parametrize("value,expected", [
    (0.0, "low"), (0.33, "low"), (0.34, "medium"),
    (0.67, "medium"), (0.68, "high"), (1.0, "high"),
    (None, None), (math.nan, None), (True, None),
])
def test_reproducible_score_buckets(value, expected):
    assert score_level(value) == expected


@pytest.mark.parametrize("bpm,expected", [
    (0, None), (math.nan, None), (89, "slow"),
    (90, "medium"), (139.99, "medium"), (140, "fast"),
])
def test_tempo_buckets_are_derived_not_persisted(bpm, expected):
    assert tempo_range(bpm) == expected
