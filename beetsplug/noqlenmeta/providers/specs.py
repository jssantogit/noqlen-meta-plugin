"""Dependency-light metadata describing built-in provider capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import TypeAlias


def _canonical_name(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    normalized = value.strip().lower()
    if not normalized.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"{label} contains invalid characters")
    return normalized


class ProviderScope(Enum):
    """The musical entity supplied to a provider adapter."""

    RELEASE = "release"
    TRACK = "track"
    ARTIST = "artist"


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Static identity and current output capabilities of one provider adapter."""

    name: str
    display_name: str
    supported_fields: frozenset[str]
    scope: ProviderScope = ProviderScope.RELEASE

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
        if not isinstance(self.scope, ProviderScope):
            raise TypeError("provider scope must be a ProviderScope")


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
    scope=ProviderScope.RELEASE,
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
    scope=ProviderScope.RELEASE,
)

LASTFM_SPEC = ProviderSpec(
    name="lastfm",
    display_name="Last.fm",
    supported_fields=frozenset({"genres"}),
    scope=ProviderScope.RELEASE,
)

ITUNES_SPEC = ProviderSpec(
    name="itunes",
    display_name="iTunes",
    supported_fields=frozenset({"genres", "year"}),
    scope=ProviderScope.RELEASE,
)

LRCLIB_SPEC = ProviderSpec(
    name="lrclib",
    display_name="LRCLIB",
    supported_fields=frozenset({"lyrics", "synced_lyrics"}),
    scope=ProviderScope.TRACK,
)

ProviderKey: TypeAlias = tuple[str, ProviderScope]
_BUILTIN_PROVIDER_CAPABILITIES = (
    DISCOGS_SPEC,
    MUSICBRAINZ_SPEC,
    LASTFM_SPEC,
    ITUNES_SPEC,
    LRCLIB_SPEC,
)
BUILTIN_PROVIDER_SPECS: Mapping[ProviderKey, ProviderSpec] = MappingProxyType(
    {(spec.name, spec.scope): spec for spec in _BUILTIN_PROVIDER_CAPABILITIES}
)
BUILTIN_PROVIDER_NAMES = frozenset(spec.name for spec in _BUILTIN_PROVIDER_CAPABILITIES)
BUILTIN_RELEASE_PROVIDER_SPECS: Mapping[str, ProviderSpec] = MappingProxyType(
    {
        spec.name: spec
        for spec in _BUILTIN_PROVIDER_CAPABILITIES
        if spec.scope is ProviderScope.RELEASE
    }
)
BUILTIN_TRACK_PROVIDER_SPECS: Mapping[str, ProviderSpec] = MappingProxyType(
    {
        spec.name: spec
        for spec in _BUILTIN_PROVIDER_CAPABILITIES
        if spec.scope is ProviderScope.TRACK
    }
)
BUILTIN_ARTIST_PROVIDER_SPECS: Mapping[str, ProviderSpec] = MappingProxyType(
    {
        spec.name: spec
        for spec in _BUILTIN_PROVIDER_CAPABILITIES
        if spec.scope is ProviderScope.ARTIST
    }
)


def provider_display_name(name: str) -> str:
    """Return built-in branding with a safe generic fallback for unknown names."""
    normalized = name.casefold()
    spec = next(
        (spec for spec in _BUILTIN_PROVIDER_CAPABILITIES if spec.name == normalized), None
    )
    return spec.display_name if spec is not None else name.title()
