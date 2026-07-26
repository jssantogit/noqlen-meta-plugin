import pytest

from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.orchestration import (
    eligible_provider_fields,
    provider_can_contribute,
    validate_provider_candidates,
)
from beetsplug.noqlenmeta.providers.base import ProviderContractError
from beetsplug.noqlenmeta.providers.specs import DISCOGS_SPEC, ITUNES_SPEC, ProviderSpec
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
        providers or {"discogs": True, "itunes": True},
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


def test_unknown_provider_is_safely_ineligible() -> None:
    unknown = ProviderSpec("unknown", "Unknown", frozenset({"genres"}))

    assert not provider_can_contribute(policy({"genres": (True, ("unknown",))}), unknown)


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
