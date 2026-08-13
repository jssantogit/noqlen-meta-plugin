"""Conservative album-level enrichment from one iTunes collection."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Collection, Mapping, Sequence
from datetime import datetime
from http.client import HTTPException
from json import JSONDecodeError
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

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
from beetsplug.noqlenmeta.providers.base import ProviderError, ReleaseProviderEnrichment
from beetsplug.noqlenmeta.providers.specs import ITUNES_SPEC, ProviderScope
from beetsplug.noqlenmeta.release_catalog import parse_iso_datetime_date

_ITUNES_COLLECTION_NAMESPACE = "itunes.collection"
_API_URL = "https://itunes.apple.com"
_SEARCH_LIMIT = 10
_TIMEOUT = 10
_MAX_RESPONSE_BYTES = 1_000_000
_USER_AGENT = "NoqlenMeta/0.0.0"

# Provider-local confidence describes collection identification, not field authority.
_DIRECT_CONFIDENCE = 0.98
_UPC_CONFIDENCE = 0.94
_SEARCH_CONFIDENCE = 0.82

_EXTERNAL_ERRORS = (
    OSError,
    HTTPException,
    JSONDecodeError,
    UnicodeDecodeError,
    KeyError,
)


class ITunesProvider:
    """Resolve one iTunes collection and emit its defensible metadata."""

    name = ITUNES_SPEC.name
    supported_fields = ITUNES_SPEC.supported_fields

    def __init__(
        self,
        storefront: str = "us",
        *,
        request_json: Callable[[str], Mapping[str, object]] | None = None,
    ) -> None:
        storefront = storefront.strip().lower()
        if re.fullmatch(r"[a-z]{2}", storefront) is None:
            raise ProviderError("iTunes storefront configuration is invalid")
        self._storefront = storefront
        self._request_json = request_json or _request_json

    def get_candidates(self, context: ReleaseEnrichmentContext) -> Sequence[MetadataCandidate]:
        return self.get_enrichment(context, ()).candidates

    def get_enrichment(
        self,
        context: ReleaseEnrichmentContext,
        enabled_fields: Collection[str],
    ) -> ReleaseProviderEnrichment:
        resolved = self._resolve_collection(context)
        if resolved is None:
            return ReleaseProviderEnrichment()
        collection, confidence, method = resolved
        return ReleaseProviderEnrichment(
            tuple(_normalize_collection(collection, confidence)),
            self._catalog_evidence(collection, confidence, method, enabled_fields),
        )

    def get_release_catalog_evidence(
        self,
        context: ReleaseEnrichmentContext,
        enabled_fields: Collection[str],
    ) -> tuple[MetadataEvidence, ...]:
        return self.get_enrichment(context, enabled_fields).evidence

    def _catalog_evidence(
        self,
        collection: Mapping[str, object],
        confidence: float,
        method: AcquisitionMethod,
        enabled_fields: Collection[str],
    ) -> tuple[MetadataEvidence, ...]:
        if "date" not in enabled_fields:
            return ()
        collection_id = _positive_int(collection.get("collectionId"))
        date = parse_iso_datetime_date(collection.get("releaseDate"))
        if collection_id is None or date is None:
            return ()
        return (
            MetadataEvidence(
                field="date",
                value=date,
                subject=SubjectRef(
                    EntityKind.RELEASE,
                    (ExternalIdentifier("itunes.collection", str(collection_id)),),
                ),
                provider="itunes",
                acquisition_scope=ProviderScope.RELEASE,
                source_id=str(collection_id),
                source_url=_public_url(collection.get("collectionViewUrl")),
                provenance=AcquisitionProvenance(method),
                confidence=confidence,
            ),
        )

    def _resolve_collection(
        self, context: ReleaseEnrichmentContext
    ) -> tuple[Mapping[str, object], float, AcquisitionMethod] | None:
        direct_id, has_itunes_ids = _itunes_collection_id(context)
        if has_itunes_ids:
            if direct_id is None:
                return None
            results = self._request("lookup", id=direct_id, entity="album")
            collection = _direct_collection(results, direct_id)
            return (
                (collection, _DIRECT_CONFIDENCE, AcquisitionMethod.EXACT_LOOKUP)
                if collection
                else None
            )

        if context.barcode is not None:
            results = self._request("lookup", upc=context.barcode, entity="album")
            matches = _matching_collections(results, context)
            if len(matches) == 1:
                return (
                    matches[0],
                    _UPC_CONFIDENCE,
                    AcquisitionMethod.STRUCTURALLY_VALIDATED,
                )
            if len(matches) > 1:
                return None

        results = self._request(
            "search",
            term=f"{context.album_artist} {context.album_title}",
            media="music",
            entity="album",
            limit=_SEARCH_LIMIT,
        )
        matches = _matching_collections(results, context)
        if len(matches) != 1:
            return None
        return matches[0], _SEARCH_CONFIDENCE, AcquisitionMethod.SEARCHED_CANDIDATE

    def _request(self, operation: str, **parameters: object) -> tuple[Mapping[str, object], ...]:
        parameters["country"] = self._storefront.upper()
        url = f"{_API_URL}/{operation}?{urlencode(parameters)}"
        try:
            payload = self._request_json(url)
            results = payload["results"]
            if not isinstance(results, Sequence) or isinstance(results, (str, bytes)):
                raise KeyError("results")
        except _EXTERNAL_ERRORS:
            raise ProviderError("iTunes API request failed") from None

        return tuple(result for result in results if isinstance(result, Mapping))


def _request_json(url: str) -> Mapping[str, object]:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=_TIMEOUT) as response:
        body = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(body) > _MAX_RESPONSE_BYTES:
        raise HTTPException("iTunes response exceeded the size limit")
    payload: Any = json.loads(body.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise KeyError("response")
    return payload


def _itunes_collection_id(context: ReleaseEnrichmentContext) -> tuple[int | None, bool]:
    values = [
        identifier.value
        for identifier in context.external_ids
        if identifier.namespace == _ITUNES_COLLECTION_NAMESPACE
    ]
    if not values:
        return None, False
    if len(values) != 1 or re.fullmatch(r"[1-9][0-9]*", values[0]) is None:
        return None, True
    try:
        return int(values[0]), True
    except ValueError:
        return None, True


def _direct_collection(
    results: Sequence[Mapping[str, object]], expected_id: int
) -> Mapping[str, object]:
    matches = [
        result
        for result in results
        if _is_album_collection(result) and _positive_int(result.get("collectionId")) == expected_id
    ]
    return matches[0] if len(matches) == 1 else {}


def _matching_collections(
    results: Sequence[Mapping[str, object]], context: ReleaseEnrichmentContext
) -> tuple[Mapping[str, object], ...]:
    matches: dict[int, Mapping[str, object]] = {}
    for result in results[:_SEARCH_LIMIT]:
        collection_id = _positive_int(result.get("collectionId"))
        if (
            not _is_album_collection(result)
            or collection_id is None
            or _normalized_text(result.get("artistName")) != _normalized_text(context.album_artist)
            or _normalized_text(result.get("collectionName"))
            != _normalized_text(context.album_title)
        ):
            continue
        result_year = _release_year(result.get("releaseDate"))
        if context.year is not None and result_year is not None and result_year != context.year:
            continue
        matches.setdefault(collection_id, result)
    return tuple(matches.values())


def _is_album_collection(result: Mapping[str, object]) -> bool:
    return (
        _optional_string(result.get("wrapperType")).casefold() == "collection"
        and _optional_string(result.get("collectionType")).casefold() == "album"
    )


def _normalize_collection(
    collection: Mapping[str, object], confidence: float
) -> tuple[MetadataCandidate, ...]:
    collection_id = _positive_int(collection.get("collectionId"))
    if collection_id is None:
        return ()

    fields: list[tuple[str, int | tuple[str, ...]]] = []
    genre = _optional_string(collection.get("primaryGenreName"))
    if genre:
        fields.append(("genres", (genre,)))
    year = _release_year(collection.get("releaseDate"))
    if year is not None:
        fields.append(("year", year))

    source_url = _public_url(collection.get("collectionViewUrl"))
    return tuple(
        MetadataCandidate(
            field=field,
            value=value,
            provider="itunes",
            confidence=confidence,
            source_id=str(collection_id),
            source_url=source_url,
        )
        for field, value in fields
    )


def _normalized_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", _optional_string(value)).casefold()
    text = "".join(character if character.isalnum() else " " for character in text)
    return " ".join(text.split())


def _release_year(value: object) -> int | None:
    text = _optional_string(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).year
    except ValueError:
        return None


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


def _public_url(value: object) -> str | None:
    url = _optional_string(value)
    parsed = urlsplit(url)
    if parsed.scheme == "https" and parsed.netloc and parsed.username is None:
        return url
    return None
