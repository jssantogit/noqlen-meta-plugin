from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.configuration import default_config
from beetsplug.noqlenmeta.domain import ExternalIdentifier
from beetsplug.noqlenmeta.field_contracts import (
    FIELD_CONTRACTS,
    Cardinality,
    EntityKind,
    FieldContract,
    IdentifierCollection,
    PartialDate,
    ResolverKind,
    TargetClass,
    field_contract,
)

V3_CORE_FIELDS = frozenset(
    {
        "date",
        "original_date",
        "original_year",
        "recording_date",
        "release_type",
        "release_secondary_types",
        "release_status",
        "edition",
        "isrcs",
        "iswcs",
        "works",
        "composers",
        "lyricists",
        "producers",
        "arrangers",
        "conductors",
        "performers",
        "featured_artists",
        "guest_artists",
        "structured_artist_credits",
        "alternate_titles",
        "language",
        "script",
        "transliterations",
        "track_version",
        "vocal_languages",
        "instrumental",
        "explicitness",
        "lyrics",
        "synced_lyrics",
        "front_artwork",
        "back_artwork",
        "disc_artwork",
        "bpm",
        "key",
        "energy",
        "danceability",
        "energy_level",
        "danceability_level",
        "tempo_range",
        "movement",
        "movement_number",
        "movement_total",
        "ensembles",
    }
)


def test_registry_names_and_aliases_are_globally_unique() -> None:
    canonical = tuple(FIELD_CONTRACTS)
    aliases = tuple(alias for contract in FIELD_CONTRACTS.values() for alias in contract.aliases)

    assert len(canonical) == len(set(canonical))
    assert len(aliases) == len(set(aliases))
    assert not set(canonical) & set(aliases)
    assert field_contract("cover") is FIELD_CONTRACTS["front_artwork"]


def test_contracts_have_typed_entity_cardinality_resolver_and_targets() -> None:
    for name, contract in FIELD_CONTRACTS.items():
        assert contract.canonical_name == name
        assert contract.allowed_entities
        assert all(isinstance(entity, EntityKind) for entity in contract.allowed_entities)
        assert isinstance(contract.cardinality, Cardinality)
        assert isinstance(contract.resolver_kind, ResolverKind)
        assert contract.target_classes
        assert all(isinstance(target, TargetClass) for target in contract.target_classes)


def test_field_contract_is_immutable_and_rejects_invalid_types() -> None:
    contract = FIELD_CONTRACTS["genres"]
    with pytest.raises(FrozenInstanceError):
        contract.canonical_name = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError, match="EntityKind"):
        FieldContract(
            "invalid",
            (),
            frozenset({"release"}),  # type: ignore[arg-type]
            Cardinality.OPTIONAL_ONE,
            ResolverKind.EXCLUSIVE,
            frozenset({TargetClass.INTERNAL}),
        )


