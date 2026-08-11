import importlib
import math
import struct
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from beetsplug.noqlenmeta.tempo import (
    LibrosaTempoAnalyzer,
    LocalBpmSettings,
    TempoAnalysisUnavailable,
)


class OneValue:
    size = 1

    def __init__(self, value: float) -> None:
        self.value = value

    def item(self) -> float:
        return self.value


class MultipleValues:
    size = 2


class FakeLibrosa:
    def __init__(self, tempo: object = 127.5) -> None:
        self.tempo = tempo
        self.load_calls: list[tuple[str, dict[str, float]]] = []
        self.duration_calls: list[str] = []
        self.beat = SimpleNamespace(beat_track=self.beat_track)

    def load(self, path: str, **kwargs: float) -> tuple[list[float], int]:
        self.load_calls.append((path, kwargs))
        return [0.0], 22050

    def get_duration(self, *, path: str) -> float:
        self.duration_calls.append(path)
        return 300.0

    def beat_track(self, *, y: object, sr: int) -> tuple[object, list[int]]:
        return self.tempo, []


def install_fake(monkeypatch: pytest.MonkeyPatch, fake: FakeLibrosa) -> list[str]:
    requested = []
    real_import = importlib.import_module

    def import_module(name: str, package: str | None = None) -> object:
        requested.append(name)
        if name == "librosa":
            return fake
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", import_module)
    return requested


def test_librosa_is_imported_only_when_analysis_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sys.modules.pop("librosa", None)
    fake = FakeLibrosa(OneValue(127.5))
    requested = install_fake(monkeypatch, fake)
    analyzer = LibrosaTempoAnalyzer()

    assert "librosa" not in sys.modules
    assert requested == []

    result = analyzer.analyze(bytes(tmp_path / "track.flac"), LocalBpmSettings(enabled=True))

    assert requested == ["librosa"]
    assert result.bpm == 127.5
    assert result.backend == "librosa"
    assert fake.load_calls == [(str(tmp_path / "track.flac"), {})]


def test_window_mode_loads_one_centered_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeLibrosa(120.0)
    install_fake(monkeypatch, fake)
    path = tmp_path / "track.flac"

    LibrosaTempoAnalyzer().analyze(
        bytes(path),
        LocalBpmSettings(enabled=True, analysis_mode="window", window_seconds=90.0),
    )

    assert fake.duration_calls == [str(path)]
    assert fake.load_calls == [(str(path), {"offset": 105.0, "duration": 90.0})]


def test_window_mode_uses_full_short_track(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeLibrosa(120.0)
    fake.get_duration = lambda *, path: 30.0  # type: ignore[method-assign]
    install_fake(monkeypatch, fake)

    LibrosaTempoAnalyzer().analyze(
        bytes(tmp_path / "track.flac"),
        LocalBpmSettings(enabled=True, analysis_mode="window", window_seconds=90.0),
    )

    assert fake.load_calls[0][1] == {"offset": 0.0, "duration": 30.0}


@pytest.mark.parametrize("tempo", [MultipleValues(), 0.0, -1.0, math.nan])
def test_invalid_or_ambiguous_tempo_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tempo: object
) -> None:
    install_fake(monkeypatch, FakeLibrosa(tempo))

    with pytest.raises(TempoAnalysisUnavailable):
        LibrosaTempoAnalyzer().analyze(
            bytes(tmp_path / "track.flac"), LocalBpmSettings(enabled=True)
        )


def test_import_or_decode_failure_is_wrapped_with_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = RuntimeError("private decoder detail")
    real_import = importlib.import_module

    def fail(name: str, package: str | None = None) -> object:
        if name == "librosa":
            raise failure
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", fail)

    with pytest.raises(
        TempoAnalysisUnavailable, match="Librosa BPM analysis is unavailable"
    ) as error:
        LibrosaTempoAnalyzer().analyze(
            bytes(tmp_path / "track.flac"), LocalBpmSettings(enabled=True)
        )

    assert error.value.__cause__ is failure


def test_real_librosa_estimates_synthetic_click_track(tmp_path: Path) -> None:
    pytest.importorskip("librosa")
    sample_rate = 22050
    duration = 12
    samples = [0] * (sample_rate * duration)
    for position in range(0, len(samples), sample_rate // 2):
        for offset in range(min(300, len(samples) - position)):
            samples[position + offset] = int(24000 * (1.0 - offset / 300))
    path = tmp_path / "click.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    result = LibrosaTempoAnalyzer().analyze(bytes(path), LocalBpmSettings(enabled=True))

    assert 105.0 <= result.bpm <= 135.0
