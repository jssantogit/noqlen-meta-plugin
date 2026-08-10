"""Shared read-only orchestration for semantic metadata enrichment."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from beetsplug.noqlenmeta.domain import (
    MetadataCandidate,
    SemanticCategory,
    SemanticEvidenceBundle,
)
from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.genre_resolution import GenreSettings, resolve_genres
from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
)
from beetsplug.noqlenmeta.providers import ProviderError
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.semantic_resolution import (
    collect_scoped_semantic_fallback,
    resolve_moods,
    resolve_styles,
)

BundleCollector = Callable[[], SemanticEvidenceBundle]
_FIELDS = (
    "genres",
    "styles",
    "moods",
    "lyrics_languages",
    "artist_languages",
    "artist_countries",
    "artist_areas",
)


class SemanticFieldStatus(Enum):
    RESOLVED = "resolved"
    NO_EVIDENCE = "no-evidence"
    UNAVAILABLE = "unavailable"
    CONFLICT = "conflict"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SemanticFieldOutcome:
    field: str
    status: SemanticFieldStatus
    value: tuple[str, ...] | None = None
    provenance: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True, slots=True)
class SemanticEnrichmentResult:
    candidates: tuple[MetadataCandidate, ...]
    outcomes: Mapping[str, SemanticFieldOutcome]

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "outcomes", MappingProxyType(dict(self.outcomes)))


def derive_artist_languages(
    track_languages: Sequence[tuple[int, Sequence[str]]],
) -> tuple[str, ...]:
    """Derive contextual artist languages only from current-target track rows."""
    values: list[str] = []
    for _, languages in track_languages:
        for language in languages:
            if isinstance(language, str) and language not in values:
                values.append(language)
    return tuple(values)


def collect_semantic_enrichment(
    enabled_fields: Collection[str],
    *,
    musicbrainz_release: BundleCollector | None = None,
    musicbrainz_tracks: Sequence[BundleCollector] = (),
    musicbrainz_artists: Sequence[BundleCollector] = (),
    discogs_metadata: Sequence[MetadataCandidate] = (),
    lastfm_track: BundleCollector | None = None,
    lastfm_release: BundleCollector | None = None,
    lastfm_artist: BundleCollector | None = None,
    genre_settings: GenreSettings | None = None,
    max_moods: int = 1,
    conflict_fields: Collection[str] = (),
    blocked_fields: Collection[str] = (),
) -> SemanticEnrichmentResult:
    """Collect, normalize, and resolve semantic evidence without mutating targets."""
    enabled = set(enabled_fields) & set(_FIELDS)
    genre_settings = genre_settings or GenreSettings()
    bundles: list[SemanticEvidenceBundle] = []
    unavailable: set[str] = set()

    def collect(collector: BundleCollector, capabilities: set[str]) -> None:
        try:
            bundles.append(collector())
        except ProviderError:
            unavailable.update(enabled & capabilities)

    if musicbrainz_release is not None and enabled & {"genres", "styles", "moods"}:
        collect(musicbrainz_release, {"genres", "styles", "moods"})
    if enabled & {"genres", "moods", "lyrics_languages", "artist_languages"}:
        for collector in musicbrainz_tracks:
            collect(
                collector,
                {"genres", "moods", "lyrics_languages", "artist_languages"},
            )
    if enabled & {"genres", "moods", "artist_countries", "artist_areas"}:
        for collector in musicbrainz_artists:
            collect(collector, {"genres", "moods", "artist_countries", "artist_areas"})

    structured_genres, structured_styles = _discogs_semantics(
        discogs_metadata, genre_settings
    )
    genres = [item for bundle in bundles for item in bundle.genres]
    genres.extend(structured_genres)
    tags = [item for bundle in bundles for item in bundle.tags]

    initially_resolved = set()
    if genres:
        initially_resolved.add("genres")
    if structured_styles or any(item.category is SemanticCategory.STYLE for item in tags):
        initially_resolved.add("styles")
    if any(item.category is SemanticCategory.MOOD for item in tags):
        initially_resolved.add("moods")

    if any((lastfm_track, lastfm_release, lastfm_artist)):
        def empty() -> SemanticEvidenceBundle:
            return SemanticEvidenceBundle()

        def safe(collector: BundleCollector | None, capabilities: set[str]) -> BundleCollector:
            if collector is None:
                return empty

            def wrapped() -> SemanticEvidenceBundle:
                try:
                    return collector()
                except ProviderError:
                    unavailable.update(enabled & capabilities)
                    return SemanticEvidenceBundle()

            return wrapped

        fallback = collect_scoped_semantic_fallback(
            enabled & {"genres", "styles", "moods"},
            initially_resolved,
            safe(lastfm_track, {"genres", "styles", "moods"}),
            safe(lastfm_release, {"genres", "styles", "moods"}),
            safe(lastfm_artist, {"genres", "styles", "moods"}),
        )
        bundles.extend(fallback)
        genres.extend(item for bundle in fallback for item in bundle.genres)
        tags.extend(item for bundle in fallback for item in bundle.tags)

    values: dict[str, tuple[str, ...]] = {}
    provenance: dict[str, tuple[str, ...]] = {}
    if "genres" in enabled:
        resolved = resolve_genres(genres, settings=genre_settings)
        if resolved.genres:
            values["genres"] = resolved.genres
            provenance["genres"] = _provenance(resolved.evidence)
    if "styles" in enabled:
        styles = resolve_styles(structured_styles, tags)
        if styles:
            values["styles"] = styles
            provenance["styles"] = (
                ("discogs",) if structured_styles else _provenance(tags, SemanticCategory.STYLE)
            )
    if "moods" in enabled:
        moods = resolve_moods(tags, max_moods)
        if moods:
            values["moods"] = moods
            provenance["moods"] = _provenance(tags, SemanticCategory.MOOD)

    track_languages = tuple(
        value
        for bundle in bundles
        for value in _metadata_values(bundle, "lyrics_languages")
    )
    if "lyrics_languages" in enabled and track_languages:
        values["lyrics_languages"] = _ordered_union(track_languages)
        provenance["lyrics_languages"] = ("musicbrainz work",)
    if "artist_languages" in enabled and track_languages:
        values["artist_languages"] = derive_artist_languages(
            tuple((index, value) for index, value in enumerate(track_languages, 1))
        )
        provenance["artist_languages"] = ("current-target musicbrainz works",)
    for field in ("artist_countries", "artist_areas"):
        field_values = tuple(
            value for bundle in bundles for value in _metadata_values(bundle, field)
        )
        if field in enabled and field_values:
            values[field] = _ordered_union(field_values)
            provenance[field] = ("musicbrainz artist area",)

    conflicts = set(conflict_fields)
    blockers = set(blocked_fields)
    candidates: list[MetadataCandidate] = []
    outcomes: dict[str, SemanticFieldOutcome] = {}
    for field in _FIELDS:
        if field not in enabled:
            continue
        value = values.get(field)
        if field in blockers:
            status, reason = SemanticFieldStatus.BLOCKED, "lossless application is unavailable"
        elif field in conflicts:
            status, reason = SemanticFieldStatus.CONFLICT, "eligible evidence has no safe winner"
        elif value:
            status, reason = SemanticFieldStatus.RESOLVED, "semantic evidence resolved safely"
            candidates.append(
                MetadataCandidate(
                    field,
                    value,
                    (
                        "musicbrainz"
                        if field
                        in {
                            "lyrics_languages",
                            "artist_languages",
                            "artist_countries",
                            "artist_areas",
                        }
                        else provenance.get(field, ("musicbrainz",))[0].split()[0]
                    ),
                    0.95,
                    f"semantic:{field}",
                )
            )
        elif field in unavailable:
            status, reason = SemanticFieldStatus.UNAVAILABLE, "required provider lookup failed"
        else:
            status, reason = SemanticFieldStatus.NO_EVIDENCE, "no eligible evidence"
        outcomes[field] = SemanticFieldOutcome(
            field, status, value, provenance.get(field, ()), reason
        )
    return SemanticEnrichmentResult(tuple(candidates), outcomes)


def _discogs_semantics(
    candidates: Sequence[MetadataCandidate], settings: GenreSettings
) -> tuple[tuple[GenreEvidence, ...], tuple[str, ...]]:
    genres: list[GenreEvidence] = []
    styles: tuple[str, ...] = ()
    for candidate in candidates:
        if candidate.provider.casefold() != "discogs" or not isinstance(candidate.value, tuple):
            continue
        if candidate.field == "styles":
            styles = _ordered_union((candidate.value,))
        if candidate.field not in {"genres", "styles"}:
            continue
        if candidate.field == "styles" and not settings.promote_styles:
            continue
        kind = (
            GenreEvidenceKind.PROMOTED_STYLE
            if candidate.field == "styles"
            else GenreEvidenceKind.GENRE
        )
        for value in candidate.value:
            classification = DEFAULT_GENRE_TAXONOMY.classify(value)
            if classification.category is GenreSemanticCategory.GENRE:
                genres.append(
                    GenreEvidence(
                        classification.canonical_name,
                        "discogs",
                        ProviderScope.RELEASE,
                        kind,
                        candidate.confidence,
                        candidate.source_id,
                        candidate.source_url,
                    )
                )
    return tuple(genres), styles


def _metadata_values(
    bundle: SemanticEvidenceBundle, field: str
) -> tuple[tuple[str, ...], ...]:
    return tuple(
        candidate.value
        for candidate in bundle.metadata
        if candidate.field == field and isinstance(candidate.value, tuple)
    )


def _ordered_union(rows: Sequence[Sequence[str]]) -> tuple[str, ...]:
    values: list[str] = []
    for row in rows:
        for value in row:
            if value not in values:
                values.append(value)
    return tuple(values)


def _provenance(
    evidence: Sequence[object], category: SemanticCategory | None = None
) -> tuple[str, ...]:
    values: list[str] = []
    for item in evidence:
        if category is not None and getattr(item, "category", None) is not category:
            continue
        provider = getattr(item, "provider", None)
        if isinstance(provider, str) and provider not in values:
            values.append(provider)
    return tuple(values)
