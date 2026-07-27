"""Conservative album genre enrichment from Last.fm community tags."""

from __future__ import annotations

import importlib.util
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from functools import cache
from http.client import HTTPException
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import beets.plugins

from beetsplug.noqlenmeta.domain import MetadataCandidate, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.providers.base import ProviderError
from beetsplug.noqlenmeta.providers.specs import LASTFM_SPEC

_API_URL = "https://ws.audioscrobbler.com/2.0/"
_PUBLIC_ALBUM_URL = "https://www.last.fm/music"
_MIN_TAG_WEIGHT = 10
_MAX_GENRES = 3
_COMMUNITY_CONFIDENCE = 0.85
_TIMEOUT_SECONDS = 10.0
_MAX_RESPONSE_BYTES = 1_000_000
_MIN_REQUEST_INTERVAL_SECONDS = 1.0
_USER_AGENT = "NoqlenMeta/0.0.0"
_NO_RESOURCE_ERROR_CODES = frozenset({6, 7})
_ORDINARY_WHITESPACE = re.compile(r"[\t\n\r\f\v ]+")
_EXTERNAL_ERRORS = (
    OSError,
    HTTPException,
    JSONDecodeError,
    UnicodeDecodeError,
    KeyError,
)


@cache
def load_beets_genre_vocabulary() -> frozenset[str]:
    """Load beets' packaged LastGenre vocabulary without importing LastGenre."""
    try:
        spec = importlib.util.find_spec("beetsplug.lastgenre")
    except (ImportError, AttributeError, ValueError):
        spec = None
    locations = tuple(spec.submodule_search_locations or ()) if spec is not None else ()
    if not locations:
        raise ProviderError("beets LastGenre genre vocabulary is unavailable")

    resource = Path(locations[0]) / "genres.txt"
    try:
        lines = resource.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise ProviderError("beets LastGenre genre vocabulary is unavailable") from None

    genres = frozenset(
        line.casefold()
        for raw_line in lines
        if (line := raw_line.strip()) and not line.startswith("#")
    )
    if not genres:
        raise ProviderError("beets LastGenre genre vocabulary is unavailable")
    return genres


