from __future__ import annotations

import hashlib
import json
import math
import os
import ssl
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from http.client import HTTPException
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)

from .domain import (
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDFingerprintMaterial,
    AcoustIDResultGroup,
    AcoustIDTrackEvidence,
)
from .evidence import classify_acoustid_evidence
from .settings import AcoustIDSettings

ACOUSTID_LOOKUP_ENDPOINT = "https://api.acoustid.org/v2/lookup"
ACOUSTID_CLIENT_KEY_ENVIRONMENT = "NOQLENMETA_ACOUSTID_API_KEY"
LOOKUP_CONTENT_TYPE = "application/x-www-form-urlencoded"
MAX_LOOKUP_REQUEST_BYTES = 2_097_152
MAX_LOOKUP_RESPONSE_BYTES = 1_048_576
_RESPONSE_READ_BYTES = 65_536
_CACHE_KEY_PREFIX = b"noqlenmeta-acoustid-lookup-cache\x00v1\x00"


class _ReadableResponse(Protocol):
    def read(self, size: int = -1) -> bytes: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class AcoustIDHTTPRequest:
    body: bytes = field(repr=False)
    timeout_seconds: float
    url: str = field(default=ACOUSTID_LOOKUP_ENDPOINT, init=False)
    method: str = field(default="POST", init=False)
    content_type: str = field(default=LOOKUP_CONTENT_TYPE, init=False)


class AcoustIDTransport(Protocol):
    def send(self, request: AcoustIDHTTPRequest) -> _ReadableResponse: ...


class AcoustIDTransportFailure(Exception):
    """Sanitized failure raised by the default HTTPS transport."""


