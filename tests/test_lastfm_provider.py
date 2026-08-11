import copy
import importlib.util
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import beets.plugins
import pytest

from beetsplug.noqlenmeta.domain import (
    ArtistEnrichmentContext,
    ExternalIdentifier,
    ReleaseEnrichmentContext,
    SemanticCategory,
    TrackEnrichmentContext,
)
from beetsplug.noqlenmeta.genre_taxonomy import DEFAULT_GENRE_TAXONOMY
from beetsplug.noqlenmeta.providers import ProviderError, ReleaseMetadataProvider
from beetsplug.noqlenmeta.providers.lastfm import (
    LastFmArtistProvider,
    LastFmProvider,
    LastFmTrackProvider,
    _LastFmTransport,
)
from beetsplug.noqlenmeta.providers.specs import LASTFM_SPEC, ProviderScope

FIXTURES = Path(__file__).parent / "fixtures" / "lastfm"
FAKE_KEY = "fake-test-key"


def fixture() -> dict[str, Any]:
    return json.loads((FIXTURES / "album_top_tags.json").read_text(encoding="utf-8"))


def context(**overrides: object) -> ReleaseEnrichmentContext:
    values: dict[str, object] = {
        "album_artist": "Gojira",
        "album_title": "From Mars to Sirius",
    }
    values.update(overrides)
    return ReleaseEnrichmentContext(**values)  # type: ignore[arg-type]


class FetchTopTags:
    def __init__(self, *payloads: object) -> None:
        self.payloads = list(payloads) or [fixture()]
        self.calls: list[tuple[str, str]] = []

    def __call__(self, artist: str, album: str) -> object:
        self.calls.append((artist, album))
        return copy.deepcopy(self.payloads.pop(0))


def provider(fetch: FetchTopTags | None = None) -> LastFmProvider:
    return LastFmProvider(fetch_top_tags=fetch or FetchTopTags())


def test_community_tags_are_weight_and_vocabulary_filtered() -> None:
    candidates = provider().get_candidates(context())

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.field == "genres"
    assert candidate.value == ("Progressive Metal", "Death Metal")
    assert candidate.provider == "lastfm"
    assert candidate.confidence == 0.85
    assert candidate.source_id == "Gojira / From Mars to Sirius"
    assert candidate.source_url == "https://www.last.fm/music/Gojira/From%20Mars%20to%20Sirius"


def test_at_most_first_three_eligible_genres_are_emitted() -> None:
    payload = fixture()
    payload["toptags"]["tag"] = [
        {"name": "rock", "count": 100},
        {"name": "death metal", "count": 90},
        {"name": "thrash metal", "count": 80},
        {"name": "progressive metal", "count": 70},
    ]

    candidates = provider(FetchTopTags(payload)).get_candidates(context())

    assert candidates[0].value == ("Rock", "Death Metal", "Thrash Metal")


def test_no_accepted_genres_is_normal_empty_result() -> None:
    payload = fixture()
    payload["toptags"]["tag"] = [
        {"name": "albums I own", "count": 100},
        {"name": "rock", "count": 9},
    ]

    assert provider(FetchTopTags(payload)).get_candidates(context()) == ()


def test_malformed_tag_entries_are_skipped_without_losing_good_tags() -> None:
    payload = fixture()
    payload["toptags"]["tag"] = [
        None,
        "rock",
        {"count": 100},
        {"name": 42, "count": 100},
        {"name": "rock", "count": 10.0},
        {"name": "rock", "count": 101},
        {"name": "rock", "count": True},
        {"name": "rock", "count": -1},
        {"name": "death metal", "count": "not-a-number"},
        {"name": "progressive metal", "count": 100},
    ]

    candidates = provider(FetchTopTags(payload)).get_candidates(context())

    assert candidates[0].value == ("Progressive Metal",)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"toptags": None},
        {"toptags": {}},
        {"toptags": {"@attr": None, "tag": []}},
        {"toptags": {"@attr": {"artist": "Gojira"}, "tag": []}},
        {
            "toptags": {
                "@attr": {"artist": "Gojira", "album": "From Mars to Sirius"},
                "tag": None,
            }
        },
    ],
)
def test_malformed_structural_payload_is_provider_error(payload: object) -> None:
    with pytest.raises(ProviderError, match=r"^Last.fm API response is invalid$"):
        provider(FetchTopTags(payload)).get_candidates(context())


@pytest.mark.parametrize("code", [6, "6", 7, "7"])
def test_no_resource_api_errors_return_empty(code: object) -> None:
    payload = {"error": code, "message": "unsafe raw service detail"}

    assert provider(FetchTopTags(payload)).get_candidates(context()) == ()


@pytest.mark.parametrize("code", [8, 10, 11, 16, 26, 29, 999, "invalid"])
def test_service_and_key_api_errors_are_fixed_provider_errors(code: object) -> None:
    payload = {"error": code, "message": "unsafe raw service detail"}

    with pytest.raises(ProviderError) as raised:
        provider(FetchTopTags(payload)).get_candidates(context())

    assert str(raised.value) == "Last.fm service request failed"
    assert "unsafe" not in str(raised.value)


