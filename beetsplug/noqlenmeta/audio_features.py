"""Explicit, conservative local V3 signal and rhythmic descriptors.

These numbers are *not* Spotify/Echo Nest perceptual scores. RMS intensity
and periodic onset alignment are reproducible proxies, with stable method
identifiers and conservative abstention. Never infer absence as a score of 0.
"""
from __future__ import annotations

import importlib
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import median
from types import MappingProxyType
from typing import Protocol

ENERGY_METHOD = "rms-dbfs-v1"
DANCEABILITY_METHOD = "beat-onset-regularity-v1"
_FIELDS = ("energy", "danceability")


class AudioFeatureUnavailable(RuntimeError):
    """A reliable local feature observation could not be produced."""


@dataclass(frozen=True, slots=True)
class AudioFeatureSettings:
    enabled: bool = False
    analysis_mode: str = "full"
    window_seconds: float = 90.0

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise ValueError("local_analysis.audio_features.enabled must be boolean")
        if self.analysis_mode not in {"full", "window"}:
            raise ValueError("local_analysis.audio_features.analysis_mode is invalid")
        if (
            type(self.window_seconds) not in (int, float)
            or not math.isfinite(self.window_seconds)
            or self.window_seconds <= 0
        ):
            raise ValueError("local_analysis.audio_features.window_seconds must be positive")


@dataclass(frozen=True, slots=True)
class AudioMetric:
    value: float
    confidence: float
    method: str

    def __post_init__(self) -> None:
        for key in ("value", "confidence"):
            value = getattr(self, key)
            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise ValueError(f"audio feature {key} must be finite within [0, 1]")
        if self.method not in {ENERGY_METHOD, DANCEABILITY_METHOD}:
            raise ValueError("unknown audio feature methodology")


@dataclass(frozen=True, slots=True)
class AudioFeatureObservation:
    energy: AudioMetric | None
    danceability: AudioMetric | None
    backend: str

    def __post_init__(self) -> None:
        if self.energy is not None and self.energy.method != ENERGY_METHOD:
            raise ValueError("energy observation has wrong methodology")
        if self.danceability is not None and self.danceability.method != DANCEABILITY_METHOD:
            raise ValueError("danceability observation has wrong methodology")
        if not isinstance(self.backend, str) or not self.backend.strip():
            raise ValueError("audio feature backend is required")


@dataclass(frozen=True, slots=True)
class AudioFeaturePlanningResult:
    outcomes: Mapping[str, str]
    proposals: Mapping[str, AudioMetric]
    observation: AudioFeatureObservation | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcomes", MappingProxyType(dict(self.outcomes)))
        object.__setattr__(self, "proposals", MappingProxyType(dict(self.proposals)))


class AudioFeatureAnalyzer(Protocol):
    def analyze(
        self, path: bytes, settings: AudioFeatureSettings
    ) -> AudioFeatureObservation: ...


def audio_feature_settings_from_config(value: object) -> AudioFeatureSettings:
    if not isinstance(value, Mapping) or set(value) != {
        "enabled", "analysis_mode", "window_seconds"
    }:
        raise ValueError("local_analysis.audio_features is invalid")
    return AudioFeatureSettings(
        enabled=value["enabled"],
        analysis_mode=value["analysis_mode"],
        window_seconds=value["window_seconds"],
    )


def estimate_energy(rms_frames: Sequence[float]) -> AudioMetric | None:
    """Median positive full-scale RMS mapped from [-50,-8] dBFS to [0,1].

    This is an amplitude index, not a perceptual energy estimator; calibrated
    only for decoded floating-point full-scale audio (peak must be <=1).
    """
    if len(rms_frames) < 4 or any(
        type(value) not in (int, float)
        or not math.isfinite(value)
        or value < 0
        or value > 1
        for value in rms_frames
    ):
        return None
    level = median(rms_frames)
    if level <= 1e-8:
        return None
    dbfs = 20 * math.log10(level)
    score = min(1.0, max(0.0, (dbfs + 50.0) / 42.0))
    return AudioMetric(float(score), 1.0, ENERGY_METHOD)


