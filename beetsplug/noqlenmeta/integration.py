"""Read-only beets import integration helpers."""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from typing import Any

from beets import ui
from beets.autotag.hooks import AlbumInfo
from beets.importer.actions import Action

from beetsplug.noqlenmeta.domain import (
    ExternalIdentifier,
    MetadataCandidate,
    ReleaseEnrichmentContext,
)

_DISCOGS_RELEASE_NAMESPACE = "discogs.release"
_DISCOGS_TOKEN_ENV = "NOQLENMETA_DISCOGS_TOKEN"


def resolve_discogs_token(configured_token: str) -> str | None:
    """Resolve a token without exposing it outside the provider boundary."""
    environment_token = os.environ.get(_DISCOGS_TOKEN_ENV, "").strip()
    if environment_token:
        return environment_token
    configured_token = configured_token.strip()
    return configured_token or None


def context_from_album_info(album_info: AlbumInfo) -> ReleaseEnrichmentContext | None:
    """Copy useful selected-release identity into the provider-independent domain."""
    artist = _optional_text(album_info.artist)
    title = _optional_text(album_info.album)
    if artist is None or title is None:
        return None

    external_ids: list[ExternalIdentifier] = []
    seen_ids: set[str] = set()
    discogs_ids = [album_info.discogs_albumid]
    data_source = _optional_text(album_info.data_source)
    if data_source is not None and data_source.casefold() == "discogs":
        discogs_ids.append(album_info.album_id)
    for value in discogs_ids:
        release_id = _positive_release_id(value)
        if release_id is not None and release_id not in seen_ids:
            seen_ids.add(release_id)
            external_ids.append(ExternalIdentifier(_DISCOGS_RELEASE_NAMESPACE, release_id))

    year = album_info.year
    if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
        year = None

    return ReleaseEnrichmentContext(
        album_artist=artist,
        album_title=title,
        year=year,
        barcode=_optional_text(album_info.barcode),
        catalog_number=_optional_text(album_info.catalognum),
        external_ids=tuple(external_ids),
    )


def eligible_album_info(task: object) -> AlbumInfo | None:
    """Return selected album metadata only for a real album APPLY choice."""
    if not getattr(task, "is_album", False):
        return None
    if getattr(task, "choice_flag", None) is not Action.APPLY:
        return None
    match = getattr(task, "match", None)
    album_info = getattr(match, "info", None)
    return album_info if isinstance(album_info, AlbumInfo) else None


def render_preview(candidates: Sequence[MetadataCandidate]) -> None:
    """Print normalized candidate values without raw provider data."""
    first = candidates[0]
    lines = ["Noqlen Meta / Discogs:", f"  release: {first.source_id}"]
    for candidate in candidates:
        value: Any = candidate.value
        if isinstance(value, tuple):
            value = ", ".join(value)
        lines.append(f"  {candidate.field}: {_safe_preview_text(value)}")
    ui.print_("\n".join(lines))


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _positive_release_id(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    text = str(value).strip() if isinstance(value, (int, str)) else ""
    if not re.fullmatch(r"[0-9]+", text):
        return None
    try:
        return str(int(text)) if int(text) > 0 else None
    except ValueError:
        return None


def _safe_preview_text(value: object) -> str:
    printable = "".join(character if character.isprintable() else " " for character in str(value))
    return " ".join(printable.split())