def test_identity_comparison_allows_only_case_and_ordinary_whitespace_changes() -> None:
    payload = fixture()
    payload["toptags"]["@attr"] = {
        "artist": "  GOJIRA ",
        "album": "From   Mars\tto Sirius",
    }

    candidates = provider(FetchTopTags(payload)).get_candidates(
        context(album_artist="Gojira", album_title="From Mars to Sirius")
    )

    assert candidates
    assert candidates[0].source_id == "GOJIRA / From Mars to Sirius"


@pytest.mark.parametrize(
    ("artist", "album"),
    [("Mastodon", "From Mars to Sirius"), ("Gojira", "From Mars to Sirius (Deluxe)")],
)
def test_material_response_identity_mismatch_is_provider_error(
    artist: str, album: str
) -> None:
    payload = fixture()
    payload["toptags"]["@attr"] = {"artist": artist, "album": album}

    with pytest.raises(
        ProviderError, match=r"^Last.fm album identity does not match selected release$"
    ):
        provider(FetchTopTags(payload)).get_candidates(context())


def test_selected_identity_is_only_whitespace_cleaned_before_lookup() -> None:
    fetch = FetchTopTags(fixture())

    provider(fetch).get_candidates(
        context(album_artist=" Gojira ", album_title="From   Mars to Sirius")
    )

    assert fetch.calls == [("Gojira", "From Mars to Sirius")]


def test_same_album_is_cached_without_second_fetch() -> None:
    fetch = FetchTopTags(fixture())
    lastfm = provider(fetch)

    first = lastfm.get_candidates(context())
    second = lastfm.get_candidates(
        context(album_artist="GOJIRA", album_title="From  Mars to Sirius")
    )

    assert second == first
    assert fetch.calls == [("Gojira", "From Mars to Sirius")]


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_distinct_transport_requests_are_paced_without_real_sleep() -> None:
    clock = FakeClock()
    urls: list[str] = []

    def request_json(url: str) -> dict[str, Any]:
        urls.append(url)
        payload = fixture()
        query = parse_qs(urlsplit(url).query)
        payload["toptags"]["@attr"]["artist"] = query["artist"][0]
        payload["toptags"]["@attr"]["album"] = query["album"][0]
        return payload

    transport = _LastFmTransport(
        api_key=FAKE_KEY,
        request_json=request_json,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    lastfm = LastFmProvider(transport=transport)

    lastfm.get_candidates(context())
    lastfm.get_candidates(context(album_title="The Way of All Flesh"))

    assert len(urls) == 2
    assert clock.sleeps == [1.0]


def test_cache_hit_does_not_trigger_transport_pacing_sleep() -> None:
    clock = FakeClock()
    transport = _LastFmTransport(
        api_key=FAKE_KEY,
        request_json=lambda url: fixture(),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    lastfm = LastFmProvider(transport=transport)

    lastfm.get_candidates(context())
    lastfm.get_candidates(context())

    assert clock.sleeps == []


@pytest.mark.parametrize(
    "error",
    [
        HTTPError("https://example.invalid/fake-test-key", 503, "bad", {}, None),
        URLError("fake-test-key"),
        TimeoutError("fake-test-key"),
        json.JSONDecodeError("fake-test-key", "", 0),
        UnicodeDecodeError("utf-8", b"x", 0, 1, "fake-test-key"),
        ConnectionResetError("fake-test-key"),
        KeyError("fake-test-key"),
    ],
)
def test_expected_transport_failures_hide_underlying_details(error: Exception) -> None:
    def fail_request(url: str) -> dict[str, Any]:
        raise error

    transport = _LastFmTransport(api_key=FAKE_KEY, request_json=fail_request)

    with pytest.raises(ProviderError) as raised:
        LastFmProvider(transport=transport).get_candidates(context())

    assert str(raised.value) == "Last.fm API request failed"
    assert "fake-test-key" not in str(raised.value)


def test_programming_error_is_not_disguised_as_provider_error() -> None:
    def fail_request(url: str) -> dict[str, Any]:
        raise AttributeError("programming defect")

    transport = _LastFmTransport(api_key=FAKE_KEY, request_json=fail_request)

    with pytest.raises(AttributeError, match="programming defect"):
        LastFmProvider(transport=transport).get_candidates(context())


def test_production_http_boundary_uses_shared_beets_key_and_top_tags_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    fake_key = "fake-shared-beets-key"

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            captured["read_size"] = size
            return json.dumps(fixture()).encode()

    def fake_urlopen(request: object, timeout: float) -> Response:
        captured["url"] = request.full_url  # type: ignore[attr-defined]
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(beets.plugins, "LASTFM_KEY", fake_key)
    monkeypatch.setattr("beetsplug.noqlenmeta.providers.lastfm.urlopen", fake_urlopen)

    candidates = LastFmProvider().get_candidates(context())
    query = parse_qs(urlsplit(str(captured["url"])).query)

    assert candidates
    assert query == {
        "method": ["album.getTopTags"],
        "artist": ["Gojira"],
        "album": ["From Mars to Sirius"],
        "api_key": [fake_key],
        "format": ["json"],
        "autocorrect": ["0"],
    }
    assert "album.search" not in str(captured["url"])
    assert captured["timeout"] == 10.0
    assert captured["read_size"] == 1_000_001
    assert fake_key not in candidates[0].source_id
    assert fake_key not in str(candidates[0].source_url)


def test_oversized_production_response_is_fixed_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            return b"x" * size

    monkeypatch.setattr(
        "beetsplug.noqlenmeta.providers.lastfm.urlopen",
        lambda request, timeout: Response(),
    )

    with pytest.raises(ProviderError, match=r"^Last.fm API request failed$"):
        LastFmProvider().get_candidates(context())


def test_pathological_bounded_json_is_fixed_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            return b'{"count": ' + (b"9" * 5000) + b"}"

    monkeypatch.setattr(
        "beetsplug.noqlenmeta.providers.lastfm.urlopen",
        lambda request, timeout: Response(),
    )

    with pytest.raises(ProviderError, match=r"^Last.fm API request failed$"):
        LastFmProvider().get_candidates(context())


def test_provider_uses_packaged_taxonomy_without_discovering_lastgenre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = fixture()
    payload["toptags"]["tag"] = [
        {"name": "K-pop", "count": 80},
        {"name": "Technical Death Metal", "count": 60},
        {"name": "seen live", "count": 50},
        {"name": "2024", "count": 40},
        {"name": "Energetic", "count": 30},
    ]

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("external vocabulary discovery is forbidden")
        ),
    )

    candidates = LastFmProvider(fetch_top_tags=FetchTopTags(payload)).get_candidates(context())

    assert candidates[0].value == ("K-pop", "Technical Death Metal")


