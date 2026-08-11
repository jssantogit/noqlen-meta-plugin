"""Artwork configuration and immutable domain values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from urllib.parse import urlparse

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
