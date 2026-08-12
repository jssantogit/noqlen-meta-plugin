"""Conservative album-level enrichment from concrete Discogs releases."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Collection, Mapping, Sequence
from http.client import HTTPException
from json import JSONDecodeError
from typing import Any, Protocol

import discogs_client
from discogs_client.exceptions import DiscogsAPIError
from requests.exceptions import RequestException

from beetsplug.noqlenmeta.domain import (
    ExternalIdentifier,
    MetadataCandidate,
    ReleaseEnrichmentContext,
)
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind
from beetsplug.noqlenmeta.providers.base import ProviderError
from beetsplug.noqlenmeta.providers.specs import DISCOGS_SPEC, ProviderScope
from beetsplug.noqlenmeta.release_catalog import normalize_edition, parse_partial_date

_DISCOGS_RELEASE_NAMESPACE = "discogs.release"
_SEARCH_LIMIT = 10
_USER_AGENT = "NoqlenMeta/0.0.0"

# Provider-local confidence describes release identification, not field authority.
_DIRECT_CONFIDENCE = 0.98
_STRONG_SEARCH_CONFIDENCE = 0.92
_WEAK_SEARCH_CONFIDENCE = 0.82

_EXTERNAL_ERRORS = (
    DiscogsAPIError,
    RequestException,
    HTTPException,
    JSONDecodeError,
    UnicodeDecodeError,
    KeyError,
)


class _SearchResults(Protocol):
    per_page: int

    def page(self, index: int) -> Sequence[Any]: ...


class _DiscogsClient(Protocol):
    def release(self, release_id: int) -> Any: ...

    def search(self, **fields: object) -> _SearchResults: ...

    def set_timeout(self, connect: float, read: float) -> None: ...


class DiscogsProvider:
    """Resolve one Discogs edition and emit normalized field candidates."""

    name = DISCOGS_SPEC.name
    supported_fields = DISCOGS_SPEC.supported_fields

    def __init__(
        self,
        token: str | None = None,
        *,
        client: _DiscogsClient | None = None,
    ) -> None:
        self._token = token.strip() if token and token.strip() else None
        self._client = client or discogs_client.Client(
            _USER_AGENT,
            user_token=self._token,
        )
        self._client.set_timeout(connect=5, read=10)

    def get_candidates(self, context: ReleaseEnrichmentContext) -> Sequence[MetadataCandidate]:
        resolved = self._resolve_release(context)
        if resolved is None:
            return ()
        release, release_id, confidence = resolved
        return _normalize_release(release, release_id, confidence)

    def get_release_catalog_evidence(
        self,
        context: ReleaseEnrichmentContext,
        enabled_fields: Collection[str],
    ) -> tuple[MetadataEvidence, ...]:
        requested = set(enabled_fields) & {"date", "edition"}
        if not requested:
            return ()
        resolved = self._resolve_release(context)
        if resolved is None:
            return ()
        release, release_id, confidence = resolved
        if _positive_int(release.get("id")) != release_id:
            return ()
        fields: list[tuple[str, object]] = []
        if "date" in requested and (date := parse_partial_date(release.get("released"))):
            fields.append(("date", date))
        if "edition" in requested:
            fields.extend(("edition", value) for value in _editions(release.get("formats")))
        source_url = _optional_string(release.get("uri")) or None
        return tuple(
            MetadataEvidence(
                field=field,
                value=value,  # type: ignore[arg-type]
                subject=SubjectRef(
                    EntityKind.RELEASE,
                    (ExternalIdentifier("discogs.release", str(release_id)),),
                ),
                provider="discogs",
                acquisition_scope=ProviderScope.RELEASE,
                source_id=str(release_id),
                source_url=source_url,
                provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
                confidence=confidence,
            )
            for field, value in fields
        )

    def _resolve_release(
        self, context: ReleaseEnrichmentContext
    ) -> tuple[Mapping[str, object], int, float] | None:
        direct_id, has_discogs_ids = _discogs_release_id(context)
        if has_discogs_ids:
            if direct_id is None:
                return None
            release = self._fetch_release(direct_id)
            return release, direct_id, _DIRECT_CONFIDENCE

        if self._token is None:
            raise ProviderError("Discogs search requires a personal user token")

        selected = self._search_release(context)
        if selected is None:
            return None

        release_id, confidence = selected
        release = self._fetch_release(release_id)
        return release, release_id, confidence

    def _fetch_release(self, release_id: int) -> Mapping[str, object]:
        try:
            release = self._client.release(release_id)
            release.refresh()
            data = release.data
        except _EXTERNAL_ERRORS:
            raise ProviderError("Discogs release lookup failed") from None

        return data if isinstance(data, Mapping) else {}

    def _search_release(self, context: ReleaseEnrichmentContext) -> tuple[int, float] | None:
        try:
            results = self._client.search(**_search_parameters(context))
            results.per_page = _SEARCH_LIMIT
            first_page = results.page(1)
        except _EXTERNAL_ERRORS:
            raise ProviderError("Discogs release search failed") from None

        return _select_release(first_page, context)


def _discogs_release_id(
    context: ReleaseEnrichmentContext,
) -> tuple[int | None, bool]:
    values = [
        identifier.value
        for identifier in context.external_ids
        if identifier.namespace == _DISCOGS_RELEASE_NAMESPACE
    ]
    if not values:
        return None, False
    if len(values) != 1 or re.fullmatch(r"[1-9][0-9]*", values[0]) is None:
        return None, True
    try:
        return int(values[0]), True
    except ValueError:
        return None, True


def _search_parameters(context: ReleaseEnrichmentContext) -> dict[str, object]:
    parameters: dict[str, object] = {
        "type": "release",
        "artist": context.album_artist,
        "release_title": context.album_title,
    }
    if context.year is not None:
        parameters["year"] = context.year
    if context.barcode is not None:
        parameters["barcode"] = context.barcode
    if context.catalog_number is not None:
        parameters["catno"] = context.catalog_number
    return parameters


def _select_release(
    results: Sequence[Any], context: ReleaseEnrichmentContext
) -> tuple[int, float] | None:
    matches: list[tuple[int, bool, bool]] = []
    for result in results[:_SEARCH_LIMIT]:
        data = getattr(result, "data", None)
        if not isinstance(data, Mapping):
            continue

        release_id = _positive_int(data.get("id"))
        artist, title = _search_artist_title(data)
        if (
            release_id is None
            or _normalized_artist(artist) != _normalized_artist(context.album_artist)
            or _normalized_text(title) != _normalized_text(context.album_title)
        ):
            continue

        result_year = _positive_int(data.get("year"))
        if context.year is not None and result_year is not None and result_year != context.year:
            continue

        barcode_match = _matches_any(context.barcode, data.get("barcode"))
        catno_match = _matches_any(context.catalog_number, data.get("catno"))
        if context.barcode is not None and data.get("barcode") and not barcode_match:
            continue
        if context.catalog_number is not None and data.get("catno") and not catno_match:
            continue
        matches.append((release_id, barcode_match, catno_match))

    strong = [match for match in matches if match[1] or match[2]]
    if len(strong) == 1:
        return strong[0][0], _STRONG_SEARCH_CONFIDENCE
    if len(strong) > 1 or len(matches) != 1:
        return None
    return matches[0][0], _WEAK_SEARCH_CONFIDENCE


def _search_artist_title(data: Mapping[str, object]) -> tuple[str, str]:
    artist = _optional_string(data.get("artist"))
    title = _optional_string(data.get("title"))
    if artist:
        return artist, title
    if " - " not in title:
        return "", title
    return tuple(title.split(" - ", 1))  # type: ignore[return-value]


def _normalize_release(
    data: Mapping[str, object], expected_id: int, confidence: float
) -> tuple[MetadataCandidate, ...]:
    release_id = _positive_int(data.get("id"))
    if release_id != expected_id:
        return ()

    source_url = _optional_string(data.get("uri")) or None
    fields: list[tuple[str, str | int | tuple[str, ...]]] = []

    for field in ("genres", "styles"):
        values = _ordered_strings(data.get(field))
        if values:
            fields.append((field, values))

    labels, catalog_numbers = _labels_and_catalog_numbers(data.get("labels"))
    if labels:
        fields.append(("labels", labels))
    if catalog_numbers:
        fields.append(("catalog_numbers", catalog_numbers))

    barcodes = _barcodes(data.get("identifiers"))
    if barcodes:
        fields.append(("barcodes", barcodes))

    country = _optional_string(data.get("country"))
    if country:
        fields.append(("country", country))

    year = _positive_int(data.get("year"))
    if year is not None and year <= 9999:
        fields.append(("year", year))

    media, format_descriptions = _formats(data.get("formats"))
    if media:
        fields.append(("media", media))
    if format_descriptions:
        fields.append(("format_descriptions", format_descriptions))

    return tuple(
        MetadataCandidate(
            field=field,
            value=value,
            provider="discogs",
            confidence=confidence,
            source_id=str(release_id),
            source_url=source_url,
        )
        for field, value in fields
    )


def _labels_and_catalog_numbers(value: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return (), ()
    labels: list[str] = []
    catalog_numbers: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        _append_unique(labels, _optional_string(item.get("name")))
        catno = _optional_string(item.get("catno"))
        if catno.casefold() != "none":
            _append_unique(catalog_numbers, catno)
    return tuple(labels), tuple(catalog_numbers)


def _barcodes(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    barcodes: list[str] = []
    for item in value:
        if isinstance(item, Mapping) and _optional_string(item.get("type")).casefold() == "barcode":
            _append_unique(barcodes, _optional_string(item.get("value")))
    return tuple(barcodes)


def _formats(value: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return (), ()
    media: list[str] = []
    descriptions: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        _append_unique(media, _optional_string(item.get("name")))
        for description in _ordered_strings(item.get("descriptions")):
            _append_unique(descriptions, description)
    return tuple(media), tuple(descriptions)


def _editions(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    editions: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        for description in _ordered_strings(item.get("descriptions")):
            edition = normalize_edition(description)
            if edition is not None:
                _append_unique(editions, edition)
    return tuple(editions)


def _ordered_strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    values: list[str] = []
    for item in value:
        _append_unique(values, _optional_string(item))
    return tuple(values)


def _matches_any(expected: str | None, actual: object) -> bool:
    if expected is None:
        return False
    values = (
        actual
        if isinstance(actual, Sequence) and not isinstance(actual, (str, bytes))
        else (actual,)
    )
    normalized_expected = _normalized_identifier(expected)
    return any(
        normalized_expected == _normalized_identifier(value)
        for value in values
        if _optional_string(value)
    )


def _normalized_identifier(value: object) -> str:
    return "".join(
        character for character in _optional_string(value).casefold() if character.isalnum()
    )


def _normalized_artist(value: object) -> str:
    return re.sub(r"\s+\([0-9]+\)$", "", _normalized_text(value))


def _normalized_text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", _optional_string(value)).casefold().split())


def _positive_int(value: object) -> int | None:
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
    return parsed if parsed > 0 else None


def _optional_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)