def test_lastfm_provider_satisfies_metadata_provider_contract() -> None:
    lastfm = provider()

    assert isinstance(lastfm, ReleaseMetadataProvider)
    assert lastfm.name == LASTFM_SPEC.name
    assert lastfm.supported_fields is LASTFM_SPEC.supported_fields


def test_scoped_semantic_tags_preserve_provenance_and_category() -> None:
    payload = {
        "toptags": {
            "@attr": {"artist": "Synthetic Artist", "track": "Synthetic Track"},
            "tag": [
                {"name": "k-pop", "count": "80"},
                {"name": "dreamy", "count": "70"},
                {"name": "seen live", "count": "60"},
            ],
        }
    }
    bundle = LastFmTrackProvider(
        fetch_top_tags=lambda artist, title, mbid: payload
    ).get_semantic_evidence(
        TrackEnrichmentContext(
            "Synthetic Artist",
            "Synthetic Track",
            external_ids=(
                ExternalIdentifier(
                    "musicbrainz.recording", "11111111-1111-4111-8111-111111111111"
                ),
            ),
        )
    )
    assert [(item.genre, item.scope, item.weight) for item in bundle.genres] == [
        ("K-pop", ProviderScope.TRACK, 80)
    ]
    assert [(item.canonical_term, item.category, item.scope) for item in bundle.tags] == [
        ("Dreamy", SemanticCategory.MOOD, ProviderScope.TRACK)
    ]
    assert bundle.tags[0].provider == "lastfm"
    assert bundle.tags[0].source_id == "Synthetic Artist / Synthetic Track"
    assert bundle.tags[0].raw_tag == "dreamy"


def test_release_and_artist_semantic_tags_keep_their_scopes() -> None:
    release_payload = {
        "toptags": {
            "@attr": {"artist": "Gojira", "album": "From Mars to Sirius"},
            "tag": [{"name": "dreamy", "count": 50}],
        }
    }
    release = LastFmProvider(
        fetch_top_tags=FetchTopTags(release_payload)
    ).get_semantic_evidence(context())
    artist_payload = {
        "toptags": {
            "@attr": {"artist": "Synthetic Artist"},
            "tag": [{"name": "alternative metal", "count": 40}],
        }
    }
    artist = LastFmArtistProvider(
        fetch_top_tags=lambda name, mbid: artist_payload
    ).get_semantic_evidence(ArtistEnrichmentContext("Synthetic Artist"))

    assert release.tags[0].scope is ProviderScope.RELEASE
    assert release.tags[0].category is SemanticCategory.MOOD
    assert artist.genres[0].scope is ProviderScope.ARTIST
    assert artist.genres[0].genre == "Alternative Metal"


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("NOQLEN_LIVE_TESTS") != "1",
    reason="set NOQLEN_LIVE_TESTS=1 to run live provider tests",
)
def test_live_lastfm_album_genres_pass_production_vocabulary() -> None:
    candidates = LastFmProvider().get_candidates(context())

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.provider == "lastfm"
    assert candidate.field == "genres"
    assert isinstance(candidate.value, tuple) and candidate.value
    assert all(isinstance(genre, str) for genre in candidate.value)
    assert all(DEFAULT_GENRE_TAXONOMY.is_genre(genre) for genre in candidate.value)
