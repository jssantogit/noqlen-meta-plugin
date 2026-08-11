import inspect

from requests import RequestException

from beetsplug.noqlenmeta.beets_mapping import map_change_plan_to_beets
from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
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
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction
from beetsplug.noqlenmeta.semantic_enrichment import (
    SemanticFieldOutcome,
    SemanticFieldStatus,
    collect_semantic_enrichment,
    derive_artist_languages,
    reconcile_semantic_outcomes,
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

    assert calls == ["track", "release"]
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


def test_collection_outcomes_distinguish_no_evidence_and_unavailable() -> None:
    def unavailable() -> SemanticEvidenceBundle:
        raise ProviderError("network")

    result = collect_semantic_enrichment(
        {"lyrics_languages", "artist_areas"},
        musicbrainz_tracks=(lambda: bundle(),),
        musicbrainz_artists=(unavailable,),
    )
    assert result.outcomes["lyrics_languages"].status is SemanticFieldStatus.NO_EVIDENCE
    assert result.outcomes["artist_areas"].status is SemanticFieldStatus.UNAVAILABLE


def test_reconciliation_uses_real_review_and_target_blocker() -> None:
    mood = MetadataCandidate("moods", ("Dreamy",), "musicbrainz", 0.9, "recording")
    style = MetadataCandidate("styles", ("Metal",), "discogs", 0.9, "release")
    plan = ChangePlan(
        changes=(PlannedChange("moods", None, mood.value, mood, "winner"),),
        reviews=(
            FieldDecision(
                field="styles",
                current_value=None,
                selected=None,
                action=ResolutionAction.REVIEW,
                reason="review required",
                alternatives=(style,),
            ),
        ),
    )
    outcomes = {
        field: SemanticFieldOutcome(field, SemanticFieldStatus.RESOLVED, value)
        for field, value in (("moods", mood.value), ("styles", style.value))
    }

    target_plan = map_change_plan_to_beets(plan)
    reconciled = reconcile_semantic_outcomes(
        outcomes,
        plan,
        tuple(blocker.source.field for blocker in target_plan.blocked_changes),
    )

    assert reconciled["styles"].status is SemanticFieldStatus.CONFLICT
    assert reconciled["moods"].status is SemanticFieldStatus.BLOCKED


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


def test_min_confidence_rejects_track_and_continues_to_release() -> None:
    calls = []

    def mood_bundle(scope: ProviderScope, confidence: float) -> SemanticEvidenceBundle:
        return SemanticEvidenceBundle(
            tags=(
                SemanticTagEvidence(
                    scope.value.title(),
                    SemanticCategory.MOOD,
                    "lastfm",
                    scope,
                    confidence,
                    f"{scope.value}-id",
                    None,
                    10,
                    scope.value,
                ),
            )
        )

    result = collect_semantic_enrichment(
        {"moods"},
        lastfm_track=lambda: calls.append("track")
        or mood_bundle(ProviderScope.TRACK, 0.85),
        lastfm_release=lambda: calls.append("release")
        or mood_bundle(ProviderScope.RELEASE, 0.92),
        lastfm_artist=lambda: calls.append("artist")
        or mood_bundle(ProviderScope.ARTIST, 0.99),
        min_confidence={"moods": 0.9},
    )

    assert calls == ["track", "release"]
    assert result.candidates[0].value == ("Release",)
    assert result.candidates[0].confidence == 0.92
    assert result.candidates[0].source_id == "release-id"


def test_genre_scope_fallback_prefers_release_then_eligible_track() -> None:
    def genre_bundle(
        value: str, scope: ProviderScope, confidence: float
    ) -> SemanticEvidenceBundle:
        return SemanticEvidenceBundle(
            genres=(
                GenreEvidence(
                    value,
                    "musicbrainz",
                    scope,
                    GenreEvidenceKind.GENRE,
                    confidence,
                    f"{scope.value}-id",
                ),
            )
        )

    release_fallback = collect_semantic_enrichment(
        {"genres"},
        musicbrainz_tracks=(
            lambda: genre_bundle("Progressive Metal", ProviderScope.TRACK, 0.85),
        ),
        musicbrainz_release=lambda: genre_bundle(
            "Technical Death Metal", ProviderScope.RELEASE, 0.92
        ),
        musicbrainz_artists=(
            lambda: genre_bundle("Death Metal", ProviderScope.ARTIST, 0.99),
        ),
        min_confidence={"genres": 0.9},
    )
    eligible_track = collect_semantic_enrichment(
        {"genres"},
        musicbrainz_tracks=(
            lambda: genre_bundle("Progressive Metal", ProviderScope.TRACK, 0.9),
        ),
        musicbrainz_release=lambda: genre_bundle(
            "Technical Death Metal", ProviderScope.RELEASE, 0.99
        ),
        musicbrainz_artists=(
            lambda: genre_bundle("Death Metal", ProviderScope.ARTIST, 1.0),
        ),
        min_confidence={"genres": 0.9},
    )

    assert release_fallback.candidates[0].value == ("Technical Death Metal",)
    assert release_fallback.candidates[0].source_id == "release-id"
    assert eligible_track.candidates[0].value == ("Progressive Metal",)
    assert eligible_track.candidates[0].source_id == "track-id"


def test_musicbrainz_artist_collectors_run_once_in_credit_order() -> None:
    calls = []

    def artist(index: int):
        def collect() -> SemanticEvidenceBundle:
            calls.append(index)
            return bundle(scope=ProviderScope.ARTIST)

        return collect

    collect_semantic_enrichment(
        {"artist_areas"},
        musicbrainz_artists=(artist(1), artist(2)),
    )

    assert calls == [1, 2]


def test_derived_language_fields_apply_independent_confidence_thresholds() -> None:
    metadata = (
        MetadataCandidate(
            "lyrics_languages", ("kor",), "musicbrainz", 0.85, "recording"
        ),
    )

    result = collect_semantic_enrichment(
        {"lyrics_languages", "artist_languages"},
        musicbrainz_tracks=(lambda: bundle(metadata=metadata),),
        min_confidence={"lyrics_languages": 0.9, "artist_languages": 0.8},
    )

    assert {candidate.field: candidate.value for candidate in result.candidates} == {
        "artist_languages": ("kor",)
    }
