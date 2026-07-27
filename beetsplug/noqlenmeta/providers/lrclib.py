"""Exact-signature track lyrics enrichment from LRCLIB."""

from __future__ import annotations

import importlib.metadata
import json
import math
import re
import time
from collections.abc import Callable, Mapping, Sequence
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from beetsplug.noqlenmeta.domain import MetadataCandidate, TrackEnrichmentContext
from beetsplug.noqlenmeta.providers.base import ProviderError
from beetsplug.noqlenmeta.providers.specs import LRCLIB_SPEC

_API_URL = "https://lrclib.net/api/get"
_PUBLIC_RECORD_URL = "https://lrclib.net/api/get"
_PROJECT_URL = "https://pypi.org/project/beets-noqlenmeta/"
_TIMEOUT_SECONDS = 10.0
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MIN_REQUEST_INTERVAL_SECONDS = 0.3
_CONFIDENCE = 0.95
_ORDINARY_WHITESPACE = re.compile(r"[\t\n\r\f\v ]+")
_REQUEST_FAILED = "LRCLIB API request failed"
_INVALID_RESPONSE = "LRCLIB API response is invalid"
_IDENTITY_MISMATCH = "LRCLIB track identity does not match selected track"
_DURATION_MISMATCH = "LRCLIB track duration does not match selected track"
_RATE_LIMITED = "LRCLIB API rate limit exceeded"
_INVALID_RATE_LIMIT = "LRCLIB API rate limit response is invalid"
_OVERSIZED_RESPONSE = "LRCLIB API response exceeded the size limit"


def _user_agent() -> str:
    try:
        version = importlib.metadata.version("beets-noqlenmeta")
    except importlib.metadata.PackageNotFoundError:
        version = "0+unknown"
    if not version.strip():
        version = "0+unknown"
    return f"beets-noqlenmeta/{version} ({_PROJECT_URL})"


