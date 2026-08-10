from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.resolver import (
    FieldRule,
    ResolutionAction,
    ResolutionPolicy,
    default_resolution_policy,
    resolve_metadata,
)


def candidate(
    provider: str,
    value: object,
    confidence: float = 0.9,
    *,
    field: str = "genres",
    source_id: str | None = None,
) -> MetadataCandidate:
    return MetadataCandidate(
        field=field,
        value=value,  # type: ignore[arg-type]
        provider=provider,
        confidence=confidence,
        source_id=source_id or f"{provider}-release",
        source_url=f"https://{provider}.invalid/releases/1",
    )


def policy(
    *,
    enabled: bool = True,
    authority: tuple[str, ...] = ("catalog", "community", "fallback"),
    min_confidence: float = 0.8,
    preserve_existing: bool = True,
    providers: dict[str, bool] | None = None,
) -> ResolutionPolicy:
    return ResolutionPolicy(
        field_rules={
            "genres": FieldRule(
                enabled=enabled,
                authority=authority,
                min_confidence=min_confidence,
                preserve_existing=preserve_existing,
            )
        },
        providers=(
            providers
            if providers is not None
            else {"catalog": True, "community": True, "fallback": True}
        ),
    )


def test_policy_distinguishes_known_and_enabled_fields() -> None:
    resolution_policy = default_resolution_policy()

    assert resolution_policy.is_field_enabled("genres")
    assert "moods" in resolution_policy.field_rules
    assert not resolution_policy.is_field_enabled("moods")
    assert not resolution_policy.is_field_enabled("unknown")


def test_policy_tracks_provider_enablement_independently() -> None:
    resolution_policy = ResolutionPolicy(
        {"genres": FieldRule(enabled=True, authority=("catalog", "community"))},
        {"catalog": True, "community": False},
    )

    assert resolution_policy.is_provider_enabled("catalog")
    assert not resolution_policy.is_provider_enabled("community")
    assert not resolution_policy.is_provider_enabled("unknown")


def test_provider_contribution_requires_enablement_field_and_authority() -> None:
    resolution_policy = ResolutionPolicy(
        {
            "genres": FieldRule(enabled=True, authority=("catalog",)),
            "mood": FieldRule(enabled=True, authority=("community",)),
            "styles": FieldRule(enabled=False, authority=("fallback",)),
        },
        {"catalog": True, "community": False, "fallback": True},
    )

    assert resolution_policy.provider_has_enabled_authority("catalog")
    assert not resolution_policy.provider_has_enabled_authority("community")
    assert not resolution_policy.provider_has_enabled_authority("fallback")
    assert not resolution_policy.provider_has_enabled_authority("unknown")


def test_unlisted_provider_has_no_authority() -> None:
    resolution_policy = policy(authority=("catalog",))

    assert resolution_policy.authority_rank("genres", "catalog") == 0
    assert resolution_policy.authority_rank("genres", "community") is None
    assert resolution_policy.authority_rank("unknown", "catalog") is None


def test_policy_answers_threshold_and_preserve_queries_safely() -> None:
    resolution_policy = policy(min_confidence=0.85, preserve_existing=False)

    assert resolution_policy.confidence_threshold("genres") == 0.85
    assert not resolution_policy.preserves_existing("genres")
    assert resolution_policy.confidence_threshold("unknown") is None
    assert resolution_policy.preserves_existing("unknown")


@pytest.mark.parametrize(
    "confidence", [-0.01, 1.01, float("inf"), float("nan"), True]
)
def test_field_rule_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="minimum confidence"):
        FieldRule(min_confidence=confidence)


def test_field_rule_normalizes_provider_names_and_rejects_duplicates() -> None:
    rule = FieldRule(authority=(" Catalog ", "COMMUNITY"))

    assert rule.authority == ("catalog", "community")
    with pytest.raises(ValueError, match="unique"):
        FieldRule(authority=("catalog", " CATALOG "))
    with pytest.raises(ValueError, match="invalid characters"):
        FieldRule(authority=("not a provider",))


def test_empty_authority_has_explicit_skip_semantics() -> None:
    decision = resolve_metadata({}, [candidate("catalog", "Ambient")], policy(authority=()))[0]

    assert decision.action is ResolutionAction.SKIP
    assert decision.selected is None


def test_policy_copies_maps_and_exposes_immutable_state() -> None:
    rules = {"genres": FieldRule(enabled=True, authority=("catalog",))}
    providers = {"catalog": True}
    resolution_policy = ResolutionPolicy(rules, providers)
    rules.clear()
    providers["catalog"] = False

    assert resolution_policy.is_field_enabled("genres")
    assert resolution_policy.is_provider_enabled("catalog")
    with pytest.raises(TypeError):
        resolution_policy.providers["catalog"] = False  # type: ignore[index]


