"""Exact MusicBrainz semantic lookups and evidence normalization."""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass

from requests import RequestException

from beetsplug.noqlenmeta.credits import (
    ArtistCredit,
    ArtistCreditNode,
    CreditParty,
    CreditReference,
    CreditRole,
    canonical_credit_references,
)
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
from beetsplug.noqlenmeta.provider_cache import (
    CommandEntityCache,
    EntityCacheKey,
    EntityFetchProfile,
)
from beetsplug.noqlenmeta.providers.base import ProviderError
from beetsplug.noqlenmeta.providers.specs import (
    MUSICBRAINZ_ARTIST_SPEC,
    MUSICBRAINZ_TRACK_SPEC,
    ProviderScope,
)
from beetsplug.noqlenmeta.release_catalog import parse_partial_date
from beetsplug.noqlenmeta.semantic_tags import classify_semantic_tag
from beetsplug.noqlenmeta.work_identity import WorkReference, canonical_work_references

EntityFetcher = Callable[..., Mapping[str, object] | None]

_PUBLIC_URL = "https://musicbrainz.org/{}/{}"
_DIRECT_CONFIDENCE = 0.99
_COMMUNITY_CONFIDENCE = 0.85
_LANGUAGE = re.compile(r"[a-z]{3}")
_ISWC = re.compile(r"T-\d{3}\.\d{3}\.\d{3}-\d")
_NON_SPECIFIC_LANGUAGES = frozenset({"mul", "und", "zxx"})
_PERFORMANCE_TYPE_ID = "a3005666-a872-32c3-ad06-98af558e99b0"
_RECORDED_AT_TYPE_ID = "ad462279-14b0-4180-9b58-571d0eef7c51"
_RECORDING_SCHEMA_VERSION = "normalized-recording-v1"
_WORK_SCHEMA_VERSION = "normalized-work-v2"
_DEFAULT_FETCH_PROFILE = EntityFetchProfile()


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

    def _lookup(
        self,
        entity_type: str,
        entity_id: str,
        profile: EntityFetchProfile = _DEFAULT_FETCH_PROFILE,
    ) -> Mapping[str, object] | None:
        canonical_id = canonical_uuid(entity_id)
        if canonical_id is None:
            return None
        key = EntityCacheKey(
            "musicbrainz",
            entity_type,
            canonical_id,
            _RECORDING_SCHEMA_VERSION
            if entity_type == "recording"
            else _WORK_SCHEMA_VERSION
            if entity_type == "work"
            else "v1",
            profile,
        )

        def fetch_and_validate() -> Mapping[str, object] | None:
            try:
                fetcher = self._fetchers[entity_type]
                payload = (
                    fetcher(canonical_id, profile)
                    if entity_type == "recording"
                    or entity_type in {"release", "work"} and profile.includes
                    else fetcher(canonical_id)
                )
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

    def lookup_release(
        self, entity_id: str, profile: EntityFetchProfile = _DEFAULT_FETCH_PROFILE
    ) -> Mapping[str, object] | None:
        return self._lookup("release", entity_id, profile)

    def lookup_release_group(self, entity_id: str) -> Mapping[str, object] | None:
        return self._lookup("release_group", entity_id)

    def lookup_recording(
        self, entity_id: str, profile: EntityFetchProfile = _DEFAULT_FETCH_PROFILE
    ) -> Mapping[str, object] | None:
        return self._lookup("recording", entity_id, profile)

    def lookup_work(
        self, entity_id: str, profile: EntityFetchProfile = _DEFAULT_FETCH_PROFILE
    ) -> Mapping[str, object] | None:
        return self._lookup("work", entity_id, profile)

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
        defaults = self.supported_fields | {"artist_languages"}
        self.enabled_fields = set(defaults if enabled_fields is None else enabled_fields)

    def get_semantic_evidence(self, context: TrackEnrichmentContext) -> SemanticEvidenceBundle:
        return self.get_enrichment(context).semantic

    def get_enrichment(self, context: TrackEnrichmentContext) -> MusicBrainzTrackEnrichment:
        if not self.enabled_fields:
            return MusicBrainzTrackEnrichment()
        recording_id = _context_mbid(context.external_ids, "musicbrainz.recording")
        if recording_id is None:
            return MusicBrainzTrackEnrichment()
        payload = self.client.lookup_recording(
            recording_id, _recording_profile(self.enabled_fields)
        )
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
        for field, value in _recording_credit_values(payload, recording_id).items():
            if field in self.enabled_fields:
                evidence.append(_recording_evidence(field, value, recording_id))
        if (
            "structured_artist_credits" in self.enabled_fields
            and (
                artist_credit := artist_credit_from_payload(
                    payload, EntityKind.RECORDING, recording_id
                )
            )
        ):
            evidence.append(
                _recording_evidence("structured_artist_credits", artist_credit, recording_id)
            )
        work_credit_fields = {"composers", "lyricists", "arrangers"}
        work_fields = {"lyrics_languages", "artist_languages", "iswcs"} | work_credit_fields
        if self.enabled_fields & work_fields:
            work_ids = (
                tuple(reference.mbid for reference in work_references)
                if self.enabled_fields & {"works", "iswcs"}
                else _related_ids(payload, "work")
            )
            if not work_ids:
                work_ids = _related_ids(payload, "work")
            for work_id in work_ids:
                try:
                    work = self.client.lookup_work(
                        work_id,
                        EntityFetchProfile(("artist-rels",))
                        if self.enabled_fields & work_credit_fields
                        else _DEFAULT_FETCH_PROFILE,
                    )
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
                for field, value in _work_credit_values(work, work_id).items():
                    if field in self.enabled_fields:
                        evidence.append(_work_evidence(field, value, work_id, recording_id))
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
    relations = _relation_rows(payload, "work")
    values: list[WorkReference] = []
    for relation in relations:
        work = relation.get("work")
        if not isinstance(work, Mapping):
            continue
        work_id = canonical_uuid(work.get("id"))
        relation_type = _text(relation.get("type"))
        type_id_present = "type_id" in relation or "type-id" in relation
        raw_type_id = (
            relation.get("type_id")
            if "type_id" in relation
            else relation.get("type-id")
        )
        type_id = canonical_uuid(raw_type_id)
        if work_id is None or not _relationship_matches(
            type_id,
            relation_type,
            _PERFORMANCE_TYPE_ID,
            "performance",
            type_id_present=type_id_present,
        ):
            continue
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
        ordering = relation.get("ordering_key", relation.get("ordering-key"))
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
    relations = _relation_rows(payload, "place")
    values = []
    for relation in relations:
        relation_type = _text(relation.get("type"))
        type_id_present = "type_id" in relation or "type-id" in relation
        raw_type_id = (
            relation.get("type_id")
            if "type_id" in relation
            else relation.get("type-id")
        )
        type_id = canonical_uuid(raw_type_id)
        if not _relationship_matches(
            type_id,
            relation_type,
            _RECORDED_AT_TYPE_ID,
            "recorded at",
            type_id_present=type_id_present,
        ):
            continue
        begin = parse_partial_date(relation.get("begin"))
        end = parse_partial_date(relation.get("end"))
        if begin is not None and begin == end:
            values.append(begin)
    return tuple(sorted(set(values), key=str))


