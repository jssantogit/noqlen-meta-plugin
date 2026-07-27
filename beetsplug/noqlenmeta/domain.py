"""Provider-independent metadata enrichment domain values."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import TypeAlias
from uuid import UUID

ScalarMetadataValue: TypeAlias = str | int | float | bool
MetadataValue: TypeAlias = ScalarMetadataValue | tuple[str, ...]


def canonical_uuid(value: object) -> str | None:
    """Return canonical UUID text without allowing malformed stored IDs to escape."""
    if not isinstance(value, str):
        return None
    try:
        return str(UUID(value.strip()))
    except (AttributeError, ValueError):
        return None


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


@dataclass(frozen=True, slots=True)
class ExternalIdentifier:
    """A provider-independent, namespaced identifier for a release."""

    namespace: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "namespace", _text(self.namespace, "identifier namespace"))
        object.__setattr__(self, "value", _text(self.value, "identifier value"))


@dataclass(frozen=True, slots=True)
class ReleaseEnrichmentContext:
    """Identity and search hints for a release already identified by beets."""

    album_artist: str
    album_title: str
    year: int | None = None
    barcode: str | None = None
    catalog_number: str | None = None
    external_ids: tuple[ExternalIdentifier, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "album_artist", _text(self.album_artist, "album artist"))
        object.__setattr__(self, "album_title", _text(self.album_title, "album title"))

        if self.year is not None and (
            isinstance(self.year, bool)
            or not isinstance(self.year, int)
            or not 1 <= self.year <= 9999
        ):
            raise ValueError("year must be an integer between 1 and 9999")

        object.__setattr__(self, "barcode", _optional_text(self.barcode, "barcode"))
        object.__setattr__(
            self,
            "catalog_number",
            _optional_text(self.catalog_number, "catalog number"),
        )

        external_ids = tuple(self.external_ids)
        if not all(isinstance(identifier, ExternalIdentifier) for identifier in external_ids):
            raise TypeError("external_ids must contain ExternalIdentifier values")
        object.__setattr__(self, "external_ids", external_ids)


@dataclass(frozen=True, slots=True)
class MetadataCandidate:
    """A provider's normalized proposal for one metadata field.

    Confidence uses an inclusive 0.0 to 1.0 scale, where 0.0 means no provider
    confidence and 1.0 means the provider considers the proposal fully certain.
    """

    field: str
    value: MetadataValue
    provider: str
    confidence: float
    source_id: str
    source_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "field", _text(self.field, "field"))
        object.__setattr__(self, "provider", _text(self.provider, "provider"))
        object.__setattr__(self, "source_id", _text(self.source_id, "source ID"))
        object.__setattr__(
            self,
            "source_url",
            _optional_text(self.source_url, "source URL"),
        )
        object.__setattr__(self, "value", self._validated_value(self.value))

        confidence = self.confidence
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not isfinite(confidence)
            or not 0.0 <= confidence <= 1.0
        ):
            raise ValueError("confidence must be a finite number between 0.0 and 1.0")
        object.__setattr__(self, "confidence", float(confidence))

    @staticmethod
    def _validated_value(value: object) -> MetadataValue:
        if isinstance(value, str):
            return _text(value, "candidate value")
        if isinstance(value, bool) or isinstance(value, int):
            return value
        if isinstance(value, float):
            if not isfinite(value):
                raise ValueError("numeric candidate value must be finite")
            return value
        if isinstance(value, tuple):
            if not value:
                raise ValueError("multi-value candidate value must not be empty")
            return tuple(_text(item, "multi-value candidate item") for item in value)
        raise TypeError("candidate value must be a string, number, boolean, or tuple of strings")
