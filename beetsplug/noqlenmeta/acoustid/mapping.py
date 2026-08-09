from __future__ import annotations

from .domain import (
    AcoustIDDatabaseState,
    AcoustIDDatabaseTargetPlan,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDExistingValues,
    AcoustIDFieldPlan,
    AcoustIDPlanningItemSnapshot,
    AcoustIDPlanningSnapshot,
    AcoustIDStoredValueState,
    AcoustIDTrackDatabasePlan,
    AcoustIDTrackOutcome,
    SelectedAcoustIDTarget,
)


def snapshot_acoustid_target(selected: SelectedAcoustIDTarget) -> AcoustIDPlanningSnapshot:
    if type(selected) is not SelectedAcoustIDTarget:
        raise ValueError("planning snapshot requires a selected AcoustID target")
    if any(
        item.item.id != item.item_id
        or (
            item.item.album_id != item.album_id
            and not (item.album_id is None and item.item.album_id in (None, 0))
        )
        or item.item.path != item.media_path
        for item in selected.items
    ):
        raise ValueError("selected AcoustID target changed before planning")
    if any(
        AcoustIDExistingValues.from_stored(
            item.item.acoustid_id,
            item.item.acoustid_fingerprint,
            item.item.length,
        )
        != item.existing_values
        for item in selected.items
    ):
        raise ValueError("selected AcoustID values changed before planning")
    return AcoustIDPlanningSnapshot(
        selected.kind,
        selected.album_id,
        tuple(
            AcoustIDPlanningItemSnapshot(
                local_key=item.local_key,
                item_id=item.item_id,
                album_id=item.item.album_id,
                media_path=item.media_path,
                length=item.item.length,
                acoustid_id=item.item.acoustid_id,
                acoustid_fingerprint=item.item.acoustid_fingerprint,
            )
            for item in selected.items
        ),
    )


def canonical_acoustid_database_plan(
    snapshot: AcoustIDPlanningSnapshot,
    outcomes: tuple[AcoustIDTrackOutcome, ...],
) -> AcoustIDDatabaseTargetPlan:
    if not isinstance(snapshot, AcoustIDPlanningSnapshot):
        raise ValueError("canonical mapping requires a planning snapshot")
    outcomes = tuple(outcomes)
    if tuple(item.local_key for item in snapshot.items) != tuple(
        outcome.local_key for outcome in outcomes
    ):
        raise ValueError("canonical mapping track ordering is inconsistent")
    return AcoustIDDatabaseTargetPlan(
        tuple(
            _map_track(item, outcome)
            for item, outcome in zip(snapshot.items, outcomes, strict=True)
        )
    )


def _map_track(
    snapshot: AcoustIDPlanningItemSnapshot,
    outcome: AcoustIDTrackOutcome,
) -> AcoustIDTrackDatabasePlan:
    current = AcoustIDExistingValues.from_stored(
        snapshot.acoustid_id,
        snapshot.acoustid_fingerprint,
        snapshot.length,
    )
    evidence = outcome.evidence
    proposed_id = (
        evidence.selected_acoustid_id
        if evidence is not None and evidence.verdict is AcoustIDEvidenceVerdict.DECISIVE
        else None
    )
    id_plan = _identifier_plan(current, proposed_id)

    material = outcome.preparation.material
    if outcome.preparation.reason is AcoustIDEvidenceReason.STALE_SOURCE_FILE:
        fingerprint_plan = AcoustIDFieldPlan(AcoustIDDatabaseState.BLOCKED)
    elif material is None:
        fingerprint_plan = AcoustIDFieldPlan(AcoustIDDatabaseState.KEEP)
    else:
        fingerprint_plan = _fingerprint_plan(current, material._fingerprint_text())
    return AcoustIDTrackDatabasePlan(snapshot.local_key, id_plan, fingerprint_plan)


def _identifier_plan(
    current: AcoustIDExistingValues, proposed: str | None
) -> AcoustIDFieldPlan:
    if proposed is None:
        return AcoustIDFieldPlan(AcoustIDDatabaseState.KEEP)
    if current.acoustid_id_state is AcoustIDStoredValueState.MISSING:
        return AcoustIDFieldPlan(AcoustIDDatabaseState.PROPOSE, proposed)
    if (
        current.acoustid_id_state is AcoustIDStoredValueState.VALID
        and current.acoustid_id == proposed
    ):
        return AcoustIDFieldPlan(AcoustIDDatabaseState.KEEP)
    return AcoustIDFieldPlan(AcoustIDDatabaseState.REVIEW, proposed)


def _fingerprint_plan(
    current: AcoustIDExistingValues, proposed: str
) -> AcoustIDFieldPlan:
    if current.fingerprint_state is AcoustIDStoredValueState.MISSING:
        return AcoustIDFieldPlan(AcoustIDDatabaseState.PROPOSE, proposed)
    if (
        current.fingerprint_state is AcoustIDStoredValueState.VALID
        and current._fingerprint == proposed
    ):
        return AcoustIDFieldPlan(AcoustIDDatabaseState.KEEP)
    return AcoustIDFieldPlan(AcoustIDDatabaseState.REVIEW, proposed)
