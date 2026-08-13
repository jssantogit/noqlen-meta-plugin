"""Exact MusicBrainz semantic lookups and evidence normalization."""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass

from requests import RequestException

from beetsplug.noqlenmeta.domain import (
    ArtistEnrichmentContext,
    ExternalIdentifier,
    MetadataCandidate,
    SemanticCategory,
    SemanticEvidenceBundle,
    SemanticTagEvidence,
    TrackEnrichmentContext,
    canonical_isrc,
    canonical_uuid,
)
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind, IdentifierCollection
from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
)
from beetsplug.noqlenmeta.provider_cache import CommandEntityCache, EntityCacheKey
from beetsplug.noqlenmeta.providers.base import ProviderError
from beetsplug.noqlenmeta.providers.specs import (
    MUSICBRAINZ_ARTIST_SPEC,
    MUSICBRAINZ_TRACK_SPEC,
    ProviderScope,
)
from beetsplug.noqlenmeta.release_catalog import parse_partial_date
from beetsplug.noqlenmeta.semantic_tags import classify_semantic_tag
from beetsplug.noqlenmeta.work_identity import WorkReference, canonical_work_references

EntityFetcher = Callable[[str], Mapping[str, object] | None]

_PUBLIC_URL = "https://musicbrainz.org/{}/{}"
_DIRECT_CONFIDENCE = 0.99
_COMMUNITY_CONFIDENCE = 0.85
_LANGUAGE = re.compile(r"[a-z]{3}")
_ISWC = re.compile(r"T-\d{3}\.\d{3}\.\d{3}-\d")
_NON_SPECIFIC_LANGUAGES = frozenset({"mul", "und", "zxx"})


@dataclass(frozen=True, slots=True)
class MusicBrainzTrackEnrichment:
    semantic: SemanticEvidenceBundle = SemanticEvidenceBundle()
    evidence: tuple[MetadataEvidence, ...] = ()
    unavailable_fields: frozenset[str] = frozenset()


class MusicBrainzSemanticClient:
    """Cache and validate exact MusicBrainz entity responses for one command."""

    def __init__(
        self,
        *,
        cache: CommandEntityCache | None = None,
        fetch_release: EntityFetcher | None = None,
        fetch_release_group: EntityFetcher | None = None,
        fetch_recording: EntityFetcher | None = None,
        fetch_work: EntityFetcher | None = None,
        fetch_artist: EntityFetcher | None = None,
        fetch_area: EntityFetcher | None = None,
    ) -> None:
        self.cache = cache or CommandEntityCache()
        self._fetchers = {
            "release": fetch_release or _fetch_release,
            "release_group": fetch_release_group or _fetch_release_group,
            "recording": fetch_recording or _fetch_recording,
            "work": fetch_work or _fetch_work,
            "artist": fetch_artist or _fetch_artist,
            "area": fetch_area or _fetch_area,
        }

    def _lookup(self, entity_type: str, entity_id: str) -> Mapping[str, object] | None:
        canonical_id = canonical_uuid(entity_id)
        if canonical_id is None:
            return None
        key = EntityCacheKey("musicbrainz", entity_type, canonical_id)

        def fetch_and_validate() -> Mapping[str, object] | None:
            try:
                payload = self._fetchers[entity_type](canonical_id)
            except RequestException:
                raise ProviderError("MusicBrainz API request failed") from None
            if payload is None:
                return None
            if not isinstance(payload, Mapping):
                raise ProviderError(f"MusicBrainz {entity_type} response is invalid")
            response_id = canonical_uuid(payload.get("id"))
            if response_id != canonical_id:
                raise ProviderError(f"MusicBrainz {entity_type} response is invalid")
            return payload

        return self.cache.get_or_fetch(key, fetch_and_validate)

    def lookup_release(self, entity_id: str) -> Mapping[str, object] | None:
        return self._lookup("release", entity_id)

    def lookup_release_group(self, entity_id: str) -> Mapping[str, object] | None:
        return self._lookup("release_group", entity_id)

    def lookup_recording(self, entity_id: str) -> Mapping[str, object] | None:
        return self._lookup("recording", entity_id)

    def lookup_work(self, entity_id: str) -> Mapping[str, object] | None:
        return self._lookup("work", entity_id)

    def lookup_artist(self, entity_id: str) -> Mapping[str, object] | None:
        return self._lookup("artist", entity_id)

    def lookup_area(self, entity_id: str) -> Mapping[str, object] | None:
        return self._lookup("area", entity_id)


