"""Local BPM configuration and immutable domain values."""

from __future__ import annotations

import importlib
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real
from typing import Protocol

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


@dataclass(frozen=True, slots=True)
class BpmPlanningResult:
    outcome: str
    current_bpm: float | None
    observation: TempoObservation | None
    canonical_bpm: float | None
    reason: str | None = None


class TempoAnalysisUnavailable(RuntimeError):
    """Local tempo analysis could not produce trustworthy evidence."""


class TempoAnalyzer(Protocol):
    def analyze(self, path: bytes, settings: LocalBpmSettings) -> TempoObservation: ...


class LibrosaTempoAnalyzer:
    """Analyze one track while keeping the optional Librosa import lazy."""

    def analyze(self, path: bytes, settings: LocalBpmSettings) -> TempoObservation:
        path_string = os.fsdecode(path)
        try:
            librosa = importlib.import_module("librosa")
            if settings.analysis_mode == "full":
                y, sample_rate = librosa.load(path_string)
            elif settings.analysis_mode == "window":
                duration = float(librosa.get_duration(path=path_string))
                if not math.isfinite(duration) or duration <= 0:
                    raise ValueError("invalid audio duration")
                window = min(settings.window_seconds, duration)
                offset = max(0.0, (duration - window) / 2.0)
                y, sample_rate = librosa.load(
                    path_string,
                    offset=offset,
                    duration=window,
                )
            else:
                raise ValueError("invalid local BPM analysis mode")
            tempo, _ = librosa.beat.beat_track(y=y, sr=sample_rate)
            value = _scalar_tempo(tempo)
            if not math.isfinite(value) or value <= 0:
                raise TempoAnalysisUnavailable(
                    "Librosa BPM analysis produced no usable tempo"
                )
            return TempoObservation(value, "librosa")
        except TempoAnalysisUnavailable:
            raise
        except Exception as error:
            raise TempoAnalysisUnavailable(
                "Librosa BPM analysis is unavailable"
            ) from error


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


def normalize_bpm(observation: TempoObservation, settings: BpmSettings) -> float:
    """Apply explicit octave normalization followed by optional rounding."""
    value = float(observation.bpm)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("tempo observation must be finite and positive")
    if settings.octave_normalization:
        normalized = value
        if normalized < settings.octave_min:
            while normalized < settings.octave_min:
                normalized *= 2.0
        elif normalized > settings.octave_max:
            while normalized > settings.octave_max:
                normalized /= 2.0
        if settings.octave_min <= normalized <= settings.octave_max:
            value = normalized
    if settings.round:
        value = float(round(value))
    return value


def plan_bpm(
    *,
    path: bytes,
    existing_bpm: object,
    field_enabled: bool,
    bpm_settings: BpmSettings,
    local_settings: LocalBpmSettings,
    analyzer: TempoAnalyzer | None,
) -> BpmPlanningResult:
    """Prepare canonical BPM evidence without mutating database or media state."""
    current = _existing_bpm(existing_bpm)
    if not field_enabled:
        return BpmPlanningResult(
            "NO_EVIDENCE", current, None, None, "BPM field is disabled"
        )
    if current is not None and not bpm_settings.recalculate_existing:
        return BpmPlanningResult(
            "PRESERVED", current, None, current, "existing BPM is preserved"
        )
    if not local_settings.enabled:
        if current is not None:
            return BpmPlanningResult(
                "PRESERVED",
                current,
                None,
                current,
                "local BPM recalculation is disabled",
            )
        return BpmPlanningResult(
            "NO_EVIDENCE", None, None, None, "local BPM analysis is disabled"
        )
    if analyzer is None:
        return BpmPlanningResult(
            "UNAVAILABLE", current, None, None, "local BPM analysis is unavailable"
        )
    try:
        observation = analyzer.analyze(path, local_settings)
        canonical = normalize_bpm(observation, bpm_settings)
    except Exception:
        return BpmPlanningResult(
            "UNAVAILABLE", current, None, None, "local BPM analysis is unavailable"
        )
    return BpmPlanningResult(
        "RESOLVED",
        current,
        observation,
        canonical,
        "resolved local BPM analysis",
    )


def _scalar_tempo(value: object) -> float:
    if isinstance(value, Real) and not isinstance(value, bool):
        return float(value)
    size = getattr(value, "size", None)
    item = getattr(value, "item", None)
    if size == 1 and callable(item):
        scalar = item()
        if isinstance(scalar, Real) and not isinstance(scalar, bool):
            return float(scalar)
    raise TempoAnalysisUnavailable("Librosa BPM analysis returned an ambiguous tempo")


def _existing_bpm(value: object) -> float | None:
    if isinstance(value, Real) and not isinstance(value, bool):
        bpm = float(value)
        if math.isfinite(bpm) and bpm > 0:
            return bpm
    return None
