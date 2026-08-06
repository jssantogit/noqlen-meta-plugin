from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, fields


def _boolean(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be boolean")
    return value


def _number(
    value: object, field_name: str, lower: float, upper: float, *, open_lower: bool = False
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite number in the allowed range")
    normalized = float(value)
    lower_valid = normalized > lower if open_lower else normalized >= lower
    if not math.isfinite(normalized) or not lower_valid or normalized > upper:
        raise ValueError(f"{field_name} must be a finite number in the allowed range")
    return normalized


def _integer(value: object, field_name: str, lower: int, upper: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
        raise ValueError(f"{field_name} must be an integer in the allowed range")
    return value


@dataclass(frozen=True, slots=True)
class AcoustIDSettings:
    enabled: bool
    reuse_existing: bool
    compute_missing: bool
    lookup: bool
    use_for_identity: bool
    min_score: float
    min_margin: float
    max_results: int
    max_recordings_per_result: int
    timeout_seconds: float
    requests_per_second: float
    cache_entries: int
    fpcalc: str

    def __post_init__(self) -> None:
        for field_name in (
            "enabled",
            "reuse_existing",
            "compute_missing",
            "lookup",
            "use_for_identity",
        ):
            object.__setattr__(self, field_name, _boolean(getattr(self, field_name), field_name))
        object.__setattr__(self, "min_score", _number(self.min_score, "min_score", 0, 1))
        object.__setattr__(self, "min_margin", _number(self.min_margin, "min_margin", 0, 1))
        object.__setattr__(
            self, "max_results", _integer(self.max_results, "max_results", 1, 20)
        )
        object.__setattr__(
            self,
            "max_recordings_per_result",
            _integer(
                self.max_recordings_per_result,
                "max_recordings_per_result",
                1,
                50,
            ),
        )
        object.__setattr__(
            self,
            "timeout_seconds",
            _number(self.timeout_seconds, "timeout_seconds", 1, 60),
        )
        object.__setattr__(
            self,
            "requests_per_second",
            _number(
                self.requests_per_second,
                "requests_per_second",
                0,
                3,
                open_lower=True,
            ),
        )
        object.__setattr__(
            self, "cache_entries", _integer(self.cache_entries, "cache_entries", 0, 4096)
        )
        if not isinstance(self.fpcalc, str) or not self.fpcalc.strip():
            raise ValueError("fpcalc must be a non-empty string")
        object.__setattr__(self, "fpcalc", self.fpcalc.strip())

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> AcoustIDSettings:
        if not isinstance(values, Mapping):
            raise ValueError("AcoustID settings must be a complete mapping")
        expected = {item.name for item in fields(cls)}
        supplied = set(values)
        if missing := sorted(expected - supplied):
            raise ValueError(f"missing AcoustID setting: {missing[0]}")
        if supplied - expected:
            raise ValueError("unknown AcoustID setting")
        return cls(**values)  # type: ignore[arg-type]


def default_acoustid_settings() -> AcoustIDSettings:
    return AcoustIDSettings(
        enabled=False,
        reuse_existing=True,
        compute_missing=False,
        lookup=True,
        use_for_identity=True,
        min_score=0.90,
        min_margin=0.05,
        max_results=5,
        max_recordings_per_result=10,
        timeout_seconds=15.0,
        requests_per_second=3.0,
        cache_entries=256,
        fpcalc="fpcalc",
    )