class MusicBrainzTrackProvider:
    name = MUSICBRAINZ_TRACK_SPEC.name
    supported_fields = MUSICBRAINZ_TRACK_SPEC.supported_fields

    def __init__(
        self,
        client: MusicBrainzSemanticClient | None = None,
        *,
        enabled_fields: Collection[str] | None = None,
    ) -> None:
        self.client = client or MusicBrainzSemanticClient()
        self.enabled_fields = set(enabled_fields or self.supported_fields | {"artist_languages"})

    def get_semantic_evidence(self, context: TrackEnrichmentContext) -> SemanticEvidenceBundle:
        return self.get_enrichment(context).semantic

    def get_enrichment(self, context: TrackEnrichmentContext) -> MusicBrainzTrackEnrichment:
        recording_id = _context_mbid(context.external_ids, "musicbrainz.recording")
        if recording_id is None:
            return MusicBrainzTrackEnrichment()
        payload = self.client.lookup_recording(recording_id)
        if payload is None:
            return MusicBrainzTrackEnrichment()
        genres, tags = ((), ())
        if self.enabled_fields & {"genres", "moods"}:
            genres, tags = semantic_tags_from_payload(
                payload,
                entity_id=recording_id,
                entity_type="recording",
                scope=ProviderScope.TRACK,
            )
        languages: list[str] = []
        unavailable_fields: set[str] = set()
        wave_unavailable: set[str] = set()
        evidence: list[MetadataEvidence] = []
        work_references = _work_references(payload)
        if "isrcs" in self.enabled_fields and (isrcs := _recording_isrcs(payload)):
            evidence.append(_recording_evidence("isrcs", isrcs, recording_id))
        if "works" in self.enabled_fields and work_references:
            evidence.append(_recording_evidence("works", work_references, recording_id))
        if "recording_date" in self.enabled_fields:
            for recording_date in _recording_dates(payload):
                evidence.append(_recording_evidence("recording_date", recording_date, recording_id))
        work_fields = {"lyrics_languages", "artist_languages", "iswcs"}
        if self.enabled_fields & work_fields:
            work_ids = (
                tuple(reference.mbid for reference in work_references)
                if self.enabled_fields & {"works", "iswcs"}
                else _related_ids(payload, "work")
            )
            for work_id in work_ids:
                try:
                    work = self.client.lookup_work(work_id)
                except ProviderError:
                    unavailable_fields.update(
                        self.enabled_fields & {"lyrics_languages", "artist_languages"}
                    )
                    wave_unavailable.update(self.enabled_fields & {"iswcs"})
                    continue
                if work is None:
                    continue
                for language in _work_languages(work):
                    _append_unique(languages, language)
                if "iswcs" in self.enabled_fields and (iswcs := _work_iswcs(work)):
                    evidence.append(_work_evidence("iswcs", iswcs, work_id, recording_id))
        metadata = ()
        if languages:
            metadata = (
                MetadataCandidate(
                    "lyrics_languages",
                    tuple(languages),
                    self.name,
                    _DIRECT_CONFIDENCE,
                    recording_id,
                    _PUBLIC_URL.format("recording", recording_id),
                ),
            )
        semantic = SemanticEvidenceBundle(metadata, genres, tags, frozenset(unavailable_fields))
        return MusicBrainzTrackEnrichment(semantic, tuple(evidence), frozenset(wave_unavailable))


