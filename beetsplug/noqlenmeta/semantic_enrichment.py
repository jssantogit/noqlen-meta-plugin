"""Shared read-only orchestration for semantic metadata enrichment."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from beetsplug.noqlenmeta.changeplan import ChangePlan
from beetsplug.noqlenmeta.domain import (
    MetadataCandidate,
    SemanticCategory,
    SemanticEvidenceBundle,
    SemanticTagEvidence,
)
from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.genre_resolution import GenreSettings, resolve_genres
from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
)
from beetsplug.noqlenmeta.providers import ProviderError
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.resolver import ResolutionPolicy
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
    policy: ResolutionPolicy,
    musicbrainz_release: BundleCollector | None = None,
    musicbrainz_tracks: Sequence[BundleCollector] = (),
    musicbrainz_artists: Sequence[BundleCollector] = (),
    discogs_metadata: Sequence[MetadataCandidate] = (),
    lastfm_track: BundleCollector | None = None,
    lastfm_release: BundleCollector | None = None,
    lastfm_artist: BundleCollector | None = None,
    genre_settings: GenreSettings | None = None,
    max_moods: int = 1,
) -> SemanticEnrichmentResult:
    """Collect, normalize, and resolve semantic evidence without mutating targets."""
    enabled = {
        field
        for field in set(enabled_fields) & set(_FIELDS)
        if policy.is_field_enabled(field)
    }
    genre_settings = genre_settings or GenreSettings()
    thresholds = {
        field: policy.confidence_threshold(field) or 0.0 for field in enabled
    }
    bundles: list[SemanticEvidenceBundle] = []
    unavailable: set[str] = set()

    def collect(
        collector: BundleCollector, capabilities: set[str], provider: str
    ) -> None:
        eligible_capabilities = {
            field
            for field in capabilities
            if _provider_authorized(policy, field, provider)
        }
        if not enabled & eligible_capabilities:
            return
        try:
            bundle = _eligible_bundle(collector(), thresholds, policy, provider)
            bundles.append(bundle)
            unavailable.update(enabled & bundle.unavailable_fields)
        except ProviderError:
            unavailable.update(enabled & eligible_capabilities)

    if enabled & {"genres", "moods", "lyrics_languages", "artist_languages"}:
        for collector in musicbrainz_tracks:
            collect(
                collector,
                {"genres", "moods", "lyrics_languages", "artist_languages"},
                "musicbrainz",
            )
    if musicbrainz_release is not None and enabled & {"genres", "styles", "moods"}:
        collect(musicbrainz_release, {"genres", "styles", "moods"}, "musicbrainz")
    if enabled & {"genres", "moods", "artist_countries", "artist_areas"}:
        for collector in musicbrainz_artists:
            collect(
                collector,
                {"genres", "moods", "artist_countries", "artist_areas"},
                "musicbrainz",
            )

    structured_genres, structured_styles = _discogs_semantics(
        discogs_metadata, genre_settings, thresholds, policy
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

        def safe(
            collector: BundleCollector | None, capabilities: set[str], provider: str
        ) -> BundleCollector:
            eligible_capabilities = {
                field
                for field in capabilities
                if _provider_authorized(policy, field, provider)
            }
            if collector is None or not enabled & eligible_capabilities:
                return empty

            def wrapped() -> SemanticEvidenceBundle:
                try:
                    return _eligible_bundle(collector(), thresholds, policy, provider)
                except ProviderError:
                    unavailable.update(enabled & eligible_capabilities)
                    return SemanticEvidenceBundle()

            return wrapped

        fallback = collect_scoped_semantic_fallback(
            enabled & {"genres", "styles", "moods"},
            initially_resolved,
            safe(lastfm_track, {"genres", "styles", "moods"}, "lastfm"),
            safe(lastfm_release, {"genres", "styles", "moods"}, "lastfm"),
            safe(lastfm_artist, {"genres", "styles", "moods"}, "lastfm"),
            min_confidence=thresholds,
        )
        bundles.extend(fallback)
        unavailable.update(
            field
            for bundle in fallback
            for field in bundle.unavailable_fields
            if field in enabled
        )
        genres.extend(item for bundle in fallback for item in bundle.genres)
        tags.extend(item for bundle in fallback for item in bundle.tags)

    values: dict[str, tuple[str, ...]] = {}
    provenance: dict[str, tuple[str, ...]] = {}
    winners: dict[
        str, tuple[MetadataCandidate | GenreEvidence | SemanticTagEvidence, ...]
    ] = {}
    if "genres" in enabled:
        resolved = resolve_genres(
            genres,
            settings=genre_settings,
            min_confidence=thresholds.get("genres", 0.0),
        )
        if resolved.genres:
            values["genres"] = resolved.genres
            provenance["genres"] = _provenance(resolved.evidence)
            winners["genres"] = tuple(resolved.evidence)
    if "styles" in enabled:
        styles = resolve_styles(
            structured_styles,
            tags,
            min_confidence=thresholds.get("styles", 0.0),
        )
        if styles:
            values["styles"] = styles
            style_evidence: tuple[
                MetadataCandidate | GenreEvidence | SemanticTagEvidence, ...
            ] = tuple(
                candidate
                for candidate in discogs_metadata
                if candidate.field == "styles"
                and candidate.provider.casefold() == "discogs"
                and _provider_authorized(policy, "styles", candidate.provider)
                and candidate.confidence >= thresholds.get("styles", 0.0)
            )
            if not style_evidence:
                style_evidence = tuple(
                    item
                    for item in tags
                    if item.category is SemanticCategory.STYLE
                    and item.canonical_term in styles
                )
            provenance["styles"] = _provenance(style_evidence)
            winners["styles"] = style_evidence
    if "moods" in enabled:
        moods = resolve_moods(
            tags,
            max_moods,
            min_confidence=thresholds.get("moods", 0.0),
        )
        if moods:
            values["moods"] = moods
            mood_evidence = tuple(
                item
                for item in tags
                if item.category is SemanticCategory.MOOD
                and item.canonical_term in moods
            )
            provenance["moods"] = _provenance(mood_evidence)
            winners["moods"] = mood_evidence

    track_language_candidates = tuple(
        candidate
        for bundle in bundles
        for candidate in bundle.metadata
        if candidate.field == "lyrics_languages"
    )
    lyrics_candidates = tuple(
        candidate
        for candidate in track_language_candidates
        if _provider_authorized(policy, "lyrics_languages", candidate.provider)
        and candidate.confidence >= thresholds.get("lyrics_languages", 0.0)
    )
    artist_language_candidates = tuple(
        candidate
        for candidate in track_language_candidates
        if _provider_authorized(policy, "artist_languages", candidate.provider)
        and candidate.confidence >= thresholds.get("artist_languages", 0.0)
    )
    track_languages = tuple(
        candidate.value
        for candidate in lyrics_candidates
        if isinstance(candidate.value, tuple)
    )
    if "lyrics_languages" in enabled and track_languages:
        values["lyrics_languages"] = _ordered_union(track_languages)
        provenance["lyrics_languages"] = ("musicbrainz work",)
        winners["lyrics_languages"] = lyrics_candidates
    artist_track_languages = tuple(
        candidate.value
        for candidate in artist_language_candidates
        if isinstance(candidate.value, tuple)
    )
    if "artist_languages" in enabled and artist_track_languages:
        values["artist_languages"] = derive_artist_languages(
            tuple(
                (index, value)
                for index, value in enumerate(artist_track_languages, 1)
            )
        )
        provenance["artist_languages"] = ("current-target musicbrainz works",)
        winners["artist_languages"] = artist_language_candidates
    for field in ("artist_countries", "artist_areas"):
        field_candidates = tuple(
            candidate
            for bundle in bundles
            for candidate in bundle.metadata
            if candidate.field == field
            and _provider_authorized(policy, field, candidate.provider)
            and candidate.confidence >= thresholds.get(field, 0.0)
        )
        field_values = tuple(
            candidate.value
            for candidate in field_candidates
            if isinstance(candidate.value, tuple)
        )
        if field in enabled and field_values:
            values[field] = _ordered_union(field_values)
            provenance[field] = ("musicbrainz artist area",)
            winners[field] = field_candidates

    candidates: list[MetadataCandidate] = []
    outcomes: dict[str, SemanticFieldOutcome] = {}
    for field in _FIELDS:
        if field not in enabled:
            continue
        value = values.get(field)
        if value:
            if field in unavailable:
                status = SemanticFieldStatus.UNAVAILABLE
                reason = "partial semantic evidence retained; supporting provider lookup failed"
            else:
                status = SemanticFieldStatus.RESOLVED
                reason = "semantic evidence resolved safely"
            provider, confidence, source_id, source_url = _winner_details(
                winners.get(field, ())
            )
            candidates.append(
                MetadataCandidate(
                    field,
                    value,
                    provider,
                    confidence,
                    source_id,
                    source_url,
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


def reconcile_semantic_outcomes(
    outcomes: Mapping[str, SemanticFieldOutcome],
    plan: ChangePlan,
    target_blocker_fields: Collection[str] = (),
) -> Mapping[str, SemanticFieldOutcome]:
    """Reconcile collection outcomes with resolver review and target capability."""
    conflicts = {
        decision.field for decision in plan.reviews if decision.selected is None
    }
    blockers = set(target_blocker_fields)
    reconciled: dict[str, SemanticFieldOutcome] = {}
    for field, outcome in outcomes.items():
        if field in blockers:
            outcome = SemanticFieldOutcome(
                field,
                SemanticFieldStatus.BLOCKED,
                outcome.value,
                outcome.provenance,
                "lossless application is unavailable",
            )
        elif field in conflicts and outcome.status is not SemanticFieldStatus.UNAVAILABLE:
            outcome = SemanticFieldOutcome(
                field,
                SemanticFieldStatus.CONFLICT,
                outcome.value,
                outcome.provenance,
                "eligible evidence requires resolver review",
            )
        reconciled[field] = outcome
    return MappingProxyType(reconciled)


def _discogs_semantics(
    candidates: Sequence[MetadataCandidate],
    settings: GenreSettings,
    min_confidence: Mapping[str, float],
    policy: ResolutionPolicy,
) -> tuple[tuple[GenreEvidence, ...], tuple[str, ...]]:
    genres: list[GenreEvidence] = []
    styles: tuple[str, ...] = ()
    for candidate in candidates:
        if candidate.provider.casefold() != "discogs" or not isinstance(candidate.value, tuple):
            continue
        style_eligible = (
            candidate.field == "styles"
            and _provider_authorized(policy, "styles", candidate.provider)
            and candidate.confidence >= min_confidence.get("styles", 0.0)
        )
        if style_eligible:
            styles = _ordered_union((candidate.value,))
        if candidate.field not in {"genres", "styles"}:
            continue
        if not _provider_authorized(policy, "genres", candidate.provider):
            continue
        if candidate.confidence < min_confidence.get("genres", 0.0):
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


def _eligible_bundle(
    bundle: SemanticEvidenceBundle,
    min_confidence: Mapping[str, float],
    policy: ResolutionPolicy,
    provider: str,
) -> SemanticEvidenceBundle:
    categories = {
        SemanticCategory.GENRE: "genres",
        SemanticCategory.STYLE: "styles",
        SemanticCategory.MOOD: "moods",
    }
    return SemanticEvidenceBundle(
        metadata=bundle.metadata,
        genres=tuple(
            item
            for item in bundle.genres
            if _provider_authorized(policy, "genres", item.provider)
            and item.confidence >= min_confidence.get("genres", 0.0)
        ),
        tags=tuple(
            item
            for item in bundle.tags
            if (field := categories.get(item.category)) is None
            or (
                _provider_authorized(policy, field, item.provider)
                and item.confidence >= min_confidence.get(field, 0.0)
            )
        ),
        unavailable_fields=frozenset(
            field
            for field in bundle.unavailable_fields
            if field in min_confidence and _provider_authorized(policy, field, provider)
        ),
    )


def _provider_authorized(
    policy: ResolutionPolicy, field: str, provider: str
) -> bool:
    return (
        policy.is_provider_enabled(provider)
        and policy.authority_rank(field, provider) is not None
    )


def _winner_details(
    evidence: Sequence[MetadataCandidate | GenreEvidence | SemanticTagEvidence],
) -> tuple[str, float, str, str | None]:
    if not evidence:
        raise ValueError("resolved semantic field must retain supporting evidence")
    winner = max(evidence, key=lambda item: item.confidence)
    provider = winner.provider
    confidence = winner.confidence
    source_id = winner.source_id
    source_url = winner.source_url
    return provider, confidence, source_id, source_url
