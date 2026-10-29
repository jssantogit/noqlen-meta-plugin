"""V3 optional conservative Recording key analysis.

Audio evidence is not identity evidence. Ambiguous pitch-class distributions
produce no key and existing library keys are never overwritten automatically.
The optional librosa import remains lazy.
"""
from __future__ import annotations

import importlib
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

_PITCHES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
_MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
_VALID_KEYS = frozenset(
    f"{pitch} {mode}" for pitch in _PITCHES for mode in ("major", "minor")
)


class KeyAnalysisUnavailable(RuntimeError):
    """Audio cannot supply a uniquely supported key assertion."""


@dataclass(frozen=True, slots=True)
class KeySettings:
    enabled: bool = False
    analysis_mode: str = "full"
    window_seconds: float = 90.0

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise ValueError("local_analysis.key.enabled must be boolean")
        if self.analysis_mode not in {"full", "window"}:
            raise ValueError("local_analysis.key.analysis_mode is invalid")
        if (
            type(self.window_seconds) not in (int, float)
            or not math.isfinite(self.window_seconds)
            or self.window_seconds <= 0
        ):
            raise ValueError("local_analysis.key.window_seconds must be positive")


@dataclass(frozen=True, slots=True)
class KeyObservation:
    key: str
    confidence: float
    backend: str

    def __post_init__(self) -> None:
        if self.key not in _VALID_KEYS:
            raise ValueError("key must contain a canonical pitch class and mode")
        if (
            type(self.confidence) not in (int, float)
            or not math.isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("key confidence must be a finite value within [0, 1]")
        if not isinstance(self.backend, str) or not self.backend:
            raise ValueError("key backend is required")


@dataclass(frozen=True, slots=True)
class KeyPlanningResult:
    outcome: str
    current_key: str | None
    observation: KeyObservation | None
    canonical_key: str | None
    reason: str


class KeyAnalyzer(Protocol):
    def analyze(self, path: bytes, settings: KeySettings) -> KeyObservation: ...


def key_settings_from_config(value: object) -> KeySettings:
    """Reject misspelled or unsafe V3 settings; public V2 defaults are frozen."""
    if not isinstance(value, Mapping) or set(value) != {
        "enabled", "analysis_mode", "window_seconds"
    }:
        raise ValueError("local_analysis.key is invalid")
    return KeySettings(
        enabled=value["enabled"],
        analysis_mode=value["analysis_mode"],
        window_seconds=value["window_seconds"],
    )


def _correlation(left: Sequence[float], right: Sequence[float]) -> float:
    x_mean = sum(left) / 12
    y_mean = sum(right) / 12
    x = tuple(value - x_mean for value in left)
    y = tuple(value - y_mean for value in right)
    denominator = math.sqrt(
        sum(value * value for value in x) * sum(value * value for value in y)
    )
    if denominator == 0:
        return 0.0
    return sum(a * b for a, b in zip(x, y)) / denominator


def estimate_key(chroma: Sequence[float]) -> KeyObservation | None:
    """Score 24 key profiles; abstain on silence, ties and close alternatives."""
    if (
        len(chroma) != 12
        or any(
            type(value) not in (int, float)
            or not math.isfinite(value)
            or value < 0
            for value in chroma
        )
        or not any(chroma)
    ):
        return None
    scores = sorted(
        (
            (
                _correlation(
                    chroma, tuple(profile[(i - tonic) % 12] for i in range(12))
                ),
                f"{_PITCHES[tonic]} {mode}",
            )
            for profile, mode in ((_MAJOR, "major"), (_MINOR, "minor"))
            for tonic in range(12)
        ),
        reverse=True,
    )
    best, name = scores[0]
    runner_up = scores[1][0]
    if best < 0.70 or best - runner_up < 0.10:
        return None
    return KeyObservation(name, min(1.0, best), "profile-correlation")


class LibrosaKeyAnalyzer:
    """Find a well-supported key from a full track or a centered sample."""

    def analyze(self, path: bytes, settings: KeySettings) -> KeyObservation:
        try:
            librosa = importlib.import_module("librosa")
            source = os.fsdecode(path)
            if settings.analysis_mode == "window":
                duration = float(librosa.get_duration(path=source))
                if not math.isfinite(duration) or duration <= 0:
                    raise KeyAnalysisUnavailable("invalid audio duration")
                window = min(duration, settings.window_seconds)
                y, rate = librosa.load(
                    source, offset=max(0, (duration - window) / 2), duration=window
                )
            else:
                y, rate = librosa.load(source)
            if rate <= 0 or len(y) < rate * 10:
                raise KeyAnalysisUnavailable("audio excerpt is too short")
            chroma = librosa.feature.chroma_cqt(y=y, sr=rate)
            if getattr(chroma, "shape", None) is None or chroma.shape[0] != 12:
                raise KeyAnalysisUnavailable("unexpected chroma shape")
            profile = tuple(float(chroma[index].mean()) for index in range(12))
            observation = estimate_key(profile)
            if observation is None:
                raise KeyAnalysisUnavailable("key is ambiguous")
            return KeyObservation(observation.key, observation.confidence, "librosa")
        except KeyAnalysisUnavailable:
            raise
        except Exception as error:
            raise KeyAnalysisUnavailable("local key analysis is unavailable") from error


def plan_key(
    *, path: bytes, existing_key: object, field_enabled: bool,
    settings: KeySettings, analyzer: KeyAnalyzer | None,
) -> KeyPlanningResult:
    """Preview-only planning; never replace existing native initial_key."""
    current = existing_key.strip() if isinstance(existing_key, str) else None
    if not current:
        current = None
    if not field_enabled or not settings.enabled:
        return KeyPlanningResult(
            "NO_EVIDENCE", current, None, None, "local key analysis disabled"
        )
    if current is not None:
        return KeyPlanningResult(
            "PRESERVED", current, None, current, "existing key is authoritative"
        )
    if analyzer is None:
        return KeyPlanningResult(
            "UNAVAILABLE", None, None, None, "no key analysis backend"
        )
    try:
        observation = analyzer.analyze(path, settings)
        if observation.confidence < 0.70:
            raise KeyAnalysisUnavailable("low key confidence")
    except Exception:
        return KeyPlanningResult(
            "UNAVAILABLE", None, None, None, "local key evidence unavailable"
        )
    return KeyPlanningResult(
        "RESOLVED", None, observation, observation.key,
        "unique supported local key estimate",
    )