class _LastFmTransport:
    """Bounded, paced transport for Last.fm album top tags."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        request_json: Callable[[str], Mapping[str, object]] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = beets.plugins.LASTFM_KEY if api_key is None else api_key
        self._request_json = request_json or _request_json
        self._monotonic = monotonic
        self._sleep = sleep
        self._last_request_started: float | None = None

    def fetch_top_tags(self, artist: str, album: str) -> Mapping[str, object]:
        now = self._monotonic()
        if self._last_request_started is not None:
            remaining = _MIN_REQUEST_INTERVAL_SECONDS - (
                now - self._last_request_started
            )
            if remaining > 0:
                self._sleep(remaining)
                now = self._monotonic()
        self._last_request_started = now

        parameters = {
            "method": "album.getTopTags",
            "artist": artist,
            "album": album,
            "api_key": self._api_key,
            "format": "json",
            "autocorrect": "0",
        }
        url = f"{_API_URL}?{urlencode(parameters)}"
        try:
            return self._request_json(url)
        except _EXTERNAL_ERRORS:
            raise ProviderError("Last.fm API request failed") from None


class LastFmProvider:
    """Emit only vocabulary-validated genres for the selected album identity."""

    name = LASTFM_SPEC.name
    supported_fields = LASTFM_SPEC.supported_fields

    def __init__(
        self,
        *,
        fetch_top_tags: Callable[[str, str], Mapping[str, object]] | None = None,
        genre_vocabulary: frozenset[str] | None = None,
        transport: _LastFmTransport | None = None,
    ) -> None:
        if fetch_top_tags is not None and transport is not None:
            raise TypeError("provide fetch_top_tags or transport, not both")
        self._fetch_top_tags = fetch_top_tags or (
            transport or _LastFmTransport()
        ).fetch_top_tags
        self._genre_vocabulary = genre_vocabulary
        self._cache: dict[tuple[str, str], tuple[MetadataCandidate, ...]] = {}

    def get_candidates(
        self, context: ReleaseEnrichmentContext
    ) -> Sequence[MetadataCandidate]:
        artist = _clean_identity(context.album_artist)
        album = _clean_identity(context.album_title)
        cache_key = (_comparison_identity(artist), _comparison_identity(album))
        if cache_key in self._cache:
            return self._cache[cache_key]

        payload = self._fetch_top_tags(artist, album)
        candidates = self._normalize_payload(payload, artist, album)
        self._cache[cache_key] = candidates
        return candidates

    def _normalize_payload(
        self, payload: object, requested_artist: str, requested_album: str
    ) -> tuple[MetadataCandidate, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderError("Last.fm API response is invalid")

        if "error" in payload:
            error_code = _error_code(payload.get("error"))
            if error_code in _NO_RESOURCE_ERROR_CODES:
                return ()
            raise ProviderError("Last.fm service request failed")

        toptags = payload.get("toptags")
        if not isinstance(toptags, Mapping):
            raise ProviderError("Last.fm API response is invalid")
        attributes = toptags.get("@attr")
        if not isinstance(attributes, Mapping):
            raise ProviderError("Last.fm API response is invalid")
        response_artist = _optional_identity(attributes.get("artist"))
        response_album = _optional_identity(attributes.get("album"))
        if not response_artist or not response_album:
            raise ProviderError("Last.fm API response is invalid")
        if (
            _comparison_identity(response_artist)
            != _comparison_identity(requested_artist)
            or _comparison_identity(response_album)
            != _comparison_identity(requested_album)
        ):
            raise ProviderError("Last.fm album identity does not match selected release")

        tags = toptags.get("tag")
        if not isinstance(tags, Sequence) or isinstance(tags, (str, bytes)):
            raise ProviderError("Last.fm API response is invalid")

        vocabulary = self._genre_vocabulary
        if vocabulary is None:
            vocabulary = load_beets_genre_vocabulary()
        accepted: list[str] = []
        seen: set[str] = set()
        for entry in tags:
            if not isinstance(entry, Mapping):
                continue
            name = _optional_tag_name(entry.get("name"))
            weight = _tag_weight(entry.get("count"))
            folded = name.casefold()
            if (
                not name
                or weight is None
                or weight < _MIN_TAG_WEIGHT
                or folded not in vocabulary
                or folded in seen
            ):
                continue
            seen.add(folded)
            accepted.append(name)
            if len(accepted) == _MAX_GENRES:
                break

        if not accepted:
            return ()
        source_id = f"{response_artist} / {response_album}"
        source_url = (
            f"{_PUBLIC_ALBUM_URL}/{quote(response_artist, safe='')}/"
            f"{quote(response_album, safe='')}"
        )
        return (
            MetadataCandidate(
                field="genres",
                value=tuple(accepted),
                provider=self.name,
                confidence=_COMMUNITY_CONFIDENCE,
                source_id=source_id,
                source_url=source_url,
            ),
        )


def _request_json(url: str) -> Mapping[str, object]:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        body = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(body) > _MAX_RESPONSE_BYTES:
        raise HTTPException("Last.fm response exceeded the size limit")
    try:
        payload: Any = json.loads(body.decode("utf-8"))
    except ValueError:
        raise HTTPException("Last.fm response was not valid JSON") from None
    if not isinstance(payload, Mapping):
        raise KeyError("response")
    return payload


def _clean_identity(value: str) -> str:
    return _ORDINARY_WHITESPACE.sub(" ", value.strip())


def _optional_identity(value: object) -> str:
    return _clean_identity(value) if isinstance(value, str) else ""


def _comparison_identity(value: str) -> str:
    return _clean_identity(value).casefold()


def _optional_tag_name(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _tag_weight(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        try:
            parsed = int(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if 0 <= parsed <= 100 else None


def _error_code(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        try:
            return int(value)
        except ValueError:
            return None
    return None
