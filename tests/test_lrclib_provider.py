import copy
import importlib.metadata
import json
import logging
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from beetsplug.noqlenmeta.changeplan import build_change_plan
from beetsplug.noqlenmeta.domain import TrackEnrichmentContext
from beetsplug.noqlenmeta.integration import resolution_policy_from_settings
from beetsplug.noqlenmeta.orchestration import validate_provider_candidates
from beetsplug.noqlenmeta.providers import ProviderError, TrackMetadataProvider
from beetsplug.noqlenmeta.providers.lrclib import (
    LRCLIBProvider,
    _LRCLIBTransport,
)
from beetsplug.noqlenmeta.providers.specs import LRCLIB_SPEC
from beetsplug.noqlenmeta.resolver import ResolutionAction, resolve_metadata

FIXTURES = Path(__file__).parent / "fixtures" / "lrclib"


def fixture() -> dict[str, Any]:
    return json.loads((FIXTURES / "exact_track.json").read_text(encoding="utf-8"))


def context(**overrides: object) -> TrackEnrichmentContext:
    values: dict[str, object] = {
        "artist": "Synthetic Artist",
        "title": "Synthetic Track",
        "album_title": "Synthetic Album",
        "duration": 240.0,
    }
    values.update(overrides)
    return TrackEnrichmentContext(**values)  # type: ignore[arg-type]


class FetchRecord:
    def __init__(self, *payloads: object) -> None:
        self.payloads = list(payloads) or [fixture()]
        self.calls: list[tuple[str, str, str, float]] = []

    def __call__(
        self, artist: str, title: str, album: str, duration: float
    ) -> object:
        self.calls.append((artist, title, album, duration))
        return copy.deepcopy(self.payloads.pop(0))


@pytest.mark.parametrize(
    "missing",
    [
        {"album_title": None},
        {"duration": None},
    ],
)
def test_incomplete_exact_signature_returns_no_data_without_network(
    missing: dict[str, object],
) -> None:
    fetch = FetchRecord()

    assert LRCLIBProvider(fetch_record=fetch).get_candidates(context(**missing)) == ()
    assert fetch.calls == []


def test_both_lyrics_forms_are_independent_ordered_candidates() -> None:
    candidates = LRCLIBProvider(fetch_record=FetchRecord()).get_candidates(context())

    assert [candidate.field for candidate in candidates] == ["lyrics", "synced_lyrics"]
    assert candidates[0].value == "Synthetic line one\nSynthetic line two"
    assert candidates[1].value == (
        "[00:01.00] Synthetic line one\n[00:04.00] Synthetic line two"
    )
    assert all(candidate.provider == "lrclib" for candidate in candidates)
    assert all(candidate.confidence == 0.95 for candidate in candidates)
    assert {candidate.source_id for candidate in candidates} == {"12345"}
    assert {candidate.source_url for candidate in candidates} == {
        "https://lrclib.net/api/get/12345"
    }


@pytest.mark.parametrize(
    ("plain", "synced", "expected_fields"),
    [
        ("Synthetic plain lyrics", None, ["lyrics"]),
        (None, "[00:01.00] Synthetic synced lyrics", ["synced_lyrics"]),
        (None, None, []),
        ("  ", "\n\t", []),
    ],
)
def test_lyrics_forms_are_emitted_only_when_independently_present(
    plain: object, synced: object, expected_fields: list[str]
) -> None:
    payload = fixture()
    payload["plainLyrics"] = plain
    payload["syncedLyrics"] = synced

    candidates = LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())

    assert [candidate.field for candidate in candidates] == expected_fields


def test_instrumental_record_emits_no_candidates() -> None:
    payload = fixture()
    payload["instrumental"] = True

    assert LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context()) == ()


@pytest.mark.parametrize(
    ("field", "value"),
    [("plainLyrics", []), ("plainLyrics", 123), ("syncedLyrics", []), ("syncedLyrics", 123)],
)
def test_non_string_lyrics_values_are_malformed(field: str, value: object) -> None:
    payload = fixture()
    payload[field] = value

    with pytest.raises(ProviderError, match=r"^LRCLIB API response is invalid$"):
        LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())


