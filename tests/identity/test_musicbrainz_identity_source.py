from __future__ import annotations

from copy import deepcopy

import pytest
from beets.autotag import AlbumInfo, TrackInfo
from requests.exceptions import Timeout

from beetsplug.noqlenmeta.identity import (
    BeetsMusicBrainzIdentitySource,
    IdentityAuditError,
    IdentitySourceError,
    IdentityVerdict,
    audit_musicbrainz_identity,
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


def structurally_wrong_album_info(number: int) -> AlbumInfo:
    info = album_info(number, title="Unrelated Album")
    for index, track in enumerate(info.tracks, 1):
        track.title = f"Unrelated Track {index}"
        track.length = 500.0 + index
    return info


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
    fetched = album_info(100, title="Fetched Representation")
    duplicate = album_info(100, title="Search Representation")
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
    assert candidates[0].album == "Fetched Representation"


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


def test_existing_candidate_is_included_first_but_receives_no_structural_bonus() -> None:
    wrong_existing = structurally_wrong_album_info(200)
    correct_search = album_info(120)
    source = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: wrong_existing,
        search_releases=lambda artist, album: (correct_search, album_info(100)),
        maximum_candidates=2,
    )
    local = context(release_ids=(mbid(200),))

    candidates = source.candidates_for(local)
    result = audit_musicbrainz_identity(local, candidates)

    assert [item.release_mbid for item in candidates] == [mbid(200), mbid(120)]
    assert result.selected_candidate == candidates[1]
    assert result.verdict is IdentityVerdict.CONFLICT


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


def test_singleton_preserves_primary_then_alternate_order_with_cross_query_deduplication() -> None:
    def search(artist: str, album: str):
        if album == "Example Album":
            return (album_info(120), album_info(100))
        return (album_info(100), album_info(119))

    source = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None,
        search_releases=search,
        maximum_candidates=4,
    )

    candidates = source.candidates_for(context(1))

    assert [item.release_mbid for item in candidates] == [mbid(120), mbid(100), mbid(119)]


def test_source_is_bounded_and_deterministic() -> None:
    source_order = (120, 100, 119, 101, 118)
    releases = tuple(album_info(number) for number in source_order)
    source = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None,
        search_releases=lambda artist, album: releases,
        maximum_candidates=3,
    )

    first = source.candidates_for(context())
    second = source.candidates_for(context())

    assert first == second
    assert len(first) == 3
    assert [item.release_mbid for item in first] == [mbid(120), mbid(100), mbid(119)]


def test_structurally_correct_later_uuid_survives_bound_and_wins_audit() -> None:
    correct = album_info(120)
    wrong = (structurally_wrong_album_info(100), structurally_wrong_album_info(101))
    source = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None,
        search_releases=lambda artist, album: (correct, *wrong),
        maximum_candidates=2,
    )

    candidates = source.candidates_for(context())
    result = audit_musicbrainz_identity(context(), candidates)

    assert [item.release_mbid for item in candidates] == [mbid(120), mbid(100)]
    assert result.selected_candidate == candidates[0]


def test_pathological_existing_id_count_is_bounded_in_canonical_order() -> None:
    calls: list[str] = []

    def fetch(release_mbid: str) -> AlbumInfo:
        calls.append(release_mbid)
        return album_info(int(release_mbid[-4:], 16))

    source = BeetsMusicBrainzIdentitySource(
        fetch_release=fetch,
        search_releases=lambda artist, album: (),
        maximum_candidates=2,
    )

    candidates = source.candidates_for(
        context(release_ids=(mbid(120), mbid(100), mbid(119)))
    )

    assert calls == [mbid(100), mbid(119)]
    assert [item.release_mbid for item in candidates] == [mbid(100), mbid(119)]


def test_pathological_existing_id_fetch_attempts_are_bounded_even_without_results() -> None:
    calls: list[str] = []

    def fetch(release_mbid: str) -> None:
        calls.append(release_mbid)
        return None

    source = BeetsMusicBrainzIdentitySource(
        fetch_release=fetch,
        search_releases=lambda artist, album: (album_info(120),),
        maximum_candidates=2,
    )

    candidates = source.candidates_for(
        context(release_ids=(mbid(120), mbid(100), mbid(119)))
    )

    assert calls == [mbid(100), mbid(119)]
    assert [item.release_mbid for item in candidates] == [mbid(120)]


def test_network_and_malformed_source_failures_are_sanitized() -> None:
    def fail_search(artist: str, album: str):
        raise Timeout("private query details")

    failed = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None, search_releases=fail_search
    )
    malformed = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda value: None,
        search_releases=lambda artist, album: (object(),),  # type: ignore[arg-type]
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
