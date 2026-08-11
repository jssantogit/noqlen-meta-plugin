import math

import pytest

from beetsplug.noqlenmeta.configuration import default_config
from beetsplug.noqlenmeta.tempo import (
    BpmSettings,
    LocalBpmSettings,
    TempoObservation,
    bpm_settings_from_config,
    local_bpm_settings_from_config,
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