def test_identity_allows_only_case_and_ordinary_whitespace_changes() -> None:
    payload = fixture()
    payload.update(
        {
            "trackName": " SYNTHETIC   TRACK ",
            "artistName": "SYNTHETIC\tARTIST",
            "albumName": "synthetic\nAlbum",
        }
    )

    assert LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())


@pytest.mark.parametrize("field", ["trackName", "artistName", "albumName"])
def test_material_identity_mismatch_is_provider_error(field: str) -> None:
    payload = fixture()
    payload[field] = "Materially Different"

    with pytest.raises(ProviderError, match=r"identity does not match"):
        LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())


@pytest.mark.parametrize("duration", [238.0, 242.0])
def test_duration_boundary_is_accepted(duration: float) -> None:
    payload = fixture()
    payload["duration"] = duration

    assert LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())


@pytest.mark.parametrize("duration", [237.99, 242.01])
def test_duration_outside_tolerance_is_rejected(duration: float) -> None:
    payload = fixture()
    payload["duration"] = duration

    with pytest.raises(ProviderError, match=r"duration does not match"):
        LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())


@pytest.mark.parametrize(
    "duration", [True, float("nan"), float("inf"), 0, -1, "240"]
)
def test_malformed_response_duration_is_rejected(duration: object) -> None:
    payload = fixture()
    payload["duration"] = duration

    with pytest.raises(ProviderError, match=r"^LRCLIB API response is invalid$"):
        LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())


@pytest.mark.parametrize("record_id", [None, 0, -1, True, "12345", 12345.0])
def test_malformed_record_id_is_rejected(record_id: object) -> None:
    payload = fixture()
    if record_id is None:
        del payload["id"]
    else:
        payload["id"] = record_id

    with pytest.raises(ProviderError, match=r"^LRCLIB API response is invalid$"):
        LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())


@pytest.mark.parametrize("instrumental", [None, 0, 1, "false"])
def test_instrumental_flag_must_be_a_real_boolean(instrumental: object) -> None:
    payload = fixture()
    payload["instrumental"] = instrumental

    with pytest.raises(ProviderError, match=r"^LRCLIB API response is invalid$"):
        LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())


def test_same_exact_signature_success_is_cached() -> None:
    fetch = FetchRecord()
    provider = LRCLIBProvider(fetch_record=fetch)

    assert provider.get_candidates(context()) == provider.get_candidates(context())
    assert len(fetch.calls) == 1


def test_malformed_response_is_not_cached() -> None:
    malformed = fixture()
    malformed["id"] = "12345"
    fetch = FetchRecord(malformed, fixture())
    provider = LRCLIBProvider(fetch_record=fetch)

    with pytest.raises(ProviderError):
        provider.get_candidates(context())
    assert provider.get_candidates(context())
    assert len(fetch.calls) == 2


class Response:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.read_sizes: list[int] = []

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        return self.body[:size]


def test_production_transport_uses_only_exact_endpoint_and_identifying_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    response = Response(json.dumps(fixture()).encode())

    def fake_urlopen(request: object, timeout: float) -> Response:
        captured["url"] = request.full_url  # type: ignore[attr-defined]
        captured["user_agent"] = request.get_header("User-agent")  # type: ignore[attr-defined]
        captured["timeout"] = timeout
        return response

    monkeypatch.setattr("beetsplug.noqlenmeta.providers.lrclib.urlopen", fake_urlopen)

    assert LRCLIBProvider().get_candidates(context())
    parsed = urlsplit(str(captured["url"]))
    assert parsed.scheme == "https"
    assert parsed.netloc == "lrclib.net"
    assert parsed.path == "/api/get"
    assert parse_qs(parsed.query) == {
        "track_name": ["Synthetic Track"],
        "artist_name": ["Synthetic Artist"],
        "album_name": ["Synthetic Album"],
        "duration": ["240.0"],
    }
    assert "/api/search" not in str(captured["url"])
    assert "beets-noqlenmeta/" in str(captured["user_agent"])
    assert importlib.metadata.version("beets-noqlenmeta") in str(captured["user_agent"])
    assert captured["timeout"] == 10.0
    assert response.read_sizes == [2 * 1024 * 1024 + 1]


