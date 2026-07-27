import pytest

from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.orchestration import (
    eligible_provider_fields,
    provider_can_contribute,
    validate_provider_candidates,
)
from beetsplug.noqlenmeta.providers.base import ProviderContractError
from beetsplug.noqlenmeta.providers.specs import (
    DISCOGS_SPEC,
    ITUNES_SPEC,
    LASTFM_SPEC,
    LRCLIB_SPEC,
    MUSICBRAINZ_SPEC,
    ProviderScope,
    ProviderSpec,
)
from beetsplug.noqlenmeta.resolver import FieldRule, ResolutionPolicy


def policy(
    fields: dict[str, tuple[bool, tuple[str, ...]]],
    providers: dict[str, bool] | None = None,
) -> ResolutionPolicy:
    return ResolutionPolicy(
        {
            field: FieldRule(enabled=enabled, authority=authority)
            for field, (enabled, authority) in fields.items()
        },
        providers
        or {
            "discogs": True,
            "musicbrainz": True,
            "lastfm": True,
            "itunes": True,
            "lrclib": True,
        },
    )


@pytest.mark.parametrize(
    ("spec", "field", "authority", "expected"),
    [
        (DISCOGS_SPEC, "genres", ("discogs",), True),
        (DISCOGS_SPEC, "cover", ("discogs",), False),
        (ITUNES_SPEC, "genres", ("itunes",), True),
        (ITUNES_SPEC, "year", ("itunes",), True),
        (ITUNES_SPEC, "styles", ("itunes",), False),
        (ITUNES_SPEC, "labels", ("discogs", "itunes"), False),
        (ITUNES_SPEC, "genres", ("discogs",), False),
        (MUSICBRAINZ_SPEC, "year", ("musicbrainz", "discogs"), True),
        (MUSICBRAINZ_SPEC, "styles", ("musicbrainz",), False),
        (LASTFM_SPEC, "genres", ("discogs", "lastfm", "itunes"), True),
        (LASTFM_SPEC, "styles", ("lastfm",), False),
        (LASTFM_SPEC, "mood", ("lastfm",), False),
        (LRCLIB_SPEC, "lyrics", ("local", "lrclib"), True),
        (LRCLIB_SPEC, "synced_lyrics", ("lrclib",), True),
        (LRCLIB_SPEC, "genres", ("lrclib",), False),
    ],
)
def test_provider_contribution_intersects_policy_authority_and_capability(
    spec: ProviderSpec,
    field: str,
    authority: tuple[str, ...],
    expected: bool,
) -> None:
    resolution_policy = policy({field: (True, authority)})

    assert provider_can_contribute(resolution_policy, spec) is expected


def test_eligible_provider_fields_returns_the_useful_intersection() -> None:
    resolution_policy = policy(
        {
            "genres": (True, ("discogs", "itunes")),
            "year": (True, ("itunes",)),
            "labels": (True, ("itunes",)),
            "styles": (False, ("itunes",)),
        }
    )

    assert eligible_provider_fields(resolution_policy, ITUNES_SPEC) == frozenset(
        {"genres", "year"}
    )


def test_disabled_provider_or_field_cannot_contribute() -> None:
    disabled_provider = policy(
        {"genres": (True, ("itunes",))}, {"discogs": True, "itunes": False}
    )
    disabled_field = policy({"genres": (False, ("itunes",))})

    assert not provider_can_contribute(disabled_provider, ITUNES_SPEC)
    assert not provider_can_contribute(disabled_field, ITUNES_SPEC)


def test_musicbrainz_requires_enablement_authority_and_declared_capability() -> None:
    styles_only = policy({"styles": (True, ("musicbrainz",))})
    disabled = policy(
        {"year": (True, ("musicbrainz",))},
        {"musicbrainz": False},
    )

    assert not provider_can_contribute(styles_only, MUSICBRAINZ_SPEC)
    assert not provider_can_contribute(disabled, MUSICBRAINZ_SPEC)


def test_unknown_provider_is_safely_ineligible() -> None:
    unknown = ProviderSpec("unknown", "Unknown", frozenset({"genres"}))

    assert not provider_can_contribute(policy({"genres": (True, ("unknown",))}), unknown)


def test_generic_orchestration_helpers_accept_track_scoped_specs() -> None:
    spec = ProviderSpec(
        "track-provider", "Track Provider", frozenset({"lyrics"}), ProviderScope.TRACK
    )
    resolution_policy = policy(
        {"lyrics": (True, ("track-provider",))}, {"track-provider": True}
    )

    assert provider_can_contribute(resolution_policy, spec)
    assert eligible_provider_fields(resolution_policy, spec) == frozenset({"lyrics"})


def test_lrclib_cannot_contribute_when_both_lyrics_fields_are_disabled() -> None:
    resolution_policy = policy(
        {
            "lyrics": (False, ("lrclib",)),
            "synced_lyrics": (False, ("lrclib",)),
        },
        {"lrclib": True},
    )

    assert not provider_can_contribute(resolution_policy, LRCLIB_SPEC)


def candidate(field: str = "genres", provider: str = "itunes") -> MetadataCandidate:
    return MetadataCandidate(field, ("Electronic",), provider, 0.9, "collection-1")


def test_candidate_validation_preserves_valid_candidates_unchanged() -> None:
    proposal = candidate()
    candidates = [proposal]
    snapshot = candidates.copy()

    validated = validate_provider_candidates(ITUNES_SPEC, candidates)

    assert validated == (proposal,)
    assert validated[0] is proposal
    assert candidates == snapshot


def test_candidate_validation_accepts_empty_result() -> None:
    assert validate_provider_candidates(ITUNES_SPEC, ()) == ()


def test_candidate_validation_rejects_wrong_provider_identity() -> None:
    with pytest.raises(ProviderContractError, match="provider 'discogs'"):
        validate_provider_candidates(ITUNES_SPEC, (candidate(provider="discogs"),))


def test_candidate_validation_rejects_unsupported_field() -> None:
    with pytest.raises(ProviderContractError, match="unsupported field 'labels'"):
        validate_provider_candidates(ITUNES_SPEC, (candidate(field="labels"),))
