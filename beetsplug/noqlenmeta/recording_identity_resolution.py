"""Conservative resolution for Recording/Work identifiers and recording date."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from beetsplug.noqlenmeta.evidence import CanonicalValue, MetadataEvidence
from beetsplug.noqlenmeta.field_contracts import IdentifierCollection, PartialDate
from beetsplug.noqlenmeta.resolver import ResolutionAction
from beetsplug.noqlenmeta.work_identity import WorkReference, canonical_work_references


@dataclass(frozen=True, slots=True)
class RecordingIdentityDecision:
    """One immutable Recording/Work resolution outcome."""

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


def resolve_recording_identity(
    current_values: Mapping[str, CanonicalValue],
    evidence: Sequence[MetadataEvidence],
) -> tuple[RecordingIdentityDecision, ...]:
    """Resolve Wave 1 Recording/Work fields without destructive omission."""
    grouped: dict[str, list[MetadataEvidence]] = defaultdict(list)
    for item in evidence:
        if item.field not in {"isrcs", "iswcs", "works", "recording_date"}:
            raise ValueError(f"unsupported recording identity field: {item.field}")
        if item.provider != "musicbrainz":
            continue
        grouped[item.field].append(item)
    return tuple(
        _resolve_field(field, current_values.get(field), tuple(sorted(items, key=_evidence_key)))
        for field, items in sorted(grouped.items())
    )


def _resolve_field(
    field: str,
    current: CanonicalValue | None,
    items: tuple[MetadataEvidence, ...],
) -> RecordingIdentityDecision:
    if field in {"isrcs", "iswcs"}:
        value = _identifier_union(items)
    elif field == "works":
        value = _work_union(items)
    else:
        values = {item.value for item in items if isinstance(item.value, PartialDate)}
        if len(values) != 1 or len(values) != len({item.value for item in items}):
            return _decision(
                field,
                current,
                current,
                None,
                ResolutionAction.REVIEW,
                "eligible recording dates materially conflict",
                items,
                (),
            )
        value = next(iter(values))
    selected = items[0]
    return _with_current(field, current, value, selected, items)


def _identifier_union(items: tuple[MetadataEvidence, ...]) -> IdentifierCollection:
    values = {
        identifier
        for item in items
        if isinstance(item.value, IdentifierCollection)
        for identifier in item.value.values
    }
    if not values:
        raise ValueError("identifier evidence must contain IdentifierCollection values")
    ordered = tuple(sorted(values, key=lambda value: (value.namespace, value.value)))
    return IdentifierCollection(ordered)


def _work_union(items: tuple[MetadataEvidence, ...]) -> tuple[WorkReference, ...]:
    values = [
        reference
        for item in items
        if isinstance(item.value, tuple)
        for reference in item.value
        if isinstance(reference, WorkReference)
    ]
    if not values:
        raise ValueError("Work evidence must contain WorkReference values")
    return canonical_work_references(values)


def _with_current(
    field: str,
    current: CanonicalValue | None,
    incoming: CanonicalValue,
    selected: MetadataEvidence,
    contributors: tuple[MetadataEvidence, ...],
) -> RecordingIdentityDecision:
    if current is None:
        return _decision(
            field,
            current,
            incoming,
            selected,
            ResolutionAction.PROPOSE,
            "exact MusicBrainz evidence supplies a missing value",
            (),
            contributors,
        )
    if field in {"isrcs", "iswcs"}:
        if not isinstance(current, IdentifierCollection) or not isinstance(
            incoming, IdentifierCollection
        ):
            return _conflict(field, current, selected, contributors)
        current_set = set(current.values)
        incoming_set = set(incoming.values)
        if incoming_set <= current_set:
            return _keep(field, current, selected, contributors)
        if current_set < incoming_set:
            return _propose(field, current, incoming, selected, contributors)
        return _conflict(field, current, selected, contributors)
    if field == "works":
        if not _is_work_tuple(current) or not _is_work_tuple(incoming):
            return _conflict(field, current, selected, contributors)
        current_works = cast(tuple[WorkReference, ...], current)
        incoming_works = cast(tuple[WorkReference, ...], incoming)
        current_ids = {value.mbid for value in current_works}
        incoming_ids = {value.mbid for value in incoming_works}
        if incoming_ids <= current_ids:
            return _keep(field, current, selected, contributors)
        if current_ids < incoming_ids:
            return _propose(field, current, incoming, selected, contributors)
        return _conflict(field, current, selected, contributors)
    if type(current) is type(incoming) and current == incoming:
        return _keep(field, current, selected, contributors)
    return _conflict(field, current, selected, contributors)


def _is_work_tuple(value: object) -> bool:
    return isinstance(value, tuple) and bool(value) and all(
        isinstance(item, WorkReference) for item in value
    )


def _propose(
    field: str,
    current: CanonicalValue,
    incoming: CanonicalValue,
    selected: MetadataEvidence,
    contributors: tuple[MetadataEvidence, ...],
) -> RecordingIdentityDecision:
    return _decision(
        field,
        current,
        incoming,
        selected,
        ResolutionAction.PROPOSE,
        "exact MusicBrainz evidence safely enriches existing identity",
        (),
        contributors,
    )


def _keep(
    field: str,
    current: CanonicalValue,
    selected: MetadataEvidence,
    contributors: tuple[MetadataEvidence, ...],
) -> RecordingIdentityDecision:
    return _decision(
        field,
        current,
        current,
        selected,
        ResolutionAction.KEEP,
        "existing identity is equal or a safe superset",
        (),
        contributors,
    )


def _conflict(
    field: str,
    current: CanonicalValue | None,
    selected: MetadataEvidence,
    contributors: tuple[MetadataEvidence, ...],
) -> RecordingIdentityDecision:
    return _decision(
        field,
        current,
        current,
        selected,
        ResolutionAction.REVIEW,
        "existing identity materially conflicts with exact MusicBrainz evidence",
        contributors,
        (),
    )


def _decision(
    field: str,
    current: CanonicalValue | None,
    value: CanonicalValue | None,
    selected: MetadataEvidence | None,
    action: ResolutionAction,
    reason: str,
    alternatives: tuple[MetadataEvidence, ...],
    contributors: tuple[MetadataEvidence, ...],
) -> RecordingIdentityDecision:
    return RecordingIdentityDecision(
        field,
        current,
        value,
        selected,
        action,
        reason,
        alternatives,
        contributors,
    )


def _evidence_key(item: MetadataEvidence) -> tuple[object, ...]:
    return (item.subject.entity.value, item.source_id, repr(item.value))
