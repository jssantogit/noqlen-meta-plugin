import math

import pytest

from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.genre_resolution import GenreSettings, resolve_genres
from beetsplug.noqlenmeta.providers.specs import ProviderScope


def ev(
    name: str,
    provider: str,
    scope: ProviderScope,
    kind: GenreEvidenceKind = GenreEvidenceKind.GENRE,
    confidence: float = 0.9,
    weight: int | None = None,
) -> GenreEvidence:
    return GenreEvidence(
        name,
        provider,
        scope,
        kind,
        confidence,
        "synthetic",
        weight=weight,
    )


def test_genre_settings_default_to_one_genre_and_style_promotion() -> None:
    settings = GenreSettings()
    assert settings.num_genres == 1
    assert settings.promote_styles is True


@pytest.mark.parametrize("num_genres", [0, 11, True])
def test_genre_settings_reject_invalid_output_count(num_genres: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        GenreSettings(num_genres=num_genres)  # type: ignore[arg-type]


def test_genre_evidence_validates_provenance_and_native_weight() -> None:
    with pytest.raises(ValueError, match="provider"):
        ev("Rock", "", ProviderScope.RELEASE)
    with pytest.raises(ValueError, match="source"):
        GenreEvidence(
            "Rock", "discogs", ProviderScope.RELEASE, GenreEvidenceKind.GENRE, 0.9, ""
        )
    for confidence in (-0.1, 1.1, math.inf, math.nan, True):
        with pytest.raises(ValueError, match="confidence"):
            ev("Rock", "discogs", ProviderScope.RELEASE, confidence=confidence)  # type: ignore[arg-type]
    for weight in (-1, 101, 1.5, True):
        with pytest.raises(ValueError, match="weight"):
            ev("Rock", "discogs", ProviderScope.RELEASE, weight=weight)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="scope"):
        ev("Rock", "discogs", "release")  # type: ignore[arg-type]


def test_reliable_track_scope_beats_release_and_artist() -> None:
    result = resolve_genres(
        (
            ev("Drum and Bass", "musicbrainz", ProviderScope.TRACK),
            ev("K-pop", "musicbrainz", ProviderScope.ARTIST),
            ev("K-pop", "discogs", ProviderScope.RELEASE),
        ),
        settings=GenreSettings(),
    )
    assert result.genres == ("Drum and Bass",)


def test_weak_track_evidence_is_filtered_before_scope_preference() -> None:
    result = resolve_genres(
        (
            ev(
                "Experimental",
                "lastfm",
                ProviderScope.TRACK,
                GenreEvidenceKind.COMMUNITY_TAG,
                confidence=0.4,
                weight=11,
            ),
            ev("K-pop", "musicbrainz", ProviderScope.RELEASE, confidence=0.95),
            ev("K-pop", "discogs", ProviderScope.RELEASE, confidence=0.92),
        ),
        settings=GenreSettings(),
        min_confidence=0.8,
    )
    assert result.genres == ("K-pop",)


def test_specific_promoted_style_beats_broad_discogs_genre() -> None:
    result = resolve_genres(
        (
            ev("Rock", "discogs", ProviderScope.RELEASE),
            ev(
                "Technical Death Metal",
                "discogs",
                ProviderScope.RELEASE,
                GenreEvidenceKind.PROMOTED_STYLE,
            ),
        ),
        settings=GenreSettings(),
    )
    assert result.genres == ("Technical Death Metal",)


def test_distinct_provider_consensus_beats_fewer_providers() -> None:
    result = resolve_genres(
        (
            ev("K-pop", "musicbrainz", ProviderScope.RELEASE),
            ev("K-pop", "discogs", ProviderScope.RELEASE),
            ev("K-pop", "lastfm", ProviderScope.RELEASE),
            ev("Pop", "itunes", ProviderScope.RELEASE),
        ),
        settings=GenreSettings(),
    )
    assert result.genres == ("K-pop",)


def test_rows_from_one_provider_do_not_create_false_consensus() -> None:
    result = resolve_genres(
        (
            ev("Rock", "musicbrainz", ProviderScope.RELEASE, confidence=0.99),
            ev("Rock", "musicbrainz", ProviderScope.RELEASE, confidence=0.98),
            ev("Rock", "musicbrainz", ProviderScope.RELEASE, confidence=0.97),
            ev("K-pop", "discogs", ProviderScope.RELEASE, confidence=0.9),
            ev("K-pop", "itunes", ProviderScope.RELEASE, confidence=0.9),
        ),
        settings=GenreSettings(),
    )
    assert result.genres == ("K-pop",)


def test_direct_and_promoted_discogs_rows_remain_one_provider() -> None:
    result = resolve_genres(
        (
            ev("Progressive Metal", "discogs", ProviderScope.RELEASE),
            ev(
                "Progressive Metal",
                "discogs",
                ProviderScope.RELEASE,
                GenreEvidenceKind.PROMOTED_STYLE,
            ),
            ev("K-pop", "musicbrainz", ProviderScope.RELEASE),
            ev("K-pop", "itunes", ProviderScope.RELEASE),
        ),
        settings=GenreSettings(),
    )
    assert result.genres == ("K-pop",)


def test_community_tag_is_weaker_in_equivalent_conditions() -> None:
    result = resolve_genres(
        (
            ev("Rock", "lastfm", ProviderScope.RELEASE, GenreEvidenceKind.COMMUNITY_TAG),
            ev("K-pop", "lastfm", ProviderScope.RELEASE),
        ),
        settings=GenreSettings(),
    )
    assert result.genres == ("K-pop",)


def test_multiple_results_are_independently_evidenced_without_parent_expansion() -> None:
    result = resolve_genres(
        (
            ev("Technical Death Metal", "discogs", ProviderScope.RELEASE),
            ev("Progressive Metal", "musicbrainz", ProviderScope.RELEASE),
            ev("Melodic Death Metal", "itunes", ProviderScope.RELEASE),
        ),
        settings=GenreSettings(num_genres=3),
    )
    assert set(result.genres) == {
        "Technical Death Metal",
        "Progressive Metal",
        "Melodic Death Metal",
    }
    assert "Metal" not in result.genres


def test_aliases_and_duplicate_evidence_collapse_stably() -> None:
    evidence = (
        ev("dnb", "lastfm", ProviderScope.RELEASE, weight=80),
        ev("Drum and Bass", "lastfm", ProviderScope.RELEASE, weight=70),
        ev("K-pop", "discogs", ProviderScope.RELEASE),
        ev("kpop", "discogs", ProviderScope.RELEASE),
    )
    first = resolve_genres(evidence, settings=GenreSettings(num_genres=2))
    second = resolve_genres(evidence, settings=GenreSettings(num_genres=2))
    assert first == second
    assert first.genres == ("Drum and Bass", "K-pop")
    assert len(first.evidence) == 2


def test_noise_and_non_genres_never_survive() -> None:
    result = resolve_genres(
        (
            ev("Energetic", "lastfm", ProviderScope.RELEASE),
            ev("Korean", "lastfm", ProviderScope.RELEASE),
            ev("2024", "lastfm", ProviderScope.RELEASE),
        ),
        settings=GenreSettings(num_genres=3),
    )
    assert result.genres == ()
    assert result.evidence == ()
