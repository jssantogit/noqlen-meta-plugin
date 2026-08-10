import inspect

from requests import RequestException

from beetsplug.noqlenmeta.domain import (
    MetadataCandidate,
    SemanticCategory,
    SemanticEvidenceBundle,
    SemanticTagEvidence,
)
from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.genre_resolution import GenreSettings
from beetsplug.noqlenmeta.providers import ProviderError
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.semantic_enrichment import (
    SemanticFieldStatus,
    collect_semantic_enrichment,
    derive_artist_languages,
)


def bundle(
    *,
    scope: ProviderScope = ProviderScope.TRACK,
    genres: tuple[str, ...] = (),
    moods: tuple[str, ...] = (),
    metadata: tuple[MetadataCandidate, ...] = (),
    provider: str = "musicbrainz",
) -> SemanticEvidenceBundle:
    genre_rows = tuple(
        GenreEvidence(
            value,
            provider,
            scope,
            GenreEvidenceKind.GENRE,
            0.95,
            f"{scope.value}-id",
        )
        for value in genres
    )
    mood_rows = tuple(
        SemanticTagEvidence(
            value,
            SemanticCategory.MOOD,
            provider,
            scope,
            0.9,
            f"{scope.value}-id",
            None,
            8,
            value.casefold(),
        )
        for value in moods
    )
    return SemanticEvidenceBundle(metadata, genre_rows, mood_rows)


def test_derive_artist_languages_uses_only_current_target_rows() -> None:
    assert derive_artist_languages(
        ((1, ("kor",)), (1, ("kor", "eng")), (2, ("jpn",)))
    ) == ("kor", "eng", "jpn")


def test_field_gating_avoids_work_only_collector_and_write_is_not_an_input() -> None:
    calls = []

    result = collect_semantic_enrichment(
        {"genres"},
        musicbrainz_release=lambda: calls.append("release") or bundle(
            scope=ProviderScope.RELEASE, genres=("K-pop",)
        ),
        musicbrainz_tracks=(lambda: calls.append("track") or bundle(),),
    )

    assert calls == ["release", "track"]
    assert "lyrics_languages" not in result.outcomes
    assert "write" not in inspect.signature(collect_semantic_enrichment).parameters


def test_musicbrainz_only_resolves_all_zero_config_semantics() -> None:
    track_metadata = (
        MetadataCandidate(
            "lyrics_languages", ("kor", "eng"), "musicbrainz", 0.99, "recording"
        ),
    )
    artist_metadata = (
        MetadataCandidate(
            "artist_areas", ("Salvador",), "musicbrainz", 0.99, "artist"
        ),
        MetadataCandidate(
            "artist_countries", ("Brazil",), "musicbrainz", 0.99, "artist"
        ),
    )
    result = collect_semantic_enrichment(
        {
            "genres",
            "moods",
            "lyrics_languages",
            "artist_languages",
            "artist_areas",
            "artist_countries",
        },
        musicbrainz_tracks=(
            lambda: bundle(genres=("K-pop",), moods=("Dreamy",), metadata=track_metadata),
        ),
        musicbrainz_artists=(
            lambda: bundle(scope=ProviderScope.ARTIST, metadata=artist_metadata),
        ),
        genre_settings=GenreSettings(),
    )
    values = {candidate.field: candidate.value for candidate in result.candidates}
    assert values == {
        "genres": ("K-pop",),
        "moods": ("Dreamy",),
        "lyrics_languages": ("kor", "eng"),
        "artist_languages": ("kor", "eng"),
        "artist_areas": ("Salvador",),
        "artist_countries": ("Brazil",),
    }
    assert all(
        outcome.status is SemanticFieldStatus.RESOLVED
        for outcome in result.outcomes.values()
    )


def test_outcomes_distinguish_no_evidence_unavailable_conflict_and_blocked() -> None:
    def unavailable() -> SemanticEvidenceBundle:
        raise ProviderError("network")

    result = collect_semantic_enrichment(
        {"lyrics_languages", "moods", "styles", "artist_areas"},
        musicbrainz_tracks=(lambda: bundle(),),
        musicbrainz_artists=(unavailable,),
        conflict_fields={"moods"},
        blocked_fields={"styles"},
    )
    assert result.outcomes["lyrics_languages"].status is SemanticFieldStatus.NO_EVIDENCE
    assert result.outcomes["artist_areas"].status is SemanticFieldStatus.UNAVAILABLE
    assert result.outcomes["moods"].status is SemanticFieldStatus.CONFLICT
    assert result.outcomes["styles"].status is SemanticFieldStatus.BLOCKED


def test_local_provider_failure_does_not_erase_unrelated_success() -> None:
    def unavailable() -> SemanticEvidenceBundle:
        raise ProviderError("network") from RequestException("temporary")

    result = collect_semantic_enrichment(
        {"moods", "artist_areas"},
        musicbrainz_tracks=(lambda: bundle(moods=("Dreamy",)),),
        musicbrainz_artists=(unavailable,),
    )
    assert {item.field: item.value for item in result.candidates} == {
        "moods": ("Dreamy",)
    }
    assert result.outcomes["moods"].status is SemanticFieldStatus.RESOLVED
    assert result.outcomes["artist_areas"].status is SemanticFieldStatus.UNAVAILABLE
