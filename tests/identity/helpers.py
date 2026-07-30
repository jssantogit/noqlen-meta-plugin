from __future__ import annotations

from uuid import UUID

from beetsplug.noqlenmeta.identity import (
    IdentityAlbumContext,
    IdentityTrackContext,
    MusicBrainzReleaseIdentity,
    MusicBrainzTrackIdentity,
)


def mbid(number: int) -> str:
    return str(UUID(int=number))


def local_track(
    number: int,
    *,
    title: str | None = None,
    length: float | None = None,
    medium: int = 1,
    medium_index: int | None = None,
    recording: str | None = None,
    release_track: str | None = None,
) -> IdentityTrackContext:
    return IdentityTrackContext(
        local_key=f"local-{number}",
        artist="Example Artist",
        title=title or f"Track {number}",
        length=length if length is not None else 180.0 + number,
        medium=medium,
        medium_index=medium_index or number,
        index=number,
        current_recording_mbid=recording,
        current_release_track_mbid=release_track,
    )


def context(
    count: int = 3,
    *,
    tracks: tuple[IdentityTrackContext, ...] | None = None,
    release_ids: tuple[str, ...] = (),
    release_group_ids: tuple[str, ...] = (),
    album: str = "Example Album",
) -> IdentityAlbumContext:
    return IdentityAlbumContext(
        album_artist="Example Artist",
        album=album,
        tracks=tracks or tuple(local_track(index) for index in range(1, count + 1)),
        current_release_mbids=release_ids,
        current_release_group_mbids=release_group_ids,
    )


def candidate_track(
    number: int,
    *,
    title: str | None = None,
    length: float | None = None,
    medium: int = 1,
    medium_index: int | None = None,
    recording: str | None = None,
    release_track: str | None = None,
) -> MusicBrainzTrackIdentity:
    return MusicBrainzTrackIdentity(
        recording_mbid=recording or mbid(1000 + number),
        release_track_mbid=release_track or mbid(2000 + number),
        artist="Example Artist",
        title=title or f"Track {number}",
        length=length if length is not None else 180.0 + number,
        medium=medium,
        medium_index=medium_index or number,
        index=number,
    )


def candidate(
    count: int = 3,
    *,
    tracks: tuple[MusicBrainzTrackIdentity, ...] | None = None,
    release: str | None = None,
    release_group: str | None = None,
    album: str = "Example Album",
) -> MusicBrainzReleaseIdentity:
    return MusicBrainzReleaseIdentity(
        release_mbid=release or mbid(100),
        release_group_mbid=release_group or mbid(200),
        album_artist="Example Artist",
        album=album,
        tracks=tracks or tuple(candidate_track(index) for index in range(1, count + 1)),
    )
