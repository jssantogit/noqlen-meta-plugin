from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.field_contracts import EntityKind, field_contract
from beetsplug.noqlenmeta.providers.specs import (
    BUILTIN_ARTIST_PROVIDER_SPECS,
    BUILTIN_PROVIDER_CAPABILITIES,
    BUILTIN_PROVIDER_NAMES,
    BUILTIN_PROVIDER_SPECS,
    BUILTIN_RELEASE_PROVIDER_SPECS,
    BUILTIN_TRACK_PROVIDER_SPECS,
    CREDIT_PROVIDER_CAPABILITIES,
    CREDIT_PROVIDER_CAPABILITY_REGISTRY,
    DISCOGS_SPEC,
    ITUNES_SPEC,
    LASTFM_ARTIST_SPEC,
    LASTFM_SPEC,
    LASTFM_TRACK_SPEC,
    LRCLIB_SPEC,
    MUSICBRAINZ_ARTIST_SPEC,
    MUSICBRAINZ_SPEC,
    MUSICBRAINZ_TRACK_SPEC,
    RELEASE_CATALOG_PROVIDER_CAPABILITIES,
    RELEASE_CATALOG_PROVIDER_CAPABILITY_REGISTRY,
    AcquisitionCharacteristic,
    IdentityPrerequisite,
    ProviderCapability,
    ProviderScope,
    ProviderSpec,
    capability_registry,
)


def test_discogs_spec_describes_exact_current_adapter_capabilities() -> None:
    assert DISCOGS_SPEC.name == "discogs"
    assert DISCOGS_SPEC.display_name == "Discogs"
    assert DISCOGS_SPEC.supported_fields == frozenset(
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
    )


def test_itunes_spec_describes_exact_current_adapter_capabilities() -> None:
    assert ITUNES_SPEC.name == "itunes"
    assert ITUNES_SPEC.display_name == "iTunes"
    assert ITUNES_SPEC.supported_fields == frozenset({"genres", "year"})


def test_musicbrainz_spec_describes_exact_current_adapter_capabilities() -> None:
    assert MUSICBRAINZ_SPEC.name == "musicbrainz"
    assert MUSICBRAINZ_SPEC.display_name == "MusicBrainz"
    assert MUSICBRAINZ_SPEC.supported_fields == frozenset(
        {
            "labels",
            "catalog_numbers",
            "barcodes",
            "country",
            "year",
            "media",
            "genres",
        }
    )


def test_lastfm_spec_describes_exact_current_adapter_capabilities() -> None:
    assert LASTFM_SPEC.name == "lastfm"
    assert LASTFM_SPEC.display_name == "Last.fm"
    assert LASTFM_SPEC.supported_fields == frozenset({"genres", "styles", "moods"})


def test_lrclib_spec_describes_exact_track_adapter_capabilities() -> None:
    assert LRCLIB_SPEC.name == "lrclib"
    assert LRCLIB_SPEC.display_name == "LRCLIB"
    assert LRCLIB_SPEC.supported_fields == frozenset({"lyrics", "synced_lyrics"})
    assert LRCLIB_SPEC.scope is ProviderScope.TRACK


def test_provider_spec_and_supported_fields_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        ITUNES_SPEC.name = "changed"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        ITUNES_SPEC.supported_fields.add("labels")  # type: ignore[attr-defined]


def test_builtin_provider_mapping_is_immutable() -> None:
    assert dict(BUILTIN_PROVIDER_SPECS) == {
        ("discogs", ProviderScope.RELEASE): DISCOGS_SPEC,
        ("musicbrainz", ProviderScope.RELEASE): MUSICBRAINZ_SPEC,
        ("musicbrainz", ProviderScope.TRACK): MUSICBRAINZ_TRACK_SPEC,
        ("musicbrainz", ProviderScope.ARTIST): MUSICBRAINZ_ARTIST_SPEC,
        ("lastfm", ProviderScope.RELEASE): LASTFM_SPEC,
        ("lastfm", ProviderScope.TRACK): LASTFM_TRACK_SPEC,
        ("lastfm", ProviderScope.ARTIST): LASTFM_ARTIST_SPEC,
        ("itunes", ProviderScope.RELEASE): ITUNES_SPEC,
        ("lrclib", ProviderScope.TRACK): LRCLIB_SPEC,
    }
    assert BUILTIN_PROVIDER_NAMES == frozenset(
        {"discogs", "musicbrainz", "lastfm", "itunes", "lrclib"}
    )
    with pytest.raises(TypeError):
        BUILTIN_PROVIDER_SPECS[("other", ProviderScope.RELEASE)] = ITUNES_SPEC  # type: ignore[index]


