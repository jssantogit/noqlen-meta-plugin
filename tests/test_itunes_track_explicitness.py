"""Exact iTunes *track* advisory metadata: never infer clean by absence."""

from urllib.parse import parse_qs, urlparse

import pytest

from beetsplug.noqlenmeta.domain import TrackEnrichmentContext
from beetsplug.noqlenmeta.providers.base import ProviderError
from beetsplug.noqlenmeta.providers.itunes_track import ITunesTrackExplicitnessProvider

TRACK = {
    "wrapperType": "track",
    "kind": "song",
    "trackId": 1234,
    "artistName": "Synthetic Artist",
    "trackName": "Synthetic Song",
    "collectionName": "Synthetic Album",
    "trackTimeMillis": 200000,
    "trackNumber": 2,
    "discNumber": 1,
    "trackExplicitness": "explicit",
    "trackViewUrl": "https://music.apple.com/us/album/synthetic/1234",
}


def context(**kwargs: object) -> TrackEnrichmentContext:
    data = {
        "artist": "Synthetic Artist",
        "title": "Synthetic Song",
        "album_title": "Synthetic Album",
        "duration": 200.0,
        "track_number": 2,
        "disc_number": 1,
    }
    data.update(kwargs)
    return TrackEnrichmentContext(**data)  # type: ignore[arg-type]


def test_exact_explicit_track_creates_recording_scoped_evidence() -> None:
    urls: list[str] = []

    def request(url: str) -> dict[str, object]:
        urls.append(url)
        return {"results": [dict(TRACK)]}

    provider = ITunesTrackExplicitnessProvider(request_json=request)
    evidence = provider.get_evidence(context())

    assert len(evidence) == 1
    assert evidence[0].field == "explicitness"
    assert evidence[0].value == "explicit"
    assert evidence[0].provider == "itunes"
    assert evidence[0].source_id == "1234"
    assert evidence[0].subject.entity.value == "recording"
    assert evidence[0].source_url == TRACK["trackViewUrl"]
    assert provider.get_evidence(context()) == evidence
    assert len(urls) == 1
    query = parse_qs(urlparse(urls[0]).query)
    assert query["entity"] == ["song"]
    assert query["country"] == ["US"]
    assert query["explicit"] == ["Yes"]


@pytest.mark.parametrize(
    ("advisory", "expected"),
    [
        ("explicit", "explicit"),
        ("cleaned", "clean"),
        ("notExplicit", None),
        ("", None),
        (None, None),
        ("unknown", None),
        (False, None),
    ],
)
def test_only_unambiguous_track_explicit_and_cleaned_are_authoritative(
    advisory: object, expected: str | None
) -> None:
    row = dict(TRACK, trackExplicitness=advisory)
    provider = ITunesTrackExplicitnessProvider(
        request_json=lambda _: {"results": [row]}
    )
    result = provider.get_evidence(context())
    assert tuple(item.value for item in result) == ((expected,) if expected else ())


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("artistName", "Another Artist"),
        ("trackName", "Different Song"),
        ("collectionName", "Other Album"),
        ("kind", "music-video"),
        ("wrapperType", "collection"),
        ("trackNumber", 3),
        ("discNumber", 2),
        ("trackTimeMillis", 197999),
        ("trackId", True),
        ("trackId", -1),
        ("trackId", None),
    ],
)
def test_inexact_or_invalid_track_metadata_cannot_assert_explicitness(
    field: str, invalid: object
) -> None:
    row = dict(TRACK, **{field: invalid})
    provider = ITunesTrackExplicitnessProvider(
        request_json=lambda _: {"results": [row]}
    )
    assert provider.get_evidence(context()) == ()


def test_missing_album_or_duration_does_not_search() -> None:
    urls: list[str] = []
    provider = ITunesTrackExplicitnessProvider(
        request_json=lambda url: urls.append(url) or {"results": [dict(TRACK)]}
    )
    assert provider.get_evidence(context(album_title=None)) == ()
    assert provider.get_evidence(context(duration=None)) == ()
    assert urls == []


def test_multiple_matching_catalog_tracks_are_ambiguous_even_when_flags_agree() -> None:
    first = dict(TRACK)
    second = dict(TRACK, trackId=9876)
    provider = ITunesTrackExplicitnessProvider(
        request_json=lambda _: {"results": [first, second]}
    )
    assert provider.get_evidence(context()) == ()


def test_invalid_api_response_is_a_safe_provider_error_and_not_cached() -> None:
    urls: list[str] = []

    def request(url: str) -> dict[str, object]:
        urls.append(url)
        return {"results": "unexpected"}

    provider = ITunesTrackExplicitnessProvider(request_json=request)
    with pytest.raises(ProviderError, match="iTunes track advisory lookup failed"):
        provider.get_evidence(context())
    with pytest.raises(ProviderError):
        provider.get_evidence(context())
    assert len(urls) == 2


