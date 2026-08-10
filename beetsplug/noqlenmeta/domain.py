"""Provider-independent metadata enrichment domain values."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import TYPE_CHECKING, TypeAlias
from uuid import UUID

if TYPE_CHECKING:
    from beetsplug.noqlenmeta.genre_evidence import GenreEvidence
    from beetsplug.noqlenmeta.providers.specs import ProviderScope

ScalarMetadataValue: TypeAlias = str | int | float | bool
MetadataValue: TypeAlias = ScalarMetadataValue | tuple[str, ...]


class SemanticCategory(Enum):
    GENRE = "genre"
    STYLE = "style"
    MOOD = "mood"
    ORIGIN = "origin"
    DESCRIPTOR = "descriptor"
    NOISE = "noise"


@dataclass(frozen=True, slots=True)
class SemanticTagEvidence:
    canonical_term: str
    category: SemanticCategory
    provider: str
    scope: ProviderScope
    confidence: float
    source_id: str
    source_url: str | None
    native_weight: int | None
    raw_tag: str

    def __post_init__(self) -> None:
        from beetsplug.noqlenmeta.providers.specs import ProviderScope

        for field, label in (
            ("canonical_term", "canonical term"),
            ("provider", "provider"),
            ("source_id", "source ID"),
            ("raw_tag", "raw tag"),
        ):
            object.__setattr__(self, field, _text(getattr(self, field), label))
        object.__setattr__(self, "source_url", _optional_text(self.source_url, "source URL"))
        if not isinstance(self.category, SemanticCategory):
            raise TypeError("category must be a SemanticCategory")
        if not isinstance(self.scope, ProviderScope):
            raise TypeError("scope must be a ProviderScope")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not isfinite(self.confidence)
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise ValueError("confidence must be a finite number between 0.0 and 1.0")
        object.__setattr__(self, "confidence", float(self.confidence))
        if self.native_weight is not None and (
            isinstance(self.native_weight, bool)
            or not isinstance(self.native_weight, int)
            or self.native_weight < 0
        ):
            raise ValueError("native weight must be a non-negative integer")


def canonical_uuid(value: object) -> str | None:
    """Return canonical UUID text without allowing malformed stored IDs to escape."""
    if not isinstance(value, str):
        return None
    try:
        return str(UUID(value.strip()))
    except (AttributeError, ValueError):
        return None


_ISRC_PATTERN = re.compile(
    r"(?:[A-Za-z]{2}[A-Za-z0-9]{3}[0-9]{7}|"
    r"[A-Za-z]{2}-[A-Za-z0-9]{3}-[0-9]{2}-[0-9]{5})"
)


def canonical_isrc(value: object) -> str | None:
    """Return canonical ISRC text or ``None`` for malformed stored metadata."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if _ISRC_PATTERN.fullmatch(text) is None:
        return None
    return text.replace("-", "").upper()


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
    """A provider-independent, namespaced identifier for a musical entity."""

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
class ArtistEnrichmentContext:
    """Identity and credit context for one artist."""

    name: str
    sort_name: str | None = None
    credit_name: str | None = None
    credit_index: int | None = None
    external_ids: tuple[ExternalIdentifier, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "artist name"))
        object.__setattr__(
            self, "sort_name", _optional_text(self.sort_name, "artist sort name")
        )
        object.__setattr__(
            self, "credit_name", _optional_text(self.credit_name, "artist credit name")
        )
        if self.credit_index is not None and (
            isinstance(self.credit_index, bool)
            or not isinstance(self.credit_index, int)
            or self.credit_index <= 0
        ):
            raise ValueError("credit index must be a positive integer")

        external_ids = tuple(self.external_ids)
        if not all(isinstance(identifier, ExternalIdentifier) for identifier in external_ids):
            raise TypeError("external_ids must contain ExternalIdentifier values")
        object.__setattr__(self, "external_ids", external_ids)


@dataclass(frozen=True, slots=True)
class TrackEnrichmentContext:
    """Identity and provider input for a track already identified by beets."""

    artist: str
    title: str
    album_title: str | None = None
    duration: float | None = None
    track_number: int | None = None
    disc_number: int | None = None
    external_ids: tuple[ExternalIdentifier, ...] = ()
    artists: tuple[ArtistEnrichmentContext, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "artist", _text(self.artist, "track artist"))
        object.__setattr__(self, "title", _text(self.title, "track title"))
        object.__setattr__(
            self,
            "album_title",
            _optional_text(self.album_title, "album title"),
        )

        duration = self.duration
        if duration is not None:
            if (
                isinstance(duration, bool)
                or not isinstance(duration, (int, float))
                or not isfinite(duration)
                or duration <= 0
            ):
                raise ValueError("duration must be a finite positive number of seconds")
            object.__setattr__(self, "duration", float(duration))

        for field, label in (
            ("track_number", "track number"),
            ("disc_number", "disc number"),
        ):
            value = getattr(self, field)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
            ):
                raise ValueError(f"{label} must be a positive integer")

        external_ids = tuple(self.external_ids)
        if not all(isinstance(identifier, ExternalIdentifier) for identifier in external_ids):
            raise TypeError("external_ids must contain ExternalIdentifier values")
        object.__setattr__(self, "external_ids", external_ids)
        artists = tuple(self.artists)
        if not all(isinstance(artist, ArtistEnrichmentContext) for artist in artists):
            raise TypeError("artists must contain ArtistEnrichmentContext values")
        object.__setattr__(self, "artists", artists)


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


@dataclass(frozen=True, slots=True)
class SemanticEvidenceBundle:
    metadata: tuple[MetadataCandidate, ...] = ()
    genres: tuple[GenreEvidence, ...] = ()
    tags: tuple[SemanticTagEvidence, ...] = ()

    def __post_init__(self) -> None:
        from beetsplug.noqlenmeta.genre_evidence import GenreEvidence

        for values, expected, label in (
            (self.metadata, MetadataCandidate, "metadata"),
            (self.genres, GenreEvidence, "genres"),
            (self.tags, SemanticTagEvidence, "tags"),
        ):
            normalized = tuple(values)
            if not all(isinstance(value, expected) for value in normalized):
                raise TypeError(f"{label} contains an invalid value")
            object.__setattr__(self, label, normalized)