def test_disabled_field_is_skipped_with_contenders() -> None:
    proposal = candidate("catalog", "Ambient")

    decision = resolve_metadata({}, [proposal], policy(enabled=False))[0]

    assert decision.action is ResolutionAction.SKIP
    assert decision.selected is None
    assert decision.alternatives == (proposal,)
    assert "field is disabled" in decision.reason


def test_unknown_candidate_field_is_skipped_by_default() -> None:
    proposal = candidate("catalog", "Synthetic", field="unknown")

    decision = resolve_metadata({}, [proposal], policy())[0]

    assert decision.field == "unknown"
    assert decision.action is ResolutionAction.SKIP
    assert decision.selected is None


def test_disabled_and_unlisted_providers_cannot_win() -> None:
    disabled = candidate("catalog", "Ambient")
    unlisted = candidate("unlisted", "Electronic")
    resolution_policy = policy(
        authority=("catalog",), providers={"catalog": False, "unlisted": True}
    )

    decision = resolve_metadata({}, [disabled, unlisted], resolution_policy)[0]

    assert decision.action is ResolutionAction.SKIP
    assert decision.selected is None
    assert set(decision.alternatives) == {disabled, unlisted}


def test_field_authority_outranks_higher_confidence() -> None:
    authoritative = candidate("catalog", "Ambient", 0.88)
    confident_fallback = candidate("community", "Electronic", 0.97)

    decision = resolve_metadata({}, [confident_fallback, authoritative], policy())[0]

    assert decision.action is ResolutionAction.PROPOSE
    assert decision.selected is authoritative
    assert decision.alternatives == (confident_fallback,)
    assert "field authority" in decision.reason


@pytest.mark.parametrize("musicbrainz_confidence", [0.9, 0.99])
def test_default_authority_selects_musicbrainz_for_release_year(
    musicbrainz_confidence: float,
) -> None:
    resolution_policy = default_resolution_policy()
    resolution_policy = ResolutionPolicy(
        resolution_policy.field_rules,
        {"discogs": True, "musicbrainz": True, "itunes": False},
    )
    musicbrainz = candidate(
        "musicbrainz", 2005, musicbrainz_confidence, field="year"
    )
    discogs = candidate("discogs", 2005, 0.99, field="year")

    decision = resolve_metadata({}, [discogs, musicbrainz], resolution_policy)[0]

    assert decision.selected is musicbrainz


def test_default_authority_keeps_discogs_ahead_for_labels() -> None:
    resolution_policy = default_resolution_policy()
    resolution_policy = ResolutionPolicy(
        resolution_policy.field_rules,
        {"discogs": True, "musicbrainz": True, "itunes": False},
    )
    musicbrainz = candidate("musicbrainz", ("MB Label",), 0.99, field="labels")
    discogs = candidate("discogs", ("Discogs Label",), 0.9, field="labels")

    decision = resolve_metadata({}, [musicbrainz, discogs], resolution_policy)[0]

    assert decision.selected is discogs


def test_default_genres_authority_selects_discogs_over_lastfm_and_itunes() -> None:
    baseline = default_resolution_policy()
    resolution_policy = ResolutionPolicy(
        baseline.field_rules,
        {"discogs": True, "lastfm": True, "itunes": True},
    )
    discogs = candidate("discogs", ("Metal",), 0.85, field="genres")
    lastfm = candidate("lastfm", ("Progressive Metal",), 0.85, field="genres")
    itunes = candidate("itunes", ("Rock",), 0.99, field="genres")

    decision = resolve_metadata({}, [itunes, lastfm, discogs], resolution_policy)[0]

    assert decision.selected is discogs


def test_default_genres_authority_selects_lastfm_when_discogs_has_no_candidate() -> None:
    baseline = default_resolution_policy()
    resolution_policy = ResolutionPolicy(
        baseline.field_rules,
        {"discogs": True, "lastfm": True, "itunes": True},
    )
    lastfm = candidate("lastfm", ("Progressive Metal",), 0.85, field="genres")
    itunes = candidate("itunes", ("Rock",), 0.99, field="genres")

    decision = resolve_metadata({}, [itunes, lastfm], resolution_policy)[0]

    assert decision.selected is lastfm


def test_custom_genres_authority_can_select_lastfm_over_discogs() -> None:
    baseline = default_resolution_policy()
    rules = dict(baseline.field_rules)
    rules["genres"] = FieldRule(
        enabled=True,
        authority=("lastfm", "discogs", "itunes"),
        min_confidence=rules["genres"].min_confidence,
        preserve_existing=rules["genres"].preserve_existing,
    )
    resolution_policy = ResolutionPolicy(
        rules,
        {"discogs": True, "lastfm": True, "itunes": True},
    )
    discogs = candidate("discogs", ("Metal",), 0.99, field="genres")
    lastfm = candidate("lastfm", ("Progressive Metal",), 0.85, field="genres")

    decision = resolve_metadata({}, [discogs, lastfm], resolution_policy)[0]

    assert decision.selected is lastfm


