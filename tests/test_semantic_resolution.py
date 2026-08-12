from beetsplug.noqlenmeta.domain import (
    SemanticCategory,
    SemanticEvidenceBundle,
    SemanticTagEvidence,
)
from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.semantic_resolution import (
    collect_scoped_semantic_fallback,
    resolve_moods,
    resolve_styles,
)


def evidence(
    term: str,
    provider: str,
    scope: ProviderScope,
    weight: int,
    *,
    confidence: float = 0.9,
) -> SemanticTagEvidence:
    return SemanticTagEvidence(
        canonical_term=term,
        category=SemanticCategory.MOOD,
        provider=provider,
        scope=scope,
        confidence=confidence,
        source_id="synthetic",
        source_url=None,
        native_weight=weight,
        raw_tag=term.casefold(),
    )


def test_mood_native_weight_breaks_equivalent_track_tie() -> None:
    result = resolve_moods(
        (
            evidence("Melancholic", "musicbrainz", ProviderScope.TRACK, 8),
            evidence("Dreamy", "musicbrainz", ProviderScope.TRACK, 7),
        ),
        max_moods=1,
    )
    assert result == ("Melancholic",)


def test_distinct_provider_corroboration_beats_single_provider() -> None:
    result = resolve_moods(
        (
            evidence("Dreamy", "musicbrainz", ProviderScope.RELEASE, 4),
            evidence("Dreamy", "lastfm", ProviderScope.RELEASE, 4),
            evidence("Melancholic", "musicbrainz", ProviderScope.RELEASE, 10),
        ),
        max_moods=1,
    )
    assert result == ("Dreamy",)


def test_structured_styles_are_preserved_without_community_merging() -> None:
    community = (
        SemanticTagEvidence(
            "Acoustic",
            SemanticCategory.STYLE,
            "lastfm",
            ProviderScope.RELEASE,
            0.9,
            "synthetic",
            None,
            8,
            "acoustic",
        ),
    )
    assert resolve_styles(
        ("Ambient", "Experimental"), community
    ) == ("Ambient", "Experimental")


def test_mood_limit_never_pads_missing_values() -> None:
    result = resolve_moods(
        (
            evidence("Dreamy", "musicbrainz", ProviderScope.TRACK, 8),
            evidence("Melancholic", "musicbrainz", ProviderScope.TRACK, 7),
        ),
        max_moods=3,
    )
    assert result == ("Dreamy", "Melancholic")


def semantic_bundle(*fields: str) -> SemanticEvidenceBundle:
    genres = ()
    tags = []
    if "genres" in fields:
        genres = (
            GenreEvidence(
                "K-pop",
                "lastfm",
                ProviderScope.TRACK,
                GenreEvidenceKind.COMMUNITY_TAG,
                0.85,
                "synthetic",
            ),
        )
    for field, category, term in (
        ("moods", SemanticCategory.MOOD, "Dreamy"),
        ("styles", SemanticCategory.STYLE, "Acoustic"),
    ):
        if field in fields:
            tags.append(
                SemanticTagEvidence(
                    term,
                    category,
                    "lastfm",
                    ProviderScope.TRACK,
                    0.85,
                    "synthetic",
                    None,
                    50,
                    term,
                )
            )
    return SemanticEvidenceBundle(genres=genres, tags=tuple(tags))


def test_fallback_stops_after_track_resolves_all_requested_fields() -> None:
    calls = []

    def collect(scope: str, bundle: SemanticEvidenceBundle):
        def inner() -> SemanticEvidenceBundle:
            calls.append(scope)
            return bundle

        return inner

    bundles = collect_scoped_semantic_fallback(
        {"genres", "moods"},
        set(),
        collect("track", semantic_bundle("genres", "moods")),
        collect("release", semantic_bundle("moods")),
        collect("artist", semantic_bundle("moods")),
    )
    assert calls == ["track"]
    assert len(bundles) == 1


def test_fallback_continues_only_until_remaining_field_is_resolved() -> None:
    calls = []

    def collect(scope: str, bundle: SemanticEvidenceBundle):
        def inner() -> SemanticEvidenceBundle:
            calls.append(scope)
            return bundle

        return inner

    collect_scoped_semantic_fallback(
        {"genres", "moods"},
        set(),
        collect("track", semantic_bundle("genres")),
        collect("release", semantic_bundle("moods")),
        collect("artist", semantic_bundle("moods")),
    )
    assert calls == ["track", "release"]


def test_fallback_reaches_artist_when_track_and_release_are_insufficient() -> None:
    calls = []

    def collect(scope: str, bundle: SemanticEvidenceBundle):
        def inner() -> SemanticEvidenceBundle:
            calls.append(scope)
            return bundle

        return inner

    collect_scoped_semantic_fallback(
        {"moods"},
        set(),
        collect("track", semantic_bundle()),
        collect("release", semantic_bundle()),
        collect("artist", semantic_bundle("moods")),
    )
    assert calls == ["track", "release", "artist"]


def test_fallback_filter_preserves_field_local_unavailability() -> None:
    bundles = collect_scoped_semantic_fallback(
        {"moods"},
        set(),
        lambda: SemanticEvidenceBundle(
            unavailable_fields=frozenset({"genres", "moods"})
        ),
        lambda: semantic_bundle("moods"),
        lambda: semantic_bundle(),
    )

    assert bundles[0].unavailable_fields == frozenset({"moods"})


def test_release_beats_artist_after_ineligible_track_is_filtered() -> None:
    result = resolve_moods(
        (
            evidence("Atmospheric", "lastfm", ProviderScope.TRACK, 10, confidence=0.85),
            evidence("Dreamy", "musicbrainz", ProviderScope.RELEASE, 5, confidence=0.91),
            evidence("Melancholic", "musicbrainz", ProviderScope.ARTIST, 10, confidence=0.99),
        ),
        min_confidence=0.9,
    )

    assert result == ("Dreamy",)


def test_eligible_track_beats_stronger_release() -> None:
    result = resolve_moods(
        (
            evidence("Dreamy", "lastfm", ProviderScope.TRACK, 5, confidence=0.9),
            evidence("Melancholic", "musicbrainz", ProviderScope.RELEASE, 10, confidence=0.99),
        ),
        min_confidence=0.9,
    )

    assert result == ("Dreamy",)
