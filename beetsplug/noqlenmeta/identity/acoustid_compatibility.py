from __future__ import annotations

from dataclasses import dataclass

from beetsplug.noqlenmeta.acoustid.domain import (
    AcoustIDEvidenceVerdict,
    AcoustIDTrackEvidence,
)

from .assignment import IdentityTrackAssignment
from .domain import canonical_mbid
from .scoring import IdentityCandidateEvaluation


@dataclass(frozen=True, slots=True)
class AcoustIDRecordingExpectations:
    entries: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        seen: set[str] = set()
        normalized = []
        for local_key, recording_mbid in entries:
            if not isinstance(local_key, str) or not local_key.strip():
                raise ValueError("AcoustID expectation local key is invalid")
            canonical = canonical_mbid(recording_mbid)
            if canonical is None:
                raise ValueError("AcoustID expectation recording MBID is invalid")
            if local_key in seen:
                raise ValueError("duplicate AcoustID recording expectation")
            seen.add(local_key)
            normalized.append((local_key, canonical))
        object.__setattr__(self, "entries", tuple(normalized))

    @classmethod
    def from_evidence(
        cls, evidence: tuple[AcoustIDTrackEvidence, ...]
    ) -> AcoustIDRecordingExpectations:
        values = tuple(evidence)
        if any(type(item) is not AcoustIDTrackEvidence for item in values):
            raise TypeError("AcoustID expectations require track evidence")
        return cls(
            tuple(
                (item.local_key, item.selected_recording_mbid)
                for item in values
                if item.verdict is AcoustIDEvidenceVerdict.DECISIVE
                and item.selected_recording_mbid is not None
            )
        )


@dataclass(frozen=True, slots=True)
class IdentityAcoustIDCompatibility:
    expectations: AcoustIDRecordingExpectations
    evaluations: tuple[IdentityCandidateEvaluation, ...]
    compatible_evaluations: tuple[IdentityCandidateEvaluation, ...]


def filter_identity_evaluations_by_acoustid(
    evaluations: tuple[IdentityCandidateEvaluation, ...],
    expectations: AcoustIDRecordingExpectations,
    *,
    local_keys: tuple[str, ...],
) -> IdentityAcoustIDCompatibility:
    values = tuple(evaluations)
    if any(type(item) is not IdentityCandidateEvaluation for item in values):
        raise TypeError("AcoustID compatibility requires identity evaluations")
    if type(expectations) is not AcoustIDRecordingExpectations:
        raise TypeError("AcoustID compatibility requires recording expectations")
    expected_local_keys = tuple(local_keys)
    if (
        any(not isinstance(key, str) or not key for key in expected_local_keys)
        or len(expected_local_keys) != len(set(expected_local_keys))
    ):
        raise ValueError("AcoustID compatibility local keys are inconsistent")
    compatible = tuple(
        evaluation
        for evaluation in values
        if _evaluation_is_compatible(evaluation, expectations, expected_local_keys)
    )
    return IdentityAcoustIDCompatibility(expectations, values, compatible)


def _evaluation_is_compatible(
    evaluation: IdentityCandidateEvaluation,
    expectations: AcoustIDRecordingExpectations,
    expected_local_keys: tuple[str, ...],
) -> bool:
    assignments = evaluation.assignment.assignments
    if any(type(item) is not IdentityTrackAssignment for item in assignments):
        return False
    local_keys = tuple(item.local_key for item in assignments)
    candidate_indices = tuple(item.candidate_index for item in assignments)
    candidate_count = len(evaluation.candidate.tracks)
    unmatched_local = evaluation.assignment.unmatched_local_keys
    unmatched_candidate = evaluation.assignment.unmatched_candidate_indices
    if (
        any(not isinstance(key, str) or not key for key in local_keys)
        or any(not isinstance(key, str) or not key for key in unmatched_local)
        or any(
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 0 <= index < candidate_count
            for index in (*candidate_indices, *unmatched_candidate)
        )
    ):
        return False
    if (
        len(local_keys) != len(set(local_keys))
        or len(unmatched_local) != len(set(unmatched_local))
        or set(local_keys) & set(unmatched_local)
        or set(local_keys) | set(unmatched_local) != set(expected_local_keys)
        or len(candidate_indices) != len(set(candidate_indices))
        or len(unmatched_candidate) != len(set(unmatched_candidate))
        or set(candidate_indices) & set(unmatched_candidate)
        or set(candidate_indices) | set(unmatched_candidate) != set(range(candidate_count))
    ):
        return False
    assignment_by_key = {item.local_key: item for item in assignments}
    for local_key, expected_recording_mbid in expectations.entries:
        assignment = assignment_by_key.get(local_key)
        if assignment is None:
            return False
        assigned_track = evaluation.candidate.tracks[assignment.candidate_index]
        if assigned_track.recording_mbid != expected_recording_mbid:
            return False
    return True
