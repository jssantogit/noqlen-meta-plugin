from beetsplug.noqlenmeta.domain import SemanticCategory, SemanticTagEvidence
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.semantic_resolution import resolve_moods, resolve_styles


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
            "Alternative Metal",
            SemanticCategory.STYLE,
            "lastfm",
            ProviderScope.RELEASE,
            0.9,
            "synthetic",
            None,
            8,
            "alternative metal",
        ),
    )
    assert resolve_styles(
        ("Progressive Metal", "Technical Death Metal"), community
    ) == ("Progressive Metal", "Technical Death Metal")


def test_mood_limit_never_pads_missing_values() -> None:
    result = resolve_moods(
        (
            evidence("Dreamy", "musicbrainz", ProviderScope.TRACK, 8),
            evidence("Melancholic", "musicbrainz", ProviderScope.TRACK, 7),
        ),
        max_moods=3,
    )
    assert result == ("Dreamy", "Melancholic")
