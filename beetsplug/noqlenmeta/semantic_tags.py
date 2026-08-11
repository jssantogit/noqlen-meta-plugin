"""Deterministic classification of reviewed community tags."""

from __future__ import annotations

import unicodedata

from beetsplug.noqlenmeta.domain import SemanticCategory, SemanticTagEvidence
from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
)
from beetsplug.noqlenmeta.providers.specs import ProviderScope


def semantic_identity(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


_NOISE = {"seen live": "Seen Live", "spotify": "Spotify", "last.fm": "Last.fm"}
_STYLES = {
    "alternative metal": "Alternative Metal",
    "progressive metal": "Progressive Metal",
    "technical death metal": "Technical Death Metal",
}
_MOODS = {
    "melancholy": "Melancholic",
    "melancholic": "Melancholic",
    "sad": "Melancholic",
    "sadness": "Melancholic",
    "dreamy": "Dreamy",
    "atmospheric": "Atmospheric",
    "energetic": "Energetic",
    "joyful": "Joyful",
    "dark": "Dark",
}
_ORIGINS = {"korean": "Korean", "japanese": "Japanese", "brazilian": "Brazilian"}
_DESCRIPTORS = {
    "female vocalists": "Female Vocalists",
    "girl group": "Girl Group",
    "instrumental": "Instrumental",
}


def classify_semantic_tag(
    raw_tag: str,
    provider: str,
    scope: ProviderScope,
    confidence: float,
    source_id: str,
    source_url: str | None,
    weight: int | None,
) -> SemanticTagEvidence | None:
    """Return at most one reviewed semantic identity for a community tag."""
    if not isinstance(raw_tag, str):
        raise TypeError("raw tag must be a string")
    identity = semantic_identity(raw_tag)
    if not identity:
        return None

    category: SemanticCategory
    canonical: str
    if identity in _NOISE:
        category, canonical = SemanticCategory.NOISE, _NOISE[identity]
    else:
        genre = DEFAULT_GENRE_TAXONOMY.classify(raw_tag)
        if genre.category is GenreSemanticCategory.GENRE:
            category, canonical = SemanticCategory.GENRE, genre.canonical_name
        elif identity in _STYLES:
            category, canonical = SemanticCategory.STYLE, _STYLES[identity]
        elif identity in _MOODS:
            category, canonical = SemanticCategory.MOOD, _MOODS[identity]
        elif identity in _ORIGINS:
            category, canonical = SemanticCategory.ORIGIN, _ORIGINS[identity]
        elif identity in _DESCRIPTORS:
            category, canonical = SemanticCategory.DESCRIPTOR, _DESCRIPTORS[identity]
        elif genre.category is GenreSemanticCategory.NOISE:
            category, canonical = SemanticCategory.NOISE, raw_tag.strip().title()
        else:
            return None
    return SemanticTagEvidence(
        canonical,
        category,
        provider,
        scope,
        confidence,
        source_id,
        source_url,
        weight,
        raw_tag,
    )
