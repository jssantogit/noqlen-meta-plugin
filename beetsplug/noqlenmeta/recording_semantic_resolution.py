"""Conservative V3 recording semantics independent from identity repair.

Unknown instrumental state is never interpreted as false. MusicBrainz
performance relationships may explicitly assert true; silence asserts nothing.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from beetsplug.noqlenmeta.authority import (
    AUTHORITY_MATRIX,
    AuthorityRole,
    eligible_standalone,
)
from beetsplug.noqlenmeta.evidence import CanonicalValue, MetadataEvidence
from beetsplug.noqlenmeta.field_contracts import EntityKind
from beetsplug.noqlenmeta.resolver import ResolutionAction

RECORDING_SEMANTIC_FIELDS = frozenset({"instrumental"})


@dataclass(frozen=True, slots=True)
class RecordingSemanticDecision:
    field: str
    current_value: CanonicalValue | None
    value: CanonicalValue | None
    selected: MetadataEvidence
    action: ResolutionAction
    reason: str
    contributors: tuple[MetadataEvidence, ...] = ()

    @property
    def resolved_value(self) -> CanonicalValue | None:
        return self.value

    @property
    def selected_source(self) -> MetadataEvidence:
        return self.selected

    @property
    def contributing_evidence(self) -> tuple[MetadataEvidence, ...]:
        return self.contributors


def resolve_recording_semantics(
    current_values: Mapping[str, CanonicalValue],
    evidence: Sequence[MetadataEvidence],
) -> tuple[RecordingSemanticDecision, ...]:
    """Resolve only explicitly asserted, authority-eligible recording facts."""
    grouped: dict[str, list[tuple[int, MetadataEvidence]]] = defaultdict(list)
    authority_priority = {
        AuthorityRole.PRIMARY: 0,
        AuthorityRole.SECONDARY: 1,
        AuthorityRole.FALLBACK: 2,
    }
    for item in evidence:
        if item.field not in RECORDING_SEMANTIC_FIELDS:
            raise ValueError(f"unsupported recording semantic field: {item.field}")
        if item.field == "instrumental" and item.value is not True:
            raise ValueError("instrumental evidence must be explicit true")
        if item.subject.entity is not EntityKind.RECORDING:
            continue
        role = AUTHORITY_MATRIX.role_for(
            item.field, item.subject.entity, item.acquisition_scope, item.provider
        )
        if eligible_standalone(role):
            grouped[item.field].append((authority_priority[role], item))

    decisions: list[RecordingSemanticDecision] = []
    for field, items in sorted(grouped.items()):
        eligible = tuple(
            item
            for _, item in sorted(
                items, key=lambda ranked: (ranked[0], ranked[1].provider, ranked[1].source_id)
            )
        )
        current = current_values.get(field)
        selected = eligible[0]
        if current is None:
            action = ResolutionAction.PROPOSE
            value = True
            reason = "explicit performance relationship asserts instrumental recording"
        elif type(current) is bool and current is True:
            action = ResolutionAction.KEEP
            value = current
            reason = "existing instrumental state agrees"
        else:
            action = ResolutionAction.REVIEW
            value = current
            reason = "existing instrumental state conflicts or is incompatible"
        decisions.append(
            RecordingSemanticDecision(
                field, current, value, selected, action, reason, eligible
            )
        )
    return tuple(decisions)
