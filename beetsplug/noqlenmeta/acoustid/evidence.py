from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from .domain import (
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDFingerprintOrigin,
    AcoustIDResultGroup,
    AcoustIDTrackEvidence,
    normalize_result_groups,
)


def classify_acoustid_evidence(
    local_key: str,
    fingerprint_origin: AcoustIDFingerprintOrigin | None,
    result_groups: Iterable[AcoustIDResultGroup],
    policy: AcoustIDEvidencePolicy,
) -> AcoustIDTrackEvidence:
    if not isinstance(policy, AcoustIDEvidencePolicy):
        raise ValueError("policy must be an AcoustIDEvidencePolicy")
    groups = normalize_result_groups(result_groups, policy)
    eligible = tuple(group for group in groups if group.score >= policy.min_score)
    support: dict[str, float] = {}
    for group in eligible:
        for recording_mbid in group.recording_mbids:
            support[recording_mbid] = max(support.get(recording_mbid, 0.0), group.score)

    common = {
        "local_key": local_key,
        "fingerprint_origin": fingerprint_origin,
        "result_groups": groups,
        "eligible_result_count": len(eligible),
        "eligible_recording_count": len(support),
    }
    if not support:
        return AcoustIDTrackEvidence(
            **common,
            verdict=AcoustIDEvidenceVerdict.NO_MATCH,
            selected_acoustid_id=None,
            selected_recording_mbid=None,
            reason=AcoustIDEvidenceReason.NO_RESULT_ABOVE_MINIMUM,
            top_score=None,
            runner_up_score=None,
            margin=None,
        )

    candidates = sorted(support.items(), key=lambda item: (-item[1], item[0]))
    selected_recording, top_score = candidates[0]
    runner_up_score = candidates[1][1] if len(candidates) > 1 else None
    margin = top_score - runner_up_score if runner_up_score is not None else None
    if runner_up_score == top_score:
        return AcoustIDTrackEvidence(
            **common,
            verdict=AcoustIDEvidenceVerdict.AMBIGUOUS,
            selected_acoustid_id=None,
            selected_recording_mbid=None,
            reason=AcoustIDEvidenceReason.COMPETING_RECORDINGS,
            top_score=top_score,
            runner_up_score=runner_up_score,
            margin=margin,
        )
    if (
        margin is not None
        and Decimal(str(top_score)) - Decimal(str(runner_up_score))
        < Decimal(str(policy.min_margin))
    ):
        return AcoustIDTrackEvidence(
            **common,
            verdict=AcoustIDEvidenceVerdict.AMBIGUOUS,
            selected_acoustid_id=None,
            selected_recording_mbid=None,
            reason=AcoustIDEvidenceReason.INSUFFICIENT_MARGIN,
            top_score=top_score,
            runner_up_score=runner_up_score,
            margin=margin,
        )

    selected_group = min(
        (group for group in eligible if selected_recording in group.recording_mbids),
        key=lambda group: (-group.score, group.acoustid_id),
    )
    return AcoustIDTrackEvidence(
        **common,
        verdict=AcoustIDEvidenceVerdict.DECISIVE,
        selected_acoustid_id=selected_group.acoustid_id,
        selected_recording_mbid=selected_recording,
        reason=AcoustIDEvidenceReason.RECORDING_DECISIVE,
        top_score=top_score,
        runner_up_score=runner_up_score,
        margin=margin,
    )
