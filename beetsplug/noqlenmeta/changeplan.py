"""Immutable, target-independent consequences of resolved metadata decisions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.evidence import CanonicalValue, MetadataEvidence
from beetsplug.noqlenmeta.release_catalog_resolution import CatalogFieldDecision
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction


class ChangePlanError(RuntimeError):
    """An impossible or inconsistent resolved-decision contract."""


@dataclass(frozen=True, slots=True)
class PlannedChange:
    """One explicit consequence of a resolved PROPOSE decision."""

    field: str
    before: CanonicalValue | None
    after: CanonicalValue
    source: MetadataCandidate | MetadataEvidence
    reason: str
    evidence: tuple[MetadataEvidence, ...] = ()

    def __post_init__(self) -> None:
        if self.source.field != self.field:
            raise ChangePlanError(
                f"selected candidate field {self.source.field!r} does not match {self.field!r}"
            )
        if isinstance(self.source, MetadataCandidate) and (
            type(self.source.value) is not type(self.after) or self.source.value != self.after
        ):
            raise ChangePlanError("planned value does not match the selected candidate value")
        evidence = tuple(self.evidence)
        if not all(isinstance(item, MetadataEvidence) for item in evidence):
            raise TypeError("evidence must contain MetadataEvidence values")
        if isinstance(self.source, MetadataEvidence) and not evidence:
            evidence = (self.source,)
        if isinstance(self.source, MetadataEvidence) and self.source not in evidence:
            raise ChangePlanError("selected evidence must be retained by the planned change")
        object.__setattr__(self, "evidence", evidence)


@dataclass(frozen=True, slots=True)
class ChangePlan:
    """Read-only metadata consequences grouped by resolved action."""

    changes: tuple[PlannedChange, ...] = ()
    reviews: tuple[FieldDecision | CatalogFieldDecision, ...] = ()
    kept: tuple[FieldDecision | CatalogFieldDecision, ...] = ()
    skipped: tuple[FieldDecision | CatalogFieldDecision, ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(self.changes)

    @property
    def requires_review(self) -> bool:
        return bool(self.reviews)

    @property
    def is_conflict_free(self) -> bool:
        return not self.reviews


def build_change_plan(decisions: Sequence[FieldDecision]) -> ChangePlan:
    """Translate resolved decisions into deterministic, read-only consequences."""

    changes: list[PlannedChange] = []
    reviews: list[FieldDecision] = []
    kept: list[FieldDecision] = []
    skipped: list[FieldDecision] = []
    seen_fields: set[str] = set()

    for decision in decisions:
        field = _canonical_field(decision.field)
        if field in seen_fields:
            raise ChangePlanError(f"duplicate decision for canonical field {field!r}")
        seen_fields.add(field)

        if decision.selected is not None and decision.selected.field != field:
            raise ChangePlanError(
                f"selected candidate field {decision.selected.field!r} does not match {field!r}"
            )

        if decision.action is ResolutionAction.PROPOSE:
            if decision.selected is None:
                raise ChangePlanError(f"PROPOSE decision for {field!r} has no selected candidate")
            changes.append(
                PlannedChange(
                    field=field,
                    before=decision.current_value,
                    after=decision.selected.value,
                    source=decision.selected,
                    reason=decision.reason,
                )
            )
        elif decision.action is ResolutionAction.REVIEW:
            reviews.append(decision)
        elif decision.action is ResolutionAction.KEEP:
            kept.append(decision)
        elif decision.action is ResolutionAction.SKIP:
            skipped.append(decision)
        else:
            raise ChangePlanError(f"unsupported resolution action for {field!r}")

    return ChangePlan(
        changes=tuple(sorted(changes, key=lambda change: change.field)),
        reviews=tuple(sorted(reviews, key=lambda decision: decision.field)),
        kept=tuple(sorted(kept, key=lambda decision: decision.field)),
        skipped=tuple(sorted(skipped, key=lambda decision: decision.field)),
    )


def build_catalog_change_plan(
    decisions: Sequence[CatalogFieldDecision],
) -> ChangePlan:
    """Translate V3 catalog decisions into the shared immutable ChangePlan."""
    changes: list[PlannedChange] = []
    reviews: list[CatalogFieldDecision] = []
    kept: list[CatalogFieldDecision] = []
    skipped: list[CatalogFieldDecision] = []
    seen_fields: set[str] = set()
    for decision in decisions:
        field = _canonical_field(decision.field)
        if field in seen_fields:
            raise ChangePlanError(f"duplicate decision for canonical field {field!r}")
        seen_fields.add(field)
        if decision.action is ResolutionAction.PROPOSE:
            if decision.selected is None or decision.value is None:
                raise ChangePlanError(f"PROPOSE decision for {field!r} is incomplete")
            contributors = (decision.selected, *decision.alternatives)
            changes.append(
                PlannedChange(
                    field,
                    decision.current_value,
                    decision.value,
                    decision.selected,
                    decision.reason,
                    contributors,
                )
            )
        elif decision.action is ResolutionAction.REVIEW:
            reviews.append(decision)
        elif decision.action is ResolutionAction.KEEP:
            kept.append(decision)
        elif decision.action is ResolutionAction.SKIP:
            skipped.append(decision)
        else:
            raise ChangePlanError(f"unsupported resolution action for {field!r}")
    return ChangePlan(
        changes=tuple(sorted(changes, key=lambda change: change.field)),
        reviews=tuple(sorted(reviews, key=lambda decision: decision.field)),
        kept=tuple(sorted(kept, key=lambda decision: decision.field)),
        skipped=tuple(sorted(skipped, key=lambda decision: decision.field)),
    )


def _canonical_field(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChangePlanError("decision field must be a non-empty canonical name")
    canonical = value.strip().lower()
    if not canonical.replace("_", "").replace("-", "").isalnum() or value != canonical:
        raise ChangePlanError(f"decision field {value!r} is not canonical")
    return canonical