def _recording_profile(enabled_fields: Collection[str]) -> EntityFetchProfile:
    includes: set[str] = set()
    fields = set(enabled_fields)
    if fields & {"genres", "moods"}:
        includes.update({"genres", "tags"})
    if "isrcs" in fields:
        includes.add("isrcs")
    if fields & {"works", "iswcs", "lyrics_languages", "artist_languages"}:
        includes.add("work-rels")
    if "recording_date" in fields:
        includes.add("place-rels")
    if fields & {
        "producers",
        "arrangers",
        "conductors",
        "performers",
        "featured_artists",
        "structured_artist_credits",
    }:
        includes.add("artist-rels")
    if fields & {"composers", "lyricists", "arrangers"}:
        includes.add("work-rels")
    return EntityFetchProfile(tuple(includes))


_RECORDING_CREDIT_TYPES = {
    "5c0ceac3-feb4-41f0-868d-dc06f6e27fc0": ("producer", CreditRole.PRODUCER),
    "22661fb8-cdb7-4f67-8385-b2a8be6c9f0d": ("arranger", CreditRole.ARRANGER),
    "234670ce-5f22-4fd0-921b-ef1662695c5d": ("conductor", CreditRole.CONDUCTOR),
    "628a9658-f54c-4142-b0c0-95f031b544da": ("performer", CreditRole.PERFORMER),
    "59054b12-01ac-43ee-a618-285fd397e461": ("instrument", CreditRole.PERFORMER),
    "0fdbe3c6-7700-4a31-ae54-b53f06ae1cfa": ("vocal", CreditRole.PERFORMER),
    "3b6616c5-88ba-4341-b4ee-81ce1e6d7ebb": (
        "performing orchestra",
        CreditRole.PERFORMER,
    ),
}
_WORK_CREDIT_TYPES = {
    "d59d99ea-23d4-4a80-b066-edca32ee158f": ("composer", CreditRole.COMPOSER),
    "3e48faba-ec01-47fd-8e89-30e81161661c": ("lyricist", CreditRole.LYRICIST),
    "d3fd781c-5894-47e2-8c12-86cc0e2c8d08": ("arranger", CreditRole.ARRANGER),
}
_RELEASE_CREDIT_TYPES = {
    "8bf377ba-8d71-4ecc-97f2-7bb2d8a2a75f": ("producer", CreditRole.PRODUCER),
    "9ae9e4d0-f26b-42fb-ab5c-1149a47cf83b": ("conductor", CreditRole.CONDUCTOR),
    "888a2320-52e4-4fe8-a8a0-7a4c8dfde167": ("performer", CreditRole.PERFORMER),
    "67555849-61e5-455b-96e3-29733f0115f5": ("instrument", CreditRole.PERFORMER),
    "eb10f8a0-0f4c-4dce-aa47-87bcb2bc42f3": ("vocal", CreditRole.PERFORMER),
    "23a2e2e7-81ca-4865-8d05-2243848a77bf": (
        "performing orchestra",
        CreditRole.PERFORMER,
    ),
}
_ROLE_FIELDS = {
    CreditRole.COMPOSER: "composers",
    CreditRole.LYRICIST: "lyricists",
    CreditRole.PRODUCER: "producers",
    CreditRole.ARRANGER: "arrangers",
    CreditRole.CONDUCTOR: "conductors",
    CreditRole.PERFORMER: "performers",
    CreditRole.FEATURED_ARTIST: "featured_artists",
    CreditRole.GUEST_ARTIST: "featured_artists",
}


