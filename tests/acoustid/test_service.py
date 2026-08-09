from __future__ import annotations

import json
import ssl
from dataclasses import replace
from email.message import Message
from http.client import HTTPException, IncompleteRead
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl

import pytest

import beetsplug.noqlenmeta.acoustid.service as service_module
from beetsplug.noqlenmeta.acoustid import (
    ACOUSTID_LOOKUP_ENDPOINT,
    MAX_LOOKUP_REQUEST_BYTES,
    MAX_LOOKUP_RESPONSE_BYTES,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDFingerprintMaterial,
    AcoustIDFingerprintOrigin,
    AcoustIDHTTPRequest,
    AcoustIDLookupService,
    AcoustIDTransportFailure,
    UrllibAcoustIDTransport,
    default_acoustid_settings,
)
from beetsplug.noqlenmeta.acoustid.service import (
    _cache_key,
    _RejectRedirects,
    _request_body,
)

PRIVATE_FINGERPRINT = "synthetic-private-fingerprint"
PRIVATE_KEY = "synthetic-private-client-key"
PRIVATE_PATH = "/private/media/track.flac"
ACOUSTID_ID = "00000001-0000-4000-8000-000000000001"
RECORDING_ID = "00000065-0000-4000-8000-000000000065"


def material(
    fingerprint: str = PRIVATE_FINGERPRINT, duration: float = 120.0
) -> AcoustIDFingerprintMaterial:
    return AcoustIDFingerprintMaterial(
        "library-item:1", fingerprint, duration, AcoustIDFingerprintOrigin.EXISTING
    )


def successful_body(*, results: list[object] | None = None, **extra: object) -> bytes:
    document: dict[str, object] = {"status": "ok", **extra}
    if results is not None:
        document["results"] = results
    return json.dumps(document, separators=(",", ":")).encode()


def result(
    number: int = 1,
    score: float = 0.95,
    recordings: list[object] | None = None,
    **extra: object,
) -> dict[str, object]:
    return {
        "id": f"{number:08x}-0000-4000-8000-{number:012x}",
        "score": score,
        "recordings": recordings
        if recordings is not None
        else [{"id": RECORDING_ID}],
        **extra,
    }


