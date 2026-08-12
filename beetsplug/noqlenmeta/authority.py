"""Explicit field and scope authority roles for ordinary provider evidence."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import Enum
from types import MappingProxyType

from beetsplug.noqlenmeta.field_contracts import EntityKind, field_contract
from beetsplug.noqlenmeta.providers.specs import (
    BUILTIN_PROVIDER_CAPABILITY_REGISTRY,
    ProviderScope,
)


class AuthorityRole(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    FALLBACK = "fallback"
    CORROBORATION_ONLY = "corroboration_only"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True, slots=True)
class AuthorityRule:
    field: str
    asserted_entity: EntityKind
    acquisition_scope: ProviderScope
    provider: str
    role: AuthorityRole

    def __post_init__(self) -> None:
        contract = field_contract(self.field)
        object.__setattr__(self, "field", contract.canonical_name)
        if not isinstance(self.asserted_entity, EntityKind):
            raise TypeError("asserted_entity must be an EntityKind")
        if self.asserted_entity not in contract.allowed_entities:
            raise ValueError("asserted entity is not among the field's allowed entities")
        if not isinstance(self.acquisition_scope, ProviderScope):
            raise TypeError("acquisition_scope must be a ProviderScope")
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("provider must be a non-empty string")
        object.__setattr__(self, "provider", self.provider.strip().casefold())
        if not isinstance(self.role, AuthorityRole):
            raise TypeError("role must be an AuthorityRole")


AuthorityKey = tuple[str, EntityKind, ProviderScope, str]


@dataclass(frozen=True, slots=True)
class AuthorityMatrix:
    rules: tuple[AuthorityRule, ...]
    _indexed: MappingProxyType = dataclass_field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        rules = tuple(self.rules)
        indexed: dict[AuthorityKey, AuthorityRule] = {}
        for authority in rules:
            if not isinstance(authority, AuthorityRule):
                raise TypeError("rules must contain AuthorityRule values")
            if authority.role is AuthorityRole.INELIGIBLE:
                raise ValueError("ineligible combinations must remain unlisted")
            key = (
                authority.field,
                authority.asserted_entity,
                authority.acquisition_scope,
                authority.provider,
            )
            if key in indexed:
                raise ValueError(f"duplicate authority rule: {key!r}")
            indexed[key] = authority
        object.__setattr__(self, "rules", rules)
        object.__setattr__(self, "_indexed", MappingProxyType(indexed))

    def role_for(
        self,
        field: str,
        asserted_entity: EntityKind,
        acquisition_scope: ProviderScope,
        provider: str,
    ) -> AuthorityRole:
        contract = field_contract(field)
        authority = self._indexed.get(
            (
                contract.canonical_name,
                asserted_entity,
                acquisition_scope,
                provider.strip().casefold(),
            )
        )
        return authority.role if authority is not None else AuthorityRole.INELIGIBLE


def eligible_standalone(role: AuthorityRole) -> bool:
    """Return whether a role may independently supply a canonical value."""
    if not isinstance(role, AuthorityRole):
        raise TypeError("role must be an AuthorityRole")
    return role in {AuthorityRole.PRIMARY, AuthorityRole.SECONDARY, AuthorityRole.FALLBACK}


@dataclass(frozen=True, slots=True)
class V2AuthorityEntry:
    """Exact ordinal V2 compatibility policy, intentionally without V3 roles."""

    field: str
    provider: str
    rank: int


def translate_v2_authority(field: str, providers: tuple[str, ...]) -> tuple[V2AuthorityEntry, ...]:
    """Preserve V2 ordering without guessing V3 fallback/corroboration semantics."""
    canonical = field_contract(field).canonical_name
    normalized = tuple(provider.strip().casefold() for provider in providers)
    if any(not provider for provider in normalized) or len(normalized) != len(set(normalized)):
        raise ValueError("V2 authority providers must be non-empty and unique")
    return tuple(
        V2AuthorityEntry(field=canonical, provider=provider, rank=rank)
        for rank, provider in enumerate(normalized)
    )


def _rule(
    field: str,
    provider: str,
    role: AuthorityRole,
    scope: ProviderScope,
    entity: EntityKind | None = None,
) -> AuthorityRule:
    contract = field_contract(field)
    if entity is None:
        if len(contract.allowed_entities) != 1:
            raise ValueError(f"multi-entity authority rule {field!r} requires an entity")
        entity = next(iter(contract.allowed_entities))
    return AuthorityRule(
        field=field,
        asserted_entity=entity,
        acquisition_scope=scope,
        provider=provider,
        role=role,
    )


_RULES = (
    # Executable V2 catalog capabilities, aligned to the approved V3 proposal.
    _rule("year", "musicbrainz", AuthorityRole.PRIMARY, ProviderScope.RELEASE),
    _rule("year", "discogs", AuthorityRole.SECONDARY, ProviderScope.RELEASE),
    _rule("year", "itunes", AuthorityRole.FALLBACK, ProviderScope.RELEASE),
    _rule("labels", "discogs", AuthorityRole.PRIMARY, ProviderScope.RELEASE),
    _rule("labels", "musicbrainz", AuthorityRole.SECONDARY, ProviderScope.RELEASE),
    _rule("catalog_numbers", "discogs", AuthorityRole.PRIMARY, ProviderScope.RELEASE),
    _rule("catalog_numbers", "musicbrainz", AuthorityRole.SECONDARY, ProviderScope.RELEASE),
    _rule("barcodes", "discogs", AuthorityRole.PRIMARY, ProviderScope.RELEASE),
    _rule("barcodes", "musicbrainz", AuthorityRole.SECONDARY, ProviderScope.RELEASE),
    _rule("country", "discogs", AuthorityRole.PRIMARY, ProviderScope.RELEASE),
    _rule("country", "musicbrainz", AuthorityRole.SECONDARY, ProviderScope.RELEASE),
    _rule("media", "discogs", AuthorityRole.PRIMARY, ProviderScope.RELEASE, EntityKind.RELEASE),
    _rule(
        "media", "musicbrainz", AuthorityRole.SECONDARY, ProviderScope.RELEASE, EntityKind.RELEASE
    ),
    _rule(
        "format_descriptions",
        "discogs",
        AuthorityRole.PRIMARY,
        ProviderScope.RELEASE,
        EntityKind.RELEASE,
    ),
    # Existing taxonomy and semantic evidence remains specialized.
    _rule(
        "genres", "musicbrainz", AuthorityRole.PRIMARY, ProviderScope.RELEASE, EntityKind.RELEASE
    ),
    _rule("genres", "discogs", AuthorityRole.PRIMARY, ProviderScope.RELEASE, EntityKind.RELEASE),
    _rule("genres", "lastfm", AuthorityRole.FALLBACK, ProviderScope.RELEASE, EntityKind.RELEASE),
    _rule("genres", "itunes", AuthorityRole.FALLBACK, ProviderScope.RELEASE, EntityKind.RELEASE),
    _rule(
        "genres",
        "musicbrainz",
        AuthorityRole.PRIMARY,
        ProviderScope.TRACK,
        EntityKind.RECORDING,
    ),
    _rule(
        "genres",
        "lastfm",
        AuthorityRole.FALLBACK,
        ProviderScope.TRACK,
        EntityKind.RECORDING,
    ),
    _rule("genres", "musicbrainz", AuthorityRole.PRIMARY, ProviderScope.ARTIST, EntityKind.ARTIST),
    _rule("genres", "lastfm", AuthorityRole.FALLBACK, ProviderScope.ARTIST, EntityKind.ARTIST),
    _rule(
        "styles",
        "discogs",
        AuthorityRole.PRIMARY,
        ProviderScope.RELEASE,
        EntityKind.RELEASE,
    ),
    _rule(
        "styles",
        "lastfm",
        AuthorityRole.FALLBACK,
        ProviderScope.RELEASE,
        EntityKind.RELEASE,
    ),
    _rule("styles", "lastfm", AuthorityRole.FALLBACK, ProviderScope.TRACK, EntityKind.RECORDING),
    _rule("styles", "lastfm", AuthorityRole.FALLBACK, ProviderScope.ARTIST, EntityKind.ARTIST),
    _rule(
        "moods",
        "musicbrainz",
        AuthorityRole.PRIMARY,
        ProviderScope.TRACK,
        EntityKind.RECORDING,
    ),
    _rule(
        "moods",
        "lastfm",
        AuthorityRole.SECONDARY,
        ProviderScope.TRACK,
        EntityKind.RECORDING,
    ),
    _rule("moods", "musicbrainz", AuthorityRole.PRIMARY, ProviderScope.ARTIST, EntityKind.ARTIST),
    _rule("moods", "lastfm", AuthorityRole.SECONDARY, ProviderScope.ARTIST, EntityKind.ARTIST),
    _rule("moods", "lastfm", AuthorityRole.SECONDARY, ProviderScope.RELEASE, EntityKind.RELEASE),
    _rule("lyrics_languages", "musicbrainz", AuthorityRole.PRIMARY, ProviderScope.TRACK),
    _rule("artist_countries", "musicbrainz", AuthorityRole.PRIMARY, ProviderScope.ARTIST),
    _rule("artist_areas", "musicbrainz", AuthorityRole.PRIMARY, ProviderScope.ARTIST),
    # LRCLIB is the current lyrics source; artwork/AcoustID are separate domains.
    _rule("lyrics", "lrclib", AuthorityRole.PRIMARY, ProviderScope.TRACK),
    _rule("synced_lyrics", "lrclib", AuthorityRole.PRIMARY, ProviderScope.TRACK),
)


def _validate_capabilities(rules: tuple[AuthorityRule, ...]) -> None:
    for authority in rules:
        key = (
            authority.provider,
            authority.field,
            authority.asserted_entity,
            authority.acquisition_scope,
        )
        if key not in BUILTIN_PROVIDER_CAPABILITY_REGISTRY:
            raise ValueError(f"authority has no registered provider capability: {key!r}")


_validate_capabilities(_RULES)
AUTHORITY_MATRIX = AuthorityMatrix(_RULES)
