"""Anchored enrichment from an exact beets-selected MusicBrainz release."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import TypeGuard

from beetsplug.noqlenmeta.domain import (
    MetadataCandidate,
    ReleaseEnrichmentContext,
    SemanticEvidenceBundle,
    canonical_uuid,
)
from beetsplug.noqlenmeta.provider_cache import CommandEntityCache
from beetsplug.noqlenmeta.providers.base import ProviderError
from beetsplug.noqlenmeta.providers.musicbrainz_semantic import (
    MusicBrainzSemanticClient,
    semantic_tags_from_payload,
)
from beetsplug.noqlenmeta.providers.specs import MUSICBRAINZ_SPEC, ProviderScope

_MUSICBRAINZ_RELEASE_NAMESPACE = "musicbrainz.release"
_PUBLIC_RELEASE_URL = "https://musicbrainz.org/release/{}"

# Confidence represents association with the exact selected release, not a claim
# that MusicBrainz data can never contain errors.
_DIRECT_CONFIDENCE = 0.99


class MusicBrainzProvider:
    """Emit metadata only for an exact MusicBrainz release MBID."""

    name = MUSICBRAINZ_SPEC.name
    supported_fields = MUSICBRAINZ_SPEC.supported_fields

    def __init__(
        self,
        *,
        fetch_release: Callable[[str], Mapping[str, object]] | None = None,
        cache: CommandEntityCache | None = None,
    ) -> None:
        self._semantic_client = MusicBrainzSemanticClient(
            cache=cache, fetch_release=fetch_release or _fetch_release
        )

    def get_candidates(
        self, context: ReleaseEnrichmentContext
    ) -> Sequence[MetadataCandidate]:
        release_mbid = _release_mbid(context)
        if release_mbid is None:
            return ()

        payload = self._semantic_client.lookup_release(release_mbid)
        if not isinstance(payload, Mapping):
            raise ProviderError("MusicBrainz release response is invalid")
        return _normalize_release(payload, release_mbid)

    def get_semantic_evidence(
        self, context: ReleaseEnrichmentContext
    ) -> SemanticEvidenceBundle:
        release_mbid = _release_mbid(context)
        if release_mbid is None:
            return SemanticEvidenceBundle()
        payload = self._semantic_client.lookup_release(release_mbid)
        if payload is None:
            return SemanticEvidenceBundle()
        genres, tags = semantic_tags_from_payload(
            payload,
            entity_id=release_mbid,
            entity_type="release",
            scope=ProviderScope.RELEASE,
        )
        return SemanticEvidenceBundle(genres=genres, tags=tags)


def _fetch_release(release_mbid: str) -> Mapping[str, object]:
    from beetsplug._utils.musicbrainz import MusicBrainzAPI

    return MusicBrainzAPI().get_release(
        release_mbid,
        includes=["labels", "media", "genres", "tags", "recordings", "artist-credits"],
    )


def _release_mbid(context: ReleaseEnrichmentContext) -> str | None:
    raw_values = [
        identifier.value
        for identifier in context.external_ids
        if identifier.namespace == _MUSICBRAINZ_RELEASE_NAMESPACE
    ]
    if not raw_values:
        return None
    normalized = [canonical_uuid(value) for value in raw_values]
    if any(value is None for value in normalized):
        return None
    distinct = set(normalized)
    return distinct.pop() if len(distinct) == 1 else None


def _normalize_release(
    payload: Mapping[str, object], release_mbid: str
) -> tuple[MetadataCandidate, ...]:
    fields: list[tuple[str, str | int | tuple[str, ...]]] = []
    labels, catalog_numbers = _label_info(payload.get("label_info"))
    if labels:
        fields.append(("labels", labels))
    if catalog_numbers:
        fields.append(("catalog_numbers", catalog_numbers))

    barcode = _optional_string(payload.get("barcode"))
    if barcode:
        fields.append(("barcodes", (barcode,)))
    country = _optional_string(payload.get("country"))
    if country:
        fields.append(("country", country))
    year = _release_year(payload.get("date"))
    if year is not None:
        fields.append(("year", year))
    media = _media_formats(payload.get("media"))
    if media:
        fields.append(("media", media))

    return tuple(
        MetadataCandidate(
            field=field,
            value=value,
            provider=MUSICBRAINZ_SPEC.name,
            confidence=_DIRECT_CONFIDENCE,
            source_id=release_mbid,
            source_url=_PUBLIC_RELEASE_URL.format(release_mbid),
        )
        for field, value in fields
    )


def _label_info(value: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not _is_sequence(value):
        return (), ()
    labels: list[str] = []
    catalog_numbers: list[str] = []
    for entry in value:
        if not isinstance(entry, Mapping):
            continue
        label = entry.get("label")
        if isinstance(label, Mapping):
            _append_unique(labels, _optional_string(label.get("name")))
        _append_unique(catalog_numbers, _optional_string(entry.get("catalog_number")))
    return tuple(labels), tuple(catalog_numbers)


def _media_formats(value: object) -> tuple[str, ...]:
    if not _is_sequence(value):
        return ()
    formats: list[str] = []
    for entry in value:
        if isinstance(entry, Mapping):
            _append_unique(formats, _optional_string(entry.get("format")))
    return tuple(formats)


def _release_year(value: object) -> int | None:
    text = _optional_string(value)
    match = re.fullmatch(
        r"([0-9]{4})(?:-(?:0[1-9]|1[0-2]|\?\?)(?:-(?:0[1-9]|[12][0-9]|3[01]|\?\?))?)?",
        text,
    )
    if match is None:
        return None
    year = int(match.group(1))
    return year if 1 <= year <= 9999 else None


def _is_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _optional_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)