def test_user_agent_uses_safe_fallback_when_package_metadata_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def missing_version(distribution: str) -> str:
        raise importlib.metadata.PackageNotFoundError(distribution)

    def fake_urlopen(request: object, timeout: float) -> Response:
        captured["user_agent"] = request.get_header("User-agent")  # type: ignore[attr-defined]
        return Response(json.dumps(fixture()).encode())

    monkeypatch.setattr(
        "beetsplug.noqlenmeta.providers.lrclib.importlib.metadata.version",
        missing_version,
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.providers.lrclib.urlopen", fake_urlopen)

    assert LRCLIBProvider().get_candidates(context())
    assert captured["user_agent"] == (
        "beets-noqlenmeta/0+unknown (https://pypi.org/project/beets-noqlenmeta/)"
    )


def http_error(code: int, retry_after: object = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return HTTPError("https://lrclib.net/api/get", code, "unsafe", headers, None)


def test_production_404_is_cached_quiet_no_data() -> None:
    calls = 0

    def not_found(request: object, timeout: float) -> object:
        nonlocal calls
        calls += 1
        raise http_error(404)

    provider = LRCLIBProvider(transport=_LRCLIBTransport(opener=not_found))

    assert provider.get_candidates(context()) == ()
    assert provider.get_candidates(context()) == ()
    assert calls == 1


def test_production_500_is_fixed_provider_error() -> None:
    def unavailable(request: object, timeout: float) -> object:
        raise http_error(500)

    with pytest.raises(ProviderError) as raised:
        LRCLIBProvider(transport=_LRCLIBTransport(opener=unavailable)).get_candidates(
            context()
        )

    assert str(raised.value) == "LRCLIB API request failed"
    assert "unsafe" not in str(raised.value)


def test_invalid_json_is_fixed_provider_error() -> None:
    transport = _LRCLIBTransport(opener=lambda request, timeout: Response(b"not json"))

    with pytest.raises(ProviderError, match=r"^LRCLIB API response is invalid$"):
        LRCLIBProvider(transport=transport).get_candidates(context())


def test_oversized_response_is_fixed_provider_error() -> None:
    body = b"x" * (2 * 1024 * 1024 + 1)
    transport = _LRCLIBTransport(opener=lambda request, timeout: Response(body))

    with pytest.raises(ProviderError, match=r"exceeded the size limit$"):
        LRCLIBProvider(transport=transport).get_candidates(context())


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_two_uncached_signatures_are_paced_without_real_sleep() -> None:
    clock = FakeClock()
    payloads = [fixture(), fixture()]

    def opener(request: object, timeout: float) -> Response:
        payload = payloads.pop(0)
        query = parse_qs(urlsplit(request.full_url).query)  # type: ignore[attr-defined]
        payload["trackName"] = query["track_name"][0]
        return Response(json.dumps(payload).encode())

    provider = LRCLIBProvider(
        transport=_LRCLIBTransport(
            opener=opener, monotonic=clock.monotonic, sleep=clock.sleep
        )
    )
    provider.get_candidates(context())
    provider.get_candidates(context(title="Synthetic Second Track"))

    assert clock.sleeps == [pytest.approx(0.3)]


def test_cache_hit_does_not_trigger_pacing_sleep() -> None:
    clock = FakeClock()
    provider = LRCLIBProvider(
        transport=_LRCLIBTransport(
            opener=lambda request, timeout: Response(json.dumps(fixture()).encode()),
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )
    )

    provider.get_candidates(context())
    provider.get_candidates(context())

    assert clock.sleeps == []


def test_valid_retry_after_blocks_the_next_uncached_request() -> None:
    clock = FakeClock()
    calls = 0

    def opener(request: object, timeout: float) -> Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise http_error(429, 2)
        payload = fixture()
        query = parse_qs(urlsplit(request.full_url).query)  # type: ignore[attr-defined]
        payload["trackName"] = query["track_name"][0]
        return Response(json.dumps(payload).encode())

    provider = LRCLIBProvider(
        transport=_LRCLIBTransport(
            opener=opener, monotonic=clock.monotonic, sleep=clock.sleep
        )
    )

    with pytest.raises(ProviderError, match=r"^LRCLIB API rate limit exceeded$"):
        provider.get_candidates(context())
    assert provider.get_candidates(context(title="Synthetic Second Track"))
    assert clock.sleeps == [2.0]


@pytest.mark.parametrize("retry_after", [None, -1, "not-a-number", "NaN"])
def test_invalid_retry_after_is_fixed_safe_error(retry_after: object) -> None:
    def rate_limited(request: object, timeout: float) -> object:
        raise http_error(429, retry_after)

    with pytest.raises(ProviderError) as raised:
        LRCLIBProvider(
            transport=_LRCLIBTransport(opener=rate_limited)
        ).get_candidates(context())

    assert str(raised.value) == "LRCLIB API rate limit response is invalid"
    assert str(retry_after) not in str(raised.value)


def test_invalid_retry_after_keeps_normal_minimum_pacing_for_next_request() -> None:
    clock = FakeClock()
    calls = 0

    def opener(request: object, timeout: float) -> Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise http_error(429, "not-a-number")
        payload = fixture()
        query = parse_qs(urlsplit(request.full_url).query)  # type: ignore[attr-defined]
        payload["trackName"] = query["track_name"][0]
        return Response(json.dumps(payload).encode())

    provider = LRCLIBProvider(
        transport=_LRCLIBTransport(
            opener=opener, monotonic=clock.monotonic, sleep=clock.sleep
        )
    )

    with pytest.raises(ProviderError):
        provider.get_candidates(context())
    assert provider.get_candidates(context(title="Synthetic Second Track"))
    assert clock.sleeps == [pytest.approx(0.3)]


def test_external_failure_body_and_exception_detail_never_escape(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail(request: object, timeout: float) -> object:
        raise URLError("Synthetic line one")

    with caplog.at_level(logging.DEBUG), pytest.raises(ProviderError) as raised:
        LRCLIBProvider(transport=_LRCLIBTransport(opener=fail)).get_candidates(context())

    assert "Synthetic line one" not in str(raised.value)
    assert "Synthetic line one" not in caplog.text


def test_programming_error_is_not_disguised_as_provider_error() -> None:
    def fail(request: object, timeout: float) -> object:
        raise AttributeError("programming defect")

    with pytest.raises(AttributeError, match="programming defect"):
        LRCLIBProvider(transport=_LRCLIBTransport(opener=fail)).get_candidates(context())


def test_lrclib_provider_satisfies_track_provider_contract() -> None:
    provider = LRCLIBProvider(fetch_record=FetchRecord())

    assert isinstance(provider, TrackMetadataProvider)
    assert provider.name == LRCLIB_SPEC.name
    assert provider.supported_fields is LRCLIB_SPEC.supported_fields


def test_candidates_flow_through_shared_resolver_and_change_plan() -> None:
    candidates = validate_provider_candidates(
        LRCLIB_SPEC,
        LRCLIBProvider(fetch_record=FetchRecord()).get_candidates(context()),
    )
    policy = resolution_policy_from_settings(
        {"lyrics": True, "synced_lyrics": True},
        {"lrclib": True},
    )

    decisions = resolve_metadata({}, candidates, policy)
    plan = build_change_plan(decisions)

    assert {decision.field: decision.action for decision in decisions} == {
        "lyrics": ResolutionAction.PROPOSE,
        "synced_lyrics": ResolutionAction.PROPOSE,
    }
    assert [change.field for change in plan.changes] == ["lyrics", "synced_lyrics"]


def test_existing_lyrics_safety_remains_shared_resolver_policy() -> None:
    payload = fixture()
    payload["syncedLyrics"] = None
    candidates = LRCLIBProvider(fetch_record=FetchRecord(payload)).get_candidates(context())
    preserving = resolution_policy_from_settings(
        {"lyrics": True}, {"lrclib": True}
    )
    replacing = resolution_policy_from_settings(
        {"lyrics": True},
        {"lrclib": True},
        preserve_existing_settings={"lyrics": False},
    )

    assert resolve_metadata(
        {"lyrics": "Existing local lyrics"}, candidates, preserving
    )[0].action is ResolutionAction.REVIEW
    assert resolve_metadata(
        {"lyrics": "Existing local lyrics"}, candidates, replacing
    )[0].action is ResolutionAction.PROPOSE