def test_disabled_or_below_threshold_musicbrainz_year_cannot_win() -> None:
    baseline = default_resolution_policy()
    disabled_policy = ResolutionPolicy(
        baseline.field_rules,
        {"discogs": True, "musicbrainz": False, "itunes": False},
    )
    enabled_policy = ResolutionPolicy(
        baseline.field_rules,
        {"discogs": True, "musicbrainz": True, "itunes": False},
    )
    musicbrainz = candidate("musicbrainz", 2005, 0.79, field="year")
    discogs = candidate("discogs", 2006, 0.9, field="year")

    assert resolve_metadata({}, [musicbrainz, discogs], disabled_policy)[0].selected is discogs
    assert resolve_metadata({}, [musicbrainz, discogs], enabled_policy)[0].selected is discogs


def test_lower_authority_wins_without_eligible_higher_authority() -> None:
    fallback = candidate("community", "Ambient", 0.9)

    decision = resolve_metadata({}, [fallback], policy())[0]

    assert decision.selected is fallback
    assert decision.action is ResolutionAction.PROPOSE


def test_below_threshold_higher_authority_does_not_block_fallback() -> None:
    below_threshold = candidate("catalog", "Electronic", 0.79)
    fallback = candidate("community", "Ambient", 0.9)

    decision = resolve_metadata({}, [below_threshold, fallback], policy())[0]

    assert decision.selected is fallback
    assert decision.alternatives == (below_threshold,)


def test_resolution_is_deterministic_regardless_of_candidate_order() -> None:
    proposals = [
        candidate("fallback", "Dance", 0.99),
        candidate("catalog", "Ambient", 0.85),
        candidate("community", "Electronic", 0.95),
    ]

    forward = resolve_metadata({}, proposals, policy())
    reverse = resolve_metadata({}, list(reversed(proposals)), policy())

    assert forward == reverse


def test_conflicting_highest_authority_values_require_review() -> None:
    first = candidate("catalog", "Ambient", source_id="release-1")
    second = candidate("catalog", "Electronic", source_id="release-2")

    decision = resolve_metadata({}, [second, first], policy())[0]

    assert decision.action is ResolutionAction.REVIEW
    assert decision.selected is None
    assert set(decision.alternatives) == {first, second}
    assert "conflicting values" in decision.reason


def test_identical_provider_values_deduplicate_without_ambiguity() -> None:
    lower_confidence = candidate("catalog", "Ambient", 0.85, source_id="release-2")
    higher_confidence = candidate("catalog", "Ambient", 0.95, source_id="release-1")

    decision = resolve_metadata({}, [lower_confidence, higher_confidence], policy())[0]

    assert decision.action is ResolutionAction.PROPOSE
    assert decision.selected is higher_confidence
    assert decision.alternatives == ()


def test_lower_authority_disagreement_is_retained_as_alternative() -> None:
    authoritative = candidate("catalog", "Ambient")
    disagreement = candidate("community", "Electronic", 0.99)

    decision = resolve_metadata({}, [disagreement, authoritative], policy())[0]

    assert decision.selected is authoritative
    assert decision.action is ResolutionAction.PROPOSE
    assert decision.alternatives == (disagreement,)


@pytest.mark.parametrize(
    ("current_values", "preserve_existing", "expected"),
    [
        ({}, True, ResolutionAction.PROPOSE),
        ({"genres": "Ambient"}, True, ResolutionAction.KEEP),
        ({"genres": "Electronic"}, True, ResolutionAction.REVIEW),
        ({"genres": "Electronic"}, False, ResolutionAction.PROPOSE),
    ],
)
def test_current_value_controls_resolution_action(
    current_values: dict[str, str],
    preserve_existing: bool,
    expected: ResolutionAction,
) -> None:
    decision = resolve_metadata(
        current_values,
        [candidate("catalog", "Ambient")],
        policy(preserve_existing=preserve_existing),
    )[0]

    assert decision.action is expected


def test_tuple_metadata_and_selected_provenance_remain_intact() -> None:
    proposal = candidate("catalog", ("Electronic", "Ambient"))

    decision = resolve_metadata({}, [proposal], policy())[0]

    assert decision.selected is proposal
    selected = decision.selected
    assert selected is not None
    assert selected.value == ("Electronic", "Ambient")
    assert isinstance(selected.value, tuple)
    assert selected.source_id == "catalog-release"
    assert selected.source_url == "https://catalog.invalid/releases/1"


def test_resolver_does_not_mutate_inputs_and_decisions_are_immutable() -> None:
    current_values = {"genres": ("Existing",)}
    proposals = [candidate("catalog", ("Ambient",))]
    original_current = current_values.copy()
    original_proposals = proposals.copy()

    decision = resolve_metadata(current_values, proposals, policy())[0]

    assert current_values == original_current
    assert proposals == original_proposals
    with pytest.raises(FrozenInstanceError):
        decision.reason = "changed"  # type: ignore[misc]
