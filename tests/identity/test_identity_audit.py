from beetsplug.noqlenmeta.identity import (
    IdentityFieldStatus,
    IdentityVerdict,
    audit_musicbrainz_identity,
)

from .helpers import candidate, candidate_track, context, local_track, mbid


def matching_context(count: int = 3):
    return context(
        count,
        tracks=tuple(
            local_track(
                index,
                recording=mbid(1000 + index),
                release_track=mbid(2000 + index),
            )
            for index in range(1, count + 1)
        ),
        release_ids=(mbid(100),),
        release_group_ids=(mbid(200),),
    )


def test_confirmed_identity_has_all_four_categories_and_needs_no_repair() -> None:
    result = audit_musicbrainz_identity(matching_context(), (candidate(),))

    assert result.verdict is IdentityVerdict.CONFIRMED
    assert not result.repair_ready
    assert [finding.field for finding in result.field_findings] == [
        "mb_albumid",
        "mb_releasegroupid",
        "mb_trackid",
        "mb_releasetrackid",
        "mb_trackid",
        "mb_releasetrackid",
        "mb_trackid",
        "mb_releasetrackid",
    ]
    assert all(
        finding.status is IdentityFieldStatus.CONFIRMED for finding in result.field_findings
    )


def test_missing_identity_is_repair_ready() -> None:
    result = audit_musicbrainz_identity(context(), (candidate(),))

    assert result.verdict is IdentityVerdict.MISSING
    assert result.repair_ready
    assert all(finding.status is IdentityFieldStatus.MISSING for finding in result.field_findings)


def test_conflict_including_malformed_value_supersedes_missing() -> None:
    local = context(
        tracks=(local_track(1, recording="malformed"),),
        release_ids=(mbid(999),),
    )

    result = audit_musicbrainz_identity(local, (candidate(1),))

    assert result.verdict is IdentityVerdict.CONFLICT
    assert result.has_conflicts
    assert result.has_missing
    assert result.repair_ready


def test_no_candidate_or_weak_candidate_is_ambiguous_without_findings() -> None:
    none = audit_musicbrainz_identity(context(), ())
    weak = audit_musicbrainz_identity(
        context(),
        (
            candidate(
                tracks=tuple(
                    candidate_track(index, title=f"Unrelated {index}")
                    for index in range(1, 4)
                )
            ),
        ),
    )

    assert none.verdict is IdentityVerdict.AMBIGUOUS
    assert none.reason == "no_candidates"
    assert not none.field_findings
    assert weak.verdict is IdentityVerdict.AMBIGUOUS
    assert weak.reason == "below_minimum_score"


def test_near_tie_remains_ambiguous() -> None:
    result = audit_musicbrainz_identity(
        context(), (candidate(release=mbid(101)), candidate(release=mbid(102)))
    )

    assert result.verdict is IdentityVerdict.AMBIGUOUS
    assert result.reason == "insufficient_margin"
    assert result.selected_candidate is None


def test_existing_wrong_release_id_does_not_bias_structural_selection() -> None:
    wrong_release = mbid(999)
    local = context(release_ids=(wrong_release,))
    correct = candidate(release=mbid(100))
    structurally_wrong = candidate(
        release=wrong_release,
        tracks=tuple(
            candidate_track(index, title=f"Wrong {index}") for index in range(1, 4)
        ),
    )

    result = audit_musicbrainz_identity(local, (structurally_wrong, correct))

    assert result.selected_candidate == correct
    assert result.verdict is IdentityVerdict.CONFLICT


def test_multiple_album_ids_are_conflicts_not_consensus() -> None:
    local = context(
        release_ids=(mbid(100), mbid(999)),
        release_group_ids=(mbid(200), mbid(998)),
    )

    result = audit_musicbrainz_identity(local, (candidate(),))

    assert result.verdict is IdentityVerdict.CONFLICT
    assert [finding.status for finding in result.field_findings[:2]] == [
        IdentityFieldStatus.CONFLICT,
        IdentityFieldStatus.CONFLICT,
    ]


def test_singleton_strictness_accepts_unique_exact_but_rejects_near_tie() -> None:
    single_context = context(1)
    exact = candidate(1, release=mbid(100))

    unique = audit_musicbrainz_identity(single_context, (exact,))
    tied = audit_musicbrainz_identity(
        single_context, (exact, candidate(1, release=mbid(101)))
    )

    assert unique.verdict is IdentityVerdict.MISSING
    assert tied.verdict is IdentityVerdict.AMBIGUOUS
    assert tied.reason == "insufficient_margin"


def test_unmatched_local_track_prevents_repair_ready_result() -> None:
    local = context(10)
    remote = candidate(9)

    result = audit_musicbrainz_identity(local, (remote,))

    assert result.verdict is IdentityVerdict.AMBIGUOUS
    assert result.reason == "unmatched_local_tracks"
    assert not result.repair_ready


def test_duplicate_release_track_identity_is_ineligible_but_recording_repeat_is_valid() -> None:
    duplicate_release_track = candidate(
        tracks=(
            candidate_track(1, release_track=mbid(2001)),
            candidate_track(2, release_track=mbid(2001)),
            candidate_track(3),
        )
    )
    repeated_recording = candidate(
        tracks=(
            candidate_track(1, recording=mbid(1001)),
            candidate_track(2, recording=mbid(1001)),
            candidate_track(3),
        )
    )

    invalid = audit_musicbrainz_identity(context(), (duplicate_release_track,))
    valid = audit_musicbrainz_identity(context(), (repeated_recording,))

    assert invalid.reason == "invalid_candidate_identity"
    assert valid.verdict is IdentityVerdict.MISSING


def test_indistinguishable_track_occurrences_are_not_repair_ready() -> None:
    local = context(
        tracks=(
            type(local_track(1))("first", "Example Artist", "Same", length=100),
            type(local_track(1))("second", "Example Artist", "Same", length=100),
        )
    )
    remote = candidate(
        tracks=(
            candidate_track(1, title="Same", length=100),
            candidate_track(2, title="Same", length=100),
        )
    )

    result = audit_musicbrainz_identity(local, (remote,))

    assert result.verdict is IdentityVerdict.AMBIGUOUS
    assert result.reason == "ambiguous_track_assignment"
    assert not result.repair_ready
