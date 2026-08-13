"""Immutable, target-independent consequences of resolved metadata decisions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.evidence import CanonicalValue, MetadataEvidence


class PlannableDecision(Protocol):
    """Structural decision contract consumed by target-independent planning."""

    field: str
    current_value: CanonicalValue | None
    action: object
    reason: str

    @property
    def resolved_value(self) -> CanonicalValue | None: ...

    @property
    def selected_source(self) -> MetadataCandidate | MetadataEvidence | None: ...

    @property
    def contributing_evidence(self) -> tuple[MetadataEvidence, ...]: ...


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
    reviews: tuple[PlannableDecision, ...] = ()
    kept: tuple[PlannableDecision, ...] = ()
    skipped: tuple[PlannableDecision, ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(self.changes)

    @property
    def requires_review(self) -> bool:
        return bool(self.reviews)

    @property
    def is_conflict_free(self) -> bool:
        return not self.reviews


def build_change_plan(decisions: Sequence[PlannableDecision]) -> ChangePlan:
    """Translate resolved decisions into deterministic, read-only consequences."""

    changes: list[PlannedChange] = []
    reviews: list[PlannableDecision] = []
    kept: list[PlannableDecision] = []
    skipped: list[PlannableDecision] = []
    seen_fields: set[str] = set()

    for decision in decisions:
        field = _canonical_field(decision.field)
        if field in seen_fields:
            raise ChangePlanError(f"duplicate decision for canonical field {field!r}")
        seen_fields.add(field)

        selected = decision.selected_source
        if selected is not None and selected.field != field:
            raise ChangePlanError(
                f"selected candidate field {selected.field!r} does not match {field!r}"
            )

        action = _action_name(decision.action)
        if action == "PROPOSE":
            value = decision.resolved_value
            if selected is None:
                raise ChangePlanError(f"PROPOSE decision for {field!r} has no selected candidate")
            if value is None:
                raise ChangePlanError(f"PROPOSE decision for {field!r} has no resolved value")
            changes.append(
                PlannedChange(
                    field=field,
                    before=decision.current_value,
                    after=value,
                    source=selected,
                    reason=decision.reason,
                    evidence=decision.contributing_evidence,
                )
            )
        elif action == "REVIEW":
            reviews.append(decision)
        elif action == "KEEP":
            kept.append(decision)
        elif action == "SKIP":
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
    decisions: Sequence[PlannableDecision],
) -> ChangePlan:
    """Compatibility wrapper for callers of the Wave 1A builder."""
    return build_change_plan(decisions)


def compose_change_plans(*plans: ChangePlan, suppress_fields: Sequence[str] = ()) -> ChangePlan:
    """Combine independently resolved domains while rejecting canonical collisions."""
    suppressed = {_canonical_field(field) for field in suppress_fields}
    changes = [
        change for plan in plans for change in plan.changes if change.field not in suppressed
    ]
    groups = tuple(
        tuple(
            decision
            for plan in plans
            for decision in decisions(plan)
            if decision.field not in suppressed
        )
        for decisions in (
            lambda plan: plan.reviews,
            lambda plan: plan.kept,
            lambda plan: plan.skipped,
        )
    )
    fields = [change.field for change in changes] + [
        decision.field for group in groups for decision in group
    ]
    if len(fields) != len(set(fields)):
        raise ChangePlanError("duplicate canonical field while composing ChangePlans")
    return ChangePlan(
        tuple(sorted(changes, key=lambda change: change.field)),
        tuple(sorted(groups[0], key=lambda decision: decision.field)),
        tuple(sorted(groups[1], key=lambda decision: decision.field)),
        tuple(sorted(groups[2], key=lambda decision: decision.field)),
    )


def _action_name(value: object) -> str:
    name = getattr(value, "name", None)
    if not isinstance(name, str):
        raise ChangePlanError("resolution action must be an enum value")
    return name


def _canonical_field(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChangePlanError("decision field must be a non-empty canonical name")
    canonical = value.strip().lower()
    if not canonical.replace("_", "").replace("-", "").isalnum() or value != canonical:
        raise ChangePlanError(f"decision field {value!r} is not canonical")
    return canonical
