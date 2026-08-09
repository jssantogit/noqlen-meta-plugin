from __future__ import annotations

from collections.abc import Callable

from .backend import FingerprintBackend, acquire_source_snapshot, prepare_fingerprint
from .domain import (
    AcoustIDSourceSnapshot,
    AcoustIDTargetResult,
    AcoustIDTrackOutcome,
    SelectedAcoustIDTarget,
)
from .mapping import canonical_acoustid_database_plan, snapshot_acoustid_target
from .service import AcoustIDLookupService
from .settings import AcoustIDSettings


def plan_acoustid_target(
    selected: SelectedAcoustIDTarget,
    settings: AcoustIDSettings,
    invocation_allows_missing_calculation: bool,
    backend_factory: Callable[[], FingerprintBackend],
    lookup_service: AcoustIDLookupService,
    *,
    snapshot_function: Callable[[bytes | str], AcoustIDSourceSnapshot] = acquire_source_snapshot,
) -> AcoustIDTargetResult:
    if type(selected) is not SelectedAcoustIDTarget:
        raise ValueError("AcoustID planning requires a selected target")
    planning_snapshot = snapshot_acoustid_target(selected)
    outcomes = []
    for item in selected.items:
        preparation = prepare_fingerprint(
            item,
            settings,
            invocation_allows_missing_calculation,
            backend_factory,
            snapshot_function=snapshot_function,
        )
        evidence = (
            lookup_service.lookup(preparation.material)
            if preparation.material is not None
            else None
        )
        outcomes.append(AcoustIDTrackOutcome(preparation, evidence))
    immutable_outcomes = tuple(outcomes)
    plan = canonical_acoustid_database_plan(planning_snapshot, immutable_outcomes)
    return AcoustIDTargetResult(selected, planning_snapshot, immutable_outcomes, plan)