def _recording_credit_values(
    payload: Mapping[str, object], source_entity_id: str
) -> dict[str, tuple[CreditReference, ...]]:
    return _credit_values(
        payload,
        EntityKind.RECORDING,
        source_entity_id,
        _RECORDING_CREDIT_TYPES,
    )


def _work_credit_values(
    payload: Mapping[str, object], source_entity_id: str
) -> dict[str, tuple[CreditReference, ...]]:
    return _credit_values(payload, EntityKind.WORK, source_entity_id, _WORK_CREDIT_TYPES)


def release_credit_values(
    payload: Mapping[str, object], source_entity_id: str
) -> dict[str, tuple[CreditReference, ...]]:
    return _credit_values(
        payload,
        EntityKind.RELEASE,
        source_entity_id,
        _RELEASE_CREDIT_TYPES,
    )


def _credit_values(
    payload: Mapping[str, object],
    scope: EntityKind,
    source_entity_id: str,
    accepted_types: Mapping[str, tuple[str, CreditRole]],
) -> dict[str, tuple[CreditReference, ...]]:
    grouped: dict[str, list[CreditReference]] = {}
    for relation in _relation_rows(payload, "artist"):
        relation_type = _text(relation.get("type"))
        type_id_present = "type_id" in relation or "type-id" in relation
        raw_type_id = relation.get("type_id", relation.get("type-id"))
        relation_type_id = canonical_uuid(raw_type_id) if type_id_present else None
        accepted = accepted_types.get(relation_type_id) if relation_type_id is not None else None
        if type_id_present and accepted is None:
            continue
        if accepted is None:
            accepted = next(
                (
                    value
                    for value in accepted_types.values()
                    if relation_type.casefold() == value[0]
                ),
                None,
            )
        if accepted is None or relation_type.casefold() != accepted[0]:
            continue
        artist = relation.get("artist")
        if not isinstance(artist, Mapping):
            continue
        artist_id = canonical_uuid(artist.get("id"))
        artist_name = _text(artist.get("name"))
        if artist_id is None or not artist_name:
            continue
        attributes = tuple(
            value.strip()
            for value in relation.get("attributes", ())
            if isinstance(value, str) and value.strip()
        ) if _is_sequence(relation.get("attributes", ())) else ()
        try:
            party = CreditParty(
                artist_name,
                artist_id,
                _text(relation.get("target_credit", relation.get("target-credit"))) or None,
            )
            instruments = _relation_instruments(relation, accepted[1])
            references = [
                CreditReference(
                    party,
                    accepted[1],
                    scope,
                    instrument=instrument,
                    relation_type=relation_type,
                    relation_type_id=relation_type_id,
                    source_entity_id=source_entity_id,
                    attributes=attributes,
                    direction=_text(relation.get("direction")) or None,
                    ordering_key=_non_negative_int(
                        relation.get("ordering_key", relation.get("ordering-key"))
                    ),
                )
                for instrument in instruments
            ]
        except (TypeError, ValueError):
            continue
        grouped.setdefault(_ROLE_FIELDS[accepted[1]], []).extend(references)
        if scope in {EntityKind.RECORDING, EntityKind.RELEASE} and any(
            attribute.casefold() == "guest" for attribute in attributes
        ):
            grouped.setdefault("featured_artists", []).append(
                CreditReference(
                    party,
                    CreditRole.GUEST_ARTIST,
                    scope,
                    relation_type=relation_type,
                    relation_type_id=relation_type_id,
                    source_entity_id=source_entity_id,
                    attributes=attributes,
                    direction=_text(relation.get("direction")) or None,
                )
            )
    return {
        field: canonical_credit_references(references)
        for field, references in grouped.items()
        if references
    }