@pytest.mark.parametrize(
    ("date", "parts"),
    [
        (PartialDate(2026), (2026, None, None)),
        (PartialDate(2026, 8), (2026, 8, None)),
        (PartialDate(2024, 2, 29), (2024, 2, 29)),
    ],
)
def test_partial_date_preserves_precision(date: PartialDate, parts: tuple[object, ...]) -> None:
    assert (date.year, date.month, date.day) == parts


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ((0,), "year"),
        ((10000,), "year"),
        ((2026, 0), "month"),
        ((2026, 13), "month"),
        ((2026, None, 1), "without month"),
        ((2023, 2, 29), "valid calendar date"),
        ((2026, 4, 31), "valid calendar date"),
    ],
)
def test_partial_date_rejects_invalid_dates(args: tuple[object, ...], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PartialDate(*args)  # type: ignore[arg-type]


def test_partial_dates_do_not_claim_order_across_different_precision() -> None:
    with pytest.raises(TypeError):
        assert PartialDate(2026) < PartialDate(2026, 1)  # type: ignore[operator]


def test_identifier_collection_is_typed_lossless_and_deduplicated() -> None:
    first = ExternalIdentifier("isrc", "USAAA2600001")
    second = ExternalIdentifier("isrc", "USAAA2600002")
    identifiers = IdentifierCollection((first, second))

    assert identifiers.values == (first, second)
    with pytest.raises(ValueError, match="unique"):
        IdentifierCollection((first, first))
    with pytest.raises(TypeError, match="ExternalIdentifier"):
        IdentifierCollection((first, {"namespace": "isrc"}))  # type: ignore[arg-type]


def test_isrc_iswc_and_work_contracts_preserve_multiplicity() -> None:
    for field in ("isrcs", "iswcs", "works"):
        assert FIELD_CONTRACTS[field].cardinality is Cardinality.ZERO_OR_MANY
    assert FIELD_CONTRACTS["isrcs"].allowed_entities == frozenset({EntityKind.RECORDING})
    assert FIELD_CONTRACTS["iswcs"].allowed_entities == frozenset({EntityKind.WORK})
    assert FIELD_CONTRACTS["works"].allowed_entities == frozenset({EntityKind.RECORDING})


@pytest.mark.parametrize(
    ("field", "entities"),
    [
        ("genres", {EntityKind.RECORDING, EntityKind.RELEASE, EntityKind.ARTIST}),
        ("styles", {EntityKind.RECORDING, EntityKind.RELEASE, EntityKind.ARTIST}),
        ("moods", {EntityKind.RECORDING, EntityKind.RELEASE, EntityKind.ARTIST}),
        ("media", {EntityKind.RELEASE, EntityKind.MEDIUM}),
        ("format_descriptions", {EntityKind.RELEASE, EntityKind.MEDIUM}),
        ("composers", {EntityKind.WORK, EntityKind.RECORDING}),
        ("lyricists", {EntityKind.WORK, EntityKind.RECORDING}),
        ("arrangers", {EntityKind.WORK, EntityKind.RECORDING}),
        ("producers", {EntityKind.RECORDING, EntityKind.RELEASE}),
        ("conductors", {EntityKind.RECORDING, EntityKind.RELEASE}),
        ("performers", {EntityKind.RECORDING, EntityKind.RELEASE}),
        ("featured_artists", {EntityKind.RECORDING, EntityKind.RELEASE}),
        ("guest_artists", {EntityKind.RECORDING, EntityKind.RELEASE}),
        ("structured_artist_credits", {EntityKind.RECORDING, EntityKind.RELEASE}),
        (
            "alternate_titles",
            {EntityKind.RECORDING, EntityKind.RELEASE, EntityKind.WORK},
        ),
        (
            "transliterations",
            {EntityKind.RECORDING, EntityKind.RELEASE, EntityKind.WORK},
        ),
    ],
)
def test_multi_entity_contracts_are_explicit(field: str, entities: set[EntityKind]) -> None:
    assert FIELD_CONTRACTS[field].allowed_entities == frozenset(entities)


@pytest.mark.parametrize(
    ("field", "entity"),
    [
        ("isrcs", EntityKind.RECORDING),
        ("iswcs", EntityKind.WORK),
        ("recording_date", EntityKind.RECORDING),
        ("edition", EntityKind.RELEASE),
        ("release_status", EntityKind.RELEASE),
    ],
)
def test_strict_entity_contracts_remain_strict(field: str, entity: EntityKind) -> None:
    assert FIELD_CONTRACTS[field].allowed_entities == frozenset({entity})


def test_all_public_v2_fields_resolve_to_registered_concepts() -> None:
    for field in default_config()["fields"]:
        assert field_contract(field)
    assert field_contract("lyrics_languages") is not field_contract("vocal_languages")
    assert field_contract("year") is not field_contract("date")
    assert field_contract("originaldate") is field_contract("original_date")


def test_public_v2_field_defaults_match_contracts_through_aliases() -> None:
    for field, enabled in default_config()["fields"].items():
        assert field_contract(field).default_enabled is enabled


def test_all_v3_core_concepts_are_registered() -> None:
    assert not V3_CORE_FIELDS - FIELD_CONTRACTS.keys()


def test_recording_date_is_db_only_and_future_fields_do_not_gain_audio_tags() -> None:
    assert FIELD_CONTRACTS["recording_date"].target_classes == frozenset({TargetClass.TYPED_DB})
    for field in ("iswcs", "energy", "danceability"):
        assert TargetClass.NATIVE_BEETS not in FIELD_CONTRACTS[field].target_classes