class Response:
    def __init__(self, body: bytes, *, max_chunk: int | None = None) -> None:
        self.body = body
        self.max_chunk = max_chunk
        self.offset = 0
        self.read_sizes: list[int] = []
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if size < 0:
            raise AssertionError("unbounded read")
        if self.max_chunk is not None:
            size = min(size, self.max_chunk)
        chunk = self.body[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True


class Transport:
    def __init__(self, *outcomes: bytes | Exception) -> None:
        self.outcomes = list(outcomes) or [successful_body(results=[])]
        self.requests = []
        self.responses: list[Response] = []

    def send(self, request):
        self.requests.append(request)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        response = Response(outcome, max_chunk=7)
        self.responses.append(response)
        return response


class FalseyTransport(Transport):
    def __bool__(self) -> bool:
        return False


class Clock:
    def __init__(self, value: float = 0.0, *, advance_on_sleep: bool = True) -> None:
        self.value = value
        self.advance_on_sleep = advance_on_sleep
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        if self.advance_on_sleep:
            self.value += seconds


def service(
    transport: Transport,
    *,
    settings=None,
    credential_resolver=lambda: PRIVATE_KEY,
    clock: Clock | None = None,
) -> AcoustIDLookupService:
    clock = clock or Clock()
    return AcoustIDLookupService(
        settings or default_acoustid_settings(),
        transport=transport,
        credential_resolver=credential_resolver,
        monotonic=clock.monotonic,
        sleeper=clock.sleep,
    )


def test_lookup_disabled_is_fully_lazy() -> None:
    calls: list[str] = []
    transport = Transport()
    value = AcoustIDLookupService(
        replace(default_acoustid_settings(), lookup=False),
        transport=transport,
        credential_resolver=lambda: calls.append("credential"),  # type: ignore[arg-type,func-returns-value]
        monotonic=lambda: calls.append("clock"),  # type: ignore[arg-type,func-returns-value]
        sleeper=lambda seconds: calls.append("sleep"),
    ).lookup(material())

    assert value.verdict is AcoustIDEvidenceVerdict.UNAVAILABLE
    assert value.reason is AcoustIDEvidenceReason.LOOKUP_DISABLED
    assert calls == []
    assert transport.requests == []


@pytest.mark.parametrize("key", [None, ""])
def test_credential_is_lazy_and_missing_key_stops_before_pacing(key: str | None) -> None:
    calls: list[str] = []
    transport = Transport()
    value = AcoustIDLookupService(
        default_acoustid_settings(),
        transport=transport,
        credential_resolver=lambda: calls.append("credential") or key,
        monotonic=lambda: calls.append("clock"),  # type: ignore[arg-type,func-returns-value]
    ).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.CLIENT_KEY_MISSING
    assert calls == ["credential"]
    assert transport.requests == []


def test_default_transport_is_not_constructed_when_lookup_is_disabled(monkeypatch) -> None:
    constructions: list[str] = []
    monkeypatch.setattr(
        service_module,
        "UrllibAcoustIDTransport",
        lambda: constructions.append("transport"),
    )

    value = AcoustIDLookupService(
        replace(default_acoustid_settings(), lookup=False),
        credential_resolver=lambda: PRIVATE_KEY,
    ).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_DISABLED
    assert constructions == []


def test_default_transport_is_not_constructed_when_client_key_is_missing(monkeypatch) -> None:
    constructions: list[str] = []
    monkeypatch.setattr(
        service_module,
        "UrllibAcoustIDTransport",
        lambda: constructions.append("transport"),
    )

    value = AcoustIDLookupService(
        default_acoustid_settings(), credential_resolver=lambda: None
    ).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.CLIENT_KEY_MISSING
    assert constructions == []


def test_default_transport_is_not_constructed_for_oversized_request(monkeypatch) -> None:
    constructions: list[str] = []
    fixed_size = len(_request_body("", 120, PRIVATE_FINGERPRINT))
    oversized_key = "k" * (MAX_LOOKUP_REQUEST_BYTES - fixed_size + 1)
    monkeypatch.setattr(
        service_module,
        "UrllibAcoustIDTransport",
        lambda: constructions.append("transport"),
    )

    value = AcoustIDLookupService(
        default_acoustid_settings(), credential_resolver=lambda: oversized_key
    ).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert constructions == []


def test_default_transport_is_not_constructed_for_prepopulated_cache_hit(monkeypatch) -> None:
    constructions: list[str] = []
    monkeypatch.setattr(
        service_module,
        "UrllibAcoustIDTransport",
        lambda: constructions.append("transport"),
    )
    lookup = AcoustIDLookupService(
        default_acoustid_settings(),
        credential_resolver=lambda: (_ for _ in ()).throw(AssertionError("credential used")),
        monotonic=lambda: (_ for _ in ()).throw(AssertionError("pacing used")),
    )
    lookup._cache[_cache_key(PRIVATE_FINGERPRINT, 120)] = ()

    value = lookup.lookup(material())

    assert value.verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert constructions == []


def test_default_transport_is_created_after_pacing_and_memoized(monkeypatch) -> None:
    events: list[str] = []
    clock = Clock()

    class DefaultTransport(Transport):
        def send(self, request):
            events.append("send")
            return super().send(request)

    transport = DefaultTransport()

    def construct_transport():
        events.append("construct")
        return transport

    def monotonic() -> float:
        events.append("pace")
        return clock.monotonic()

    monkeypatch.setattr(service_module, "UrllibAcoustIDTransport", construct_transport)
    lookup = AcoustIDLookupService(
        replace(default_acoustid_settings(), cache_entries=0),
        credential_resolver=lambda: PRIVATE_KEY,
        monotonic=monotonic,
        sleeper=clock.sleep,
    )

    lookup.lookup(material("fingerprint-a"))
    clock.value = 1.0
    lookup.lookup(material("fingerprint-b"))

    assert events == ["pace", "construct", "send", "pace", "send"]
    assert len(transport.requests) == 2


def test_request_contract_is_exact_and_uses_injected_timeout() -> None:
    transport = Transport(successful_body(results=[result()]))
    settings = replace(default_acoustid_settings(), timeout_seconds=7.25, cache_entries=0)

    value = service(transport, settings=settings).lookup(material(duration=12.5))

    request = transport.requests[0]
    assert request.url == ACOUSTID_LOOKUP_ENDPOINT
    assert request.method == "POST"
    assert request.content_type == "application/x-www-form-urlencoded"
    assert request.timeout_seconds == 7.25
    assert "?" not in request.url
    assert parse_qsl(request.body.decode(), keep_blank_values=True) == [
        ("client", PRIVATE_KEY),
        ("duration", "13"),
        ("fingerprint", PRIVATE_FINGERPRINT),
        ("meta", "recordingids"),
        ("format", "json"),
    ]
    assert len(parse_qsl(request.body.decode(), keep_blank_values=True)) == 5
    assert value.verdict is AcoustIDEvidenceVerdict.DECISIVE


@pytest.mark.parametrize(
    ("duration", "expected"),
    [(0.1, "1"), (0.49, "1"), (1.49, "1"), (1.5, "2"), (2.5, "3")],
)
def test_duration_uses_deterministic_half_up_rounding(duration: float, expected: str) -> None:
    transport = Transport()

    service(transport).lookup(material(duration=duration))

    assert dict(parse_qsl(transport.requests[0].body.decode()))["duration"] == expected


def test_request_size_accepts_exact_limit_and_rejects_above_before_transport() -> None:
    fingerprint = PRIVATE_FINGERPRINT
    fixed_size = len(_request_body("", 120, fingerprint))
    exact_key = "k" * (MAX_LOOKUP_REQUEST_BYTES - fixed_size)
    exact_transport = Transport()
    above_transport = Transport()

    exact = service(exact_transport, credential_resolver=lambda: exact_key).lookup(
        material(fingerprint)
    )
    above = service(above_transport, credential_resolver=lambda: exact_key + "k").lookup(
        material(fingerprint)
    )

    assert len(exact_transport.requests[0].body) == MAX_LOOKUP_REQUEST_BYTES
    assert exact.verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert above.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert above_transport.requests == []


def test_default_transport_builds_exact_verified_post_without_retry() -> None:
    captured = []

    def opener(request, *, timeout):
        captured.append((request, timeout))
        return Response(successful_body())

    request_body = _request_body(PRIVATE_KEY, 1, PRIVATE_FINGERPRINT)
    transport = UrllibAcoustIDTransport(opener)
    response = transport.send(AcoustIDHTTPRequest(request_body, 4.0))

    request, timeout = captured[0]
    assert request.full_url == ACOUSTID_LOOKUP_ENDPOINT
    assert request.get_method() == "POST"
    assert request.data == request_body
    assert request.get_header("Content-type") == "application/x-www-form-urlencoded"
    assert timeout == 4.0
    assert response is not None
    assert len(captured) == 1


def test_default_transport_rejects_non_https_or_non_contract_request_before_open() -> None:
    calls = []
    transport = UrllibAcoustIDTransport(lambda *args, **kwargs: calls.append((args, kwargs)))
    request = AcoustIDHTTPRequest(b"private request body", 4.0)
    object.__setattr__(request, "url", "http://api.acoustid.org/v2/lookup")

    with pytest.raises(AcoustIDTransportFailure):
        transport.send(request)
    assert calls == []


def test_default_transport_builds_verified_tls_context(monkeypatch) -> None:
    context = object()
    handlers = []

    class Opener:
        def open(self, request, *, timeout):  # pragma: no cover - construction-only fake
            raise AssertionError("network must remain unused")

    monkeypatch.setattr(service_module.ssl, "create_default_context", lambda: context)
    monkeypatch.setattr(
        service_module,
        "build_opener",
        lambda *values: handlers.extend(values) or Opener(),
    )

    UrllibAcoustIDTransport()

    https_handler = next(
        value for value in handlers if isinstance(value, service_module.HTTPSHandler)
    )
    assert https_handler._context is context
    assert any(isinstance(value, _RejectRedirects) for value in handlers)


def test_falsey_injected_transport_is_used_without_default_network_boundary() -> None:
    transport = FalseyTransport()

    value = service(transport).lookup(material())

    assert value.verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert len(transport.requests) == 1


def test_default_transport_closes_and_sanitizes_http_error_without_retry() -> None:
    response = BytesIO(b"private response body")
    calls = []

    def opener(request, *, timeout):
        calls.append((request, timeout))
        raise HTTPError(ACOUSTID_LOOKUP_ENDPOINT, 429, "private error", Message(), response)

    transport = UrllibAcoustIDTransport(opener)
    with pytest.raises(AcoustIDTransportFailure) as captured:
        transport.send(AcoustIDHTTPRequest(b"private request body", 4.0))

    assert str(captured.value) == "AcoustID lookup transport failed"
    assert response.closed
    assert len(calls) == 1
    assert captured.value.__context__ is None


def test_redirect_handler_fails_closed_and_service_does_not_retry() -> None:
    redirect_response = Response(b"private redirect response")
    with pytest.raises(AcoustIDTransportFailure, match="transport failed"):
        _RejectRedirects().redirect_request(
            None, redirect_response, 302, "secret", {}, "https://other"
        )
    assert redirect_response.closed

    transport = Transport(AcoustIDTransportFailure("private redirect detail"))
    value = service(transport).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert len(transport.requests) == 1


def test_response_reader_is_incremental_and_accepts_exact_limit() -> None:
    body = successful_body() + b" " * (MAX_LOOKUP_RESPONSE_BYTES - len(successful_body()))
    transport = Transport(body)

    value = service(transport).lookup(material())

    response = transport.responses[0]
    assert value.verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert response.closed
    assert response.offset == MAX_LOOKUP_RESPONSE_BYTES
    assert all(0 <= size <= 65_536 for size in response.read_sizes)


def test_response_above_limit_is_closed_and_fails() -> None:
    body = successful_body() + b" " * (MAX_LOOKUP_RESPONSE_BYTES + 1 - len(successful_body()))
    transport = Transport(body)

    value = service(transport).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert transport.responses[0].closed
    assert transport.responses[0].offset == MAX_LOOKUP_RESPONSE_BYTES + 1


@pytest.mark.parametrize(
    "body",
    [
        b"\xff",
        b"{",
        b'{"status":"ok"} trailing',
        b'{"status":"ok","results":[NaN]}',
        b'{"status":"ok","results":[Infinity]}',
        b'{"status":"ok","results":[-Infinity]}',
        b'{"status":"error","status":"ok"}',
        b'{"status":"ok","results":[],"results":[]}',
    ],
)
def test_invalid_utf8_malformed_or_nonstandard_json_fails(body: bytes) -> None:
    value = service(Transport(body)).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_FAILED


@pytest.mark.parametrize(
    "body",
    [
        b"[]",
        b"{}",
        b'{"status":"error","error":{"message":"private server error"}}',
        b'{"status":1}',
        b'{"status":"ok","results":{}}',
        b'{"status":"ok","results":[null]}',
        b'{"status":"ok","results":[{"id":"bad","score":0.9,"recordings":[]}]}',
        b'{"status":"ok","results":[{"id":"00000001-0000-4000-8000-000000000001","score":true,"recordings":[{"id":"00000065-0000-4000-8000-000000000065"}]}]}',
        b'{"status":"ok","results":[{"score":0.9,"recordings":[{"id":"00000065-0000-4000-8000-000000000065"}]}]}',
        b'{"status":"ok","results":[{"id":"00000001-0000-4000-8000-000000000001","recordings":[{"id":"00000065-0000-4000-8000-000000000065"}]}]}',
        b'{"status":"ok","results":[{"id":"00000001-0000-4000-8000-000000000001","score":1.1,"recordings":[{"id":"00000065-0000-4000-8000-000000000065"}]}]}',
        b'{"status":"ok","results":[{"id":"00000001-0000-4000-8000-000000000001","score":1e999,"recordings":[{"id":"00000065-0000-4000-8000-000000000065"}]}]}',
        b'{"status":"ok","results":[{"id":"00000001-0000-4000-8000-000000000001","score":0.9,"recordings":[{}]}]}',
        b'{"status":"ok","results":[{"id":"00000001-0000-4000-8000-000000000001","score":0.9,"recordings":[{"id":"bad"}]}]}',
    ],
)
def test_bad_service_status_or_retained_schema_fails(body: bytes) -> None:
    value = service(Transport(body)).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_FAILED


@pytest.mark.parametrize("body", [successful_body(), successful_body(results=[])])
def test_absent_or_empty_results_is_valid_no_match(body: bytes) -> None:
    value = service(Transport(body)).lookup(material())

    assert value.verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert value.reason is AcoustIDEvidenceReason.NO_RESULT_ABOVE_MINIMUM


def test_unknown_metadata_is_ignored_and_never_enters_domain() -> None:
    private_metadata = "private-title-artist-release-url-isrc-source"
    body = successful_body(
        results=[
            result(
                title=private_metadata,
                artists=[{"name": private_metadata}],
                releases=[{"id": private_metadata}],
                recordings=[{"id": RECORDING_ID, "title": private_metadata}],
            )
        ],
        error={"message": private_metadata},
    )

    value = service(Transport(body)).lookup(material())

    assert value.result_groups[0].acoustid_id == ACOUSTID_ID
    assert value.result_groups[0].recording_mbids == (RECORDING_ID,)
    assert private_metadata not in repr(value)
    assert set(value.result_groups[0].__slots__) == {"acoustid_id", "score", "recording_mbids"}


def test_result_and_recording_bounds_apply_before_domain_construction() -> None:
    settings = replace(
        default_acoustid_settings(), max_results=2, max_recordings_per_result=2
    )
    body = successful_body(
        results=[
            result(1, recordings=[{"id": RECORDING_ID}, {"id": RECORDING_ID}, None]),
            result(
                2,
                recordings=[
                    {"id": "00000066-0000-4000-8000-000000000066"},
                    {"id": "00000067-0000-4000-8000-000000000067"},
                    None,
                ],
            ),
            None,
        ]
    )

    value = service(Transport(body), settings=settings).lookup(material())

    assert len(value.result_groups) == 2
    assert value.result_groups[0].recording_mbids == (RECORDING_ID,)
    assert len(value.result_groups[1].recording_mbids) == 2


def test_sequential_pacing_uses_monotonic_interval_and_first_request_does_not_sleep() -> None:
    clock = Clock(10.0)
    transport = Transport()
    lookup = service(
        transport,
        settings=replace(default_acoustid_settings(), requests_per_second=2.0, cache_entries=0),
        clock=clock,
    )

    lookup.lookup(material("fingerprint-a"))
    lookup.lookup(material("fingerprint-b"))

    assert clock.sleeps == [0.5]
    assert len(transport.requests) == 2


def test_pacing_has_no_wall_clock_dependency(monkeypatch) -> None:
    monkeypatch.setattr(
        service_module.time,
        "time",
        lambda: (_ for _ in ()).throw(AssertionError("wall clock used")),
    )

    value = service(Transport(), clock=Clock()).lookup(material())

    assert value.verdict is AcoustIDEvidenceVerdict.NO_MATCH


def test_cache_hit_neither_sleeps_nor_uses_network() -> None:
    clock = Clock()
    transport = Transport(successful_body(results=[result()]))
    lookup = service(transport, clock=clock)

    first = lookup.lookup(material())
    second = lookup.lookup(material())

    assert second == first
    assert len(transport.requests) == 1
    assert clock.sleeps == []


def test_network_failure_consumes_slot_and_is_not_cached() -> None:
    clock = Clock()
    transport = Transport(TimeoutError("private timeout"), successful_body())
    lookup = service(transport, clock=clock)

    first = lookup.lookup(material())
    second = lookup.lookup(material())

    assert first.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert second.verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert len(transport.requests) == 2
    assert clock.sleeps == [pytest.approx(1 / 3)]


@pytest.mark.parametrize("second_time", [9.0, float("nan"), float("inf")])
def test_impossible_monotonic_movement_fails_without_transport(second_time: float) -> None:
    times = iter([10.0, second_time])
    transport = Transport()
    lookup = AcoustIDLookupService(
        replace(default_acoustid_settings(), cache_entries=0),
        transport=transport,
        credential_resolver=lambda: PRIVATE_KEY,
        monotonic=lambda: next(times),
        sleeper=lambda seconds: None,
    )

    assert lookup.lookup(material("fingerprint-a")).verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert lookup.lookup(material("fingerprint-b")).reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert len(transport.requests) == 1


def test_cache_entries_zero_disables_cache() -> None:
    transport = Transport()
    lookup = service(
        transport, settings=replace(default_acoustid_settings(), cache_entries=0), clock=Clock()
    )

    lookup.lookup(material())
    lookup.lookup(material())

    assert len(transport.requests) == 2


def test_cache_uses_deterministic_fifo_eviction() -> None:
    transport = Transport()
    lookup = service(
        transport, settings=replace(default_acoustid_settings(), cache_entries=2), clock=Clock()
    )

    lookup.lookup(material("fingerprint-a"))
    lookup.lookup(material("fingerprint-b"))
    lookup.lookup(material("fingerprint-a"))
    lookup.lookup(material("fingerprint-c"))
    lookup.lookup(material("fingerprint-b"))
    lookup.lookup(material("fingerprint-a"))

    assert len(transport.requests) == 4


def test_cache_key_is_digest_only_and_frames_fingerprint_and_rounded_duration() -> None:
    first = _cache_key(PRIVATE_FINGERPRINT, 1)
    changed_fingerprint = _cache_key(PRIVATE_FINGERPRINT + "x", 1)
    changed_duration = _cache_key(PRIVATE_FINGERPRINT, 2)

    assert len(first) == 64
    assert first != changed_fingerprint != changed_duration
    assert PRIVATE_FINGERPRINT not in first
    assert PRIVATE_KEY not in first
    assert repr(first) == repr(first)


def test_parsing_and_service_failures_are_not_cached() -> None:
    transport = Transport(b"{", successful_body())
    lookup = service(transport, clock=Clock())

    assert lookup.lookup(material()).reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert lookup.lookup(material()).verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert len(transport.requests) == 2


def test_response_read_failure_is_closed_sanitized_and_not_cached() -> None:
    class ReadFailureResponse(Response):
        def read(self, size: int = -1) -> bytes:
            raise OSError("private read failure")

    class ReadFailureTransport(Transport):
        def send(self, request):
            self.requests.append(request)
            response = ReadFailureResponse(b"private response")
            self.responses.append(response)
            return response

    transport = ReadFailureTransport()
    lookup = service(transport, clock=Clock())

    first = lookup.lookup(material())
    second = lookup.lookup(material())

    assert first.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert second.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert len(transport.requests) == 2
    assert all(response.closed for response in transport.responses)
    assert "private" not in repr((first, second))


@pytest.mark.parametrize(
    "read_error",
    [
        IncompleteRead(b"private partial response", expected=123),
        HTTPException("private HTTP reader failure"),
    ],
)
def test_http_response_read_failure_is_operational_closed_and_not_cached(
    read_error: HTTPException,
) -> None:
    class HTTPReadFailureResponse(Response):
        def read(self, size: int = -1) -> bytes:
            raise read_error

    class HTTPReadFailureTransport(Transport):
        def send(self, request):
            self.requests.append(request)
            response = (
                HTTPReadFailureResponse(b"")
                if len(self.requests) == 1
                else Response(successful_body())
            )
            self.responses.append(response)
            return response

    transport = HTTPReadFailureTransport()
    lookup = service(transport, clock=Clock())

    first = lookup.lookup(material())
    second = lookup.lookup(material())

    assert first.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert second.verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert len(transport.requests) == 2
    assert all(response.closed for response in transport.responses)
    assert "private partial response" not in repr(first)
    assert "private HTTP reader failure" not in repr(first)


def test_unexpected_credential_resolver_error_is_sanitized_and_propagated() -> None:
    private_error = f"programmer {PRIVATE_KEY} {PRIVATE_FINGERPRINT} {PRIVATE_PATH}"
    lookup = AcoustIDLookupService(
        default_acoustid_settings(),
        credential_resolver=lambda: (_ for _ in ()).throw(RuntimeError(private_error)),
    )

    with pytest.raises(RuntimeError) as captured:
        lookup.lookup(material())

    assert str(captured.value) == "AcoustID credential boundary failed"
    assert private_error not in str(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_unexpected_transport_error_is_sanitized_and_propagated() -> None:
    class ProgrammerTransport(Transport):
        def send(self, request):
            raise RuntimeError(request.body.decode())

    with pytest.raises(RuntimeError) as captured:
        service(ProgrammerTransport()).lookup(material())

    assert str(captured.value) == "AcoustID transport boundary failed"
    assert PRIVATE_KEY not in str(captured.value)
    assert PRIVATE_FINGERPRINT not in str(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_unexpected_response_error_is_sanitized_and_propagated() -> None:
    class ProgrammerResponse(Response):
        def read(self, size: int = -1) -> bytes:
            raise RuntimeError(f"private response {PRIVATE_FINGERPRINT}")

    class ProgrammerTransport(Transport):
        def send(self, request):
            response = ProgrammerResponse(b"")
            self.responses.append(response)
            return response

    transport = ProgrammerTransport()

    with pytest.raises(RuntimeError) as captured:
        service(transport).lookup(material())

    assert str(captured.value) == "AcoustID response boundary failed"
    assert PRIVATE_FINGERPRINT not in str(captured.value)
    assert transport.responses[0].closed
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_unexpected_evidence_error_is_sanitized_and_propagated(monkeypatch) -> None:
    private_error = f"programmer {PRIVATE_KEY} {PRIVATE_FINGERPRINT}"
    monkeypatch.setattr(
        service_module,
        "classify_acoustid_evidence",
        lambda *args: (_ for _ in ()).throw(RuntimeError(private_error)),
    )

    with pytest.raises(RuntimeError) as captured:
        service(Transport()).lookup(material())

    assert str(captured.value) == "AcoustID evidence boundary failed"
    assert private_error not in str(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_non_encodable_fingerprint_fails_before_credential_pacing_or_network() -> None:
    private_fingerprint = "private-surrogate-\ud800-fingerprint"
    calls: list[str] = []
    transport = Transport()
    lookup = AcoustIDLookupService(
        default_acoustid_settings(),
        transport=transport,
        credential_resolver=lambda: calls.append("credential"),  # type: ignore[arg-type,func-returns-value]
        monotonic=lambda: calls.append("pace"),  # type: ignore[arg-type,func-returns-value]
    )

    value = lookup.lookup(material(private_fingerprint))

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert calls == []
    assert transport.requests == []
    assert private_fingerprint not in repr(value)


def test_non_encodable_client_key_fails_before_pacing_or_network() -> None:
    private_key = "private-surrogate-\ud800-key"
    calls: list[str] = []
    transport = Transport()
    lookup = AcoustIDLookupService(
        default_acoustid_settings(),
        transport=transport,
        credential_resolver=lambda: private_key,
        monotonic=lambda: calls.append("pace"),  # type: ignore[arg-type,func-returns-value]
    )

    value = lookup.lookup(material())

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert calls == []
    assert transport.requests == []
    assert private_key not in repr(value)


@pytest.mark.parametrize("status", [400, 404, 429, 500, 503])
def test_http_failures_map_to_lookup_failed_without_retry(status: int) -> None:
    error = HTTPError(
        ACOUSTID_LOOKUP_ENDPOINT, status, "private server error", {}, Response(b"private body")
    )
    transport = Transport(error)

    value = service(transport).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert len(transport.requests) == 1


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("private timeout"),
        ssl.SSLError("private tls"),
        URLError("private url"),
        ConnectionError("private connection"),
        OSError("private os error"),
        AcoustIDTransportFailure("private redirect"),
    ],
)
def test_transport_failures_are_sanitized(error: Exception) -> None:
    value = service(Transport(error)).lookup(material())

    assert value.reason is AcoustIDEvidenceReason.LOOKUP_FAILED
    assert "private" not in repr(value)


def test_complete_public_sanitization() -> None:
    private_response = b'{"status":"error","error":{"message":"private server body"}}'
    transport = Transport(private_response)
    lookup = service(transport, credential_resolver=lambda: PRIVATE_KEY)

    value = lookup.lookup(material())

    rendered = repr((lookup, transport.requests[0], value))
    for private in (
        PRIVATE_KEY,
        PRIVATE_FINGERPRINT,
        PRIVATE_PATH,
        transport.requests[0].body.decode(),
        private_response.decode(),
        "private server body",
    ):
        assert private not in rendered
