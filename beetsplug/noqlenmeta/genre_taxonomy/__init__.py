"""Packaged Noqlen genre taxonomy and semantic classifier."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from importlib import resources

from beetsplug.noqlenmeta.genre_taxonomy.aliases import (
    ALIASES,
    BROAD_GENRES,
    DESCRIPTORS,
    MOODS,
    NOISE_LABELS,
    ORIGINS,
)

_WHITESPACE = re.compile(r"\s+")
_YEAR_OR_DECADE = re.compile(r"(?:[12][0-9]{3}|[0-9]{2,4}s)", re.IGNORECASE)
_PERSONAL_TERMS = re.compile(r"\b(?:favou?rites?|own|seen live|personal)\b", re.IGNORECASE)


class GenreSemanticCategory(Enum):
    GENRE = "genre"
    MOOD = "mood"
    ORIGIN = "origin"
    DESCRIPTOR = "descriptor"
    NOISE = "noise"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class GenreClassification:
    canonical_name: str
    category: GenreSemanticCategory
    broad: bool = False


def _normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value).strip())


class GenreTaxonomy:
    """Classify labels against one immutable packaged vocabulary snapshot."""

    def __init__(self, genres_text: str) -> None:
        encoded = genres_text.encode("utf-8")
        canonical: dict[str, str] = {}
        for raw_name in genres_text.splitlines():
            name = _normalize(raw_name)
            if not name:
                continue
            key = name.casefold()
            if key in canonical:
                raise ValueError("genre taxonomy contains duplicate identities")
            canonical[key] = name
        if not canonical:
            raise ValueError("genre taxonomy must not be empty")

        self._canonical = canonical
        self._aliases = {
            _normalize(alias).casefold(): self._canonical_name(target)
            for alias, target in ALIASES.items()
        }
        self._broad = frozenset(name.casefold() for name in BROAD_GENRES)
        self._moods = frozenset(name.casefold() for name in MOODS)
        self._origins = frozenset(name.casefold() for name in ORIGINS)
        self._descriptors = frozenset(name.casefold() for name in DESCRIPTORS)
        self._noise = frozenset(name.casefold() for name in NOISE_LABELS)
        self.snapshot_id = hashlib.sha256(encoded).hexdigest()[:16]

    @classmethod
    def from_package(cls) -> GenreTaxonomy:
        text = resources.files(__package__).joinpath("genres.txt").read_text(encoding="utf-8")
        return cls(text)

    def _canonical_name(self, name: str) -> str:
        canonical = self._canonical.get(_normalize(name).casefold())
        if canonical is None:
            raise ValueError(f"taxonomy alias target is unavailable: {name}")
        return canonical

    def classify(
        self, raw: str, *, artist_names: tuple[str, ...] = ()
    ) -> GenreClassification:
        if not isinstance(raw, str):
            raise TypeError("genre label must be a string")
        name = _normalize(raw)
        if not name:
            return GenreClassification("", GenreSemanticCategory.UNKNOWN)
        key = name.casefold()
        artist_keys = {_normalize(artist).casefold() for artist in artist_names}
        if (
            key in artist_keys
            or key in self._noise
            or _YEAR_OR_DECADE.fullmatch(name)
            or _PERSONAL_TERMS.search(name)
            or len(name.split()) > 6
        ):
            return GenreClassification(name, GenreSemanticCategory.NOISE)
        if key in self._moods:
            return GenreClassification(name, GenreSemanticCategory.MOOD)
        if key in self._origins:
            return GenreClassification(name, GenreSemanticCategory.ORIGIN)
        if key in self._descriptors:
            return GenreClassification(name, GenreSemanticCategory.DESCRIPTOR)

        canonical = self._aliases.get(key) or self._canonical.get(key)
        if canonical is None:
            return GenreClassification(name, GenreSemanticCategory.UNKNOWN)
        return GenreClassification(
            canonical,
            GenreSemanticCategory.GENRE,
            canonical.casefold() in self._broad,
        )

    def is_genre(self, raw: str) -> bool:
        return self.classify(raw).category is GenreSemanticCategory.GENRE


DEFAULT_GENRE_TAXONOMY = GenreTaxonomy.from_package()

__all__ = [
    "DEFAULT_GENRE_TAXONOMY",
    "GenreClassification",
    "GenreSemanticCategory",
    "GenreTaxonomy",
]
