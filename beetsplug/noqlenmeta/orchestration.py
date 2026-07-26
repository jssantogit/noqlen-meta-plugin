"""Capability-aware helpers for provider orchestration."""

from __future__ import annotations

from collections.abc import Sequence

from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.providers.base import ProviderContractError
from beetsplug.noqlenmeta.providers.specs import ProviderSpec
from beetsplug.noqlenmeta.resolver import ResolutionPolicy


def eligible_provider_fields(
    policy: ResolutionPolicy, spec: ProviderSpec
) -> frozenset[str]:
    """Return enabled authoritative fields that the adapter can currently emit."""
    if not policy.provider_has_enabled_authority(spec.name):
        return frozenset()
    return frozenset(
        field
        for field, rule in policy.field_rules.items()
        if field in spec.supported_fields and rule.enabled and spec.name in rule.authority
    )


def provider_can_contribute(policy: ResolutionPolicy, spec: ProviderSpec) -> bool:
    """Return whether provider policy and concrete adapter capability intersect."""
    return bool(eligible_provider_fields(policy, spec))


def validate_provider_candidates(
    spec: ProviderSpec, candidates: Sequence[MetadataCandidate]
) -> tuple[MetadataCandidate, ...]:
    """Enforce provider identity and declared field capabilities without normalization."""
    validated = tuple(candidates)
    for candidate in validated:
        if candidate.provider != spec.name:
            raise ProviderContractError(
                f"{spec.display_name} emitted candidate for provider {candidate.provider!r}"
            )
        if candidate.field not in spec.supported_fields:
            raise ProviderContractError(
                f"{spec.display_name} emitted unsupported field {candidate.field!r}"
            )
    return validated
