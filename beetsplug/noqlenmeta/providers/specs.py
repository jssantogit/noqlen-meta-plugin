"""Dependency-light metadata describing built-in provider capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


def _canonical_name(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    normalized = value.strip().lower()
    if not normalized.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"{label} contains invalid characters")
    return normalized


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Static identity and current output capabilities of one provider adapter."""

    name: str
    display_name: str
    supported_fields: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _canonical_name(self.name, "provider name"))
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("provider display name must be a non-empty string")
        object.__setattr__(self, "display_name", self.display_name.strip())

        if isinstance(self.supported_fields, str):
            raise TypeError("supported fields must be a collection of field names")
        fields = tuple(
            _canonical_name(field, "supported field") for field in self.supported_fields
        )
        if len(fields) != len(set(fields)):
            raise ValueError("supported field names must be unique after normalization")
        object.__setattr__(self, "supported_fields", frozenset(fields))


DISCOGS_SPEC = ProviderSpec(
    name="discogs",
    display_name="Discogs",
    supported_fields=frozenset(
        {
            "genres",
            "styles",
            "labels",
            "catalog_numbers",
            "barcodes",
            "country",
            "year",
            "media",
            "format_descriptions",
        }
    ),
)

MUSICBRAINZ_SPEC = ProviderSpec(
    name="musicbrainz",
    display_name="MusicBrainz",
    supported_fields=frozenset(
        {
            "labels",
            "catalog_numbers",
            "barcodes",
            "country",
            "year",
            "media",
        }
    ),
)

LASTFM_SPEC = ProviderSpec(
    name="lastfm",
    display_name="Last.fm",
    supported_fields=frozenset({"genres"}),
)

ITUNES_SPEC = ProviderSpec(
    name="itunes",
    display_name="iTunes",
    supported_fields=frozenset({"genres", "year"}),
)

BUILTIN_PROVIDER_SPECS: Mapping[str, ProviderSpec] = MappingProxyType(
    {
        spec.name: spec
        for spec in (DISCOGS_SPEC, MUSICBRAINZ_SPEC, LASTFM_SPEC, ITUNES_SPEC)
    }
)


def provider_display_name(name: str) -> str:
    """Return built-in branding with a safe generic fallback for unknown names."""
    spec = BUILTIN_PROVIDER_SPECS.get(name.casefold())
    return spec.display_name if spec is not None else name.title()
