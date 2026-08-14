"""Dependency-light metadata describing built-in provider capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import TypeAlias

from beetsplug.noqlenmeta.field_contracts import EntityKind, field_contract


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


class IdentityPrerequisite(Enum):
    """Identity context required before an adapter may acquire evidence."""

    NONE = "none"
    EXACT_CANONICAL_ID = "exact_canonical_id"
    EXACT_PROVIDER_ID = "exact_provider_id"
    STRUCTURALLY_VALIDATED_CONTEXT = "structurally_validated_context"


class AcquisitionCharacteristic(Enum):
    """Discrete acquisition behavior relevant to lazy planning."""

    DIRECT_LOOKUP = "direct_lookup"
    SEARCH = "search"
    RESPONSE_REUSE = "response_reuse"
    SUPPORTING_TRAVERSAL = "supporting_traversal"


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    """One field an ordinary adapter can emit under explicit preconditions."""

    provider: str
    field: str
    asserted_entity: EntityKind
    acquisition_scope: ProviderScope
    identity_prerequisites: frozenset[IdentityPrerequisite]
    characteristics: frozenset[AcquisitionCharacteristic] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", _canonical_name(self.provider, "provider name"))
        contract = field_contract(self.field)
        object.__setattr__(self, "field", contract.canonical_name)
        if not isinstance(self.asserted_entity, EntityKind):
            raise TypeError("asserted entity must be an EntityKind")
        if self.asserted_entity not in contract.allowed_entities:
            raise ValueError("asserted entity is not among the field's allowed entities")
        if not isinstance(self.acquisition_scope, ProviderScope):
            raise TypeError("acquisition scope must be a ProviderScope")
        prerequisites = frozenset(self.identity_prerequisites)
        if not prerequisites or not all(
            isinstance(prerequisite, IdentityPrerequisite) for prerequisite in prerequisites
        ):
            raise TypeError("identity_prerequisites must contain IdentityPrerequisite values")
        object.__setattr__(self, "identity_prerequisites", prerequisites)
        characteristics = frozenset(self.characteristics)
        if not all(
            isinstance(characteristic, AcquisitionCharacteristic)
            for characteristic in characteristics
        ):
            raise TypeError("characteristics must contain AcquisitionCharacteristic values")
        object.__setattr__(self, "characteristics", characteristics)


CapabilityKey: TypeAlias = tuple[str, str, EntityKind, ProviderScope]


def capability_registry(
    capabilities: tuple[ProviderCapability, ...],
) -> Mapping[CapabilityKey, ProviderCapability]:
    """Build an immutable capability index and reject duplicate declarations."""
    registry: dict[CapabilityKey, ProviderCapability] = {}
    for capability in capabilities:
        if not isinstance(capability, ProviderCapability):
            raise TypeError("capabilities must contain ProviderCapability values")
        key = (
            capability.provider,
            capability.field,
            capability.asserted_entity,
            capability.acquisition_scope,
        )
        if key in registry:
            raise ValueError(f"duplicate capability: {key!r}")
        registry[key] = capability
    return MappingProxyType(registry)


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
        fields = tuple(_canonical_name(field, "supported field") for field in self.supported_fields)
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
            "genres",
        }
    ),
    scope=ProviderScope.RELEASE,
)

MUSICBRAINZ_TRACK_SPEC = ProviderSpec(
    name="musicbrainz",
    display_name="MusicBrainz",
    supported_fields=frozenset(
        {"genres", "moods", "lyrics_languages", "isrcs", "works", "iswcs", "recording_date"}
    ),
    scope=ProviderScope.TRACK,
)

MUSICBRAINZ_ARTIST_SPEC = ProviderSpec(
    name="musicbrainz",
    display_name="MusicBrainz",
    supported_fields=frozenset({"genres", "moods", "artist_countries", "artist_areas"}),
    scope=ProviderScope.ARTIST,
)

LASTFM_SPEC = ProviderSpec(
    name="lastfm",
    display_name="Last.fm",
    supported_fields=frozenset({"genres", "styles", "moods"}),
    scope=ProviderScope.RELEASE,
)

LASTFM_TRACK_SPEC = ProviderSpec(
    name="lastfm",
    display_name="Last.fm",
    supported_fields=frozenset({"genres", "styles", "moods"}),
    scope=ProviderScope.TRACK,
)

LASTFM_ARTIST_SPEC = ProviderSpec(
    name="lastfm",
    display_name="Last.fm",
    supported_fields=frozenset({"genres", "styles", "moods"}),
    scope=ProviderScope.ARTIST,
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
    MUSICBRAINZ_TRACK_SPEC,
    MUSICBRAINZ_ARTIST_SPEC,
    LASTFM_SPEC,
    LASTFM_TRACK_SPEC,
    LASTFM_ARTIST_SPEC,
    ITUNES_SPEC,
    LRCLIB_SPEC,
)


def _asserted_entity(spec: ProviderSpec, field: str) -> EntityKind:
    if field in {"lyrics_languages", "iswcs"}:
        return EntityKind.WORK
    return {
        ProviderScope.RELEASE: EntityKind.RELEASE,
        ProviderScope.TRACK: EntityKind.RECORDING,
        ProviderScope.ARTIST: EntityKind.ARTIST,
    }[spec.scope]


def _identity_prerequisites(spec: ProviderSpec) -> frozenset[IdentityPrerequisite]:
    if spec.name == "musicbrainz":
        return frozenset({IdentityPrerequisite.EXACT_CANONICAL_ID})
    if spec.name in {"discogs", "itunes"}:
        return frozenset(
            {
                IdentityPrerequisite.EXACT_PROVIDER_ID,
                IdentityPrerequisite.STRUCTURALLY_VALIDATED_CONTEXT,
            }
        )
    return frozenset({IdentityPrerequisite.STRUCTURALLY_VALIDATED_CONTEXT})


def _characteristics(spec: ProviderSpec, field: str) -> frozenset[AcquisitionCharacteristic]:
    values = {
        AcquisitionCharacteristic.DIRECT_LOOKUP,
        AcquisitionCharacteristic.RESPONSE_REUSE,
    }
    if spec.name in {"discogs", "itunes"}:
        values.add(AcquisitionCharacteristic.SEARCH)
    if spec.name == "musicbrainz" and field in {"lyrics_languages", "iswcs"}:
        values.add(AcquisitionCharacteristic.SUPPORTING_TRAVERSAL)
    return frozenset(values)


BUILTIN_PROVIDER_CAPABILITIES = tuple(
    ProviderCapability(
        provider=spec.name,
        field=field,
        asserted_entity=_asserted_entity(spec, field),
        acquisition_scope=spec.scope,
        identity_prerequisites=_identity_prerequisites(spec),
        characteristics=_characteristics(spec, field),
    )
    for spec in _BUILTIN_PROVIDER_CAPABILITIES
    for field in sorted(spec.supported_fields)
)
BUILTIN_PROVIDER_CAPABILITY_REGISTRY = capability_registry(BUILTIN_PROVIDER_CAPABILITIES)


def _catalog_capability(provider: str, field: str, entity: EntityKind) -> ProviderCapability:
    return ProviderCapability(
        provider=provider,
        field=field,
        asserted_entity=entity,
        acquisition_scope=ProviderScope.RELEASE,
        identity_prerequisites=(
            frozenset({IdentityPrerequisite.EXACT_CANONICAL_ID})
            if provider == "musicbrainz"
            else _identity_prerequisites(
                next(
                    spec
                    for spec in _BUILTIN_PROVIDER_CAPABILITIES
                    if spec.name == provider and spec.scope is ProviderScope.RELEASE
                )
            )
        ),
        characteristics=(
            frozenset(
                {
                    AcquisitionCharacteristic.DIRECT_LOOKUP,
                    AcquisitionCharacteristic.RESPONSE_REUSE,
                    *(
                        {AcquisitionCharacteristic.SEARCH}
                        if provider in {"discogs", "itunes"}
                        else set()
                    ),
                    *(
                        {AcquisitionCharacteristic.SUPPORTING_TRAVERSAL}
                        if provider == "musicbrainz" and entity is EntityKind.RELEASE_GROUP
                        else set()
                    ),
                }
            )
        ),
    )


RELEASE_CATALOG_PROVIDER_CAPABILITIES = (
    _catalog_capability("musicbrainz", "date", EntityKind.RELEASE),
    _catalog_capability("musicbrainz", "original_date", EntityKind.RELEASE_GROUP),
    _catalog_capability("musicbrainz", "release_type", EntityKind.RELEASE_GROUP),
    _catalog_capability("musicbrainz", "release_secondary_types", EntityKind.RELEASE_GROUP),
    _catalog_capability("musicbrainz", "release_status", EntityKind.RELEASE),
    _catalog_capability("discogs", "date", EntityKind.RELEASE),
    _catalog_capability("discogs", "edition", EntityKind.RELEASE),
    _catalog_capability("itunes", "date", EntityKind.RELEASE),
)
RELEASE_CATALOG_PROVIDER_CAPABILITY_REGISTRY = capability_registry(
    RELEASE_CATALOG_PROVIDER_CAPABILITIES
)


def _credit_capability(
    provider: str,
    field: str,
    entity: EntityKind,
    scope: ProviderScope,
) -> ProviderCapability:
    return ProviderCapability(
        provider=provider,
        field=field,
        asserted_entity=entity,
        acquisition_scope=scope,
        identity_prerequisites=(
            frozenset({IdentityPrerequisite.EXACT_CANONICAL_ID})
            if provider == "musicbrainz"
            else frozenset(
                {
                    IdentityPrerequisite.EXACT_PROVIDER_ID,
                    IdentityPrerequisite.STRUCTURALLY_VALIDATED_CONTEXT,
                }
            )
        ),
        characteristics=frozenset(
            {
                AcquisitionCharacteristic.DIRECT_LOOKUP,
                AcquisitionCharacteristic.RESPONSE_REUSE,
                *(
                    {AcquisitionCharacteristic.SUPPORTING_TRAVERSAL}
                    if entity is EntityKind.WORK
                    else set()
                ),
            }
        ),
    )


CREDIT_PROVIDER_CAPABILITIES = (
    _credit_capability("musicbrainz", "composers", EntityKind.WORK, ProviderScope.TRACK),
    _credit_capability("musicbrainz", "lyricists", EntityKind.WORK, ProviderScope.TRACK),
    _credit_capability("musicbrainz", "arrangers", EntityKind.WORK, ProviderScope.TRACK),
    _credit_capability("musicbrainz", "arrangers", EntityKind.RECORDING, ProviderScope.TRACK),
    _credit_capability("musicbrainz", "producers", EntityKind.RECORDING, ProviderScope.TRACK),
    _credit_capability("musicbrainz", "conductors", EntityKind.RECORDING, ProviderScope.TRACK),
    _credit_capability("musicbrainz", "performers", EntityKind.RECORDING, ProviderScope.TRACK),
    _credit_capability(
        "musicbrainz", "featured_artists", EntityKind.RECORDING, ProviderScope.TRACK
    ),
    _credit_capability(
        "musicbrainz",
        "structured_artist_credits",
        EntityKind.RECORDING,
        ProviderScope.TRACK,
    ),
    *(
        _credit_capability("musicbrainz", field, EntityKind.RELEASE, ProviderScope.RELEASE)
        for field in (
            "producers",
            "conductors",
            "performers",
            "featured_artists",
            "structured_artist_credits",
        )
    ),
)
CREDIT_PROVIDER_CAPABILITY_REGISTRY = capability_registry(CREDIT_PROVIDER_CAPABILITIES)
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
    spec = next((spec for spec in _BUILTIN_PROVIDER_CAPABILITIES if spec.name == normalized), None)
    return spec.display_name if spec is not None else name.title()
