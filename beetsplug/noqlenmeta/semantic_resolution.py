"""Pure field-specific resolution for semantic community evidence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass

from beetsplug.noqlenmeta.domain import (
    SemanticCategory,
    SemanticEvidenceBundle,
    SemanticTagEvidence,
)
from beetsplug.noqlenmeta.providers.specs import ProviderScope

_SCOPE_RANK = {
    ProviderScope.TRACK: 0,
    ProviderScope.RELEASE: 1,
    ProviderScope.ARTIST: 2,
}


def collect_scoped_semantic_fallback(
    requested_fields: Collection[str],
    resolved_fields: Collection[str],
    track: Callable[[], SemanticEvidenceBundle],
    release: Callable[[], SemanticEvidenceBundle],
    artist: Callable[[], SemanticEvidenceBundle],
) -> tuple[SemanticEvidenceBundle, ...]:
    """Collect Track -> Release -> Artist only while requested fields remain unresolved."""
    requested = set(requested_fields) & {"genres", "styles", "moods"}
    unresolved = requested - set(resolved_fields)
    bundles: list[SemanticEvidenceBundle] = []
    for collector in (track, release, artist):
        if not unresolved:
            break
        bundle = _filter_bundle(collector(), unresolved)
        bundles.append(bundle)
        unresolved -= _bundle_fields(bundle)
    return tuple(bundles)


def _bundle_fields(bundle: SemanticEvidenceBundle) -> set[str]:
    fields = {"genres"} if bundle.genres else set()
    if any(item.category is SemanticCategory.STYLE for item in bundle.tags):
        fields.add("styles")
    if any(item.category is SemanticCategory.MOOD for item in bundle.tags):
        fields.add("moods")
    return fields


def _filter_bundle(
    bundle: SemanticEvidenceBundle, fields: Collection[str]
) -> SemanticEvidenceBundle:
    categories = {
        SemanticCategory.STYLE: "styles",
        SemanticCategory.MOOD: "moods",
    }
    return SemanticEvidenceBundle(
        metadata=bundle.metadata,
        genres=bundle.genres if "genres" in fields else (),
        tags=tuple(item for item in bundle.tags if categories.get(item.category) in fields),
    )


@dataclass(frozen=True, slots=True)
class MoodSettings:
    max_moods: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.max_moods, bool) or not isinstance(self.max_moods, int):
            raise TypeError("max_moods must be an integer")
        if not 1 <= self.max_moods <= 10:
            raise ValueError("max_moods must be between 1 and 10")


def resolve_styles(
    structured: Sequence[str], community: Sequence[SemanticTagEvidence]
) -> tuple[str, ...]:
    """Prefer lossless structured styles and use classified tags only as fallback."""
    selected: list[str] = []
    seen: set[str] = set()
    for value in structured:
        if not isinstance(value, str) or not value.strip():
            continue
        canonical = value.strip()
        identity = canonical.casefold()
        if identity not in seen:
            seen.add(identity)
            selected.append(canonical)
    if selected:
        return tuple(selected)
    for item in community:
        if item.category is not SemanticCategory.STYLE or item.confidence <= 0.0:
            continue
        identity = item.canonical_term.casefold()
        if identity not in seen:
            seen.add(identity)
            selected.append(item.canonical_term)
    return tuple(selected)


def resolve_moods(
    evidence: Sequence[SemanticTagEvidence], max_moods: int = 1
) -> tuple[str, ...]:
    """Select recognized moods using ordered, discrete ranking components."""
    settings = MoodSettings(max_moods)
    grouped: dict[str, list[tuple[int, SemanticTagEvidence]]] = defaultdict(list)
    names: dict[str, str] = {}
    for index, item in enumerate(evidence):
        if not isinstance(item, SemanticTagEvidence):
            raise TypeError("evidence must contain SemanticTagEvidence values")
        if item.category is not SemanticCategory.MOOD or item.confidence <= 0.0:
            continue
        identity = item.canonical_term.casefold()
        names.setdefault(identity, item.canonical_term)
        grouped[identity].append((index, item))

    def ranking(identity: str) -> tuple[object, ...]:
        rows = grouped[identity]
        return (
            min(_SCOPE_RANK[item.scope] for _, item in rows),
            -len({item.provider.casefold() for _, item in rows}),
            -max(item.confidence for _, item in rows),
            -max(item.native_weight if item.native_weight is not None else -1 for _, item in rows),
            min(index for index, _ in rows),
            identity,
        )

    ordered = sorted(grouped, key=ranking)
    return tuple(names[identity] for identity in ordered[: settings.max_moods])
