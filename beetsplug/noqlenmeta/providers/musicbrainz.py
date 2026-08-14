"""Anchored enrichment from an exact beets-selected MusicBrainz release."""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import TypeGuard

from beetsplug.noqlenmeta.domain import (
    ExternalIdentifier,
    MetadataCandidate,
    ReleaseEnrichmentContext,
    SemanticEvidenceBundle,
    canonical_uuid,
)
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind
from beetsplug.noqlenmeta.provider_cache import CommandEntityCache, EntityFetchProfile
from beetsplug.noqlenmeta.providers.base import ProviderError, ReleaseProviderEnrichment
from beetsplug.noqlenmeta.providers.musicbrainz_semantic import (
    MusicBrainzSemanticClient,
    artist_credit_from_payload,
    release_credit_values,
    semantic_tags_from_payload,
)
from beetsplug.noqlenmeta.providers.specs import MUSICBRAINZ_SPEC, ProviderScope
from beetsplug.noqlenmeta.release_catalog import (
    normalize_release_secondary_types,
    normalize_release_status,
    normalize_release_type,
    parse_partial_date,
)

_MUSICBRAINZ_RELEASE_NAMESPACE = "musicbrainz.release"
_MUSICBRAINZ_RELEASE_GROUP_NAMESPACE = "musicbrainz.release_group"
_PUBLIC_RELEASE_URL = "https://musicbrainz.org/release/{}"
_PUBLIC_RELEASE_GROUP_URL = "https://musicbrainz.org/release-group/{}"
_RELEASE_GROUP_FIELDS = frozenset({"original_date", "release_type", "release_secondary_types"})

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
        fetch_release_group: Callable[[str], Mapping[str, object] | None] | None = None,
        cache: CommandEntityCache | None = None,
    ) -> None:
        self._semantic_client = MusicBrainzSemanticClient(
            cache=cache,
            fetch_release=fetch_release,
            fetch_release_group=fetch_release_group,
        )

    def get_candidates(self, context: ReleaseEnrichmentContext) -> Sequence[MetadataCandidate]:
        return self.get_enrichment(context, ()).candidates

    def get_enrichment(
        self,
        context: ReleaseEnrichmentContext,
        enabled_fields: Collection[str],
    ) -> ReleaseProviderEnrichment:
        release_mbid = _release_mbid(context)
        if release_mbid is None:
            return ReleaseProviderEnrichment()

        relationship_fields = {
            "producers",
            "conductors",
            "performers",
            "featured_artists",
        }
        profile = (
            EntityFetchProfile(("artist-rels",))
            if set(enabled_fields) & relationship_fields
            else EntityFetchProfile()
        )
        payload = self._semantic_client.lookup_release(release_mbid, profile)
        if not isinstance(payload, Mapping):
            raise ProviderError("MusicBrainz release response is invalid")
        return ReleaseProviderEnrichment(
            tuple(_normalize_release(payload, release_mbid)),
            self._v3_evidence(context, payload, release_mbid, enabled_fields),
        )

    def get_semantic_evidence(self, context: ReleaseEnrichmentContext) -> SemanticEvidenceBundle:
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

    def get_release_catalog_evidence(
        self,
        context: ReleaseEnrichmentContext,
        enabled_fields: Collection[str],
    ) -> tuple[MetadataEvidence, ...]:
        """Compatibility boundary for callers requesting only V3 evidence."""
        return self.get_enrichment(context, enabled_fields).evidence

    def _catalog_evidence(
        self,
        context: ReleaseEnrichmentContext,
        payload: Mapping[str, object],
        release_mbid: str,
        enabled_fields: Collection[str],
    ) -> tuple[MetadataEvidence, ...]:
        requested = set(enabled_fields) & {
            "date",
            "original_date",
            "release_type",
            "release_secondary_types",
            "release_status",
        }
        if not requested:
            return ()

        evidence = list(_release_catalog_evidence(payload, release_mbid, requested))
        group_fields = requested & _RELEASE_GROUP_FIELDS
        if not group_fields:
            return tuple(evidence)
        nested = payload.get("release_group")
        nested = nested if isinstance(nested, Mapping) else {}
        group_id = canonical_uuid(nested.get("id")) or _release_group_mbid(context)
        if group_id is None:
            return tuple(evidence)
        missing = group_fields - {item.field for item in evidence}
        group_payload = nested
        if missing:
            try:
                looked_up = self._semantic_client.lookup_release_group(group_id)
            except ProviderError:
                return tuple(evidence)
            if not isinstance(looked_up, Mapping):
                return tuple(evidence)
            group_payload = looked_up
        evidence.extend(
            item
            for item in _release_group_catalog_evidence(group_payload, group_id, missing)
            if item.field not in {existing.field for existing in evidence}
        )
        return tuple(evidence)

    def _v3_evidence(
        self,
        context: ReleaseEnrichmentContext,
        payload: Mapping[str, object],
        release_mbid: str,
        enabled_fields: Collection[str],
    ) -> tuple[MetadataEvidence, ...]:
        evidence = list(self._catalog_evidence(context, payload, release_mbid, enabled_fields))
        enabled = set(enabled_fields)
        for field, value in release_credit_values(payload, release_mbid).items():
            if field in enabled:
                evidence.append(_release_evidence(field, value, release_mbid))
        if (
            "structured_artist_credits" in enabled
            and (
                credit := artist_credit_from_payload(
                    payload, EntityKind.RELEASE, release_mbid
                )
            )
        ):
            evidence.append(
                _release_evidence("structured_artist_credits", credit, release_mbid)
            )
        return tuple(evidence)


