from beetsplug.noqlenmeta.identity import assign_identity_tracks, score_track_pair

from .helpers import candidate_track, local_track, mbid


def mapping(result: object) -> dict[str, int]:
    return {item.local_key: item.candidate_index for item in result.assignments}  # type: ignore[attr-defined]


def test_exact_ordered_album_assigns_every_track() -> None:
    result = assign_identity_tracks(
        tuple(local_track(index) for index in range(1, 4)),
        tuple(candidate_track(index) for index in range(1, 4)),
    )

    assert mapping(result) == {"local-1": 0, "local-2": 1, "local-3": 2}
    assert not result.unmatched_local_keys
    assert not result.unmatched_candidate_indices


def test_reordered_local_tracks_use_global_metadata_assignment_not_zip() -> None:
    locals_ = (local_track(2), local_track(1), local_track(3))
    candidates = tuple(candidate_track(index) for index in range(1, 4))

    result = assign_identity_tracks(locals_, candidates)

    assert mapping(result) == {"local-2": 1, "local-1": 0, "local-3": 2}


def test_multidisc_duplicate_track_numbers_are_distinguished() -> None:
    locals_ = (
        local_track(2, title="Disc Two", medium=2, medium_index=1),
        local_track(1, title="Disc One", medium=1, medium_index=1),
    )
    candidates = (
        candidate_track(1, title="Disc One", medium=1, medium_index=1),
        candidate_track(2, title="Disc Two", medium=2, medium_index=1),
    )

    assert mapping(assign_identity_tracks(locals_, candidates)) == {
        "local-2": 1,
        "local-1": 0,
    }


def test_unequal_counts_report_both_kinds_of_unmatched_track() -> None:
    candidate_extra = assign_identity_tracks(
        (local_track(1),), (candidate_track(1), candidate_track(2))
    )
    local_extra = assign_identity_tracks(
        (local_track(1), local_track(2)), (candidate_track(1),)
    )

    assert candidate_extra.unmatched_candidate_indices == (1,)
    assert local_extra.unmatched_local_keys == ("local-2",)


def test_duration_distinguishes_identical_titles() -> None:
    locals_ = (
        local_track(1, title="Part", length=100),
        local_track(2, title="Part", length=200),
    )
    candidates = (
        candidate_track(1, title="Part", length=200),
        candidate_track(2, title="Part", length=100),
    )

    assert mapping(assign_identity_tracks(locals_, candidates)) == {
        "local-1": 1,
        "local-2": 0,
    }


def test_title_dominates_wrong_position() -> None:
    local = local_track(1, title="Correct Song")
    right_title = candidate_track(2, title="Correct Song")
    wrong_title = candidate_track(1, title="Entirely Different")

    assert score_track_pair(local, right_title).pair_score > score_track_pair(
        local, wrong_title
    ).pair_score


def test_equal_cost_assignment_is_deterministic_and_unique() -> None:
    locals_ = (
        local_track(1, title="Same", length=100),
        local_track(2, title="Same", length=100),
    )
    candidates = (
        candidate_track(1, title="Same", length=100),
        candidate_track(2, title="Same", length=100),
    )

    first = assign_identity_tracks(locals_, candidates)
    second = assign_identity_tracks(locals_, candidates)

    assert first == second
    assert len({item.local_key for item in first.assignments}) == 2
    assert len({item.candidate_index for item in first.assignments}) == 2


def test_indistinguishable_tracks_report_assignment_ambiguity() -> None:
    locals_ = (
        local_track(1, title="Same", length=100, medium_index=1),
        local_track(2, title="Same", length=100, medium_index=2),
    )
    locals_without_positions = tuple(
        type(track)(
            track.local_key,
            track.artist,
            track.title,
            length=track.length,
        )
        for track in locals_
    )
    candidates = (
        candidate_track(1, title="Same", length=100),
        candidate_track(2, title="Same", length=100),
    )

    assert assign_identity_tracks(locals_without_positions, candidates).ambiguous


def test_existing_mbids_do_not_affect_assignment() -> None:
    plain = (local_track(1), local_track(2))
    wrong_ids = (
        local_track(1, recording=mbid(999), release_track=mbid(998)),
        local_track(2, recording=mbid(997), release_track=mbid(996)),
    )
    candidates = (candidate_track(2), candidate_track(1))

    assert mapping(assign_identity_tracks(plain, candidates)) == mapping(
        assign_identity_tracks(wrong_ids, candidates)
    )


def test_fifty_track_assignment_is_complete_and_deterministic() -> None:
    locals_ = tuple(local_track(index) for index in range(1, 51))
    candidates = tuple(candidate_track(index) for index in range(50, 0, -1))

    first = assign_identity_tracks(locals_, candidates)
    second = assign_identity_tracks(locals_, candidates)

    assert len(first.assignments) == 50
    assert first == second
