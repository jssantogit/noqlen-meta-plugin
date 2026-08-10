from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from .acoustid_compatibility import (
    AcoustIDRecordingExpectations,
    IdentityAcoustIDCompatibility,
    filter_identity_evaluations_by_acoustid,
)
from .domain import (
    IdentityAlbumContext,
    IdentityAuditPolicy,
    IdentityFieldFinding,
    IdentityFieldStatus,
    IdentityVerdict,
    MusicBrainzReleaseIdentity,
    canonical_mbid,
)
from .scoring import IdentityCandidateEvaluation, rank_identity_candidates

DEFAULT_IDENTITY_AUDIT_POLICY = IdentityAuditPolicy()


class MusicBrainzIdentitySource(Protocol):
    def candidates_for(
        self, context: IdentityAlbumContext
    ) -> Sequence[MusicBrainzReleaseIdentity]: ...


@dataclass(frozen=True, slots=True)
class IdentityAuditResult:
    verdict: IdentityVerdict
    reason: str
    context: IdentityAlbumContext
    evaluations: tuple[IdentityCandidateEvaluation, ...]
    selected_candidate: MusicBrainzReleaseIdentity | None
    selected_evaluation: IdentityCandidateEvaluation | None
    field_findings: tuple[IdentityFieldFinding, ...]
    repair_ready: bool
    acoustid_compatibility: IdentityAcoustIDCompatibility | None = None

    @property
    def has_conflicts(self) -> bool:
        return any(item.status is IdentityFieldStatus.CONFLICT for item in self.field_findings)

    @property
    def has_missing(self) -> bool:
        return any(item.status is IdentityFieldStatus.MISSING for item in self.field_findings)

    @property
    def is_confirmed(self) -> bool:
        return self.verdict is IdentityVerdict.CONFIRMED

    @property
    def is_ambiguous(self) -> bool:
        return self.verdict is IdentityVerdict.AMBIGUOUS


def audit_musicbrainz_identity(
    context: IdentityAlbumContext,
    candidates: Sequence[MusicBrainzReleaseIdentity],
    *,
    policy: IdentityAuditPolicy = DEFAULT_IDENTITY_AUDIT_POLICY,
    acoustid_expectations: AcoustIDRecordingExpectations | None = None,
) -> IdentityAuditResult:
    candidate_tuple = tuple(candidates)
    if any(not isinstance(candidate, MusicBrainzReleaseIdentity) for candidate in candidate_tuple):
        raise TypeError("candidates must be MusicBrainzReleaseIdentity values")
    return audit_identity_candidate_evaluations(
        context,
        rank_identity_candidates(context, candidate_tuple),
        policy=policy,
        acoustid_expectations=acoustid_expectations,
    )


def audit_identity_candidate_evaluations(
    context: IdentityAlbumContext,
    evaluations: tuple[IdentityCandidateEvaluation, ...],
    *,
    policy: IdentityAuditPolicy = DEFAULT_IDENTITY_AUDIT_POLICY,
    acoustid_expectations: AcoustIDRecordingExpectations | None = None,
) -> IdentityAuditResult:
    structural_evaluations = tuple(evaluations)
    if any(
        type(evaluation) is not IdentityCandidateEvaluation
        for evaluation in structural_evaluations
    ):
        raise TypeError("evaluations must be IdentityCandidateEvaluation values")
    if not structural_evaluations:
        return _ambiguous(context, structural_evaluations, "no_candidates")
    compatibility = None
    evaluations = structural_evaluations
    if acoustid_expectations is not None and acoustid_expectations.entries:
        compatibility = filter_identity_evaluations_by_acoustid(
            structural_evaluations,
            acoustid_expectations,
            local_keys=tuple(track.local_key for track in context.tracks),
        )
        evaluations = compatibility.compatible_evaluations
        if not evaluations:
            return _ambiguous(
                context,
                evaluations,
                "acoustid_recording_conflict",
                acoustid_compatibility=compatibility,
            )
    top = evaluations[0]
    singleton = len(context.tracks) == 1
    minimum_score = policy.singleton_minimum_score if singleton else policy.minimum_score
    minimum_margin = policy.singleton_minimum_margin if singleton else policy.minimum_margin
    if top.score.total < minimum_score:
        return _ambiguous(
            context,
            evaluations,
            "below_minimum_score",
            acoustid_compatibility=compatibility,
        )
    if not _candidate_identity_is_safe(top.candidate):
        return _ambiguous(
            context,
            evaluations,
            "invalid_candidate_identity",
            acoustid_compatibility=compatibility,
        )
    if policy.require_all_local_tracks_assigned and top.assignment.unmatched_local_keys:
        return _ambiguous(
            context,
            evaluations,
            "unmatched_local_tracks",
            acoustid_compatibility=compatibility,
        )
    if top.assignment.ambiguous:
        return _ambiguous(
            context,
            evaluations,
            "ambiguous_track_assignment",
            acoustid_compatibility=compatibility,
        )
    if any(item.pair_score < policy.minimum_pair_score for item in top.assignment.assignments):
        return _ambiguous(
            context,
            evaluations,
            "weak_track_assignment",
            acoustid_compatibility=compatibility,
        )
    if len(evaluations) > 1 and top.score.total - evaluations[1].score.total < minimum_margin:
        return _ambiguous(
            context,
            evaluations,
            "insufficient_margin",
            acoustid_compatibility=compatibility,
        )
    findings = _identity_findings(context, top)
    if any(item.status is IdentityFieldStatus.CONFLICT for item in findings):
        verdict = IdentityVerdict.CONFLICT
        reason = "identity_conflict"
    elif any(item.status is IdentityFieldStatus.MISSING for item in findings):
        verdict = IdentityVerdict.MISSING
        reason = "identity_missing"
    else:
        verdict = IdentityVerdict.CONFIRMED
        reason = "identity_confirmed"
    return IdentityAuditResult(
        verdict=verdict,
        reason=reason,
        context=context,
        evaluations=evaluations,
        selected_candidate=top.candidate,
        selected_evaluation=top,
        field_findings=findings,
        repair_ready=(
            verdict in {IdentityVerdict.MISSING, IdentityVerdict.CONFLICT}
            and not top.assignment.unmatched_local_keys
            and len(top.assignment.assignments) == len(context.tracks)
        ),
        acoustid_compatibility=compatibility,
    )


