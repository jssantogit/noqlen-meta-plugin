from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.providers.specs import (
    BUILTIN_PROVIDER_SPECS,
    DISCOGS_SPEC,
    ITUNES_SPEC,
    MUSICBRAINZ_SPEC,
    ProviderSpec,
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
        {"labels", "catalog_numbers", "barcodes", "country", "year", "media"}
    )


def test_provider_spec_and_supported_fields_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        ITUNES_SPEC.name = "changed"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        ITUNES_SPEC.supported_fields.add("labels")  # type: ignore[attr-defined]


def test_builtin_provider_mapping_is_immutable() -> None:
    assert dict(BUILTIN_PROVIDER_SPECS) == {
        "discogs": DISCOGS_SPEC,
        "musicbrainz": MUSICBRAINZ_SPEC,
        "itunes": ITUNES_SPEC,
    }
    with pytest.raises(TypeError):
        BUILTIN_PROVIDER_SPECS["other"] = ITUNES_SPEC  # type: ignore[index]


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
