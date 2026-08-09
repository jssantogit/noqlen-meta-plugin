from __future__ import annotations

from collections import Counter

from .domain import (
    AcoustIDDatabaseState,
    AcoustIDEvidenceReason,
    AcoustIDFingerprintOrigin,
    AcoustIDTargetResult,
    AcoustIDTrackOutcome,
)


def render_acoustid_preview(result: AcoustIDTargetResult) -> str:
    if not isinstance(result, AcoustIDTargetResult):
        raise ValueError("AcoustID preview requires a target result")
    states = Counter(track.state for track in result.database_plan.tracks)
    lines = [
        f"AcoustID {result.planning_snapshot.kind.value}",
        f"Tracks      {len(result.outcomes)}",
        "Summary     "
        + " ".join(f"{state.value}={states[state]}" for state in AcoustIDDatabaseState),
    ]
    for outcome, plan in zip(result.outcomes, result.database_plan.tracks, strict=True):
        evidence = outcome.evidence
        lines.extend(
            (
                f"Track       {outcome.local_key}",
                f"Fingerprint {_fingerprint_state(outcome)}",
                f"Lookup      {evidence.verdict.value.upper() if evidence else 'UNAVAILABLE'}",
                "AcoustID     "
                + (
                    evidence.selected_acoustid_id[:8]
                    if evidence and evidence.selected_acoustid_id
                    else "none"
                ),
                "Recording    "
                + (
                    evidence.selected_recording_mbid
                    if evidence and evidence.selected_recording_mbid
                    else "none"
                ),
                f"Database    {plan.state.value}",
                f"Reason      {_reason(outcome, plan.state).value}",
            )
        )
    return "\n".join(lines)


def _fingerprint_state(outcome: AcoustIDTrackOutcome) -> str:
    material = outcome.preparation.material
    if material is not None:
        return (
            "REUSED"
            if material.origin is AcoustIDFingerprintOrigin.EXISTING
            else "GENERATED"
        )
    if outcome.preparation.reason is AcoustIDEvidenceReason.FINGERPRINT_MISSING:
        return "MISSING"
    return "UNAVAILABLE"


def _reason(
    outcome: AcoustIDTrackOutcome, database_state: AcoustIDDatabaseState
) -> AcoustIDEvidenceReason:
    if database_state is AcoustIDDatabaseState.REVIEW:
        return AcoustIDEvidenceReason.EXISTING_VALUE_CONFLICT
    if database_state is AcoustIDDatabaseState.BLOCKED:
        return AcoustIDEvidenceReason.STALE_SOURCE_FILE
    return outcome.evidence.reason if outcome.evidence is not None else outcome.preparation.reason