def _release_evidence(field: str, value: object, release_mbid: str) -> MetadataEvidence:
    return MetadataEvidence(
        field=field,
        value=value,  # type: ignore[arg-type]
        subject=SubjectRef(
            EntityKind.RELEASE,
            (ExternalIdentifier("musicbrainz.release", release_mbid),),
        ),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.RELEASE,
        source_id=release_mbid,
        source_url=_PUBLIC_RELEASE_URL.format(release_mbid),
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=_DIRECT_CONFIDENCE,
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


def _release_group_mbid(context: ReleaseEnrichmentContext) -> str | None:
    raw_values = [
        identifier.value
        for identifier in context.external_ids
        if identifier.namespace == _MUSICBRAINZ_RELEASE_GROUP_NAMESPACE
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


def _release_catalog_evidence(
    payload: Mapping[str, object], release_mbid: str, requested: set[str]
) -> tuple[MetadataEvidence, ...]:
    fields: list[tuple[str, object]] = []
    if "date" in requested and (date := parse_partial_date(payload.get("date"))):
        fields.append(("date", date))
    if "release_status" in requested and (
        status := normalize_release_status(payload.get("status"))
    ):
        fields.append(("release_status", status))
    nested = payload.get("release_group")
    if isinstance(nested, Mapping) and (group_id := canonical_uuid(nested.get("id"))):
        return tuple(
            _catalog_evidence(
                field,
                value,
                EntityKind.RELEASE,
                release_mbid,
                _PUBLIC_RELEASE_URL.format(release_mbid),
            )
            for field, value in fields
        ) + _release_group_catalog_evidence(nested, group_id, requested & _RELEASE_GROUP_FIELDS)
    return tuple(
        _catalog_evidence(
            field,
            value,
            EntityKind.RELEASE,
            release_mbid,
            _PUBLIC_RELEASE_URL.format(release_mbid),
        )
        for field, value in fields
    )


def _release_group_catalog_evidence(
    payload: Mapping[str, object], group_id: str, requested: Collection[str]
) -> tuple[MetadataEvidence, ...]:
    if canonical_uuid(payload.get("id")) != group_id:
        return ()
    fields: list[tuple[str, object]] = []
    if "original_date" in requested and (
        date := parse_partial_date(payload.get("first_release_date"))
    ):
        fields.append(("original_date", date))
    if "release_type" in requested and (
        release_type := normalize_release_type(payload.get("primary_type"))
    ):
        fields.append(("release_type", release_type))
    if "release_secondary_types" in requested and (
        secondary := normalize_release_secondary_types(payload.get("secondary_types"))
    ):
        fields.append(("release_secondary_types", secondary))
    return tuple(
        _catalog_evidence(
            field,
            value,
            EntityKind.RELEASE_GROUP,
            group_id,
            _PUBLIC_RELEASE_GROUP_URL.format(group_id),
        )
        for field, value in fields
    )


def _catalog_evidence(
    field: str,
    value: object,
    entity: EntityKind,
    source_id: str,
    source_url: str,
) -> MetadataEvidence:
    return MetadataEvidence(
        field=field,
        value=value,  # type: ignore[arg-type]
        subject=SubjectRef(
            entity,
            (
                ExternalIdentifier(
                    f"musicbrainz.{entity.value}",
                    source_id,
                ),
            ),
        ),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.RELEASE,
        source_id=source_id,
        source_url=source_url,
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=_DIRECT_CONFIDENCE,
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