class _LRCLIBTransport:
    """Bounded, sequential, paced transport for LRCLIB exact lookups."""

    def __init__(
        self,
        *,
        opener: Callable[..., object] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._opener = opener or urlopen
        self._monotonic = monotonic
        self._sleep = sleep
        self._last_request_started: float | None = None
        self._next_allowed_request = 0.0

    def fetch_record(
        self,
        artist: str,
        title: str,
        album_title: str,
        duration: float,
    ) -> Mapping[str, object] | None:
        self._pace_request()
        parameters = {
            "track_name": title,
            "artist_name": artist,
            "album_name": album_title,
            "duration": duration,
        }
        request = Request(
            f"{_API_URL}?{urlencode(parameters)}",
            headers={"User-Agent": _user_agent()},
        )
        self._last_request_started = self._monotonic()

        try:
            response = self._opener(request, timeout=_TIMEOUT_SECONDS)
            with response:  # type: ignore[attr-defined]
                body = response.read(_MAX_RESPONSE_BYTES + 1)  # type: ignore[attr-defined]
        except HTTPError as error:
            if error.code == 404:
                return None
            if error.code == 429:
                self._handle_rate_limit(error)
            raise ProviderError(_REQUEST_FAILED) from None
        except (URLError, TimeoutError, OSError, HTTPException):
            raise ProviderError(_REQUEST_FAILED) from None

        if not isinstance(body, bytes):
            raise ProviderError(_INVALID_RESPONSE)
        if len(body) > _MAX_RESPONSE_BYTES:
            raise ProviderError(_OVERSIZED_RESPONSE)
        try:
            payload: Any = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderError(_INVALID_RESPONSE) from None
        if not isinstance(payload, Mapping):
            raise ProviderError(_INVALID_RESPONSE)
        return payload

    def _pace_request(self) -> None:
        now = self._monotonic()
        minimum = self._next_allowed_request
        if self._last_request_started is not None:
            minimum = max(
                minimum,
                self._last_request_started + _MIN_REQUEST_INTERVAL_SECONDS,
            )
        remaining = minimum - now
        if remaining > 0:
            self._sleep(remaining)

    def _handle_rate_limit(self, error: HTTPError) -> None:
        raw_retry_after = error.headers.get("Retry-After") if error.headers else None
        try:
            retry_after = float(raw_retry_after) if raw_retry_after is not None else math.nan
        except (TypeError, ValueError):
            retry_after = math.nan
        if not math.isfinite(retry_after) or retry_after < 0:
            raise ProviderError(_INVALID_RATE_LIMIT) from None
        self._next_allowed_request = max(
            self._next_allowed_request,
            self._monotonic() + retry_after,
        )
        raise ProviderError(_RATE_LIMITED) from None


class LRCLIBProvider:
    """Emit independent lyrics candidates for one selected exact track signature."""

    name = LRCLIB_SPEC.name
    supported_fields = LRCLIB_SPEC.supported_fields

    def __init__(
        self,
        *,
        fetch_record: Callable[
            [str, str, str, float], Mapping[str, object] | None
        ]
        | None = None,
        transport: _LRCLIBTransport | None = None,
    ) -> None:
        if fetch_record is not None and transport is not None:
            raise TypeError("provide fetch_record or transport, not both")
        self._fetch_record = fetch_record or (transport or _LRCLIBTransport()).fetch_record
        self._cache: dict[
            tuple[str, str, str, float], tuple[MetadataCandidate, ...]
        ] = {}

    def get_candidates(
        self,
        context: TrackEnrichmentContext,
    ) -> Sequence[MetadataCandidate]:
        album_title = context.album_title
        duration = context.duration
        if album_title is None or duration is None:
            return ()
        cache_key = (
            context.artist,
            context.title,
            album_title,
            duration,
        )
        if cache_key in self._cache:
            return self._cache[cache_key]

        payload = self._fetch_record(
            context.artist,
            context.title,
            album_title,
            duration,
        )
        if payload is None:
            self._cache[cache_key] = ()
            return ()
        candidates = self._normalize_payload(payload, context)
        self._cache[cache_key] = candidates
        return candidates

    def _normalize_payload(
        self,
        payload: object,
        context: TrackEnrichmentContext,
    ) -> tuple[MetadataCandidate, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderError(_INVALID_RESPONSE)

        album_title = context.album_title
        requested_duration = context.duration
        if album_title is None or requested_duration is None:
            raise TypeError("LRCLIB normalization requires an exact track signature")

        record_id = payload.get("id")
        if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id <= 0:
            raise ProviderError(_INVALID_RESPONSE)

        for response_field, requested_value in (
            ("trackName", context.title),
            ("artistName", context.artist),
            ("albumName", album_title),
        ):
            response_value = payload.get(response_field)
            if not isinstance(response_value, str) or not response_value.strip():
                raise ProviderError(_INVALID_RESPONSE)
            if _comparison_text(response_value) != _comparison_text(requested_value):
                raise ProviderError(_IDENTITY_MISMATCH)

        response_duration = payload.get("duration")
        if (
            isinstance(response_duration, bool)
            or not isinstance(response_duration, (int, float))
            or not math.isfinite(response_duration)
            or response_duration <= 0
        ):
            raise ProviderError(_INVALID_RESPONSE)
        if abs(float(response_duration) - requested_duration) > 2.0:
            raise ProviderError(_DURATION_MISMATCH)

        instrumental = payload.get("instrumental")
        if not isinstance(instrumental, bool):
            raise ProviderError(_INVALID_RESPONSE)
        if instrumental:
            return ()

        lyrics = _lyrics_value(payload.get("plainLyrics"))
        synced_lyrics = _lyrics_value(payload.get("syncedLyrics"))
        source_id = str(record_id)
        source_url = f"{_PUBLIC_RECORD_URL}/{record_id}"
        candidates: list[MetadataCandidate] = []
        for field, value in (
            ("lyrics", lyrics),
            ("synced_lyrics", synced_lyrics),
        ):
            if value is not None:
                candidates.append(
                    MetadataCandidate(
                        field=field,
                        value=value,
                        provider=self.name,
                        confidence=_CONFIDENCE,
                        source_id=source_id,
                        source_url=source_url,
                    )
                )
        return tuple(candidates)


def _comparison_text(value: str) -> str:
    return _ORDINARY_WHITESPACE.sub(" ", value.strip()).casefold()


def _lyrics_value(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderError(_INVALID_RESPONSE)
    return value if value.strip() else None