def test_builtin_provider_scopes_and_filtered_registries_are_explicit() -> None:
    assert dict(BUILTIN_RELEASE_PROVIDER_SPECS) == {
        "discogs": DISCOGS_SPEC,
        "musicbrainz": MUSICBRAINZ_SPEC,
        "lastfm": LASTFM_SPEC,
        "itunes": ITUNES_SPEC,
    }
    assert dict(BUILTIN_TRACK_PROVIDER_SPECS) == {
        "musicbrainz": MUSICBRAINZ_TRACK_SPEC,
        "lastfm": LASTFM_TRACK_SPEC,
        "lrclib": LRCLIB_SPEC,
    }
    assert dict(BUILTIN_ARTIST_PROVIDER_SPECS) == {
        "musicbrainz": MUSICBRAINZ_ARTIST_SPEC,
        "lastfm": LASTFM_ARTIST_SPEC,
    }
    assert ProviderScope.ARTIST.value == "artist"
    with pytest.raises(TypeError):
        BUILTIN_RELEASE_PROVIDER_SPECS["other"] = ITUNES_SPEC  # type: ignore[index]
    with pytest.raises(TypeError):
        BUILTIN_TRACK_PROVIDER_SPECS["other"] = ITUNES_SPEC  # type: ignore[index]


def test_test_only_track_provider_spec_retains_scope() -> None:
    spec = ProviderSpec("lyrics", "Lyrics", frozenset({"lyrics"}), ProviderScope.TRACK)

    assert spec.scope is ProviderScope.TRACK
    assert "lyrics" not in BUILTIN_PROVIDER_NAMES


def test_provider_registry_keys_same_provider_name_by_scope() -> None:
    artist_spec = ProviderSpec(
        "musicbrainz",
        "MusicBrainz",
        frozenset({"artist_countries"}),
        ProviderScope.ARTIST,
    )
    registry = {(spec.name, spec.scope): spec for spec in (MUSICBRAINZ_SPEC, artist_spec)}

    assert registry[("musicbrainz", ProviderScope.RELEASE)] is MUSICBRAINZ_SPEC
    assert registry[("musicbrainz", ProviderScope.ARTIST)] is artist_spec
    assert (MUSICBRAINZ_SPEC.name, ProviderScope.RELEASE) in BUILTIN_PROVIDER_SPECS


def test_semantic_multi_scope_capabilities_are_explicit() -> None:
    assert MUSICBRAINZ_TRACK_SPEC.supported_fields == frozenset(
        {
            "genres",
            "moods",
            "lyrics_languages",
            "isrcs",
            "iswcs",
            "works",
            "recording_date",
        }
    )
    assert MUSICBRAINZ_ARTIST_SPEC.supported_fields == frozenset(
        {"genres", "moods", "artist_countries", "artist_areas"}
    )
    for spec in (LASTFM_TRACK_SPEC, LASTFM_SPEC, LASTFM_ARTIST_SPEC):
        assert spec.supported_fields == frozenset({"genres", "styles", "moods"})
    assert "artist_languages" not in MUSICBRAINZ_ARTIST_SPEC.supported_fields


def test_provider_spec_rejects_arbitrary_scope_strings() -> None:
    with pytest.raises(TypeError, match="ProviderScope"):
        ProviderSpec("provider", "Provider", frozenset(), "track")  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["", " ", "not a provider", "provider!"])
def test_provider_spec_rejects_invalid_name(name: str) -> None:
    with pytest.raises(ValueError, match="provider name"):
        ProviderSpec(name, "Provider", frozenset({"genres"}))


@pytest.mark.parametrize("field", ["", " ", "not a field", "field!"])
def test_provider_spec_rejects_invalid_supported_field(field: str) -> None:
    with pytest.raises(ValueError, match="supported field"):
        ProviderSpec("provider", "Provider", frozenset({field}))


