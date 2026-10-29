"""V3 exact-release Back artwork as a safe associated JPEG asset.

No Album.artpath mutation, no audio embed, no release-group fallback and no
replacement of an existing back.jpg. A proposed asset is committed only from
a previously verified exact-release CAA metadata plan.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests
from beets.library import Album, Library

from beetsplug.noqlenmeta.artwork import (
    ArtworkCandidate,
    ArtworkContext,
    ArtworkLookupResult,
    ArtworkSettings,
    _candidate_from_payload,
    _release_identity,
)
from beetsplug.noqlenmeta.artwork_application import (
    ArtworkApplicationError,
    download_artwork,
)
from beetsplug.noqlenmeta.providers.coverartarchive import (
    CoverArtArchiveClient,
    CoverArtArchiveUnavailable,
)


@dataclass(frozen=True, slots=True)
class BackArtworkPlan:
    album_id: int
    item_paths: tuple[bytes, ...]
    destinations: tuple[bytes, ...]
    candidate: ArtworkCandidate | None
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class BackArtworkResult:
    album_id: int
    status: str
    committed: tuple[bytes, ...] = ()
    reason: str = ""

    @property
    def created(self) -> bool:
        return bool(self.committed)


def _trusted_caa_url(url: str) -> bool:
    parsed = urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "coverartarchive.org"
        and parsed.username is None
        and parsed.password is None
    )


def resolve_caa_back_artwork(
    client: CoverArtArchiveClient,
    release_mbid: str,
    settings: ArtworkSettings,
) -> ArtworkLookupResult:
    """An exact approved Back image only; never borrow another edition's art."""
    try:
        payload = client.get_release(release_mbid)
    except CoverArtArchiveUnavailable:
        return ArtworkLookupResult("UNAVAILABLE", reason="CAA exact-release back unavailable")
    if payload is None:
        return ArtworkLookupResult("NO_EVIDENCE", reason="CAA release not found")
    if _release_identity(payload.get("release")) != release_mbid:
        return ArtworkLookupResult("BLOCKED", reason="CAA Back release identity mismatched")
    images = payload.get("images")
    if not isinstance(images, list):
        return ArtworkLookupResult("BLOCKED", reason="CAA Back image list invalid")
    backs = [
        image for image in images
        if isinstance(image, dict)
        and image.get("back") is True
        and image.get("approved") is True
    ]
    if len(backs) > 1:
        return ArtworkLookupResult("REVIEW", reason="multiple approved Back images")
    if not backs:
        return ArtworkLookupResult("NO_EVIDENCE", reason="no approved Back image")
    try:
        candidate = _candidate_from_payload(
            payload,
            source_scope="release",
            release_mbid=release_mbid,
            release_group_mbid=None,
            settings=settings,
            require_release_mbid=release_mbid,
            image_type="back",
        )
    except ValueError:
        return ArtworkLookupResult("BLOCKED", reason="CAA Back metadata invalid")
    if candidate is None:
        return ArtworkLookupResult("NO_EVIDENCE", reason="no usable Back representation")
    urls = (candidate.selected_url, candidate.original_url, *candidate.thumbnail_urls.values())
    if not all(_trusted_caa_url(url) for url in urls):
        return ArtworkLookupResult("BLOCKED", reason="untrusted CAA Back image URL")
    return ArtworkLookupResult("RESOLVED", candidate=candidate)


def back_artwork_requires_lookup(context: ArtworkContext) -> bool:
    return bool(context.release_mbid) and not any(
        os.path.lexists(os.path.join(directory, b"back.jpg"))
        for directory in context.disc_directories
    )


def plan_back_artwork(
    context: ArtworkContext, lookup: ArtworkLookupResult | None
) -> BackArtworkPlan:
    destinations = tuple(
        os.path.join(directory, b"back.jpg") for directory in context.disc_directories
    )
    existing = tuple(path for path in destinations if os.path.lexists(path))
    if existing:
        return BackArtworkPlan(
            context.album_id, context.item_paths, (), None, "PRESERVED",
            "existing back.jpg is authoritative and will not be overwritten",
        )
    if lookup is None or lookup.outcome != "RESOLVED" or lookup.candidate is None:
        return BackArtworkPlan(
            context.album_id, context.item_paths, (), None,
            lookup.outcome if lookup is not None else "NO_EVIDENCE",
            lookup.reason if lookup is not None else "no prepared Back evidence",
        )
    return BackArtworkPlan(
        context.album_id, context.item_paths, destinations, lookup.candidate,
        "PROPOSE", "one exact-release approved Back image",
    )


def apply_back_artwork_plan(
    library: Library,
    album: Album,
    plan: BackArtworkPlan,
    *,
    session: object | None = None,
) -> BackArtworkResult:
    """Create Back sidecars only, with atomic no-clobber commits per directory."""
    if plan.status != "PROPOSE" or plan.candidate is None:
        return BackArtworkResult(plan.album_id, plan.status, reason=plan.reason)
    fresh = library.get_album(plan.album_id)
    if fresh is None or album.id != plan.album_id:
        return BackArtworkResult(plan.album_id, "BLOCKED", reason="Album changed")
    actual_paths = tuple(sorted(item.path for item in fresh.items()))
    if actual_paths != tuple(sorted(plan.item_paths)):
        return BackArtworkResult(plan.album_id, "BLOCKED", reason="album Items changed")
    if not plan.destinations or any(
        os.path.lexists(destination) or not os.path.isdir(os.path.dirname(destination))
        for destination in plan.destinations
    ):
        return BackArtworkResult(plan.album_id, "BLOCKED", reason="back.jpg target changed")
    try:
        payload = download_artwork(plan.candidate, session or requests.Session())
    except ArtworkApplicationError:
        return BackArtworkResult(plan.album_id, "BLOCKED", reason="Back JPEG unavailable")

    committed: list[bytes] = []
    for destination in plan.destinations:
        temporary: bytes | None = None
        try:
            fd, temporary = tempfile.mkstemp(
                prefix=b".noqlen-back-", dir=os.path.dirname(destination)
            )
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temporary, destination)
            committed.append(destination)
        except OSError:
            return BackArtworkResult(
                plan.album_id,
                "PARTIAL" if committed else "BLOCKED",
                tuple(committed),
                "back.jpg target changed or storage operation failed",
            )
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass
    return BackArtworkResult(plan.album_id, "COMMITTED", tuple(committed))
