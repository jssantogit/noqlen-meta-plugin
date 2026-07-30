from dataclasses import replace

import pytest

from beetsplug.noqlenmeta.identity import (
    evaluate_identity_candidate,
    rank_identity_candidates,
)

from .helpers import candidate, candidate_track, context, local_track, mbid


def test_exact_structural_candidate_scores_strongly_and_totals_exactly() -> None:
    score = evaluate_identity_candidate(context(), candidate()).score

    assert score.total == pytest.approx(100.0)
    assert score.total == pytest.approx(
        score.album_artist
        + score.album_title
        + score.track_count
        + score.track_titles
        + score.track_durations
        + score.track_order
    )
    assert 0 <= score.total <= 100


def test_wrong_tracklist_and_duration_lower_score() -> None:
    wrong_titles = candidate(
        tracks=tuple(candidate_track(index, title=f"Wrong {index}") for index in range(1, 4))
    )
    wrong_duration = candidate(
        tracks=tuple(candidate_track(index, length=500) for index in range(1, 4))
    )

    exact = evaluate_identity_candidate(context(), candidate()).score.total
    assert evaluate_identity_candidate(context(), wrong_titles).score.total < 90
    assert evaluate_identity_candidate(context(), wrong_duration).score.total < exact


def test_missing_candidate_durations_are_unavailable_and_remaining_score_renormalizes() -> None:
    without_durations = candidate(
        tracks=tuple(
            replace(candidate_track(index), length=None) for index in range(1, 4)
        )
    )

    score = evaluate_identity_candidate(context(), without_durations).score

    assert score.track_durations == 0
    assert score.total == pytest.approx(100.0)


def test_partial_duration_quality_uses_only_comparable_assigned_pairs() -> None:
    partial = candidate(
        tracks=(
            candidate_track(1),
            candidate_track(2, length=500),
            replace(candidate_track(3), length=None),
        )
    )

    score = evaluate_identity_candidate(context(), partial).score

    assert score.track_durations == pytest.approx(5.0)
    assert score.total == pytest.approx(95.0)


def test_missing_local_duration_is_unavailable_not_a_match_or_mismatch() -> None:
    local = context(tracks=(replace(local_track(1), length=None),))

    score = evaluate_identity_candidate(local, candidate(1)).score

    assert score.track_durations == 0
    assert score.total == pytest.approx(100.0)


def test_edition_markers_are_not_stripped() -> None:
    local = context(
        tracks=(local_track(1, title="Song (Live)"),), album="Album (Live)"
    )
    exact = candidate(
        tracks=(candidate_track(1, title="Song (Live)"),), album="Album (Live)"
    )
    studio = candidate(tracks=(candidate_track(1, title="Song"),), album="Album")

    assert evaluate_identity_candidate(local, exact).score.total > evaluate_identity_candidate(
        local, studio
    ).score.total


def test_track_count_mismatch_lowers_score_but_candidate_extras_are_represented() -> None:
    result = evaluate_identity_candidate(context(), candidate(4))

    assert result.score.total < evaluate_identity_candidate(context(), candidate()).score.total
    assert result.assignment.unmatched_candidate_indices == (3,)


def test_reordered_album_with_correct_positions_remains_strong() -> None:
    reordered = context(tracks=(local_track(3), local_track(1), local_track(2)))

    assert evaluate_identity_candidate(reordered, candidate()).score.total == pytest.approx(100)


def test_existing_ids_do_not_change_score() -> None:
    plain = context()
    with_wrong_ids = context(
        tracks=tuple(local_track(index, recording=mbid(900 + index)) for index in range(1, 4)),
        release_ids=(mbid(999),),
    )

    assert evaluate_identity_candidate(plain, candidate()).score == evaluate_identity_candidate(
        with_wrong_ids, candidate()
    ).score


def test_ranking_is_deterministic_by_score_then_release_mbid() -> None:
    first = candidate(release=mbid(2))
    second = candidate(release=mbid(1))

    ranked = rank_identity_candidates(context(), (first, second))

    assert [item.candidate.release_mbid for item in ranked] == [mbid(1), mbid(2)]
