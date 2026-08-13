"""Field-scoped resolution for internal V3 release catalog evidence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from beetsplug.noqlenmeta.authority import (
    AUTHORITY_MATRIX,
    AuthorityMatrix,
    AuthorityRole,
)
from beetsplug.noqlenmeta.evidence import CanonicalValue, MetadataEvidence
from beetsplug.noqlenmeta.field_contracts import PartialDate, ResolverKind, field_contract
from beetsplug.noqlenmeta.release_catalog import (
    ReleaseSecondaryType,
    compatible_partial_dates,
    prefer_precise_date,
)
from beetsplug.noqlenmeta.resolver import ResolutionAction

_MIN_CONFIDENCE = 0.8


@dataclass(frozen=True, slots=True)
class CatalogFieldDecision:
    """One immutable release catalog resolution outcome."""

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


def resolve_release_catalog(
    current_values: Mapping[str, CanonicalValue],
    evidence: Sequence[MetadataEvidence],
    *,
    authority: AuthorityMatrix = AUTHORITY_MATRIX,
) -> tuple[CatalogFieldDecision, ...]:
    """Resolve only EXCLUSIVE and MULTIVALUE V3 release catalog fields."""
    grouped: dict[str, list[MetadataEvidence]] = defaultdict(list)
    for item in evidence:
        contract = field_contract(item.field)
        if contract.resolver_kind not in {ResolverKind.EXCLUSIVE, ResolverKind.MULTIVALUE}:
            raise ValueError(f"unsupported release catalog resolver kind: {item.field}")
        grouped[item.field].append(item)

    decisions = [
        _resolve_field(
            field,
            current_values.get(field),
            tuple(items),
            authority,
        )
        for field, items in sorted(grouped.items())
    ]
    return tuple(decisions)


def _resolve_field(
    field: str,
    current: CanonicalValue | None,
    items: tuple[MetadataEvidence, ...],
    authority: AuthorityMatrix,
) -> CatalogFieldDecision:
    ordered = tuple(sorted(items, key=_evidence_key))
    by_role: dict[AuthorityRole, list[MetadataEvidence]] = defaultdict(list)
    for item in ordered:
        role = authority.role_for(
            field,
            item.subject.entity,
            item.acquisition_scope,
            item.provider,
        )
        if item.confidence is not None and item.confidence < _MIN_CONFIDENCE:
            continue
        by_role[role].append(item)

    contenders = tuple(by_role[AuthorityRole.PRIMARY] + by_role[AuthorityRole.SECONDARY])
    if not contenders:
        contenders = tuple(by_role[AuthorityRole.FALLBACK])
    if not contenders:
        return CatalogFieldDecision(
            field,
            current,
            current,
            None,
            ResolutionAction.SKIP,
            "no standalone eligible evidence",
            ordered,
        )

    contract = field_contract(field)
    if contract.resolver_kind is ResolverKind.MULTIVALUE:
        resolved = _resolve_multivalue(contenders)
    else:
        resolved = _resolve_exclusive(contenders)
    if resolved is None:
        return CatalogFieldDecision(
            field,
            current,
            current,
            None,
            ResolutionAction.REVIEW,
            "eligible evidence materially conflicts",
            ordered,
        )
    value, selected = resolved
    alternatives = tuple(item for item in ordered if item is not selected)
    return _with_current(field, current, value, selected, alternatives, contenders)


def _resolve_exclusive(
    items: tuple[MetadataEvidence, ...],
) -> tuple[CanonicalValue, MetadataEvidence] | None:
    value = items[0].value
    selected = items[0]
    for item in items[1:]:
        if isinstance(value, PartialDate) and isinstance(item.value, PartialDate):
            precise = prefer_precise_date(value, item.value)
            if precise is None:
                return None
            if precise == item.value and precise != value:
                selected = item
            value = precise
        elif type(value) is not type(item.value) or value != item.value:
            return None
    return value, selected


def _resolve_multivalue(
    items: tuple[MetadataEvidence, ...],
) -> tuple[CanonicalValue, MetadataEvidence] | None:
    entity = items[0].subject.entity
    if any(item.subject.entity is not entity for item in items):
        return None
    values: list[ReleaseSecondaryType] = []
    for item in items:
        if not isinstance(item.value, tuple) or not all(
            isinstance(value, ReleaseSecondaryType) for value in item.value
        ):
            return None
        for value in cast(tuple[ReleaseSecondaryType, ...], item.value):
            if value not in values:
                values.append(value)
    return tuple(values), items[0]


def _with_current(
    field: str,
    current: CanonicalValue | None,
    value: CanonicalValue,
    selected: MetadataEvidence,
    alternatives: tuple[MetadataEvidence, ...],
    contributors: tuple[MetadataEvidence, ...],
) -> CatalogFieldDecision:
    if current is None:
        action = ResolutionAction.PROPOSE
        reason = "eligible evidence supplies a missing canonical value"
        result = value
    elif isinstance(current, PartialDate) and isinstance(value, PartialDate):
        if not compatible_partial_dates(current, value):
            action = ResolutionAction.REVIEW
            reason = "existing date materially conflicts with eligible evidence"
            result = current
        else:
            preferred = prefer_precise_date(current, value)
            if preferred == current:
                action = ResolutionAction.KEEP
                reason = "existing date preserves equal or greater compatible precision"
                result = current
            else:
                action = ResolutionAction.PROPOSE
                reason = "eligible evidence safely enriches date precision"
                result = value
    elif type(current) is type(value) and current == value:
        action = ResolutionAction.KEEP
        reason = "existing canonical value already agrees"
        result = current
    else:
        action = ResolutionAction.REVIEW
        reason = "existing canonical value materially conflicts with eligible evidence"
        result = current
    return CatalogFieldDecision(
        field,
        current,
        result,
        selected,
        action,
        reason,
        alternatives,
        contributors,
    )


def _evidence_key(item: MetadataEvidence) -> tuple[object, ...]:
    return (
        item.provider,
        item.subject.entity.value,
        item.source_id,
        type(item.value).__name__,
        repr(item.value),
    )
