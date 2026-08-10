from dataclasses import replace

import pytest

from beetsplug.noqlenmeta.acoustid import (
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDFingerprintOrigin,
    AcoustIDResultGroup,
    AcoustIDTrackEvidence,
    classify_acoustid_evidence,
)
from beetsplug.noqlenmeta.identity import (
    AcoustIDRecordingExpectations,
    IdentityAssignmentResult,
    IdentityAuditPolicy,
    IdentityVerdict,
    audit_musicbrainz_identity,
    filter_identity_evaluations_by_acoustid,
    rank_identity_candidates,
)

from .helpers import candidate, candidate_track, context, local_track, mbid


def decisive(local_key: str, recording: str) -> AcoustIDTrackEvidence:
    return classify_acoustid_evidence(
        local_key,
        AcoustIDFingerprintOrigin.EXISTING,
        (
            AcoustIDResultGroup(
                "00000001-0000-4000-8000-000000000001", 0.99, (recording,)
            ),
        ),
        AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
    )


def neutral(local_key: str) -> AcoustIDTrackEvidence:
    return AcoustIDTrackEvidence(
        local_key,
        None,
        (),
        AcoustIDEvidenceVerdict.UNAVAILABLE,
        None,
        None,
        AcoustIDEvidenceReason.LOOKUP_DISABLED,
        None,
        None,
        None,
        0,
        0,
    )


def expectations(*values: AcoustIDTrackEvidence) -> AcoustIDRecordingExpectations:
    return AcoustIDRecordingExpectations.from_evidence(values)


def test_expectations_include_only_decisive_fresh_evidence() -> None:
    value = expectations(neutral("local-1"), decisive("local-2", mbid(1002)))

    assert value.entries == (("local-2", mbid(1002)),)


def test_duplicate_or_conflicting_expectations_fail_closed() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        expectations(
            decisive("local-1", mbid(1001)),
            decisive("local-1", mbid(1001)),
        )
    with pytest.raises(ValueError, match="duplicate"):
        expectations(
            decisive("local-1", mbid(1001)),
            decisive("local-1", mbid(1002)),
        )


def test_decisive_match_and_one_of_multiple_mismatches_filter_existing_evaluations() -> None:
    local = context()
    first = candidate(release=mbid(100))
    second = candidate(
        release=mbid(101),
        tracks=(
            candidate_track(1),
            candidate_track(2, recording=mbid(9002)),
            candidate_track(3),
        ),
    )
    evaluations = rank_identity_candidates(local, (first, second))
    value = filter_identity_evaluations_by_acoustid(
        evaluations,
        AcoustIDRecordingExpectations(
            (("local-1", mbid(1001)), ("local-2", mbid(1002)))
        ),
        local_keys=tuple(track.local_key for track in local.tracks),
    )

    assert value.evaluations == evaluations
    assert value.compatible_evaluations == (evaluations[0],)
    assert value.compatible_evaluations[0] is evaluations[0]


def test_repeated_recording_occurrences_multidisc_and_bonus_tracks_use_assignment_index() -> None:
    local = context(
        4,
        tracks=(
            local_track(1, medium=1, medium_index=1),
            local_track(2, medium=1, medium_index=2),
            local_track(3, medium=2, medium_index=1),
            local_track(4, title="Bonus", medium=2, medium_index=2),
        ),
    )
    remote = candidate(
        4,
        tracks=(
            candidate_track(1, recording=mbid(1001), medium=1, medium_index=1),
            candidate_track(2, recording=mbid(1001), medium=1, medium_index=2),
            candidate_track(3, medium=2, medium_index=1),
            candidate_track(4, title="Bonus", medium=2, medium_index=2),
        ),
    )
    evaluations = rank_identity_candidates(local, (remote,))

    value = filter_identity_evaluations_by_acoustid(
        evaluations,
        AcoustIDRecordingExpectations(
            (("local-2", mbid(1001)), ("local-4", mbid(1004)))
        ),
        local_keys=tuple(track.local_key for track in local.tracks),
    )

    assert value.compatible_evaluations == evaluations


@pytest.mark.parametrize(
    "failure", ["missing", "negative", "duplicate", "unaccounted", "unhashable"]
)
def test_inconsistent_assignment_fails_closed(failure: str) -> None:
    evaluation = rank_identity_candidates(context(), (candidate(),))[0]
    assignments = evaluation.assignment.assignments
    if failure == "missing":
        malformed = replace(
            evaluation,
            assignment=IdentityAssignmentResult(
                assignments[1:], ("local-1",), evaluation.assignment.unmatched_candidate_indices
            ),
        )
    elif failure == "negative":
        malformed = replace(
            evaluation,
            assignment=replace(
                evaluation.assignment,
                assignments=(replace(assignments[0], candidate_index=-1), *assignments[1:]),
            ),
        )
    elif failure == "duplicate":
        malformed = replace(
            evaluation,
            assignment=replace(
                evaluation.assignment,
                assignments=(
                    assignments[0],
                    replace(assignments[1], candidate_index=0),
                    assignments[2],
                ),
            ),
        )
    elif failure == "unaccounted":
        malformed = replace(
            evaluation,
            assignment=replace(
                evaluation.assignment,
                assignments=assignments[:-1],
                unmatched_candidate_indices=(),
            ),
        )
    else:
        malformed = replace(
            evaluation,
            assignment=replace(
                evaluation.assignment,
                unmatched_local_keys=([],),  # type: ignore[arg-type]
            ),
        )
    value = filter_identity_evaluations_by_acoustid(
        (malformed,),
        AcoustIDRecordingExpectations((("local-1", mbid(1001)),)),
        local_keys=("local-1", "local-2", "local-3"),
    )

    assert value.compatible_evaluations == ()


