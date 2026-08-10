"""Conservative album genre enrichment from Last.fm community tags."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from http.client import HTTPException
from json import JSONDecodeError
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import beets.plugins

from beetsplug.noqlenmeta.domain import (
    ArtistEnrichmentContext,
    MetadataCandidate,
    ReleaseEnrichmentContext,
    SemanticCategory,
    SemanticEvidenceBundle,
    TrackEnrichmentContext,
    canonical_uuid,
)
from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
    GenreTaxonomy,
)
from beetsplug.noqlenmeta.providers.base import ProviderError
from beetsplug.noqlenmeta.providers.specs import (
    LASTFM_ARTIST_SPEC,
    LASTFM_SPEC,
    LASTFM_TRACK_SPEC,
    ProviderScope,
)
from beetsplug.noqlenmeta.semantic_tags import classify_semantic_tag

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
        return self._fetch_top_tags(
            {
                "method": "album.getTopTags",
                "artist": artist,
                "album": album,
            }
        )

    def fetch_track_top_tags(
        self, artist: str, track: str, mbid: str | None
    ) -> Mapping[str, object]:
        identity = {"mbid": mbid} if mbid else {"artist": artist, "track": track}
        return self._fetch_top_tags({"method": "track.getTopTags", **identity})

    def fetch_artist_top_tags(
        self, artist: str, mbid: str | None
    ) -> Mapping[str, object]:
        identity = {"mbid": mbid} if mbid else {"artist": artist}
        return self._fetch_top_tags({"method": "artist.getTopTags", **identity})

    def _fetch_top_tags(self, identity: Mapping[str, str]) -> Mapping[str, object]:
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
            **identity,
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
        taxonomy: GenreTaxonomy = DEFAULT_GENRE_TAXONOMY,
        transport: _LastFmTransport | None = None,
    ) -> None:
        if fetch_top_tags is not None and transport is not None:
            raise TypeError("provide fetch_top_tags or transport, not both")
        self._fetch_top_tags = fetch_top_tags or (
            transport or _LastFmTransport()
        ).fetch_top_tags
        if not isinstance(taxonomy, GenreTaxonomy):
            raise TypeError("taxonomy must be a GenreTaxonomy")
        self._taxonomy = taxonomy
        self._cache: dict[tuple[str, str], tuple[MetadataCandidate, ...]] = {}
        self._payload_cache: dict[tuple[str, str], Mapping[str, object]] = {}

    def get_candidates(
        self, context: ReleaseEnrichmentContext
    ) -> Sequence[MetadataCandidate]:
        artist = _clean_identity(context.album_artist)
        album = _clean_identity(context.album_title)
        cache_key = (_comparison_identity(artist), _comparison_identity(album))
        if cache_key in self._cache:
            return self._cache[cache_key]

        payload = self._payload(artist, album)
        candidates = self._normalize_payload(payload, artist, album)
        self._cache[cache_key] = candidates
        return candidates

    def get_semantic_evidence(
        self, context: ReleaseEnrichmentContext
    ) -> SemanticEvidenceBundle:
        artist = _clean_identity(context.album_artist)
        album = _clean_identity(context.album_title)
        payload = self._payload(artist, album)
        source_id = f"{artist} / {album}"
        source_url = f"{_PUBLIC_ALBUM_URL}/{quote(artist, safe='')}/{quote(album, safe='')}"
        return _semantic_bundle(
            payload,
            expected={"artist": artist, "album": album},
            scope=ProviderScope.RELEASE,
            source_id=source_id,
            source_url=source_url,
        )

    def _payload(self, artist: str, album: str) -> Mapping[str, object]:
        key = (_comparison_identity(artist), _comparison_identity(album))
        if key not in self._payload_cache:
            self._payload_cache[key] = self._fetch_top_tags(artist, album)
        return self._payload_cache[key]

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

        accepted: list[str] = []
        seen: set[str] = set()
        for entry in tags:
            if not isinstance(entry, Mapping):
                continue
            name = _optional_tag_name(entry.get("name"))
            weight = _tag_weight(entry.get("count"))
            classification = self._taxonomy.classify(name) if name else None
            folded = classification.canonical_name.casefold() if classification else ""
            if (
                not name
                or weight is None
                or weight < _MIN_TAG_WEIGHT
                or classification is None
                or classification.category is not GenreSemanticCategory.GENRE
                or folded in seen
            ):
                continue
            seen.add(folded)
            accepted.append(classification.canonical_name)
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


class LastFmTrackProvider:
    name = LASTFM_TRACK_SPEC.name
    supported_fields = LASTFM_TRACK_SPEC.supported_fields

    def __init__(
        self,
        *,
        fetch_top_tags: Callable[[str, str, str | None], Mapping[str, object]] | None = None,
        transport: _LastFmTransport | None = None,
    ) -> None:
        if fetch_top_tags is not None and transport is not None:
            raise TypeError("provide fetch_top_tags or transport, not both")
        self._fetch_top_tags = fetch_top_tags or (
            transport or _LastFmTransport()
        ).fetch_track_top_tags
        self._cache: dict[tuple[str, str, str | None], SemanticEvidenceBundle] = {}

    def get_semantic_evidence(
        self, context: TrackEnrichmentContext
    ) -> SemanticEvidenceBundle:
        artist = _clean_identity(context.artist)
        title = _clean_identity(context.title)
        mbid = _external_mbid(context.external_ids, "musicbrainz.recording")
        key = (_comparison_identity(artist), _comparison_identity(title), mbid)
        if key in self._cache:
            return self._cache[key]
        payload = self._fetch_top_tags(artist, title, mbid)
        source_id = f"{artist} / {title}"
        source_url = f"{_PUBLIC_ALBUM_URL}/{quote(artist, safe='')}/_/{quote(title, safe='')}"
        bundle = _semantic_bundle(
            payload,
            expected={"artist": artist, "track": title},
            scope=ProviderScope.TRACK,
            source_id=source_id,
            source_url=source_url,
        )
        self._cache[key] = bundle
        return bundle


class LastFmArtistProvider:
    name = LASTFM_ARTIST_SPEC.name
    supported_fields = LASTFM_ARTIST_SPEC.supported_fields

    def __init__(
        self,
        *,
        fetch_top_tags: Callable[[str, str | None], Mapping[str, object]] | None = None,
        transport: _LastFmTransport | None = None,
    ) -> None:
        if fetch_top_tags is not None and transport is not None:
            raise TypeError("provide fetch_top_tags or transport, not both")
        self._fetch_top_tags = fetch_top_tags or (
            transport or _LastFmTransport()
        ).fetch_artist_top_tags
        self._cache: dict[tuple[str, str | None], SemanticEvidenceBundle] = {}

    def get_semantic_evidence(
        self, context: ArtistEnrichmentContext
    ) -> SemanticEvidenceBundle:
        artist = _clean_identity(context.name)
        mbid = _external_mbid(context.external_ids, "musicbrainz.artist")
        key = (_comparison_identity(artist), mbid)
        if key in self._cache:
            return self._cache[key]
        payload = self._fetch_top_tags(artist, mbid)
        bundle = _semantic_bundle(
            payload,
            expected={"artist": artist},
            scope=ProviderScope.ARTIST,
            source_id=artist,
            source_url=f"{_PUBLIC_ALBUM_URL}/{quote(artist, safe='')}",
        )
        self._cache[key] = bundle
        return bundle


def _semantic_bundle(
    payload: object,
    *,
    expected: Mapping[str, str],
    scope: ProviderScope,
    source_id: str,
    source_url: str,
) -> SemanticEvidenceBundle:
    if not isinstance(payload, Mapping):
        raise ProviderError("Last.fm API response is invalid")
    if "error" in payload:
        if _error_code(payload.get("error")) in _NO_RESOURCE_ERROR_CODES:
            return SemanticEvidenceBundle()
        raise ProviderError("Last.fm service request failed")
    toptags = payload.get("toptags")
    if not isinstance(toptags, Mapping):
        raise ProviderError("Last.fm API response is invalid")
    attributes = toptags.get("@attr")
    if not isinstance(attributes, Mapping):
        raise ProviderError("Last.fm API response is invalid")
    for field, expected_value in expected.items():
        actual = _optional_identity(attributes.get(field))
        if not actual or _comparison_identity(actual) != _comparison_identity(expected_value):
            raise ProviderError(f"Last.fm {scope.value} identity does not match selected target")
    rows = toptags.get("tag")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ProviderError("Last.fm API response is invalid")

    genres: list[GenreEvidence] = []
    tags = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        name = _optional_tag_name(row.get("name"))
        weight = _tag_weight(row.get("count"))
        if not name or weight is None or weight < _MIN_TAG_WEIGHT:
            continue
        evidence = classify_semantic_tag(
            name,
            "lastfm",
            scope,
            _COMMUNITY_CONFIDENCE,
            source_id,
            source_url,
            weight,
        )
        if evidence is None:
            continue
        if evidence.category is SemanticCategory.GENRE:
            genres.append(
                GenreEvidence(
                    evidence.canonical_term,
                    evidence.provider,
                    evidence.scope,
                    GenreEvidenceKind.COMMUNITY_TAG,
                    evidence.confidence,
                    evidence.source_id,
                    evidence.source_url,
                    weight,
                )
            )
        elif evidence.category in {SemanticCategory.STYLE, SemanticCategory.MOOD}:
            tags.append(evidence)
    return SemanticEvidenceBundle(genres=tuple(genres), tags=tuple(tags))


def _external_mbid(identifiers: Sequence[object], namespace: str) -> str | None:
    values = {
        value
        for identifier in identifiers
        if getattr(identifier, "namespace", None) == namespace
        and (value := canonical_uuid(getattr(identifier, "value", None))) is not None
    }
    return values.pop() if len(values) == 1 else None


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