def test_provider_spec_normalizes_names_and_rejects_normalized_duplicates() -> None:
    spec = ProviderSpec(
        " Provider ",
        " Display ",
        (" Genres ", "release-year"),  # type: ignore[arg-type]
    )

    assert spec.name == "provider"
    assert spec.display_name == "Display"
    assert spec.supported_fields == frozenset({"genres", "release-year"})
    with pytest.raises(ValueError, match="unique"):
        ProviderSpec(
            "provider",
            "Provider",
            ("genres", " GENRES "),  # type: ignore[arg-type]
        )


def test_every_builtin_capability_references_registered_field_and_provider() -> None:
    for capability in BUILTIN_PROVIDER_CAPABILITIES:
        assert field_contract(capability.field)
        assert capability.provider in BUILTIN_PROVIDER_NAMES
        assert isinstance(capability.asserted_entity, EntityKind)
        assert capability.asserted_entity in field_contract(capability.field).allowed_entities
        assert isinstance(capability.acquisition_scope, ProviderScope)


def test_supported_fields_remain_exact_compatibility_views() -> None:
    for spec in BUILTIN_PROVIDER_SPECS.values():
        fields = frozenset(
            capability.field
            for capability in BUILTIN_PROVIDER_CAPABILITIES
            if capability.provider == spec.name and capability.acquisition_scope is spec.scope
        )
        assert spec.supported_fields == fields


def test_musicbrainz_capability_describes_exact_lookup_and_traversal() -> None:
    capability = next(
        capability
        for capability in BUILTIN_PROVIDER_CAPABILITIES
        if capability.provider == "musicbrainz" and capability.field == "lyrics_languages"
    )

    assert capability.asserted_entity is EntityKind.WORK
    assert capability.acquisition_scope is ProviderScope.TRACK
    assert capability.identity_prerequisites == frozenset({IdentityPrerequisite.EXACT_CANONICAL_ID})
    assert AcquisitionCharacteristic.DIRECT_LOOKUP in capability.characteristics
    assert AcquisitionCharacteristic.RESPONSE_REUSE in capability.characteristics
    assert AcquisitionCharacteristic.SUPPORTING_TRAVERSAL in capability.characteristics


@pytest.mark.parametrize(
    ("provider", "expected", "unexpected", "prerequisites"),
    [
        (
            "discogs",
            {
                AcquisitionCharacteristic.DIRECT_LOOKUP,
                AcquisitionCharacteristic.SEARCH,
                AcquisitionCharacteristic.RESPONSE_REUSE,
            },
            set(),
            {
                IdentityPrerequisite.EXACT_PROVIDER_ID,
                IdentityPrerequisite.STRUCTURALLY_VALIDATED_CONTEXT,
            },
        ),
        (
            "itunes",
            {
                AcquisitionCharacteristic.DIRECT_LOOKUP,
                AcquisitionCharacteristic.SEARCH,
                AcquisitionCharacteristic.RESPONSE_REUSE,
            },
            set(),
            {
                IdentityPrerequisite.EXACT_PROVIDER_ID,
                IdentityPrerequisite.STRUCTURALLY_VALIDATED_CONTEXT,
            },
        ),
        (
            "lastfm",
            {
                AcquisitionCharacteristic.DIRECT_LOOKUP,
                AcquisitionCharacteristic.RESPONSE_REUSE,
            },
            {AcquisitionCharacteristic.SEARCH},
            {IdentityPrerequisite.STRUCTURALLY_VALIDATED_CONTEXT},
        ),
        (
            "lrclib",
            {
                AcquisitionCharacteristic.DIRECT_LOOKUP,
                AcquisitionCharacteristic.RESPONSE_REUSE,
            },
            {AcquisitionCharacteristic.SEARCH},
            {IdentityPrerequisite.STRUCTURALLY_VALIDATED_CONTEXT},
        ),
    ],
)
def test_provider_capabilities_describe_real_acquisition_paths(
    provider: str,
    expected: set[AcquisitionCharacteristic],
    unexpected: set[AcquisitionCharacteristic],
    prerequisites: set[IdentityPrerequisite],
) -> None:
    capabilities = [
        capability
        for capability in BUILTIN_PROVIDER_CAPABILITIES
        if capability.provider == provider
    ]

    assert capabilities
    for capability in capabilities:
        assert expected <= capability.characteristics
        assert not unexpected & capability.characteristics
        assert capability.identity_prerequisites == frozenset(prerequisites)