def estimate_danceability(
    beat_times: Sequence[float],
    onset_strength: Sequence[float],
    *,
    hop_seconds: float,
) -> AudioMetric | None:
    """A rhythmic regularity *proxy*, not human dancing suitability.

    Require >=9 consecutive beats, stable inter-beat intervals, and audible
    onset prominence at those beats. No tempo-as-danceability shortcut.
    """
    if (
        type(hop_seconds) not in (int, float)
        or not math.isfinite(hop_seconds)
        or hop_seconds <= 0
        or len(beat_times) < 9
        or len(onset_strength) < 16
    ):
        return None
    if any(
        type(x) not in (int, float) or not math.isfinite(x) or x < 0
        for x in (*beat_times, *onset_strength)
    ):
        return None
    intervals = tuple(
        beat_times[i] - beat_times[i - 1] for i in range(1, len(beat_times))
    )
    if any(interval <= 0 for interval in intervals):
        return None
    average = sum(intervals) / len(intervals)
    if average < 0.25 or average > 2.0:
        return None
    cv = math.sqrt(
        sum((interval - average) ** 2 for interval in intervals) / len(intervals)
    ) / average
    if cv > 0.15:
        return None
    mean_onset = sum(onset_strength) / len(onset_strength)
    if mean_onset <= 1e-8:
        return None
    aligned = []
    for time in beat_times:
        frame = round(time / hop_seconds)
        if frame < 1 or frame >= len(onset_strength) - 1:
            return None
        aligned.append(max(onset_strength[frame - 1:frame + 2]))
    prominence_ratio = (sum(aligned) / len(aligned)) / mean_onset
    if prominence_ratio < 1.25:
        return None
    consistency = max(0.0, 1.0 - cv / 0.15)
    prominence = min(1.0, max(0.0, (prominence_ratio - 1.0) / 2.0))
    score = 0.65 * consistency + 0.35 * prominence
    return AudioMetric(score, min(1.0, prominence_ratio / 2), DANCEABILITY_METHOD)


class LibrosaAudioFeatureAnalyzer:
    """Lazily decode one track and reuse the same signal for both descriptors."""

    def analyze(self, path: bytes, settings: AudioFeatureSettings) -> AudioFeatureObservation:
        try:
            librosa = importlib.import_module("librosa")
            source = os.fsdecode(path)
            if settings.analysis_mode == "window":
                duration = float(librosa.get_duration(path=source))
                if not math.isfinite(duration) or duration <= 0:
                    raise AudioFeatureUnavailable("invalid audio duration")
                length = min(duration, settings.window_seconds)
                y, rate = librosa.load(
                    source, offset=max(0.0, (duration - length) / 2), duration=length
                )
            else:
                y, rate = librosa.load(source)
            if rate <= 0 or len(y) < rate * 10:
                raise AudioFeatureUnavailable("insufficient decoded audio duration")
            rms = tuple(float(x) for x in librosa.feature.rms(y=y)[0])
            energy = estimate_energy(rms)
            onset = tuple(float(x) for x in librosa.onset.onset_strength(
                y=y, sr=rate, hop_length=512
            ))
            _, frames = librosa.beat.beat_track(
                onset_envelope=onset, sr=rate, hop_length=512
            )
            beats = tuple(float(t) for t in librosa.frames_to_time(
                frames, sr=rate, hop_length=512
            ))
            danceability = estimate_danceability(
                beats, onset, hop_seconds=512 / rate
            )
            return AudioFeatureObservation(energy, danceability, "librosa")
        except AudioFeatureUnavailable:
            raise
        except Exception as error:
            raise AudioFeatureUnavailable("audio analysis is unavailable") from error


def plan_audio_features(
    *,
    path: bytes,
    current_values: Mapping[str, object],
    field_enabled: Mapping[str, bool],
    settings: AudioFeatureSettings,
    analyzer: AudioFeatureAnalyzer | None,
) -> AudioFeaturePlanningResult:
    """One read-only analysis for missing, enabled Recording measurements."""
    outcomes = {}
    for field in _FIELDS:
        if not field_enabled.get(field, False) or not settings.enabled:
            outcomes[field] = "NO_EVIDENCE"
        elif current_values.get(field) is not None:
            outcomes[field] = "PRESERVED"
        else:
            outcomes[field] = "PENDING"

    if "PENDING" not in outcomes.values():
        return AudioFeaturePlanningResult(outcomes, {})

    if analyzer is None:
        return AudioFeaturePlanningResult(
            {k: "UNAVAILABLE" if v == "PENDING" else v for k, v in outcomes.items()}, {}
        )
    try:
        observation = analyzer.analyze(path, settings)
        if not isinstance(observation, AudioFeatureObservation):
            raise AudioFeatureUnavailable("invalid analyzer output")
    except Exception:
        return AudioFeaturePlanningResult(
            {k: "UNAVAILABLE" if v == "PENDING" else v for k, v in outcomes.items()}, {}
        )

    proposals = {}
    for field, state in outcomes.items():
        if state != "PENDING":
            continue
        metric = getattr(observation, field)
        # Require relatively clear supporting rhythm evidence for danceability.
        if metric is None or metric.confidence < (0.7 if field == "danceability" else 1.0):
            outcomes[field] = "NO_EVIDENCE"
        else:
            outcomes[field] = "RESOLVED"
            proposals[field] = metric
    return AudioFeaturePlanningResult(outcomes, proposals, observation)


def score_level(value: object) -> str | None:
    """Deterministic descriptive buckets for measured 0..1 proxy scores."""
    if type(value) not in (int, float) or not math.isfinite(value):
        return None
    if not 0 <= value <= 1:
        return None
    return "low" if value <= 0.33 else "medium" if value <= 0.67 else "high"


def tempo_range(bpm: object) -> str | None:
    """Unpersisted BPM bucket; never substitute for a rhythmic score."""
    if type(bpm) not in (int, float) or not math.isfinite(bpm) or bpm <= 0:
        return None
    return "slow" if bpm < 90 else "medium" if bpm < 140 else "fast"