def test_no_expectations_is_behaviorally_identical() -> None:
    baseline = audit_musicbrainz_identity(context(), (candidate(),))
    result = audit_musicbrainz_identity(
        context(), (candidate(),), acoustid_expectations=AcoustIDRecordingExpectations()
    )

    assert result == baseline


def test_filter_preserves_score_pair_scores_assignments_and_threshold_gate() -> None:
    local = context()
    compatible = candidate(release=mbid(100))
    incompatible_runner_up = candidate(
        release=mbid(101),
        tracks=(candidate_track(1, recording=mbid(9001)), candidate_track(2), candidate_track(3)),
    )
    baseline = rank_identity_candidates(local, (compatible, incompatible_runner_up))
    result = audit_musicbrainz_identity(
        local,
        (compatible, incompatible_runner_up),
        acoustid_expectations=AcoustIDRecordingExpectations((("local-1", mbid(1001)),)),
    )

    assert result.verdict is IdentityVerdict.MISSING
    assert result.acoustid_compatibility is not None
    assert result.acoustid_compatibility.evaluations == baseline
    structural_top = result.acoustid_compatibility.evaluations[0]
    assert result.selected_evaluation is structural_top
    assert result.selected_evaluation.score is structural_top.score
    assert result.selected_evaluation.assignment is structural_top.assignment
    selected_pair_scores = tuple(
        item.pair_score for item in result.selected_evaluation.assignment.assignments
    )
    assert selected_pair_scores == tuple(
        item.pair_score for item in baseline[0].assignment.assignments
    )


def test_all_incompatible_returns_stable_conflict_without_repair() -> None:
    result = audit_musicbrainz_identity(
        context(),
        (candidate(),),
        acoustid_expectations=AcoustIDRecordingExpectations((("local-1", mbid(9999)),)),
    )

    assert result.verdict is IdentityVerdict.AMBIGUOUS
    assert result.reason == "acoustid_recording_conflict"
    assert result.selected_candidate is None
    assert result.selected_evaluation is None
    assert result.field_findings == ()
    assert result.repair_ready is False


def test_weak_incomplete_ambiguous_and_margin_gates_remain_authoritative() -> None:
    expected = AcoustIDRecordingExpectations((("local-1", mbid(1001)),))
    weak = candidate(
        tracks=tuple(candidate_track(index, title=f"Unrelated {index}") for index in range(1, 4))
    )
    incomplete = candidate(2)
    ambiguous_local = context(
        2,
        tracks=(
            type(local_track(1))("track-1", "Example Artist", "Same", length=100),
            type(local_track(1))("track-2", "Example Artist", "Same", length=100),
        ),
    )
    ambiguous_remote = candidate(
        2,
        tracks=(
            candidate_track(1, title="Same", length=100),
            candidate_track(2, title="Same", length=100),
        ),
    )
    weak_pair = candidate(
        tracks=(candidate_track(1, length=190), candidate_track(2), candidate_track(3))
    )

    assert audit_musicbrainz_identity(
        context(), (weak,), acoustid_expectations=expected
    ).reason == "below_minimum_score"
    assert audit_musicbrainz_identity(
        context(),
        (incomplete,),
        policy=IdentityAuditPolicy(minimum_score=0),
        acoustid_expectations=expected,
    ).reason == "unmatched_local_tracks"
    assert audit_musicbrainz_identity(
        context(),
        (weak_pair,),
        policy=IdentityAuditPolicy(minimum_score=0, minimum_pair_score=99),
        acoustid_expectations=expected,
    ).reason == "weak_track_assignment"
    assert audit_musicbrainz_identity(
        ambiguous_local,
        (ambiguous_remote,),
        acoustid_expectations=AcoustIDRecordingExpectations((("track-1", mbid(1001)),)),
    ).reason == "ambiguous_track_assignment"
    assert audit_musicbrainz_identity(
        context(),
        (candidate(release=mbid(100)), candidate(release=mbid(101))),
        acoustid_expectations=expected,
    ).reason == "insufficient_margin"


def test_filter_is_deterministic() -> None:
    evaluations = rank_identity_candidates(
        context(), (candidate(release=mbid(102)), candidate(release=mbid(101)))
    )
    expected = AcoustIDRecordingExpectations((("local-1", mbid(1001)),))

    assert filter_identity_evaluations_by_acoustid(
        evaluations,
        expected,
        local_keys=("local-1", "local-2", "local-3"),
    ) == filter_identity_evaluations_by_acoustid(
        evaluations,
        expected,
        local_keys=("local-1", "local-2", "local-3"),
    )


def test_omitted_unrelated_local_assignment_is_incompatible() -> None:
    evaluation = rank_identity_candidates(context(), (candidate(),))[0]
    malformed = replace(
        evaluation,
        assignment=replace(
            evaluation.assignment,
            assignments=evaluation.assignment.assignments[1:],
            unmatched_local_keys=(),
            unmatched_candidate_indices=(0,),
        ),
    )

    value = filter_identity_evaluations_by_acoustid(
        (malformed,),
        AcoustIDRecordingExpectations((("local-2", mbid(1002)),)),
        local_keys=("local-1", "local-2", "local-3"),
    )

    assert value.compatible_evaluations == ()
