"""Internal orchestration boundary for V3 Wave 1A release catalog planning."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from beetsplug.noqlenmeta.changeplan import ChangePlan, build_catalog_change_plan
from beetsplug.noqlenmeta.evidence import CanonicalValue, MetadataEvidence
from beetsplug.noqlenmeta.release_catalog_mapping import (
    ReleaseCatalogTargetPlan,
    map_release_catalog_plan,
)
from beetsplug.noqlenmeta.release_catalog_resolution import (
    CatalogFieldDecision,
    resolve_release_catalog,
)


@dataclass(frozen=True, slots=True)
class ReleaseCatalogPlanningResult:
    decisions: tuple[CatalogFieldDecision, ...]
    change_plan: ChangePlan
    target_plan: ReleaseCatalogTargetPlan


def plan_release_catalog(
    current_values: Mapping[str, CanonicalValue],
    evidence: Sequence[MetadataEvidence],
) -> ReleaseCatalogPlanningResult:
    """Resolve and target-plan already acquired evidence without side effects."""
    decisions = resolve_release_catalog(current_values, evidence)
    change_plan = build_catalog_change_plan(decisions)
    target_plan = map_release_catalog_plan(change_plan)
    return ReleaseCatalogPlanningResult(decisions, change_plan, target_plan)
