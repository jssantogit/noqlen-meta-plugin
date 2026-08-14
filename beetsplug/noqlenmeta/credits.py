"""Canonical structured musical credits and artist-credit sequences."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from beetsplug.noqlenmeta.domain import canonical_uuid
from beetsplug.noqlenmeta.field_contracts import EntityKind


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string or None")
    return value.strip() or None


class CreditRole(Enum):
    COMPOSER = "composer"
    LYRICIST = "lyricist"
    PRODUCER = "producer"
    ARRANGER = "arranger"
    CONDUCTOR = "conductor"
    PERFORMER = "performer"
    FEATURED_ARTIST = "featured_artist"
    GUEST_ARTIST = "guest_artist"


_WORK_RECORDING_ROLES = frozenset(
    {CreditRole.COMPOSER, CreditRole.LYRICIST, CreditRole.ARRANGER}
)
_RELEASE_RECORDING_ROLES = frozenset(
    {
        CreditRole.PRODUCER,
        CreditRole.CONDUCTOR,
        CreditRole.PERFORMER,
        CreditRole.FEATURED_ARTIST,
        CreditRole.GUEST_ARTIST,
    }
)


@dataclass(frozen=True, slots=True)
class CreditParty:
    name: str
    mbid: str | None = None
    credited_as: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "party name"))
        if self.mbid is not None:
            mbid = canonical_uuid(self.mbid)
            if mbid is None:
                raise ValueError("party MBID must be a UUID")
            object.__setattr__(self, "mbid", mbid)
        object.__setattr__(
            self,
            "credited_as",
            _optional_text(self.credited_as, "credited-as name"),
        )


@dataclass(frozen=True, slots=True)
class CreditReference:
    party: CreditParty
    role: CreditRole
    scope: EntityKind
    instrument: str | None = None
    relation_type: str | None = None
    relation_type_id: str | None = None
    source_entity_id: str | None = None
    attributes: tuple[str, ...] = ()
    direction: str | None = None
    ordering_key: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.party, CreditParty):
            raise TypeError("party must be a CreditParty")
        if not isinstance(self.role, CreditRole):
            raise TypeError("role must be a CreditRole")
        if not isinstance(self.scope, EntityKind):
            raise TypeError("scope must be an EntityKind")
        allowed = (
            frozenset({EntityKind.WORK, EntityKind.RECORDING})
            if self.role in _WORK_RECORDING_ROLES
            else frozenset({EntityKind.RELEASE, EntityKind.RECORDING})
            if self.role in _RELEASE_RECORDING_ROLES
            else frozenset()
        )
        if self.scope not in allowed:
            raise ValueError("credit scope is not allowed for the role")
        instrument = _optional_text(self.instrument, "instrument")
        if instrument is not None and self.role is not CreditRole.PERFORMER:
            raise ValueError("instrument is meaningful only for performer credits")
        object.__setattr__(self, "instrument", instrument)
        object.__setattr__(
            self,
            "relation_type",
            _optional_text(self.relation_type, "relation type"),
        )
        if self.relation_type_id is not None:
            relation_type_id = canonical_uuid(self.relation_type_id)
            if relation_type_id is None:
                raise ValueError("relation type ID must be a UUID")
            object.__setattr__(self, "relation_type_id", relation_type_id)
        object.__setattr__(
            self,
            "source_entity_id",
            _optional_text(self.source_entity_id, "source entity ID"),
        )
        if isinstance(self.attributes, str):
            raise TypeError("attributes must be a collection of strings")
        object.__setattr__(
            self,
            "attributes",
            tuple(_text(value, "relation attribute") for value in self.attributes),
        )
        object.__setattr__(
            self,
            "direction",
            _optional_text(self.direction, "relation direction"),
        )
        if self.ordering_key is not None and (
            isinstance(self.ordering_key, bool)
            or not isinstance(self.ordering_key, int)
            or self.ordering_key < 0
        ):
            raise ValueError("ordering key must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ArtistCreditNode:
    artist_mbid: str
    canonical_name: str
    credited_name: str
    join_phrase: str
    position: int

    def __post_init__(self) -> None:
        artist_mbid = canonical_uuid(self.artist_mbid)
        if artist_mbid is None:
            raise ValueError("artist-credit MBID must be a UUID")
        object.__setattr__(self, "artist_mbid", artist_mbid)
        object.__setattr__(self, "canonical_name", _text(self.canonical_name, "canonical name"))
        object.__setattr__(self, "credited_name", _text(self.credited_name, "credited name"))
        if not isinstance(self.join_phrase, str):
            raise ValueError("join phrase must be a string")
        if (
            isinstance(self.position, bool)
            or not isinstance(self.position, int)
            or self.position < 0
        ):
            raise ValueError("artist-credit position must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ArtistCredit:
    scope: EntityKind
    nodes: tuple[ArtistCreditNode, ...]
    source_entity_id: str | None = None

    def __post_init__(self) -> None:
        if self.scope not in {EntityKind.RECORDING, EntityKind.RELEASE}:
            raise ValueError("artist-credit scope must be Recording or Release")
        nodes = tuple(self.nodes)
        if not nodes or not all(isinstance(node, ArtistCreditNode) for node in nodes):
            raise ValueError("artist credit requires nodes")
        if tuple(node.position for node in nodes) != tuple(range(len(nodes))):
            raise ValueError("artist-credit positions must be contiguous and ordered")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(
            self,
            "source_entity_id",
            _optional_text(self.source_entity_id, "source entity ID"),
        )


def canonical_credit_references(
    values: Iterable[CreditReference],
) -> tuple[CreditReference, ...]:
    """Return deterministic structurally deduplicated credit relations."""
    references = tuple(values)
    if not all(isinstance(value, CreditReference) for value in references):
        raise TypeError("credit references must contain CreditReference values")
    unique: dict[tuple[object, ...], CreditReference] = {}
    for reference in sorted(references, key=_credit_sort_key):
        unique.setdefault(_credit_identity(reference), reference)
    return tuple(sorted(unique.values(), key=_credit_sort_key))


def _party_identity(party: CreditParty) -> tuple[str, str]:
    return ("mbid", party.mbid) if party.mbid is not None else ("name", party.name)


def _credit_identity(reference: CreditReference) -> tuple[object, ...]:
    return (
        _party_identity(reference.party),
        reference.role.value,
        reference.scope.value,
        reference.instrument or "",
        reference.relation_type_id or "",
        reference.relation_type or "",
        reference.source_entity_id or "",
    )


def _credit_sort_key(reference: CreditReference) -> tuple[object, ...]:
    return (
        reference.ordering_key is None,
        reference.ordering_key if reference.ordering_key is not None else 0,
        reference.role.value,
        _party_identity(reference.party),
        reference.instrument or "",
        reference.relation_type_id or "",
        reference.relation_type or "",
        reference.party.credited_as or "",
        reference.attributes,
        reference.direction or "",
    )
