"""Local BPM configuration and immutable domain values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from beetsplug.noqlenmeta.configuration import (
    validate_bpm_config,
    validate_local_bpm_config,
)


@dataclass(frozen=True, slots=True)
class BpmSettings:
    round: bool = False
    recalculate_existing: bool = False
    octave_normalization: bool = False
    octave_min: float = 70.0
    octave_max: float = 180.0


@dataclass(frozen=True, slots=True)
class LocalBpmSettings:
    enabled: bool = False
    analysis_mode: str = "full"
    window_seconds: float = 90.0


@dataclass(frozen=True, slots=True)
class TempoObservation:
    bpm: float
    backend: str


def bpm_settings_from_config(value: object) -> BpmSettings:
    """Validate public BPM policy and return immutable settings."""
    validate_bpm_config(value)
    assert isinstance(value, Mapping)
    octave_range = value["octave_range"]
    assert isinstance(octave_range, Mapping)
    return BpmSettings(
        round=value["round"],
        recalculate_existing=value["recalculate_existing"],
        octave_normalization=value["octave_normalization"],
        octave_min=float(octave_range["min"]),
        octave_max=float(octave_range["max"]),
    )


def local_bpm_settings_from_config(value: object) -> LocalBpmSettings:
    """Validate local BPM analysis configuration and return immutable settings."""
    validate_local_bpm_config(value)
    assert isinstance(value, Mapping)
    return LocalBpmSettings(
        enabled=value["enabled"],
        analysis_mode=value["analysis_mode"],
        window_seconds=float(value["window_seconds"]),
    )
