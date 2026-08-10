"""Deterministic pure genre resolution from normalized evidence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from math import isfinite

from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
    GenreTaxonomy,
)
from beetsplug.noqlenmeta.providers.specs import ProviderScope

_SCOPE_RANK = {
    ProviderScope.TRACK: 0,
    ProviderScope.RELEASE: 1,
    ProviderScope.ARTIST: 2,
}
_KIND_RANK = {
    GenreEvidenceKind.GENRE: 0,
    GenreEvidenceKind.PROMOTED_STYLE: 0,
    GenreEvidenceKind.COMMUNITY_TAG: 1,
}


@dataclass(frozen=True, slots=True)
class GenreSettings:
    num_genres: int = 1
    promote_styles: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.num_genres, bool) or not isinstance(self.num_genres, int):
            raise TypeError("num_genres must be an integer")
        if not 1 <= self.num_genres <= 10:
            raise ValueError("num_genres must be between 1 and 10")
        if not isinstance(self.promote_styles, bool):
            raise TypeError("promote_styles must be a boolean")


@dataclass(frozen=True, slots=True)
class GenreResolution:
    genres: tuple[str, ...]
    evidence: tuple[GenreEvidence, ...]
    explanation: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _GenreProfile:
    canonical_name: str
    broad: bool
    evidence: tuple[GenreEvidence, ...]

    @property
    def sort_key(self) -> tuple[object, ...]:
        return (
            min(_SCOPE_RANK[item.scope] for item in self.evidence),
            -len({item.provider.casefold() for item in self.evidence}),
            min(_KIND_RANK[item.kind] for item in self.evidence),
            int(self.broad),
            -max(item.confidence for item in self.evidence),
            -max(item.weight if item.weight is not None else -1 for item in self.evidence),
            self.canonical_name.casefold(),
        )


def _deduplicate(evidence: Sequence[GenreEvidence]) -> tuple[GenreEvidence, ...]:
    grouped: dict[
        tuple[str, str, ProviderScope, GenreEvidenceKind], list[GenreEvidence]
    ] = defaultdict(list)
    for item in evidence:
        key = (item.genre.casefold(), item.provider.casefold(), item.scope, item.kind)
        grouped[key].append(item)

    unique: list[GenreEvidence] = []
    for key in sorted(
        grouped,
        key=lambda value: (value[0], value[1], _SCOPE_RANK[value[2]], value[3].value),
    ):
        rows = grouped[key]
        strongest = min(
            rows,
            key=lambda item: (
                -item.confidence,
                -(item.weight if item.weight is not None else -1),
                item.source_id,
                item.source_url or "",
            ),
        )
        native_weights = [item.weight for item in rows if item.weight is not None]
        if native_weights:
            strongest = replace(strongest, weight=max(native_weights))
        unique.append(strongest)
    return tuple(unique)


def resolve_genres(
    evidence: Sequence[GenreEvidence],
    *,
    settings: GenreSettings,
    taxonomy: GenreTaxonomy = DEFAULT_GENRE_TAXONOMY,
    min_confidence: float = 0.0,
) -> GenreResolution:
    """Select independently evidenced genres using discrete ranking signals."""
    if (
        isinstance(min_confidence, bool)
        or not isinstance(min_confidence, (int, float))
        or not isfinite(min_confidence)
        or not 0.0 <= min_confidence <= 1.0
    ):
        raise ValueError("min_confidence must be a finite number between 0.0 and 1.0")
    if not isinstance(settings, GenreSettings):
        raise TypeError("settings must be GenreSettings")

    normalized: list[GenreEvidence] = []
    broad_by_name: dict[str, bool] = {}
    for item in evidence:
        if not isinstance(item, GenreEvidence):
            raise TypeError("evidence must contain GenreEvidence values")
        classification = taxonomy.classify(item.genre)
        if (
            classification.category is not GenreSemanticCategory.GENRE
            or item.confidence < min_confidence
        ):
            continue
        canonical = classification.canonical_name
        normalized.append(replace(item, genre=canonical))
        broad_by_name[canonical.casefold()] = classification.broad

    unique = _deduplicate(normalized)
    by_genre: dict[str, list[GenreEvidence]] = defaultdict(list)
    names: dict[str, str] = {}
    for item in unique:
        key = item.genre.casefold()
        names[key] = item.genre
        by_genre[key].append(item)

    profiles = sorted(
        (
            _GenreProfile(names[key], broad_by_name[key], tuple(rows))
            for key, rows in by_genre.items()
        ),
        key=lambda profile: profile.sort_key,
    )
    selected = profiles[: settings.num_genres]
    selected_evidence: list[GenreEvidence] = []
    explanation: list[str] = []
    for profile in selected:
        ordered = sorted(
            profile.evidence,
            key=lambda item: (
                item.provider.casefold(),
                _SCOPE_RANK[item.scope],
                item.kind.value,
                item.source_id,
            ),
        )
        selected_evidence.extend(ordered)
        for item in ordered:
            explanation.append(
                f"{profile.canonical_name}: {item.provider.casefold()} "
                f"{item.kind.value.replace('_', ' ')}"
            )
    return GenreResolution(
        tuple(profile.canonical_name for profile in selected),
        tuple(selected_evidence),
        tuple(explanation),
    )
