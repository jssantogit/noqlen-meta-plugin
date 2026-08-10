"""Pure field-specific resolution for semantic community evidence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from beetsplug.noqlenmeta.domain import SemanticCategory, SemanticTagEvidence
from beetsplug.noqlenmeta.providers.specs import ProviderScope

_SCOPE_RANK = {
    ProviderScope.TRACK: 0,
    ProviderScope.RELEASE: 1,
    ProviderScope.ARTIST: 2,
}


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
