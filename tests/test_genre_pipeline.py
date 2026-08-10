from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.genre_evidence import GenreEvidenceKind
from beetsplug.noqlenmeta.genre_pipeline import (
    genre_evidence_from_release_candidates,
    resolve_release_genre_decision,
)
from beetsplug.noqlenmeta.genre_resolution import GenreSettings
from beetsplug.noqlenmeta.genre_taxonomy import DEFAULT_GENRE_TAXONOMY
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.resolver import (
    FieldRule,
    ResolutionAction,
    ResolutionPolicy,
)


def candidate(
    provider: str,
    field: str,
    value: str | tuple[str, ...],
    confidence: float = 0.9,
) -> MetadataCandidate:
    return MetadataCandidate(field, value, provider, confidence, f"{provider}-release")


def policy(
    *,
    enabled: bool = True,
    min_confidence: float = 0.8,
    preserve_existing: bool = True,
    providers: dict[str, bool] | None = None,
) -> ResolutionPolicy:
    return ResolutionPolicy(
        {
            "genres": FieldRule(
                enabled,
                ("musicbrainz", "discogs", "lastfm", "itunes"),
                min_confidence,
                preserve_existing,
            ),
            "styles": FieldRule(False, ("discogs",), min_confidence),
        },
        providers
        or {"musicbrainz": True, "discogs": True, "lastfm": True, "itunes": True},
    )


def test_release_candidates_become_typed_genre_evidence() -> None:
    evidence = genre_evidence_from_release_candidates(
        (
            candidate("discogs", "genres", ("Rock",)),
            candidate("discogs", "styles", ("Technical Death Metal",)),
            candidate("lastfm", "genres", ("K-pop",)),
            candidate("itunes", "genres", "Drum and Bass"),
            candidate("discogs", "year", 2005),  # type: ignore[arg-type]
        ),
        policy=policy(),
        settings=GenreSettings(),
    )
    assert [(item.genre, item.provider, item.scope, item.kind) for item in evidence] == [
        ("Rock", "discogs", ProviderScope.RELEASE, GenreEvidenceKind.GENRE),
        (
            "Technical Death Metal",
            "discogs",
            ProviderScope.RELEASE,
            GenreEvidenceKind.PROMOTED_STYLE,
        ),
        ("K-pop", "lastfm", ProviderScope.RELEASE, GenreEvidenceKind.COMMUNITY_TAG),
        ("Drum and Bass", "itunes", ProviderScope.RELEASE, GenreEvidenceKind.GENRE),
    ]


def test_style_promotion_can_be_disabled_and_rejects_unknown_styles() -> None:
    candidates = (
        candidate("discogs", "styles", ("Technical Death Metal", "Neo Synthetic")),
    )
    promoted = genre_evidence_from_release_candidates(
        candidates, policy=policy(), settings=GenreSettings(promote_styles=True)
    )
    disabled = genre_evidence_from_release_candidates(
        candidates, policy=policy(), settings=GenreSettings(promote_styles=False)
    )
    assert [item.genre for item in promoted] == ["Technical Death Metal"]
    assert disabled == ()


def test_style_promotion_does_not_depend_on_styles_field_persistence() -> None:
    evidence = genre_evidence_from_release_candidates(
        (candidate("discogs", "styles", ("Progressive Metal",)),),
        policy=policy(),
        settings=GenreSettings(),
    )
    assert evidence[0].kind is GenreEvidenceKind.PROMOTED_STYLE


def test_disabled_unauthorized_and_weak_providers_do_not_contribute() -> None:
    candidates = (
        candidate("discogs", "genres", ("Rock",)),
        candidate("lastfm", "genres", ("K-pop",), confidence=0.7),
        candidate("unlisted", "genres", ("Metal",)),
    )
    evidence = genre_evidence_from_release_candidates(
        candidates,
        policy=policy(providers={"discogs": False, "lastfm": True, "unlisted": True}),
        settings=GenreSettings(),
    )
    assert evidence == ()


def test_aggregate_decision_promotes_specific_style_and_retains_provenance() -> None:
    decision = resolve_release_genre_decision(
        None,
        (
            candidate("discogs", "genres", ("Rock",)),
            candidate("discogs", "styles", ("Technical Death Metal",)),
        ),
        policy=policy(),
        settings=GenreSettings(),
    )
    assert decision is not None
    assert decision.action is ResolutionAction.PROPOSE
    assert decision.selected is not None
    assert decision.selected.field == "genres"
    assert decision.selected.provider == "noqlen"
    assert decision.selected.value == ("Technical Death Metal",)
    assert decision.selected.source_id == (
        f"genre-taxonomy:{DEFAULT_GENRE_TAXONOMY.snapshot_id}"
    )
    assert decision.selected.confidence == 0.9
    assert "Technical Death Metal: discogs promoted style" in decision.reason


def test_aggregate_decision_respects_existing_value_policy() -> None:
    candidates = (candidate("discogs", "genres", ("K-pop",)),)
    same = resolve_release_genre_decision(
        ("K-pop",), candidates, policy=policy(), settings=GenreSettings()
    )
    conflict = resolve_release_genre_decision(
        ("Rock",), candidates, policy=policy(), settings=GenreSettings()
    )
    replace = resolve_release_genre_decision(
        ("Rock",),
        candidates,
        policy=policy(preserve_existing=False),
        settings=GenreSettings(),
    )
    assert same is not None and same.action is ResolutionAction.KEEP
    assert conflict is not None and conflict.action is ResolutionAction.REVIEW
    assert replace is not None and replace.action is ResolutionAction.PROPOSE


def test_disabled_genres_field_produces_no_specialized_decision() -> None:
    candidates = (candidate("discogs", "genres", ("Rock",)),)
    assert (
        resolve_release_genre_decision(
            None, candidates, policy=policy(enabled=False), settings=GenreSettings()
        )
        is None
    )