class MusicBrainzArtistProvider:
    name = MUSICBRAINZ_ARTIST_SPEC.name
    supported_fields = MUSICBRAINZ_ARTIST_SPEC.supported_fields

    def __init__(
        self,
        client: MusicBrainzSemanticClient | None = None,
        *,
        enabled_fields: Collection[str] | None = None,
    ) -> None:
        self.client = client or MusicBrainzSemanticClient()
        self.enabled_fields = set(enabled_fields or self.supported_fields)

    def get_semantic_evidence(self, context: ArtistEnrichmentContext) -> SemanticEvidenceBundle:
        artist_id = _context_mbid(context.external_ids, "musicbrainz.artist")
        if artist_id is None:
            return SemanticEvidenceBundle()
        payload = self.client.lookup_artist(artist_id)
        if payload is None:
            return SemanticEvidenceBundle()
        genres, tags = ((), ())
        if self.enabled_fields & {"genres", "moods"}:
            genres, tags = semantic_tags_from_payload(
                payload,
                entity_id=artist_id,
                entity_type="artist",
                scope=ProviderScope.ARTIST,
            )
        area = None
        if self.enabled_fields & {"artist_areas", "artist_countries"}:
            area = _area_mapping(payload.get("area")) or _area_mapping(payload.get("begin-area"))
        fields: list[tuple[str, tuple[str, ...]]] = []
        unavailable_fields: set[str] = set()
        if area is not None:
            area_name = _text(area.get("name"))
            if area_name:
                fields.append(("artist_areas", (area_name,)))
            country = None
            if "artist_countries" in self.enabled_fields:
                try:
                    country, ancestry_unavailable = self._country_for_area(area)
                except ProviderError:
                    unavailable_fields.add("artist_countries")
                else:
                    if ancestry_unavailable:
                        unavailable_fields.add("artist_countries")
            if country:
                fields.append(("artist_countries", (country,)))
        metadata = tuple(
            MetadataCandidate(
                field,
                value,
                self.name,
                _DIRECT_CONFIDENCE,
                artist_id,
                _PUBLIC_URL.format("artist", artist_id),
            )
            for field, value in fields
        )
        return SemanticEvidenceBundle(metadata, genres, tags, frozenset(unavailable_fields))

    def _country_for_area(self, initial_area: Mapping[str, object]) -> tuple[str | None, bool]:
        country = _structural_country(initial_area)
        if country:
            return country, False
        initial_id = canonical_uuid(initial_area.get("id"))
        if initial_id is None:
            return _structural_country(initial_area), False
        pending = [initial_id]
        visited: set[str] = set()
        unavailable = False
        while pending:
            area_id = pending.pop(0)
            if area_id in visited:
                continue
            visited.add(area_id)
            try:
                area = self.client.lookup_area(area_id)
            except ProviderError:
                unavailable = True
                continue
            if area is None:
                continue
            country = _structural_country(area)
            if country:
                return country, unavailable
            pending.extend(
                related_id for related_id in _related_ids(area, "area") if related_id not in visited
            )
        return None, unavailable


def _recording_evidence(field: str, value: object, recording_id: str) -> MetadataEvidence:
    return MetadataEvidence(
        field=field,
        value=value,  # type: ignore[arg-type]
        subject=SubjectRef(
            EntityKind.RECORDING,
            (ExternalIdentifier("musicbrainz.recording", recording_id),),
        ),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.TRACK,
        source_id=recording_id,
        source_url=_PUBLIC_URL.format("recording", recording_id),
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=_DIRECT_CONFIDENCE,
    )


def _work_evidence(
    field: str,
    value: object,
    work_id: str,
    recording_id: str,
) -> MetadataEvidence:
    return MetadataEvidence(
        field=field,
        value=value,  # type: ignore[arg-type]
        subject=SubjectRef(
            EntityKind.WORK,
            (ExternalIdentifier("musicbrainz.work", work_id),),
        ),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.TRACK,
        source_id=work_id,
        source_url=_PUBLIC_URL.format("work", work_id),
        provenance=AcquisitionProvenance(
            AcquisitionMethod.SUPPORTING_TRAVERSAL,
            supporting_entity=EntityKind.RECORDING,
        ),
        confidence=_DIRECT_CONFIDENCE,
    )


def _recording_isrcs(payload: Mapping[str, object]) -> IdentifierCollection | None:
    raw_values = payload.get("isrcs")
    if not isinstance(raw_values, Sequence) or isinstance(raw_values, (str, bytes)):
        return None
    values = {
        ExternalIdentifier("isrc", normalized)
        for value in raw_values
        if (normalized := canonical_isrc(value)) is not None
    }
    if not values:
        return None
    return IdentifierCollection(tuple(sorted(values, key=lambda value: value.value)))