def _relation_instruments(
    relation: Mapping[str, object], role: CreditRole
) -> tuple[str | None, ...]:
    if role is not CreditRole.PERFORMER:
        return (None,)
    relation_type = _text(relation.get("type")).casefold()
    values = relation.get("attribute_values", relation.get("attribute-values"))
    instruments: list[str] = []
    if isinstance(values, Mapping):
        for value in values.values():
            text = _text(value)
            if text:
                _append_unique(instruments, text)
    if instruments:
        return tuple(instruments)
    if relation_type == "vocal":
        return ("vocals",)
    return (None,)


def artist_credit_from_payload(
    payload: Mapping[str, object], scope: EntityKind, source_entity_id: str
) -> ArtistCredit | None:
    rows = payload.get("artist_credit", payload.get("artist-credit"))
    if not _is_sequence(rows):
        return None
    nodes: list[ArtistCreditNode] = []
    for position, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return None
        artist = row.get("artist")
        if not isinstance(artist, Mapping):
            return None
        artist_id = canonical_uuid(artist.get("id"))
        canonical_name = _text(artist.get("name"))
        credited_name = _text(row.get("name"))
        join_phrase = row.get("joinphrase", "")
        if (
            artist_id is None
            or not canonical_name
            or not credited_name
            or not isinstance(join_phrase, str)
        ):
            return None
        nodes.append(
            ArtistCreditNode(
                artist_id,
                canonical_name,
                credited_name,
                join_phrase,
                position,
            )
        )
    return ArtistCredit(scope, tuple(nodes), source_entity_id) if nodes else None


def _non_negative_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _relation_rows(
    payload: Mapping[str, object], entity_type: str
) -> tuple[Mapping[str, object], ...]:
    normalized = payload.get(f"{entity_type}_relations")
    if _is_sequence(normalized):
        return tuple(row for row in normalized if isinstance(row, Mapping))
    raw = payload.get("relations")
    if not _is_sequence(raw):
        return ()
    return tuple(
        row
        for row in raw
        if isinstance(row, Mapping) and row.get("target-type") == entity_type
    )


def _relationship_matches(
    type_id: str | None,
    relation_type: str,
    expected_type_id: str,
    expected_type: str,
    *,
    type_id_present: bool,
) -> bool:
    if type_id_present:
        return (
            type_id is not None
            and type_id == expected_type_id
            and relation_type.casefold() == expected_type
        )
    return relation_type.casefold() == expected_type

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


def _fetch_release(
    entity_id: str, profile: EntityFetchProfile = _DEFAULT_FETCH_PROFILE
) -> Mapping[str, object]:
    from beetsplug._utils.musicbrainz import MusicBrainzAPI

    includes = ("labels", "media", "genres", "tags", "recordings", "artist-credits")
    return MusicBrainzAPI().get_release(entity_id, includes=[*includes, *profile.includes])


def _fetch_release_group(entity_id: str) -> Mapping[str, object]:
    return _fetch_generic("release-group", entity_id, [])


def _fetch_recording(
    entity_id: str, profile: EntityFetchProfile = _DEFAULT_FETCH_PROFILE
) -> Mapping[str, object]:
    from beetsplug._utils.musicbrainz import MusicBrainzAPI

    return MusicBrainzAPI().get_recording(entity_id, includes=list(profile.includes))


def _fetch_work(
    entity_id: str, profile: EntityFetchProfile = _DEFAULT_FETCH_PROFILE
) -> Mapping[str, object]:
    from beetsplug._utils.musicbrainz import MusicBrainzAPI

    return MusicBrainzAPI().get_work(entity_id, includes=list(profile.includes))


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
