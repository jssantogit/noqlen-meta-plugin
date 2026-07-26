from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.domain import (
    ExternalIdentifier,
    MetadataCandidate,
    ReleaseEnrichmentContext,
)


def test_release_context_contains_album_identity_and_search_hints() -> None:
    context = ReleaseEnrichmentContext(
        album_artist="Synthetic Artist",
        album_title="Synthetic Album",
        year=2024,
        barcode="000000000000",
        catalog_number="CAT-001",
    )

    assert context.album_artist == "Synthetic Artist"
    assert context.album_title == "Synthetic Album"
    assert context.year == 2024
    assert context.barcode == "000000000000"
    assert context.catalog_number == "CAT-001"


def test_release_context_uses_generic_external_identifiers() -> None:
    identifier = ExternalIdentifier("musicbrainz.release", "release-001")
    context = ReleaseEnrichmentContext(
        album_artist="Synthetic Artist",
        album_title="Synthetic Album",
        external_ids=(identifier,),
    )

    assert context.external_ids == (identifier,)


def test_release_context_is_immutable() -> None:
    context = ReleaseEnrichmentContext("Synthetic Artist", "Synthetic Album")

    with pytest.raises(FrozenInstanceError):
        context.album_title = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize("value", ["Synthetic Label", 42, 4.5, True])
def test_candidate_accepts_scalar_values(value: str | int | float | bool) -> None:
    candidate = MetadataCandidate(
        field="label",
        value=value,
        provider="catalog",
        confidence=0.75,
        source_id="release-001",
    )

    assert candidate.value == value


def test_candidate_preserves_multi_value_metadata() -> None:
    candidate = MetadataCandidate(
        field="genres",
        value=("Electronic", "Ambient"),
        provider="catalog",
        confidence=0.9,
        source_id="release-001",
        source_url="https://catalog.invalid/releases/release-001",
    )

    assert candidate.value == ("Electronic", "Ambient")


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_candidate_accepts_confidence_boundaries(confidence: float) -> None:
    candidate = MetadataCandidate("label", "Synthetic Label", "catalog", confidence, "id-1")

    assert candidate.confidence == confidence


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("inf"), float("nan"), True])
def test_candidate_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        MetadataCandidate("label", "Synthetic Label", "catalog", confidence, "id-1")


@pytest.mark.parametrize(
    ("field", "provider"),
    [("", "catalog"), ("label", "")],
)
def test_candidate_rejects_empty_field_or_provider(field: str, provider: str) -> None:
    with pytest.raises(ValueError):
        MetadataCandidate(field, "Synthetic Label", provider, 0.5, "id-1")


@pytest.mark.parametrize("value", [(), [], {"genre": "Ambient"}, float("inf")])
def test_candidate_rejects_malformed_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        MetadataCandidate("genres", value, "catalog", 0.5, "id-1")  # type: ignore[arg-type]