def _work_iswcs(payload: Mapping[str, object]) -> IdentifierCollection | None:
    raw_values = payload.get("iswcs")
    if not isinstance(raw_values, Sequence) or isinstance(raw_values, (str, bytes)):
        return None
    values = {
        ExternalIdentifier("iswc", value.strip().upper())
        for value in raw_values
        if isinstance(value, str) and _ISWC.fullmatch(value.strip())
    }
    if not values:
        return None
    return IdentifierCollection(tuple(sorted(values, key=lambda value: value.value)))


def _work_references(payload: Mapping[str, object]) -> tuple[WorkReference, ...]:
    relations = payload.get("relations")
    if not isinstance(relations, Sequence) or isinstance(relations, (str, bytes)):
        return ()
    values: list[WorkReference] = []
    for relation in relations:
        if not isinstance(relation, Mapping) or relation.get("target-type") != "work":
            continue
        work = relation.get("work")
        if not isinstance(work, Mapping):
            continue
        work_id = canonical_uuid(work.get("id"))
        relation_type = _text(relation.get("type"))
        if work_id is None or not relation_type:
            continue
        type_id = canonical_uuid(relation.get("type-id"))
        title = _text(work.get("title")) or None
        raw_attributes = relation.get("attributes")
        attributes = (
            tuple(
                attribute.strip()
                for attribute in raw_attributes
                if isinstance(attribute, str) and attribute.strip()
            )
            if isinstance(raw_attributes, Sequence)
            and not isinstance(raw_attributes, (str, bytes))
            else ()
        )
        ordering = relation.get("ordering-key")
        ordering_key = (
            ordering if isinstance(ordering, int) and not isinstance(ordering, bool) else None
        )
        values.append(
            WorkReference(
                work_id,
                title,
                relation_type,
                type_id,
                attributes,
                ordering_key,
            )
        )
    return canonical_work_references(values)


def _recording_dates(payload: Mapping[str, object]) -> tuple[object, ...]:
    relations = payload.get("relations")
    if not isinstance(relations, Sequence) or isinstance(relations, (str, bytes)):
        return ()
    values = []
    for relation in relations:
        if not isinstance(relation, Mapping) or relation.get("type") != "recorded at":
            continue
        begin = parse_partial_date(relation.get("begin"))
        end = parse_partial_date(relation.get("end"))
        if begin is not None and begin == end:
            values.append(begin)
    return tuple(sorted(set(values), key=str))

def semantic_tags_from_payload(
    payload: Mapping[str, object],
    *,
    entity_id: str,
    entity_type: str,
    scope: ProviderScope,
) -> tuple[tuple[GenreEvidence, ...], tuple[SemanticTagEvidence, ...]]:
    genres: list[GenreEvidence] = []
    tags: list[SemanticTagEvidence] = []
    source_url = _PUBLIC_URL.format(entity_type, entity_id)
    for row in _mapping_rows(payload.get("genres")):
        name = _text(row.get("name"))
        classification = DEFAULT_GENRE_TAXONOMY.classify(name)
        if classification.category is GenreSemanticCategory.GENRE:
            genres.append(
                GenreEvidence(
                    classification.canonical_name,
                    "musicbrainz",
                    scope,
                    GenreEvidenceKind.GENRE,
                    _DIRECT_CONFIDENCE,
                    entity_id,
                    source_url,
                    _weight(row.get("count"), maximum=100),
                )
            )
    for row in _mapping_rows(payload.get("tags")):
        name = _text(row.get("name"))
        if not name:
            continue
        evidence = classify_semantic_tag(
            name,
            "musicbrainz",
            scope,
            _COMMUNITY_CONFIDENCE,
            entity_id,
            source_url,
            _weight(row.get("count")),
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
                    min(evidence.native_weight, 100)
                    if evidence.native_weight is not None
                    else None,
                )
            )
        elif evidence.category in {SemanticCategory.STYLE, SemanticCategory.MOOD}:
            tags.append(evidence)
    return tuple(genres), tuple(tags)


