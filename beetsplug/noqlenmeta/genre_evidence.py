"""Immutable genre evidence with provider provenance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from beetsplug.noqlenmeta.providers.specs import ProviderScope


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


class GenreEvidenceKind(Enum):
    GENRE = "genre"
    PROMOTED_STYLE = "promoted_style"
    COMMUNITY_TAG = "community_tag"


@dataclass(frozen=True, slots=True)
class GenreEvidence:
    genre: str
    provider: str
    scope: ProviderScope
    kind: GenreEvidenceKind
    confidence: float
    source_id: str
    source_url: str | None = None
    weight: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "genre", _text(self.genre, "genre"))
        object.__setattr__(self, "provider", _text(self.provider, "provider"))
        object.__setattr__(self, "source_id", _text(self.source_id, "source ID"))
        if self.source_url is not None:
            object.__setattr__(self, "source_url", _text(self.source_url, "source URL"))
        if not isinstance(self.scope, ProviderScope):
            raise TypeError("scope must be a ProviderScope")
        if not isinstance(self.kind, GenreEvidenceKind):
            raise TypeError("kind must be a GenreEvidenceKind")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not isfinite(self.confidence)
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise ValueError("confidence must be a finite number between 0.0 and 1.0")
        object.__setattr__(self, "confidence", float(self.confidence))
        if self.weight is not None and (
            isinstance(self.weight, bool)
            or not isinstance(self.weight, int)
            or not 0 <= self.weight <= 100
        ):
            raise ValueError("weight must be an integer between 0 and 100")