def audit_with_musicbrainz_source(
    context: IdentityAlbumContext,
    source: MusicBrainzIdentitySource,
    *,
    policy: IdentityAuditPolicy = DEFAULT_IDENTITY_AUDIT_POLICY,
    acoustid_expectations: AcoustIDRecordingExpectations | None = None,
) -> IdentityAuditResult:
    return audit_musicbrainz_identity(
        context,
        source.candidates_for(context),
        policy=policy,
        acoustid_expectations=acoustid_expectations,
    )


def _ambiguous(
    context: IdentityAlbumContext,
    evaluations: tuple[IdentityCandidateEvaluation, ...],
    reason: str,
    *,
    acoustid_compatibility: IdentityAcoustIDCompatibility | None = None,
) -> IdentityAuditResult:
    return IdentityAuditResult(
        verdict=IdentityVerdict.AMBIGUOUS,
        reason=reason,
        context=context,
        evaluations=evaluations,
        selected_candidate=None,
        selected_evaluation=None,
        field_findings=(),
        repair_ready=False,
        acoustid_compatibility=acoustid_compatibility,
    )


def _candidate_identity_is_safe(candidate: MusicBrainzReleaseIdentity) -> bool:
    release_tracks = [track.release_track_mbid for track in candidate.tracks]
    positions = [(track.medium, track.medium_index) for track in candidate.tracks]
    indexes = [track.index for track in candidate.tracks]
    if len(release_tracks) != len(set(release_tracks)):
        return False
    if len(positions) != len(set(positions)) or len(indexes) != len(set(indexes)):
        return False
    # A recording may occur more than once; its release-track identity remains unique.
    return True


def _identity_findings(
    context: IdentityAlbumContext, evaluation: IdentityCandidateEvaluation
) -> tuple[IdentityFieldFinding, ...]:
    candidate = evaluation.candidate
    findings = [
        _album_finding(
            "mb_albumid", context.current_release_mbids, candidate.release_mbid
        ),
        _album_finding(
            "mb_releasegroupid",
            context.current_release_group_mbids,
            candidate.release_group_mbid,
        ),
    ]
    assignment_by_key = {item.local_key: item for item in evaluation.assignment.assignments}
    for track in context.tracks:
        assignment = assignment_by_key.get(track.local_key)
        if assignment is None:
            continue
        expected = candidate.tracks[assignment.candidate_index]
        findings.extend(
            (
                _track_finding(
                    "mb_trackid",
                    track.local_key,
                    track.current_recording_mbid,
                    expected.recording_mbid,
                ),
                _track_finding(
                    "mb_releasetrackid",
                    track.local_key,
                    track.current_release_track_mbid,
                    expected.release_track_mbid,
                ),
            )
        )
    return tuple(findings)


def _album_finding(
    field: str, current_values: tuple[str, ...], expected: str
) -> IdentityFieldFinding:
    if not current_values:
        status = IdentityFieldStatus.MISSING
        current = None
    else:
        canonical = tuple(canonical_mbid(value) for value in current_values)
        status = (
            IdentityFieldStatus.CONFIRMED
            if all(value == expected for value in canonical)
            else IdentityFieldStatus.CONFLICT
        )
        current = current_values[0] if len(current_values) == 1 else " | ".join(current_values)
    return IdentityFieldFinding(field, None, current, expected, status)


def _track_finding(
    field: str, scope_key: str, current: str | None, expected: str
) -> IdentityFieldFinding:
    if current is None:
        status = IdentityFieldStatus.MISSING
    elif canonical_mbid(current) == expected:
        status = IdentityFieldStatus.CONFIRMED
    else:
        status = IdentityFieldStatus.CONFLICT
    return IdentityFieldFinding(field, scope_key, current, expected, status)
