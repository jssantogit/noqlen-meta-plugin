"""Artwork configuration and immutable domain values."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from urllib.parse import urlparse

from beets.library import Album, Item
from mediafile import MediaFile

from beetsplug.noqlenmeta.configuration import validate_artwork_config
from beetsplug.noqlenmeta.providers.coverartarchive import (
    CoverArtArchiveClient,
    CoverArtArchiveUnavailable,
)


class ArtworkSize(Enum):
    ORIGINAL = "original"
    PX_1200 = "1200"
    PX_500 = "500"
    PX_250 = "250"


@dataclass(frozen=True, slots=True)
class ArtworkSettings:
    size: ArtworkSize = ArtworkSize.ORIGINAL
    replace_existing: bool = False


@dataclass(frozen=True, slots=True)
class ArtworkCandidate:
    source_scope: str
    release_mbid: str
    release_group_mbid: str | None
    source_release_mbid: str | None
    image_id: str
    original_url: str
    thumbnail_urls: Mapping[int, str]
    requested_size: ArtworkSize
    effective_size: str
    selected_url: str
    original_mime_hint: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "thumbnail_urls", MappingProxyType(dict(self.thumbnail_urls)))


@dataclass(frozen=True, slots=True)
class ArtworkLookupResult:
    outcome: str
    candidate: ArtworkCandidate | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ArtworkContext:
    album_id: int
    release_mbid: str
    release_group_mbid: str | None
    item_ids: tuple[int, ...]
    item_paths: tuple[bytes, ...]
    disc_directories: tuple[bytes, ...]
    existing_sidecars: tuple[bytes, ...]
    embedded_art_item_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ArtworkPlan:
    album_id: int
    outcome: str
    candidate: ArtworkCandidate | None
    local_source: bytes | None
    sidecar_destinations: tuple[bytes, ...]
    canonical_artpath: bytes | None
    embed_item_ids: tuple[int, ...]
    replace_existing: bool
    reason: str | None = None


class _InvalidArtworkMetadata(ValueError):
    pass


def artwork_settings_from_config(value: object) -> ArtworkSettings:
    """Validate public artwork configuration and return immutable settings."""
    validate_artwork_config(value)
    assert isinstance(value, Mapping)
    return ArtworkSettings(
        size=ArtworkSize(value["size"]),
        replace_existing=value["replace_existing"],
    )


def artwork_context_from_album(
    album: Album, items: list[Item] | tuple[Item, ...]
) -> ArtworkContext:
    """Snapshot album paths and existing artwork state for deterministic planning."""
    if not isinstance(album, Album) or not isinstance(album.id, int):
        raise ValueError("artwork planning requires a persisted Album")
    persisted = tuple(items)
    if not persisted or any(not isinstance(item.id, int) for item in persisted):
        raise ValueError("artwork planning requires persisted album Items")
    if any(item.album_id != album.id for item in persisted):
        raise ValueError("artwork planning Items must belong to the Album")
    item_paths = tuple(item.path for item in persisted)
    if any(not isinstance(path, bytes) or not path for path in item_paths):
        raise ValueError("artwork planning requires Item paths")
    directories = tuple(sorted({os.path.dirname(path) for path in item_paths}))
    sidecars = tuple(
        destination
        for directory in directories
        if os.path.exists(destination := os.path.join(directory, b"cover.jpg"))
    )
    embedded = []
    for item, path in zip(persisted, item_paths, strict=True):
        try:
            if MediaFile(os.fsdecode(path)).images:
                embedded.append(item.id)
        except Exception as error:
            raise ValueError("existing embedded artwork could not be inspected") from error
    release_mbid = str(album.get("mb_albumid") or "").strip()
    release_group_mbid = str(album.get("mb_releasegroupid") or "").strip() or None
    return ArtworkContext(
        album.id,
        release_mbid,
        release_group_mbid,
        tuple(item.id for item in persisted),
        item_paths,
        directories,
        sidecars,
        tuple(embedded),
    )


def artwork_context_requires_lookup(context: ArtworkContext, settings: ArtworkSettings) -> bool:
    """Return whether preservation policy permits CAA metadata collection."""
    if not context.release_mbid:
        return False
    return settings.replace_existing or not (
        context.existing_sidecars or context.embedded_art_item_ids
    )


def plan_album_artwork(
    album: Album,
    items: list[Item] | tuple[Item, ...],
    lookup: ArtworkLookupResult | None,
    settings: ArtworkSettings,
    *,
    write_enabled: bool,
) -> ArtworkPlan:
    """Prepare album artwork effects without mutating files or database state."""
    return plan_artwork_context(
        artwork_context_from_album(album, items),
        lookup,
        settings,
        write_enabled=write_enabled,
    )


def plan_artwork_context(
    context: ArtworkContext,
    lookup: ArtworkLookupResult | None,
    settings: ArtworkSettings,
    *,
    write_enabled: bool,
) -> ArtworkPlan:
    if context.embedded_art_item_ids and not settings.replace_existing:
        return ArtworkPlan(
            context.album_id,
            "PRESERVED",
            None,
            None,
            (),
            context.existing_sidecars[0] if context.existing_sidecars else None,
            (),
            False,
            "existing embedded artwork preserved for the whole album",
        )

    if context.existing_sidecars and not settings.replace_existing:
        source = context.existing_sidecars[0]
        missing = tuple(
            os.path.join(directory, b"cover.jpg")
            for directory in context.disc_directories
            if os.path.join(directory, b"cover.jpg") not in context.existing_sidecars
        )
        return ArtworkPlan(
            context.album_id,
            "RESOLVED",
            None,
            source,
            missing,
            source,
            context.item_ids if write_enabled else (),
            False,
            "existing cover.jpg is authoritative",
        )

    if lookup is None or lookup.outcome != "RESOLVED" or lookup.candidate is None:
        return ArtworkPlan(
            context.album_id,
            lookup.outcome if lookup is not None else "NO_EVIDENCE",
            None,
            None,
            (),
            None,
            (),
            settings.replace_existing,
            lookup.reason if lookup is not None else "no prepared artwork evidence",
        )

    destinations = tuple(
        os.path.join(directory, b"cover.jpg") for directory in context.disc_directories
    )
    return ArtworkPlan(
        context.album_id,
        "RESOLVED",
        lookup.candidate,
        None,
        destinations,
        destinations[0] if destinations else None,
        context.item_ids if write_enabled else (),
        settings.replace_existing,
    )


def resolve_caa_artwork(
    client: CoverArtArchiveClient,
    *,
    release_mbid: str,
    release_group_mbid: str | None,
    settings: ArtworkSettings,
) -> ArtworkLookupResult:
    """Resolve exact-release artwork, falling back only after definitive absence."""
    try:
        exact_payload = client.get_release(release_mbid)
        if exact_payload is not None:
            exact_candidate = _candidate_from_payload(
                exact_payload,
                source_scope="release",
                release_mbid=release_mbid,
                release_group_mbid=release_group_mbid,
                settings=settings,
                require_release_mbid=release_mbid,
            )
            if exact_candidate is not None:
                return ArtworkLookupResult("RESOLVED", candidate=exact_candidate)
    except (CoverArtArchiveUnavailable, _InvalidArtworkMetadata) as error:
        return ArtworkLookupResult("UNAVAILABLE", reason=str(error))

    if release_group_mbid is None:
        return ArtworkLookupResult("NO_EVIDENCE", reason="no eligible CAA front")

    try:
        group_payload = client.get_release_group(release_group_mbid)
        if group_payload is None:
            return ArtworkLookupResult("NO_EVIDENCE", reason="no eligible CAA front")
        group_candidate = _candidate_from_payload(
            group_payload,
            source_scope="release_group",
            release_mbid=release_mbid,
            release_group_mbid=release_group_mbid,
            settings=settings,
        )
    except (CoverArtArchiveUnavailable, _InvalidArtworkMetadata) as error:
        return ArtworkLookupResult("UNAVAILABLE", reason=str(error))

    if group_candidate is None:
        return ArtworkLookupResult("NO_EVIDENCE", reason="no eligible CAA front")
    return ArtworkLookupResult("RESOLVED", candidate=group_candidate)


def _candidate_from_payload(
    payload: Mapping[str, object],
    *,
    source_scope: str,
    release_mbid: str,
    release_group_mbid: str | None,
    settings: ArtworkSettings,
    require_release_mbid: str | None = None,
) -> ArtworkCandidate | None:
    images = payload.get("images")
    source_release_mbid = _release_identity(payload.get("release"))
    if not isinstance(images, list) or source_release_mbid is None:
        raise _InvalidArtworkMetadata("CAA metadata shape is invalid")
    if require_release_mbid is not None and source_release_mbid != require_release_mbid:
        raise _InvalidArtworkMetadata("CAA release identity does not match the request")

    front = next(
        (
            image
            for image in images
            if isinstance(image, Mapping)
            and image.get("front") is True
            and image.get("approved") is True
        ),
        None,
    )
    if front is None:
        return None

    image_id = front.get("id")
    original_url = front.get("image")
    raw_thumbnails = front.get("thumbnails", {})
    if not isinstance(image_id, (str, int)) or not isinstance(original_url, str):
        raise _InvalidArtworkMetadata("CAA front metadata is invalid")
    if not isinstance(raw_thumbnails, Mapping):
        raise _InvalidArtworkMetadata("CAA thumbnail metadata is invalid")
    thumbnails = {
        size: url
        for size in (1200, 500, 250)
        if isinstance((url := raw_thumbnails.get(str(size))), str)
    }
    mime_hint = _mime_hint(original_url)
    representation = _select_representation(settings.size, original_url, thumbnails, mime_hint)
    if representation is None:
        return None
    effective_size, selected_url = representation
    return ArtworkCandidate(
        source_scope=source_scope,
        release_mbid=release_mbid,
        release_group_mbid=release_group_mbid,
        source_release_mbid=(source_release_mbid if source_scope == "release_group" else None),
        image_id=str(image_id),
        original_url=original_url,
        thumbnail_urls=thumbnails,
        requested_size=settings.size,
        effective_size=effective_size,
        selected_url=selected_url,
        original_mime_hint=mime_hint,
    )


def _release_identity(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    parts = parsed.path.rstrip("/").split("/")
    if parsed.scheme != "https" or parsed.netloc != "musicbrainz.org" or len(parts) < 3:
        return None
    if parts[-2] != "release" or not parts[-1]:
        return None
    return parts[-1]


def _mime_hint(url: str) -> str | None:
    path = urlparse(url).path.lower()
    if path.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".webp"):
        return "image/webp"
    return None


def _select_representation(
    requested_size: ArtworkSize,
    original_url: str,
    thumbnails: Mapping[int, str],
    mime_hint: str | None,
) -> tuple[str, str] | None:
    if requested_size is ArtworkSize.ORIGINAL and mime_hint in {None, "image/jpeg"}:
        return "original", original_url
    maximum = 1200 if requested_size is ArtworkSize.ORIGINAL else int(requested_size.value)
    for size in (1200, 500, 250):
        if size <= maximum and size in thumbnails:
            return str(size), thumbnails[size]
    return None