def _context_mbid(identifiers: Sequence[object], namespace: str) -> str | None:
    values = [
        canonical_uuid(getattr(identifier, "value", None))
        for identifier in identifiers
        if getattr(identifier, "namespace", None) == namespace
    ]
    if not values or any(value is None for value in values):
        return None
    distinct = set(values)
    return distinct.pop() if len(distinct) == 1 else None


def _work_languages(payload: Mapping[str, object]) -> tuple[str, ...]:
    attributes = (
        {
            _text(value).casefold()
            for value in payload.get("attributes", ())
            if isinstance(value, str)
        }
        if _is_sequence(payload.get("attributes"))
        else set()
    )
    if {"instrumental", "no lyrics"} & attributes:
        return ()
    raw = payload.get("languages")
    values = raw if _is_sequence(raw) else (payload.get("language"),)
    result: list[str] = []
    for value in values:
        language = _text(value).casefold()
        if _LANGUAGE.fullmatch(language) and language not in _NON_SPECIFIC_LANGUAGES:
            _append_unique(result, language)
    return tuple(result)


def _related_ids(payload: Mapping[str, object], entity_type: str) -> tuple[str, ...]:
    values: list[str] = []
    relation_groups = [payload.get("relations"), payload.get(f"{entity_type}_relations")]
    for relations in relation_groups:
        if not _is_sequence(relations):
            continue
        for relation in relations:
            if not isinstance(relation, Mapping):
                continue
            target_type = _text(relation.get("target-type") or relation.get("target_type"))
            target = relation.get(entity_type)
            if target_type and target_type != entity_type:
                continue
            if entity_type == "area" and _text(relation.get("type")).casefold() != "part of":
                continue
            if not isinstance(target, Mapping):
                continue
            entity_id = canonical_uuid(target.get("id"))
            if entity_id:
                _append_unique(values, entity_id)
    return tuple(values)


def _structural_country(area: Mapping[str, object]) -> str | None:
    area_type = _text(area.get("type")).casefold()
    codes = area.get("iso-3166-1-codes", area.get("iso_3166_1_codes"))
    if area_type != "country" or not _is_sequence(codes):
        return None
    if not any(isinstance(code, str) and len(code.strip()) == 2 for code in codes):
        return None
    return _text(area.get("name")) or None


def _area_mapping(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    return value if canonical_uuid(value.get("id")) and _text(value.get("name")) else None


def _mapping_rows(value: object) -> tuple[Mapping[str, object], ...]:
    if not _is_sequence(value):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _weight(value: object, *, maximum: int | None = None) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return min(value, maximum) if maximum is not None else value


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _fetch_release(entity_id: str) -> Mapping[str, object]:
    from beetsplug._utils.musicbrainz import MusicBrainzAPI

    return MusicBrainzAPI().get_release(
        entity_id,
        includes=["labels", "media", "genres", "tags", "recordings", "artist-credits"],
    )


def _fetch_release_group(entity_id: str) -> Mapping[str, object]:
    return _fetch_generic("release-group", entity_id, [])


def _fetch_recording(entity_id: str) -> Mapping[str, object]:
    from beetsplug._utils.musicbrainz import MusicBrainzAPI

    return MusicBrainzAPI().get_recording(
        entity_id, includes=["genres", "tags", "artist-credits", "work-rels"]
    )


def _fetch_work(entity_id: str) -> Mapping[str, object]:
    from beetsplug._utils.musicbrainz import MusicBrainzAPI

    return MusicBrainzAPI().get_work(entity_id)


def _fetch_artist(entity_id: str) -> Mapping[str, object]:
    return _fetch_generic("artist", entity_id, ["genres", "tags", "area-rels"])


def _fetch_area(entity_id: str) -> Mapping[str, object]:
    return _fetch_generic("area", entity_id, ["area-rels"])


def _fetch_generic(
    entity_type: str, entity_id: str, includes: Sequence[str]
) -> Mapping[str, object]:
    from beetsplug._utils.musicbrainz import MusicBrainzAPI

    api = MusicBrainzAPI()
    return api.get_json(
        f"{api.api_root}/{entity_type}/{entity_id}",
        params={"inc": "+".join(includes), "fmt": "json"},
    )
