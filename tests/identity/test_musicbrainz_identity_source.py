from __future__ import annotations

from copy import deepcopy

import pytest
from beets.autotag import AlbumInfo, TrackInfo
from requests.exceptions import Timeout

from beetsplug.noqlenmeta.identity import (
    BeetsMusicBrainzIdentitySource,
    IdentityAuditError,
    IdentitySourceError,
    musicbrainz_identity_from_album_info,
)

from .helpers import context, mbid


def album_info(number: int = 100, *, title: str = "Example Album") -> AlbumInfo:
    tracks = [
        TrackInfo(
            artist="Example Artist",
            title=f"Track {index}",
            length=180.0 + index,
            medium=1,
            medium_index=index,
            index=index,
            track_id=mbid(1000 + index),
            release_track_id=mbid(number * 100 + index),
        )
        for index in range(1, 4)
    ]
    return AlbumInfo(
        tracks,
        artist="Example Artist",
        album=title,
        album_id=mbid(number),
        releasegroup_id=mbid(number + 1000),
        albumstatus="Official",
        country="US",
        year=2020,
        label="Example Label",
    )


def test_real_beets_album_info_contract_normalizes_without_mutation() -> None:
    info = album_info()
    before = deepcopy(info)

    candidate = musicbrainz_identity_from_album_info(info)

    assert candidate.release_mbid == info.album_id
    assert candidate.release_group_mbid == info.releasegroup_id
    assert candidate.status == info.albumstatus
    assert candidate.tracks[0].recording_mbid == info.tracks[0].track_id
    assert candidate.tracks[0].release_track_mbid == info.tracks[0].release_track_id
    assert info.copy() == before.copy()
    assert [track.copy() for track in info.tracks] == [track.copy() for track in before.tracks]


def test_malformed_album_info_is_rejected() -> None:
    info = album_info()
    info.tracks[0].release_track_id = None

    with pytest.raises(IdentityAuditError, match="AlbumInfo identity is invalid"):
        musicbrainz_identity_from_album_info(info)


def test_source_fetches_existing_ids_searches_text_and_deduplicates() -> None:
    calls: list[tuple[str, ...]] = []
    fetched = album_info(100)
    duplicate = album_info(100)
    searched = album_info(101)

    def fetch(release_mbid: str) -> AlbumInfo:
        calls.append(("fetch", release_mbid))
        return fetched

    def search(artist: str, album: str):
        calls.append(("search", artist, album))
        return (duplicate, searched)

    source = BeetsMusicBrainzIdentitySource(fetch_release=fetch, search_releases=search)
    candidates = source.candidates_for(context(release_ids=(mbid(100),)))

    assert calls == [
        ("fetch", mbid(100)),
        ("search", "Example Artist", "Example Album"),
    ]
    assert [item.release_mbid for item in candidates] == [mbid(100), mbid(101)]


def test_default_source_uses_beets_musicbrainz_fetch_and_search_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []

    def fetch(self: object, release_mbid: str) -> AlbumInfo:
        calls.append(("fetch", release_mbid))
        return album_info(100 if release_mbid == mbid(100) else 101)

    def search(self: object, params: object):
        calls.append(("search", params))
        return ({"id": mbid(101)},)

    monkeypatch.setattr("beetsplug.musicbrainz.MusicBrainzPlugin.album_for_id", fetch)
    monkeypatch.setattr("beetsplug.musicbrainz.MusicBrainzPlugin.get_search_response", search)

    candidates = BeetsMusicBrainzIdentitySource().candidates_for(
        context(release_ids=(mbid(100),))
    )

    assert [item.release_mbid for item in candidates] == [mbid(100), mbid(101)]
    assert calls[0] == ("fetch", mbid(100))
    search_params = calls[1][1]
    assert search_params.query_type == "album"  # type: ignore[attr-defined]
    assert search_params.filters == {  # type: ignore[attr-defined]
        "artist": "example artist",
        "release": "example album",
    }


def test_anchored_candidate_has_no_source_order_bonus() -> None:
    source = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: album_info(200),
        search_releases=lambda artist, album: (album_info(100),),
    )

    candidates = source.candidates_for(context(release_ids=(mbid(200),)))

    assert [item.release_mbid for item in candidates] == [mbid(100), mbid(200)]


def test_singleton_adds_distinct_track_title_release_query() -> None:
    calls: list[tuple[str, str]] = []

    def search(artist: str, album: str):
        calls.append((artist, album))
        return ()

    source = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None, search_releases=search
    )
    source.candidates_for(context(1))

    assert calls == [
        ("Example Artist", "Example Album"),
        ("Example Artist", "Track 1"),
    ]


def test_source_is_bounded_and_deterministic() -> None:
    releases = tuple(album_info(number) for number in range(120, 99, -1))
    source = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None,
        search_releases=lambda artist, album: releases,
    )

    first = source.candidates_for(context())
    second = source.candidates_for(context())

    assert first == second
    assert len(first) == 10
    assert [item.release_mbid for item in first] == [mbid(number) for number in range(100, 110)]


def test_network_and_malformed_source_failures_are_sanitized() -> None:
    def fail_search(artist: str, album: str):
        raise Timeout("private query details")

    failed = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None, search_releases=fail_search
    )
    malformed = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None,
        search_releases=lambda artist, album: (object(),),
    )

    with pytest.raises(IdentitySourceError, match=r"^MusicBrainz identity source request failed$"):
        failed.candidates_for(context())
    with pytest.raises(
        IdentitySourceError,
        match=r"^MusicBrainz identity source returned invalid data$",
    ):
        malformed.candidates_for(context())


def test_structural_client_failure_is_sanitized() -> None:
    def fail_search(artist: str, album: str):
        raise KeyError("raw response field")

    source = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None, search_releases=fail_search
    )

    with pytest.raises(
        IdentitySourceError,
        match=r"^MusicBrainz identity source returned invalid data$",
    ) as caught:
        source.candidates_for(context())
    assert "raw response" not in str(caught.value)
