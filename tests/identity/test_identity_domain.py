from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.identity import (
    IdentityAlbumContext,
    IdentityAuditError,
    IdentityAuditPolicy,
    IdentityTrackContext,
    MusicBrainzReleaseIdentity,
    MusicBrainzTrackIdentity,
)

from .helpers import candidate, candidate_track, context, local_track, mbid


def test_context_is_immutable_and_copies_track_sequence() -> None:
    tracks = [local_track(1)]
    value = IdentityAlbumContext(" Artist ", " Album ", tracks)  # type: ignore[arg-type]
    tracks.clear()

    assert value.album_artist == "Artist"
    assert value.album == "Album"
    assert value.tracks == (local_track(1),)
    with pytest.raises(FrozenInstanceError):
        value.album = "Changed"  # type: ignore[misc]


def test_duplicate_or_empty_local_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        IdentityAlbumContext("Artist", "Album", (local_track(1), local_track(1)))
    with pytest.raises(ValueError, match="album artist"):
        IdentityAlbumContext(" ", "Album", (local_track(1),))
    with pytest.raises(ValueError, match="album title"):
        IdentityAlbumContext("Artist", " ", (local_track(1),))
    with pytest.raises(ValueError, match="track title"):
        IdentityTrackContext("key", "Artist", " ")


@pytest.mark.parametrize("length", [0, -1, float("nan"), float("inf")])
def test_invalid_local_length_is_rejected(length: float) -> None:
    with pytest.raises(ValueError, match="length"):
        IdentityTrackContext("key", "Artist", "Title", length=length)


@pytest.mark.parametrize("field", ["medium", "medium_index", "index"])
@pytest.mark.parametrize("value", [0, -1, True])
def test_invalid_local_position_is_rejected(field: str, value: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        IdentityTrackContext("key", "Artist", "Title", **{field: value})


def test_malformed_existing_mbid_remains_auditable() -> None:
    value = context(
        tracks=(local_track(1, recording=" malformed "),),
        release_ids=(" also-malformed ",),
    )

    assert value.current_release_mbids == ("also-malformed",)
    assert value.tracks[0].current_recording_mbid == "malformed"


def test_candidate_mbids_are_canonical_and_candidate_is_immutable() -> None:
    value = candidate(
        tracks=(
            candidate_track(
                1,
                recording=f" {mbid(1001).upper()} ",
                release_track=mbid(2001).upper(),
            ),
        ),
        release=mbid(100).upper(),
    )

    assert value.release_mbid == mbid(100)
    assert value.tracks[0].recording_mbid == mbid(1001)
    with pytest.raises(FrozenInstanceError):
        value.album = "Changed"  # type: ignore[misc]


def test_malformed_or_incomplete_candidate_identity_is_rejected() -> None:
    with pytest.raises(IdentityAuditError, match="release_mbid"):
        candidate(release="invalid")
    with pytest.raises(IdentityAuditError, match="recording_mbid"):
        candidate(tracks=(candidate_track(1, recording="invalid"),))
    with pytest.raises(IdentityAuditError, match="complete track"):
        MusicBrainzReleaseIdentity(mbid(1), mbid(2), "Artist", "Album", ())
    with pytest.raises(ValueError, match="positive integer"):
        MusicBrainzTrackIdentity(mbid(1), mbid(2), "Artist", "Title", 1.0, 1, 0, 1)


@pytest.mark.parametrize("field", ["minimum_score", "minimum_margin", "minimum_pair_score"])
def test_policy_validates_ranges(field: str) -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        IdentityAuditPolicy(**{field: 101})