def test_valid_no_match_is_cached_without_fabricating_clean() -> None:
    urls: list[str] = []
    provider = ITunesTrackExplicitnessProvider(
        request_json=lambda url: urls.append(url) or {"results": []}
    )
    assert provider.get_evidence(context()) == ()
    assert provider.get_evidence(context()) == ()
    assert len(urls) == 1


def test_track_explicitness_opt_in_uses_real_plugin_orchestration() -> None:
    from beetsplug.noqlenmeta import NoqlenMetaPlugin
    from beetsplug.noqlenmeta.integration import resolution_policy_from_settings

    urls: list[str] = []
    adapter = ITunesTrackExplicitnessProvider(
        request_json=lambda url: urls.append(url) or {"results": [dict(TRACK)]}
    )
    plugin = NoqlenMetaPlugin()
    plugin._itunes_track_explicitness_provider = adapter
    policy = resolution_policy_from_settings(
        {"explicitness": True}, {"itunes": True, "musicbrainz": False}
    )

    assert plugin._has_contributing_track_provider(policy)
    result = plugin._collect_track_candidates(context(), policy)
    assert result.candidates == ()
    assert [(entry.field, entry.value) for entry in result.evidence] == [
        ("explicitness", "explicit")
    ]
    assert len(urls) == 1


def test_disabled_explicitness_never_queries_itunes_track_adapter() -> None:
    from beetsplug.noqlenmeta import NoqlenMetaPlugin
    from beetsplug.noqlenmeta.integration import resolution_policy_from_settings

    urls: list[str] = []
    adapter = ITunesTrackExplicitnessProvider(
        request_json=lambda url: urls.append(url) or {"results": [dict(TRACK)]}
    )
    plugin = NoqlenMetaPlugin()
    plugin._itunes_track_explicitness_provider = adapter
    policy = resolution_policy_from_settings(
        {"explicitness": False}, {"itunes": True, "musicbrainz": False}
    )

    result = plugin._collect_track_candidates(context(), policy)
    assert all(item.field != "explicitness" for item in result.evidence)
    assert urls == []


def test_distinct_track_searches_are_paced_but_cache_hits_are_free() -> None:
    clock = [100.0]
    sleeps: list[float] = []
    requests: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds

    def request(url: str) -> dict[str, object]:
        requests.append(clock[0])
        return {"results": []}

    provider = ITunesTrackExplicitnessProvider(
        request_json=request,
        clock=lambda: clock[0],
        sleep=sleep,
    )
    assert provider.get_evidence(context()) == ()
    assert provider.get_evidence(context()) == ()
    assert provider.get_evidence(context(title="Second Song")) == ()

    assert len(requests) == 2
    assert requests[1] - requests[0] >= 3.0
    assert len(sleeps) == 1


def test_rate_limit_still_applies_after_failed_search() -> None:
    clock = [100.0]
    calls: list[float] = []

    def request(url: str) -> dict[str, object]:
        calls.append(clock[0])
        if len(calls) == 1:
            raise OSError("unavailable")
        return {"results": []}

    provider = ITunesTrackExplicitnessProvider(
        request_json=request,
        clock=lambda: clock[0],
        sleep=lambda delay: clock.__setitem__(0, clock[0] + delay),
    )
    with pytest.raises(ProviderError, match="iTunes track advisory lookup failed"):
        provider.get_evidence(context())
    assert provider.get_evidence(context()) == ()
    assert len(calls) == 2
    assert calls[1] - calls[0] >= 3.0


def test_known_itunes_track_id_must_match_search_result() -> None:
    from beetsplug.noqlenmeta.domain import ExternalIdentifier

    provider = ITunesTrackExplicitnessProvider(
        request_json=lambda _: {"results": [dict(TRACK)]}
    )
    match = context(
        external_ids=(ExternalIdentifier("itunes.track", "1234"),)
    )
    mismatch = context(
        external_ids=(ExternalIdentifier("itunes.track", "9999"),)
    )
    assert provider.get_evidence(match)[0].value == "explicit"
    assert provider.get_evidence(mismatch) == ()


def test_known_itunes_collection_id_restricts_same_named_editions() -> None:
    from beetsplug.noqlenmeta.domain import ExternalIdentifier, ReleaseEnrichmentContext

    def album(collection_id: int) -> ReleaseEnrichmentContext:
        return ReleaseEnrichmentContext(
            "Synthetic Artist",
            "Synthetic Album",
            external_ids=(ExternalIdentifier("itunes.collection", str(collection_id)),),
        )
    row = dict(TRACK, collectionId=777)
    provider = ITunesTrackExplicitnessProvider(
        request_json=lambda _: {"results": [row]}
    )

    assert provider.get_evidence(context(release=album(777)))[0].value == "explicit"
    assert provider.get_evidence(context(release=album(778))) == ()
