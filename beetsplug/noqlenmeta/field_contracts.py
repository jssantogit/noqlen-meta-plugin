"""Intrinsic canonical field contracts for Noqlen Meta metadata."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from beetsplug.noqlenmeta.domain import ExternalIdentifier


class EntityKind(Enum):
    RELEASE = "release"
    RELEASE_GROUP = "release_group"
    MEDIUM = "medium"
    RECORDING = "recording"
    WORK = "work"
    ARTIST = "artist"


class Cardinality(Enum):
    OPTIONAL_ONE = "optional_one"
    ZERO_OR_MANY = "zero_or_many"


class ResolverKind(Enum):
    EXCLUSIVE = "exclusive"
    MULTIVALUE = "multivalue"
    TAXONOMIC = "taxonomic"
    STRUCTURED = "structured"
    LYRICS = "lyrics"
    ARTWORK = "artwork"
    AUDIO = "audio"


class TargetClass(Enum):
    NATIVE_BEETS = "native_beets"
    TYPED_DB = "typed_db"
    SIDECAR = "sidecar"
    ASSET = "asset"
    INTERNAL = "internal"


def _canonical_name(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip().lower():
        raise ValueError(f"{label} must be a canonical non-empty name")
    if not value.replace("_", "").isalnum():
        raise ValueError(f"{label} contains invalid characters")
    return value


@dataclass(frozen=True, slots=True)
class PartialDate:
    """A calendar date that preserves annual, monthly, or daily precision."""

    year: int
    month: int | None = None
    day: int | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.year, bool)
            or not isinstance(self.year, int)
            or not 1 <= self.year <= 9999
        ):
            raise ValueError("year must be an integer between 1 and 9999")
        if self.month is not None and (
            isinstance(self.month, bool)
            or not isinstance(self.month, int)
            or not 1 <= self.month <= 12
        ):
            raise ValueError("month must be an integer between 1 and 12")
        if self.day is not None and self.month is None:
            raise ValueError("day cannot exist without month")
        if self.day is not None:
            if isinstance(self.day, bool) or not isinstance(self.day, int):
                raise ValueError("day must form a valid calendar date")
            if not 1 <= self.day <= monthrange(self.year, self.month)[1]:
                raise ValueError("day must form a valid calendar date")


@dataclass(frozen=True, slots=True)
class IdentifierCollection:
    """A lossless ordered collection of typed external identifiers."""

    values: tuple[ExternalIdentifier, ...]

    def __post_init__(self) -> None:
        values = tuple(self.values)
        if not all(isinstance(value, ExternalIdentifier) for value in values):
            raise TypeError("values must contain ExternalIdentifier instances")
        if len(values) != len(set(values)):
            raise ValueError("identifier values must be unique")
        object.__setattr__(self, "values", values)


@dataclass(frozen=True, slots=True)
class FieldContract:
    """Provider-independent facts intrinsic to one canonical field."""

    canonical_name: str
    aliases: tuple[str, ...]
    allowed_entities: frozenset[EntityKind]
    cardinality: Cardinality
    resolver_kind: ResolverKind
    target_classes: frozenset[TargetClass]
    legacy: bool = False
    default_enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "canonical_name",
            _canonical_name(self.canonical_name, "canonical field name"),
        )
        if isinstance(self.aliases, str):
            raise TypeError("aliases must be a collection of field names")
        aliases = tuple(_canonical_name(alias, "field alias") for alias in self.aliases)
        if len(aliases) != len(set(aliases)):
            raise ValueError("field aliases must be unique")
        if self.canonical_name in aliases:
            raise ValueError("canonical field name cannot also be an alias")
        object.__setattr__(self, "aliases", aliases)
        entities = frozenset(self.allowed_entities)
        if not entities or not all(isinstance(entity, EntityKind) for entity in entities):
            raise TypeError("allowed_entities must contain EntityKind values")
        object.__setattr__(self, "allowed_entities", entities)
        if not isinstance(self.cardinality, Cardinality):
            raise TypeError("cardinality must be a Cardinality")
        if not isinstance(self.resolver_kind, ResolverKind):
            raise TypeError("resolver_kind must be a ResolverKind")
        targets = frozenset(self.target_classes)
        if not targets or not all(isinstance(target, TargetClass) for target in targets):
            raise TypeError("target_classes must contain TargetClass values")
        object.__setattr__(self, "target_classes", targets)
        if not isinstance(self.legacy, bool) or not isinstance(self.default_enabled, bool):
            raise TypeError("legacy and default_enabled must be booleans")


def _field(
    name: str,
    entities: EntityKind | frozenset[EntityKind],
    cardinality: Cardinality,
    resolver: ResolverKind,
    *targets: TargetClass,
    aliases: tuple[str, ...] = (),
    legacy: bool = False,
    default_enabled: bool = False,
) -> FieldContract:
    allowed_entities = (
        frozenset({entities}) if isinstance(entities, EntityKind) else frozenset(entities)
    )
    return FieldContract(
        name,
        aliases,
        allowed_entities,
        cardinality,
        resolver,
        frozenset(targets),
        legacy,
        default_enabled,
    )


_ONE = Cardinality.OPTIONAL_ONE
_MANY = Cardinality.ZERO_OR_MANY
_NATIVE = TargetClass.NATIVE_BEETS
_DB = TargetClass.TYPED_DB
_INTERNAL = TargetClass.INTERNAL
_SEMANTIC_ENTITIES = frozenset({EntityKind.RECORDING, EntityKind.RELEASE, EntityKind.ARTIST})
_RELEASE_MEDIUM_ENTITIES = frozenset({EntityKind.RELEASE, EntityKind.MEDIUM})
_WORK_RECORDING_ENTITIES = frozenset({EntityKind.WORK, EntityKind.RECORDING})
_RELEASE_RECORDING_ENTITIES = frozenset({EntityKind.RELEASE, EntityKind.RECORDING})
_TITLE_ENTITIES = frozenset({EntityKind.RECORDING, EntityKind.RELEASE, EntityKind.WORK})

_CONTRACTS = (
    # V2 catalog and semantic fields.
    _field(
        "genres", _SEMANTIC_ENTITIES, _MANY, ResolverKind.TAXONOMIC, _NATIVE, default_enabled=True
    ),
    _field(
        "styles",
        _SEMANTIC_ENTITIES,
        _MANY,
        ResolverKind.TAXONOMIC,
        _DB,
        legacy=True,
        default_enabled=True,
    ),
    _field(
        "labels", EntityKind.RELEASE, _MANY, ResolverKind.MULTIVALUE, _NATIVE, default_enabled=True
    ),
    _field(
        "catalog_numbers",
        EntityKind.RELEASE,
        _MANY,
        ResolverKind.MULTIVALUE,
        _NATIVE,
        default_enabled=True,
    ),
    _field(
        "barcodes",
        EntityKind.RELEASE,
        _MANY,
        ResolverKind.MULTIVALUE,
        _NATIVE,
        default_enabled=True,
    ),
    _field(
        "country", EntityKind.RELEASE, _ONE, ResolverKind.EXCLUSIVE, _NATIVE, default_enabled=True
    ),
    _field(
        "year",
        EntityKind.RELEASE,
        _ONE,
        ResolverKind.EXCLUSIVE,
        _NATIVE,
        legacy=True,
        default_enabled=True,
    ),
    _field(
        "media",
        _RELEASE_MEDIUM_ENTITIES,
        _MANY,
        ResolverKind.MULTIVALUE,
        _NATIVE,
        default_enabled=True,
    ),
    _field(
        "format_descriptions",
        _RELEASE_MEDIUM_ENTITIES,
        _MANY,
        ResolverKind.MULTIVALUE,
        _INTERNAL,
        default_enabled=True,
    ),
    _field(
        "moods",
        _SEMANTIC_ENTITIES,
        _MANY,
        ResolverKind.TAXONOMIC,
        _DB,
        legacy=True,
        default_enabled=True,
    ),
    _field("bpm", EntityKind.RECORDING, _ONE, ResolverKind.AUDIO, _NATIVE, default_enabled=True),
    _field(
        "lyrics_languages",
        EntityKind.WORK,
        _MANY,
        ResolverKind.MULTIVALUE,
        _DB,
        legacy=True,
        default_enabled=True,
    ),
    _field(
        "artist_countries",
        EntityKind.ARTIST,
        _MANY,
        ResolverKind.MULTIVALUE,
        _DB,
        legacy=True,
        default_enabled=True,
    ),
    _field("artist_areas", EntityKind.ARTIST, _MANY, ResolverKind.MULTIVALUE, _DB, legacy=True),
    _field(
        "artist_languages",
        EntityKind.ARTIST,
        _MANY,
        ResolverKind.MULTIVALUE,
        _DB,
        legacy=True,
        default_enabled=True,
    ),
    _field("lyrics", EntityKind.RECORDING, _ONE, ResolverKind.LYRICS, _NATIVE),
    _field("synced_lyrics", EntityKind.RECORDING, _ONE, ResolverKind.LYRICS, TargetClass.SIDECAR),
    # Dates and release classification.
    _field("date", EntityKind.RELEASE, _ONE, ResolverKind.EXCLUSIVE, _NATIVE),
    _field(
        "original_date",
        EntityKind.RELEASE_GROUP,
        _ONE,
        ResolverKind.EXCLUSIVE,
        _NATIVE,
        aliases=("originaldate",),
    ),
    _field("original_year", EntityKind.RELEASE_GROUP, _ONE, ResolverKind.EXCLUSIVE, _NATIVE),
    _field("recording_date", EntityKind.RECORDING, _ONE, ResolverKind.EXCLUSIVE, _DB),
    _field("release_type", EntityKind.RELEASE_GROUP, _ONE, ResolverKind.EXCLUSIVE, _NATIVE),
    _field(
        "release_secondary_types",
        EntityKind.RELEASE_GROUP,
        _MANY,
        ResolverKind.MULTIVALUE,
        _NATIVE,
        _DB,
    ),
    _field("release_status", EntityKind.RELEASE, _ONE, ResolverKind.EXCLUSIVE, _NATIVE),
    _field("edition", EntityKind.RELEASE, _ONE, ResolverKind.EXCLUSIVE, _DB),
    # Recording and Work identity, kept outside generic identity resolution.
    _field("isrcs", EntityKind.RECORDING, _MANY, ResolverKind.MULTIVALUE, _NATIVE, _DB),
    _field("iswcs", EntityKind.WORK, _MANY, ResolverKind.MULTIVALUE, _DB),
    _field("works", EntityKind.RECORDING, _MANY, ResolverKind.STRUCTURED, _NATIVE, _INTERNAL),
    # Credits and structured title/language concepts.
    _field(
        "composers", _WORK_RECORDING_ENTITIES, _MANY, ResolverKind.STRUCTURED, _NATIVE, _INTERNAL
    ),
    _field(
        "lyricists", _WORK_RECORDING_ENTITIES, _MANY, ResolverKind.STRUCTURED, _NATIVE, _INTERNAL
    ),
    _field(
        "producers", _RELEASE_RECORDING_ENTITIES, _MANY, ResolverKind.STRUCTURED, _DB, _INTERNAL
    ),
    _field(
        "arrangers", _WORK_RECORDING_ENTITIES, _MANY, ResolverKind.STRUCTURED, _NATIVE, _INTERNAL
    ),
    _field(
        "conductors", _RELEASE_RECORDING_ENTITIES, _MANY, ResolverKind.STRUCTURED, _DB, _INTERNAL
    ),
    _field("performers", _RELEASE_RECORDING_ENTITIES, _MANY, ResolverKind.STRUCTURED, _INTERNAL),
    _field(
        "featured_artists", _RELEASE_RECORDING_ENTITIES, _MANY, ResolverKind.STRUCTURED, _INTERNAL
    ),
    _field("guest_artists", _RELEASE_RECORDING_ENTITIES, _MANY, ResolverKind.STRUCTURED, _INTERNAL),
    _field(
        "artist_credits", _RELEASE_RECORDING_ENTITIES, _MANY, ResolverKind.STRUCTURED, _INTERNAL
    ),
    _field("alternate_titles", _TITLE_ENTITIES, _MANY, ResolverKind.STRUCTURED, _INTERNAL),
    _field("language", EntityKind.RELEASE, _ONE, ResolverKind.EXCLUSIVE, _NATIVE),
    _field("script", EntityKind.RELEASE, _ONE, ResolverKind.EXCLUSIVE, _NATIVE),
    _field("transliterations", _TITLE_ENTITIES, _MANY, ResolverKind.STRUCTURED, _INTERNAL),
    _field("track_version", EntityKind.RECORDING, _ONE, ResolverKind.STRUCTURED, _DB),
    _field("vocal_languages", EntityKind.RECORDING, _MANY, ResolverKind.MULTIVALUE, _DB),
    _field("instrumental", EntityKind.RECORDING, _ONE, ResolverKind.EXCLUSIVE, _DB),
    _field("explicitness", EntityKind.RECORDING, _ONE, ResolverKind.EXCLUSIVE, _DB),
    # Assets and audio fields.
    _field(
        "front_artwork",
        EntityKind.RELEASE,
        _ONE,
        ResolverKind.ARTWORK,
        TargetClass.ASSET,
        aliases=("cover",),
        default_enabled=True,
    ),
    _field("back_artwork", EntityKind.RELEASE, _MANY, ResolverKind.ARTWORK, TargetClass.ASSET),
    _field("disc_artwork", EntityKind.MEDIUM, _MANY, ResolverKind.ARTWORK, TargetClass.ASSET),
    _field("key", EntityKind.RECORDING, _ONE, ResolverKind.AUDIO, _NATIVE),
    _field("energy", EntityKind.RECORDING, _ONE, ResolverKind.AUDIO, _DB),
    _field("danceability", EntityKind.RECORDING, _ONE, ResolverKind.AUDIO, _DB),
    _field("energy_level", EntityKind.RECORDING, _ONE, ResolverKind.AUDIO, _INTERNAL),
    _field("danceability_level", EntityKind.RECORDING, _ONE, ResolverKind.AUDIO, _INTERNAL),
    _field("tempo_range", EntityKind.RECORDING, _ONE, ResolverKind.AUDIO, _INTERNAL),
    # Opportunistic classical projections from structured relationships.
    _field("movement", EntityKind.WORK, _ONE, ResolverKind.STRUCTURED, _NATIVE),
    _field("movement_number", EntityKind.WORK, _ONE, ResolverKind.STRUCTURED, _NATIVE),
    _field("movement_total", EntityKind.WORK, _ONE, ResolverKind.STRUCTURED, _NATIVE),
    _field("ensembles", EntityKind.RECORDING, _MANY, ResolverKind.STRUCTURED, _INTERNAL),
)


def _build_registry(contracts: tuple[FieldContract, ...]) -> MappingProxyType:
    registry: dict[str, FieldContract] = {}
    aliases: set[str] = set()
    for contract in contracts:
        if contract.canonical_name in registry or contract.canonical_name in aliases:
            raise ValueError(f"duplicate canonical field: {contract.canonical_name}")
        for alias in contract.aliases:
            if alias in registry or alias in aliases:
                raise ValueError(f"duplicate field alias: {alias}")
            aliases.add(alias)
        registry[contract.canonical_name] = contract
    return MappingProxyType(registry)


FIELD_CONTRACTS = _build_registry(_CONTRACTS)
_FIELD_ALIASES = MappingProxyType(
    {
        alias: contract.canonical_name
        for contract in FIELD_CONTRACTS.values()
        for alias in contract.aliases
    }
)

V2_ITEM_FLEXIBLE_FIELDS = (
    "moods",
    "lyrics_languages",
    "artist_countries",
    "artist_areas",
    "artist_languages",
)
V2_ALBUM_FLEXIBLE_FIELDS = (
    "styles",
    "artist_countries",
    "artist_areas",
    "artist_languages",
)


def field_contract(name: str) -> FieldContract:
    """Return a canonical field contract, resolving compatibility aliases."""
    normalized = _canonical_name(name, "field name")
    canonical = _FIELD_ALIASES.get(normalized, normalized)
    try:
        return FIELD_CONTRACTS[canonical]
    except KeyError as exc:
        raise KeyError(f"unknown field contract: {normalized}") from exc
