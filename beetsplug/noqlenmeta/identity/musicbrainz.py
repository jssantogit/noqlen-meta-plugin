from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from requests.exceptions import RequestException

from .assignment import normalize_identity_text
from .domain import (
    IdentityAlbumContext,
    IdentityAuditError,
    MusicBrainzReleaseIdentity,
    MusicBrainzTrackIdentity,
    canonical_mbid,
)

if TYPE_CHECKING:
    from beets.autotag import AlbumInfo


class IdentitySourceError(IdentityAuditError):
    """Raised when MusicBrainz candidate acquisition fails safely."""


def musicbrainz_identity_from_album_info(info: AlbumInfo) -> MusicBrainzReleaseIdentity:
    try:
        album_artist = _required_text(info.artist)
        tracks = tuple(
            MusicBrainzTrackIdentity(
                recording_mbid=_required_text(track.track_id),
                release_track_mbid=_required_text(track.release_track_id),
                artist=_required_text(track.artist or album_artist),
                title=_required_text(track.title),
                length=track.length,
                medium=_required_position(track.medium),
                medium_index=_required_position(track.medium_index),
                index=_required_position(track.index),
            )
            for track in info.tracks
        )
        return MusicBrainzReleaseIdentity(
            release_mbid=_required_text(info.album_id),
            release_group_mbid=_required_text(info.releasegroup_id),
            album_artist=album_artist,
            album=_required_text(info.album),
            tracks=tracks,
            status=info.albumstatus,
            country=info.country,
            year=info.year,
            label=info.label,
        )
    except (AttributeError, TypeError, ValueError, IdentityAuditError) as error:
        raise IdentityAuditError("MusicBrainz AlbumInfo identity is invalid") from error


class BeetsMusicBrainzIdentitySource:
    def __init__(
        self,
        *,
        fetch_release: Callable[[str], AlbumInfo | None] | None = None,
        search_releases: Callable[[str, str], Iterable[AlbumInfo]] | None = None,
        maximum_candidates: int = 10,
    ) -> None:
        if (
            isinstance(maximum_candidates, bool)
            or not isinstance(maximum_candidates, int)
            or maximum_candidates <= 0
        ):
            raise ValueError("maximum_candidates must be positive")
        if fetch_release is None or search_releases is None:
            from beets.metadata_plugins import SearchParams
            from beetsplug.musicbrainz import MusicBrainzPlugin

            plugin = MusicBrainzPlugin()
            fetch_release = fetch_release or plugin.album_for_id
            if search_releases is None:

                def default_search(artist: str, album: str) -> Iterable[AlbumInfo]:
                    query, filters = plugin.get_search_query_with_filters(
                        "album", (), artist, album, False
                    )
                    params = SearchParams(
                        "album", query, filters, plugin.config["search_limit"].get(int)
                    )
                    results = plugin.get_search_response(params)
                    return filter(
                        None, plugin.albums_for_ids(result["id"] for result in results)
                    )

                search_releases = default_search
        self._fetch_release = fetch_release
        self._search_releases = search_releases
        self._maximum_candidates = maximum_candidates

    def candidates_for(
        self, context: IdentityAlbumContext
    ) -> tuple[MusicBrainzReleaseIdentity, ...]:
        infos: list[AlbumInfo] = []
        try:
            anchored_ids = sorted(
                {
                    canonical
                    for value in context.current_release_mbids
                    if (canonical := canonical_mbid(value)) is not None
                }
            )
            for release_mbid in anchored_ids:
                if (info := self._fetch_release(release_mbid)) is not None:
                    infos.append(info)
            queries = [(context.album_artist, context.album)]
            if len(context.tracks) == 1:
                track = context.tracks[0]
                alternate = (track.artist or context.album_artist, track.title)
                if _query_key(alternate) != _query_key(queries[0]):
                    queries.append(alternate)
            for artist, album in queries:
                infos.extend(self._search_releases(artist, album))
            by_release: dict[str, MusicBrainzReleaseIdentity] = {}
            for info in infos:
                candidate = musicbrainz_identity_from_album_info(info)
                by_release.setdefault(candidate.release_mbid, candidate)
        except RequestException:
            raise IdentitySourceError("MusicBrainz identity source request failed") from None
        except IdentityAuditError:
            raise IdentitySourceError("MusicBrainz identity source returned invalid data") from None
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            raise IdentitySourceError("MusicBrainz identity source returned invalid data") from None
        return tuple(
            sorted(by_release.values(), key=lambda candidate: candidate.release_mbid)[
                : self._maximum_candidates
            ]
        )


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not (cleaned := value.strip()):
        raise ValueError("required text is missing")
    return cleaned


def _required_position(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("required position is missing")
    return value


def _query_key(query: tuple[str, str]) -> tuple[str, str]:
    return normalize_identity_text(query[0]), normalize_identity_text(query[1])
