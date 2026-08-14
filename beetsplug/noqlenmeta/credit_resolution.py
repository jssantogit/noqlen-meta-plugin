"""Authority-aware monotonic resolution for structured musical credits."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from beetsplug.noqlenmeta.authority import AUTHORITY_MATRIX, AuthorityRole, eligible_standalone
from beetsplug.noqlenmeta.credits import (
    ArtistCredit,
    CreditReference,
    canonical_credit_references,
)
from beetsplug.noqlenmeta.evidence import CanonicalValue, MetadataEvidence
from beetsplug.noqlenmeta.resolver import ResolutionAction

CREDIT_FIELDS = frozenset(
    {
        "composers",
        "lyricists",
        "producers",
        "arrangers",
        "conductors",
        "performers",
        "featured_artists",
        "structured_artist_credits",
    }
)


@dataclass(frozen=True, slots=True)
class CreditDecision:
    field: str
    current_value: CanonicalValue | None
    value: CanonicalValue | None
    selected: MetadataEvidence | None
    action: ResolutionAction
    reason: str
    alternatives: tuple[MetadataEvidence, ...] = ()
    contributors: tuple[MetadataEvidence, ...] = ()

    @property
    def resolved_value(self) -> CanonicalValue | None:
        return self.value

    @property
    def selected_source(self) -> MetadataEvidence | None:
        return self.selected

    @property
    def contributing_evidence(self) -> tuple[MetadataEvidence, ...]:
        return self.contributors


def resolve_credits(
    current_values: Mapping[str, CanonicalValue],
    evidence: Sequence[MetadataEvidence],
) -> tuple[CreditDecision, ...]:
    """Resolve structured credit fields without destructive synchronization."""
    grouped: dict[str, list[tuple[AuthorityRole, MetadataEvidence]]] = defaultdict(list)
    for item in evidence:
        role = AUTHORITY_MATRIX.role_for(
            item.field,
            item.subject.entity,
            item.acquisition_scope,
            item.provider,
        )
        if eligible_standalone(role):
            grouped[item.field].append((role, item))
    return tuple(
        _resolve_field(field, current_values.get(field), tuple(items))
        for field, items in sorted(grouped.items())
    )


def _resolve_field(
    field: str,
    current: CanonicalValue | None,
    items: tuple[tuple[AuthorityRole, MetadataEvidence], ...],
) -> CreditDecision:
    ranked = tuple(
        sorted(items, key=lambda item: (_authority_rank(item[0]), _evidence_key(item[1])))
    )
    strongest = min(_authority_rank(role) for role, _ in ranked)
    if strongest < _authority_rank(AuthorityRole.FALLBACK):
        ranked = tuple(item for item in ranked if item[0] is not AuthorityRole.FALLBACK)
    selected = ranked[0][1]
    contributors = tuple(item for _, item in ranked)
    values = tuple(item.value for item in contributors)
    if all(isinstance(value, ArtistCredit) for value in values):
        artist_credits = tuple(value for value in values if isinstance(value, ArtistCredit))
        unique = tuple(dict.fromkeys(artist_credits))
        if len(unique) != 1:
            return CreditDecision(
                field,
                current,
                current,
                selected,
                ResolutionAction.REVIEW,
                "eligible structured artist credits materially disagree",
                contributors,
            )
        incoming: CanonicalValue = unique[0]
    elif all(_is_credit_tuple(value) for value in values):
        incoming = _merge_references(
            reference
            for value in values
            for reference in value
            if isinstance(reference, CreditReference)
        )
    else:
        raise ValueError(f"credit evidence for {field!r} has incompatible canonical values")

    if current is None:
        return CreditDecision(
            field,
            None,
            incoming,
            selected,
            ResolutionAction.PROPOSE,
            "eligible structured credit evidence supplies a missing value",
            contributors=contributors,
        )
    if isinstance(incoming, ArtistCredit):
        if isinstance(current, ArtistCredit) and current == incoming:
            return CreditDecision(
                field,
                current,
                current,
                selected,
                ResolutionAction.KEEP,
                "existing structured artist credit is equal",
                contributors=contributors,
            )
        return CreditDecision(
            field,
            current,
            current,
            selected,
            ResolutionAction.REVIEW,
            "existing structured artist credit materially disagrees",
            contributors,
        )
    if not _is_credit_tuple(current):
        return CreditDecision(
            field,
            current,
            current,
            selected,
            ResolutionAction.REVIEW,
            "existing credit state has an incompatible structure",
            contributors,
        )
    current_references = tuple(current)
    current_keys = {_unit_key(reference) for reference in current_references}
    incoming_keys = {_unit_key(reference) for reference in incoming}
    if incoming_keys <= current_keys:
        return CreditDecision(
            field,
            current,
            current,
            selected,
            ResolutionAction.KEEP,
            "existing credits are equal or a safe superset",
            contributors=contributors,
        )
    union = _merge_references((*current_references, *incoming))
    return CreditDecision(
        field,
        current,
        union,
        selected,
        ResolutionAction.PROPOSE,
        "eligible evidence safely enriches existing credits",
        contributors=contributors,
    )


def _merge_references(values: object) -> tuple[CreditReference, ...]:
    references = tuple(values)  # type: ignore[arg-type]
    grouped: dict[tuple[object, ...], list[CreditReference]] = defaultdict(list)
    for reference in references:
        if not isinstance(reference, CreditReference):
            raise TypeError("credit union requires CreditReference values")
        grouped[_unit_key(reference)].append(reference)
    merged: list[CreditReference] = []
    for group in grouped.values():
        preferred = group[0]
        variants = tuple(
            dict.fromkeys(
                variant
                for reference in group
                for variant in reference.party.credited_as_variants
            )
        )
        if variants != preferred.party.credited_as_variants:
            preferred = replace(
                preferred,
                party=replace(preferred.party, credited_as_variants=variants),
            )
        merged.append(preferred)
    return canonical_credit_references(merged)


def _unit_key(reference: CreditReference) -> tuple[object, ...]:
    party = (
        ("mbid", reference.party.mbid)
        if reference.party.mbid is not None
        else ("name", reference.party.name)
    )
    return (
        party,
        reference.role,
        reference.scope,
        reference.instrument,
        reference.source_entity_id,
    )


def _is_credit_tuple(value: object) -> bool:
    return isinstance(value, tuple) and bool(value) and all(
        isinstance(item, CreditReference) for item in value
    )


def _authority_rank(role: AuthorityRole) -> int:
    return {
        AuthorityRole.PRIMARY: 0,
        AuthorityRole.SECONDARY: 1,
        AuthorityRole.FALLBACK: 2,
        AuthorityRole.CORROBORATION_ONLY: 3,
        AuthorityRole.INELIGIBLE: 4,
    }[role]


def _evidence_key(item: MetadataEvidence) -> tuple[object, ...]:
    return (item.provider, item.source_id, repr(item.value))
