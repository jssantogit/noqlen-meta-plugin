"""Real optional Librosa smoke test; skipped without [audio] extra."""
import math

import pytest

from beetsplug.noqlenmeta.audio_features import (
    AudioFeatureSettings,
    LibrosaAudioFeatureAnalyzer,
)


def test_librosa_adapter_can_reuse_one_decoded_signal_for_both_proxies(monkeypatch):
    numpy = pytest.importorskip("numpy")
    librosa = pytest.importorskip("librosa")
    sr = 22050
    seconds = 12
    wave = (0.12 * numpy.sin(2 * math.pi * 220 * numpy.arange(
        sr * seconds, dtype=float
    ) / sr)).astype("float32")

    monkeypatch.setattr(
        librosa, "load", lambda _path, **_kwargs: (wave, sr)
    )
    monkeypatch.setattr(
        librosa, "get_duration", lambda **_kwargs: float(seconds)
    )
    result = LibrosaAudioFeatureAnalyzer().analyze(
        b"/synthetic/track.flac",
        AudioFeatureSettings(enabled=True, analysis_mode="window", window_seconds=10),
    )
    assert result.backend == "librosa"
    assert result.energy is not None
    assert 0 < result.energy.value < 1
    # A steady sine does not support reliable periodic beat inference.
    assert result.danceability is None