class _UnexpectedBoundaryError(RuntimeError):
    """Sanitized programming or injected-component contract failure."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        unexpected_failure = False
        try:
            fp.close()
        except OSError:
            pass
        except Exception:
            unexpected_failure = True
        if unexpected_failure:
            raise _UnexpectedBoundaryError("AcoustID transport boundary failed")
        raise AcoustIDTransportFailure("AcoustID lookup transport failed")


class UrllibAcoustIDTransport:
    def __init__(self, opener: Callable[..., _ReadableResponse] | None = None) -> None:
        if opener is None:
            context = ssl.create_default_context()
            opener = build_opener(HTTPSHandler(context=context), _RejectRedirects()).open
        self._open = opener

    def send(self, request: AcoustIDHTTPRequest) -> _ReadableResponse:
        if (
            type(request) is not AcoustIDHTTPRequest
            or request.url != ACOUSTID_LOOKUP_ENDPOINT
            or request.method != "POST"
            or request.content_type != LOOKUP_CONTENT_TYPE
            or type(request.body) is not bytes
            or len(request.body) > MAX_LOOKUP_REQUEST_BYTES
        ):
            raise AcoustIDTransportFailure("AcoustID lookup transport failed")
        urllib_request = Request(
            request.url,
            data=request.body,
            headers={"Content-Type": request.content_type},
            method=request.method,
        )
        response: _ReadableResponse | None = None
        operational_failure = False
        unexpected_failure = False
        try:
            response = self._open(urllib_request, timeout=request.timeout_seconds)
        except HTTPError as error:
            try:
                error.close()
            except OSError:
                pass
            except Exception:
                unexpected_failure = True
            operational_failure = True
        except (URLError, TimeoutError, ssl.SSLError, OSError, ValueError):
            operational_failure = True
        if unexpected_failure:
            raise _UnexpectedBoundaryError("AcoustID transport boundary failed")
        if operational_failure:
            raise AcoustIDTransportFailure("AcoustID lookup transport failed")
        if response is None:
            raise _UnexpectedBoundaryError("AcoustID transport boundary failed")
        return response


def _environment_client_key() -> str | None:
    return os.environ.get(ACOUSTID_CLIENT_KEY_ENVIRONMENT)


def _whole_seconds(duration_seconds: float) -> int:
    return max(1, math.floor(duration_seconds + 0.5))


def _cache_key(fingerprint: str, whole_seconds: int) -> str:
    fingerprint_bytes = fingerprint.encode("utf-8")
    duration_bytes = str(whole_seconds).encode("ascii")
    digest = hashlib.sha256()
    digest.update(_CACHE_KEY_PREFIX)
    for value in (fingerprint_bytes, duration_bytes):
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def _request_body(client_key: str, whole_seconds: int, fingerprint: str) -> bytes:
    return urlencode(
        (
            ("client", client_key),
            ("duration", str(whole_seconds)),
            ("fingerprint", fingerprint),
            ("meta", "recordingids"),
            ("format", "json"),
        )
    ).encode("utf-8")


def _read_bounded(response: _ReadableResponse) -> bytes:
    retained = bytearray()
    operational_failure = False
    unexpected_failure = False
    try:
        while True:
            remaining = MAX_LOOKUP_RESPONSE_BYTES - len(retained)
            chunk = response.read(min(_RESPONSE_READ_BYTES, remaining + 1))
            if not isinstance(chunk, bytes):
                raise _UnexpectedBoundaryError("AcoustID response boundary failed")
            if not chunk:
                break
            retained.extend(chunk)
            if len(retained) > MAX_LOOKUP_RESPONSE_BYTES:
                raise AcoustIDTransportFailure("AcoustID lookup transport failed")
    except AcoustIDTransportFailure:
        operational_failure = True
    except _UnexpectedBoundaryError:
        unexpected_failure = True
    except (HTTPException, OSError):
        operational_failure = True
    except Exception:
        unexpected_failure = True
    finally:
        try:
            response.close()
        except (HTTPException, OSError):
            operational_failure = True
        except Exception:
            unexpected_failure = True
    if unexpected_failure:
        raise _UnexpectedBoundaryError("AcoustID response boundary failed")
    if operational_failure:
        raise AcoustIDTransportFailure("AcoustID lookup transport failed")
    return bytes(retained)


def _reject_json_constant(value: str) -> None:
    raise ValueError("non-standard JSON number")


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON member")
        value[key] = item
    return value


def _parse_lookup_response(
    body: bytes, settings: AcoustIDSettings
) -> tuple[AcoustIDResultGroup, ...]:
    document = json.loads(
        body.decode("utf-8"),
        parse_constant=_reject_json_constant,
        object_pairs_hook=_strict_json_object,
    )
    if type(document) is not dict or document.get("status") != "ok":
        raise ValueError("invalid AcoustID service response")
    results = document.get("results", [])
    if type(results) is not list:
        raise ValueError("invalid AcoustID result schema")

    groups: list[AcoustIDResultGroup] = []
    for result in results[: settings.max_results]:
        if type(result) is not dict or type(result.get("recordings")) is not list:
            raise ValueError("invalid AcoustID result schema")
        acoustid_id = result.get("id")
        score = result.get("score")
        if not isinstance(acoustid_id, str) or isinstance(score, bool) or not isinstance(
            score, (int, float)
        ):
            raise ValueError("invalid AcoustID result schema")
        recording_mbids: list[str] = []
        for recording in result["recordings"][: settings.max_recordings_per_result]:
            if type(recording) is not dict or "id" not in recording:
                raise ValueError("invalid AcoustID result schema")
            recording_mbid = recording["id"]
            if not isinstance(recording_mbid, str):
                raise ValueError("invalid AcoustID result schema")
            recording_mbids.append(recording_mbid)
        groups.append(AcoustIDResultGroup(acoustid_id, score, tuple(recording_mbids)))
    unique_groups: dict[str, AcoustIDResultGroup] = {}
    for group in groups:
        existing = unique_groups.get(group.acoustid_id)
        if existing is not None and existing != group:
            raise ValueError("conflicting duplicate AcoustID result groups")
        unique_groups[group.acoustid_id] = group
    return tuple(groups)


def _unavailable_evidence(
    material: AcoustIDFingerprintMaterial, reason: AcoustIDEvidenceReason
) -> AcoustIDTrackEvidence:
    return AcoustIDTrackEvidence(
        local_key=material.local_key,
        fingerprint_origin=material.origin,
        result_groups=(),
        verdict=AcoustIDEvidenceVerdict.UNAVAILABLE,
        selected_acoustid_id=None,
        selected_recording_mbid=None,
        reason=reason,
        top_score=None,
        runner_up_score=None,
        margin=None,
        eligible_result_count=0,
        eligible_recording_count=0,
    )


def _classify_lookup(
    material: AcoustIDFingerprintMaterial,
    groups: tuple[AcoustIDResultGroup, ...],
    policy: AcoustIDEvidencePolicy,
) -> AcoustIDTrackEvidence:
    unexpected_failure = False
    evidence: AcoustIDTrackEvidence | None = None
    try:
        evidence = classify_acoustid_evidence(
            material.local_key, material.origin, groups, policy
        )
    except Exception:
        unexpected_failure = True
    if unexpected_failure or evidence is None:
        raise _UnexpectedBoundaryError("AcoustID evidence boundary failed")
    return evidence


class AcoustIDLookupService:
    def __init__(
        self,
        settings: AcoustIDSettings,
        *,
        transport: AcoustIDTransport | None = None,
        credential_resolver: Callable[[], str | None] = _environment_client_key,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not isinstance(settings, AcoustIDSettings):
            raise ValueError("settings must be AcoustIDSettings")
        self._settings = settings
        self._policy = AcoustIDEvidencePolicy(
            settings.min_score,
            settings.min_margin,
            settings.max_results,
            settings.max_recordings_per_result,
        )
        self._transport = transport
        self._credential_resolver = credential_resolver
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._last_request_start: float | None = None
        self._cache: OrderedDict[str, tuple[AcoustIDResultGroup, ...]] = OrderedDict()

    def lookup(self, material: AcoustIDFingerprintMaterial) -> AcoustIDTrackEvidence:
        if not isinstance(material, AcoustIDFingerprintMaterial):
            raise ValueError("material must be AcoustIDFingerprintMaterial")
        if not self._settings.lookup:
            return _unavailable_evidence(material, AcoustIDEvidenceReason.LOOKUP_DISABLED)

        fingerprint = material._fingerprint_text()
        whole_seconds = _whole_seconds(material.duration_seconds)
        try:
            digest = _cache_key(fingerprint, whole_seconds)
        except UnicodeEncodeError:
            return _unavailable_evidence(material, AcoustIDEvidenceReason.LOOKUP_FAILED)
        cached = self._cache.get(digest)
        if cached is not None:
            return _classify_lookup(material, cached, self._policy)

        client_key = self._resolve_client_key()
        if not isinstance(client_key, str) or not client_key:
            return _unavailable_evidence(material, AcoustIDEvidenceReason.CLIENT_KEY_MISSING)

        try:
            body = _request_body(client_key, whole_seconds, fingerprint)
        except UnicodeEncodeError:
            return _unavailable_evidence(material, AcoustIDEvidenceReason.LOOKUP_FAILED)
        if len(body) > MAX_LOOKUP_REQUEST_BYTES:
            return _unavailable_evidence(material, AcoustIDEvidenceReason.LOOKUP_FAILED)
        request = AcoustIDHTTPRequest(body, self._settings.timeout_seconds)

        try:
            self._pace()
            response = self._send(request)
            response_body = _read_bounded(response)
        except AcoustIDTransportFailure:
            return _unavailable_evidence(material, AcoustIDEvidenceReason.LOOKUP_FAILED)
        try:
            groups = _parse_lookup_response(response_body, self._settings)
        except (ValueError, OverflowError, RecursionError):
            return _unavailable_evidence(material, AcoustIDEvidenceReason.LOOKUP_FAILED)
        evidence = _classify_lookup(material, groups, self._policy)

        if self._settings.cache_entries:
            self._cache[digest] = groups
            while len(self._cache) > self._settings.cache_entries:
                self._cache.popitem(last=False)
        return evidence

    def _resolve_client_key(self) -> str | None:
        unexpected_failure = False
        client_key: str | None = None
        try:
            client_key = self._credential_resolver()
        except Exception:
            unexpected_failure = True
        if unexpected_failure:
            raise _UnexpectedBoundaryError("AcoustID credential boundary failed")
        return client_key

    def _send(self, request: AcoustIDHTTPRequest) -> _ReadableResponse:
        transport = self._transport
        if transport is None:
            operational_failure = False
            unexpected_failure = False
            try:
                transport = UrllibAcoustIDTransport()
            except OSError:
                operational_failure = True
            except Exception:
                unexpected_failure = True
            if unexpected_failure:
                raise _UnexpectedBoundaryError("AcoustID transport boundary failed")
            if operational_failure:
                raise AcoustIDTransportFailure("AcoustID lookup transport failed")
            if transport is None:
                raise _UnexpectedBoundaryError("AcoustID transport boundary failed")
            self._transport = transport
        operational_failure = False
        unexpected_failure = False
        response: _ReadableResponse | None = None
        try:
            response = transport.send(request)
        except (AcoustIDTransportFailure, OSError):
            operational_failure = True
        except Exception:
            unexpected_failure = True
        if unexpected_failure:
            raise _UnexpectedBoundaryError("AcoustID transport boundary failed")
        if operational_failure:
            raise AcoustIDTransportFailure("AcoustID lookup transport failed")
        if response is None:
            raise _UnexpectedBoundaryError("AcoustID transport boundary failed")
        return response

    def _pace(self) -> None:
        now = self._monotonic_time()
        if not isinstance(now, (int, float)) or isinstance(now, bool) or not math.isfinite(now):
            raise AcoustIDTransportFailure("AcoustID lookup transport failed")
        now = float(now)
        previous = self._last_request_start
        if previous is not None:
            if now < previous:
                raise AcoustIDTransportFailure("AcoustID lookup transport failed")
            remaining = 1.0 / self._settings.requests_per_second - (now - previous)
            if remaining > 0:
                self._sleep(remaining)
                started = self._monotonic_time()
                if (
                    not isinstance(started, (int, float))
                    or isinstance(started, bool)
                    or not math.isfinite(started)
                    or started <= now
                    or started < previous
                    or started - previous < 1.0 / self._settings.requests_per_second
                ):
                    raise AcoustIDTransportFailure("AcoustID lookup transport failed")
                now = float(started)
        self._last_request_start = now

    def _monotonic_time(self) -> float:
        operational_failure = False
        unexpected_failure = False
        value = 0.0
        try:
            value = self._monotonic()
        except OSError:
            operational_failure = True
        except Exception:
            unexpected_failure = True
        if unexpected_failure:
            raise _UnexpectedBoundaryError("AcoustID pacing boundary failed")
        if operational_failure:
            raise AcoustIDTransportFailure("AcoustID lookup transport failed")
        return value

    def _sleep(self, seconds: float) -> None:
        operational_failure = False
        unexpected_failure = False
        try:
            self._sleeper(seconds)
        except OSError:
            operational_failure = True
        except Exception:
            unexpected_failure = True
        if unexpected_failure:
            raise _UnexpectedBoundaryError("AcoustID pacing boundary failed")
        if operational_failure:
            raise AcoustIDTransportFailure("AcoustID lookup transport failed")