def test_duplicate_capability_is_rejected() -> None:
    capability = ProviderCapability(
        provider="catalog",
        field="year",
        asserted_entity=EntityKind.RELEASE,
        acquisition_scope=ProviderScope.RELEASE,
        identity_prerequisites=frozenset({IdentityPrerequisite.STRUCTURALLY_VALIDATED_CONTEXT}),
        characteristics=frozenset({AcquisitionCharacteristic.SEARCH}),
    )

    with pytest.raises(ValueError, match="duplicate capability"):
        capability_registry((capability, capability))


def test_caa_and_acoustid_remain_outside_ordinary_capabilities() -> None:
    assert not {"coverartarchive", "acoustid"} & {
        capability.provider for capability in BUILTIN_PROVIDER_CAPABILITIES
    }


def test_release_catalog_capabilities_match_only_implemented_v3_methods() -> None:
    assert {
        (capability.provider, capability.field, capability.asserted_entity)
        for capability in RELEASE_CATALOG_PROVIDER_CAPABILITIES
    } == {
        ("musicbrainz", "date", EntityKind.RELEASE),
        ("musicbrainz", "original_date", EntityKind.RELEASE_GROUP),
        ("musicbrainz", "release_type", EntityKind.RELEASE_GROUP),
        ("musicbrainz", "release_secondary_types", EntityKind.RELEASE_GROUP),
        ("musicbrainz", "release_status", EntityKind.RELEASE),
        ("discogs", "date", EntityKind.RELEASE),
        ("discogs", "edition", EntityKind.RELEASE),
        ("itunes", "date", EntityKind.RELEASE),
    }
    assert "original_year" not in {
        capability.field for capability in RELEASE_CATALOG_PROVIDER_CAPABILITIES
    }
    assert len(RELEASE_CATALOG_PROVIDER_CAPABILITY_REGISTRY) == len(
        RELEASE_CATALOG_PROVIDER_CAPABILITIES
    )
    release_group = [
        capability
        for capability in RELEASE_CATALOG_PROVIDER_CAPABILITIES
        if capability.provider == "musicbrainz"
        and capability.asserted_entity is EntityKind.RELEASE_GROUP
    ]
    assert release_group
    assert all(
        AcquisitionCharacteristic.SUPPORTING_TRAVERSAL in capability.characteristics
        for capability in release_group
    )


def test_credit_capabilities_match_implemented_musicbrainz_scopes() -> None:
    actual = {
        (capability.provider, capability.field, capability.asserted_entity)
        for capability in CREDIT_PROVIDER_CAPABILITIES
    }
    assert actual == {
        ("musicbrainz", "composers", EntityKind.WORK),
        ("musicbrainz", "lyricists", EntityKind.WORK),
        ("musicbrainz", "arrangers", EntityKind.WORK),
        ("musicbrainz", "arrangers", EntityKind.RECORDING),
        ("musicbrainz", "producers", EntityKind.RECORDING),
        ("musicbrainz", "conductors", EntityKind.RECORDING),
        ("musicbrainz", "performers", EntityKind.RECORDING),
        ("musicbrainz", "featured_artists", EntityKind.RECORDING),
        ("musicbrainz", "structured_artist_credits", EntityKind.RECORDING),
        ("musicbrainz", "producers", EntityKind.RELEASE),
        ("musicbrainz", "conductors", EntityKind.RELEASE),
        ("musicbrainz", "performers", EntityKind.RELEASE),
        ("musicbrainz", "featured_artists", EntityKind.RELEASE),
        ("musicbrainz", "structured_artist_credits", EntityKind.RELEASE),
    }
    assert len(CREDIT_PROVIDER_CAPABILITY_REGISTRY) == len(CREDIT_PROVIDER_CAPABILITIES)


def test_capability_rejects_entity_outside_field_contract() -> None:
    with pytest.raises(ValueError, match="allowed entities"):
        ProviderCapability(
            provider="catalog",
            field="isrcs",
            asserted_entity=EntityKind.RELEASE,
            acquisition_scope=ProviderScope.RELEASE,
            identity_prerequisites=frozenset({IdentityPrerequisite.STRUCTURALLY_VALIDATED_CONTEXT}),
        )
