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

RECORDING_SEMANTIC_FIELDS = frozenset({
    "instrumental", "explicitness", "vocal_languages",
})


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
        if item.field == "explicitness" and (
            type(item.value) is not str or item.value not in {"explicit", "clean"}
        ):
            raise ValueError("explicitness evidence must be explicit or clean")
        if item.field == "vocal_languages" and not _valid_vocal_languages(
            item.value
        ):
            raise ValueError("vocal_languages require specific ISO-639-3 codes")
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
        incoming = selected.value
        if field == "vocal_languages" and current_values.get("instrumental") is True:
            action = ResolutionAction.REVIEW
            value = current
            reason = "known instrumental recording conflicts with vocal languages"
        elif field == "vocal_languages" and any(
            item.value != incoming for item in eligible[1:]
        ):
            action = ResolutionAction.REVIEW
            value = current
            reason = "different plausible Work languages require review"
        elif any(item.value != incoming for item in eligible[1:]):
            action = ResolutionAction.REVIEW
            value = current
            reason = "eligible recording-level assertions materially disagree"
        elif current is None:
            action = ResolutionAction.PROPOSE
            value = incoming
            reason = "explicit recording-level evidence supplies a missing state"
        elif field == "vocal_languages" and _valid_vocal_languages(current):
            current_languages = set(current)
            new_languages = set(incoming)
            if new_languages <= current_languages:
                action = ResolutionAction.KEEP
                value = current
                reason = "existing vocal languages already contain Work evidence"
            elif current_languages < new_languages:
                action = ResolutionAction.PROPOSE
                value = incoming
                reason = "Work-derived languages safely extend the existing set"
            else:
                action = ResolutionAction.REVIEW
                value = current
                reason = "Work-derived languages conflict with existing language set"
        elif type(current) is type(incoming) and current == incoming:
            action = ResolutionAction.KEEP
            value = current
            reason = "existing recording-level state agrees"
        else:
            action = ResolutionAction.REVIEW
            value = current
            reason = "existing recording-level state conflicts or is incompatible"
        decisions.append(
            RecordingSemanticDecision(
                field, current, value, selected, action, reason, eligible
            )
        )
    return tuple(decisions)


def _valid_vocal_languages(value: object) -> bool:
    """No release/artist language, empty list, generic code or scalar is valid."""
    return (
        isinstance(value, tuple)
        and bool(value)
        and all(
            isinstance(language, str)
            and len(language) == 3
            and language.isascii()
            and language.isalpha()
            and language.islower()
            and language not in {"und", "mul", "zxx"}
            for language in value
        )
        and len(value) == len(set(value))
    )
