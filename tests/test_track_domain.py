from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.domain import (
    ExternalIdentifier,
    TrackEnrichmentContext,
    canonical_isrc,
)


def test_track_context_contains_trimmed_required_identity() -> None:
    context = TrackEnrichmentContext(" Gojira ", " Flying Whales ")

    assert context.artist == "Gojira"
    assert context.title == "Flying Whales"


@pytest.mark.parametrize("field", ["artist", "title"])
@pytest.mark.parametrize("value", ["", " ", None, 12])
def test_track_context_rejects_invalid_required_identity(field: str, value: object) -> None:
    values: dict[str, object] = {"artist": "Gojira", "title": "Flying Whales"}
    values[field] = value

    with pytest.raises(ValueError, match="non-empty string"):
        TrackEnrichmentContext(**values)  # type: ignore[arg-type]


def test_track_context_accepts_optional_album_title() -> None:
    assert TrackEnrichmentContext("Gojira", "Flying Whales").album_title is None
    assert (
        TrackEnrichmentContext(
            "Gojira", "Flying Whales", album_title=" From Mars to Sirius "
        ).album_title
        == "From Mars to Sirius"
    )


def test_track_context_rejects_blank_explicit_album_title() -> None:
    with pytest.raises(ValueError, match="album title"):
        TrackEnrichmentContext("Gojira", "Flying Whales", album_title=" ")


@pytest.mark.parametrize(("value", "expected"), [(248, 248.0), (248.42, 248.42)])
def test_track_context_normalizes_positive_duration(value: object, expected: float) -> None:
    context = TrackEnrichmentContext("Gojira", "Flying Whales", duration=value)  # type: ignore[arg-type]

    assert context.duration == expected
    assert isinstance(context.duration, float)


@pytest.mark.parametrize(
    "value", [0, -1, float("nan"), float("inf"), True, "248"]
)
def test_track_context_rejects_invalid_duration(value: object) -> None:
    with pytest.raises(ValueError, match="duration"):
        TrackEnrichmentContext("Gojira", "Flying Whales", duration=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["track_number", "disc_number"])
@pytest.mark.parametrize("value", [1, 2, 15])
def test_track_context_accepts_positive_numbering(field: str, value: int) -> None:
    context = TrackEnrichmentContext("Gojira", "Flying Whales", **{field: value})

    assert getattr(context, field) == value


@pytest.mark.parametrize("field", ["track_number", "disc_number"])
@pytest.mark.parametrize("value", [0, -1, True, 1.0, "1"])
def test_track_context_rejects_invalid_numbering(field: str, value: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        TrackEnrichmentContext(
            "Gojira", "Flying Whales", **{field: value}  # type: ignore[arg-type]
        )


def test_track_context_validates_and_freezes_external_ids() -> None:
    identifier = ExternalIdentifier("isrc", "USABC1201234")
    identifiers = [identifier]
    context = TrackEnrichmentContext(
        "Gojira", "Flying Whales", external_ids=identifiers  # type: ignore[arg-type]
    )
    identifiers.clear()

    assert context.external_ids == (identifier,)
    with pytest.raises(FrozenInstanceError):
        context.title = "Changed"  # type: ignore[misc]
    with pytest.raises(TypeError, match="ExternalIdentifier"):
        TrackEnrichmentContext(
            "Gojira", "Flying Whales", external_ids=("USABC1201234",)  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "value", ["USABC1201234", "US-ABC-12-01234", "usabc1201234"]
)
def test_canonical_isrc_accepts_normal_representations(value: str) -> None:
    assert canonical_isrc(value) == "USABC1201234"


@pytest.mark.parametrize(
    "value",
    [
        "USABC120123",
        "1SABC1201234",
        "USAB!1201234",
        "USABC1A01234",
        "USABC120123A",
        "US_ABC_12_01234",
        "US--ABC-12-01234",
        None,
        123,
    ],
)
def test_canonical_isrc_rejects_malformed_values(value: object) -> None:
    assert canonical_isrc(value) is None
