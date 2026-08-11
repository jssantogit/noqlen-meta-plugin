"""Bounded and verified album artwork application."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from typing import Any

import requests
from beets import plugins
from beets.library import Album, Item, Library
from mediafile import Image, ImageType, MediaFile

from beetsplug.noqlenmeta.artwork import ArtworkCandidate, ArtworkPlan
from beetsplug.noqlenmeta.media_snapshot import (
    copy_regular_file_without_source_atime,
    fingerprint_media_file,
)

MAX_ARTWORK_BYTES = 50 * 1024 * 1024
_TIMEOUT = (5.0, 30.0)
_CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True, slots=True)
class ArtworkApplicationResult:
    album_id: int
    committed_sidecars: tuple[bytes, ...] = ()
    embedded_item_ids: tuple[int, ...] = ()
    artpath_committed: bool = False
    blocked_reason: str | None = None
    state_uncertain: bool = False
    recovery_artifact_retained: bool = False


class ArtworkApplicationError(RuntimeError):
    """Artwork bytes or a requested mutation failed validation."""

    def __init__(
        self,
        message: str,
        *,
        state_uncertain: bool = False,
        recovery_artifact_retained: bool = False,
    ) -> None:
        super().__init__(message)
        self.state_uncertain = state_uncertain
        self.recovery_artifact_retained = recovery_artifact_retained


def validate_jpeg_bytes(payload: bytes) -> None:
    """Require a non-empty JPEG representation accepted by the embedding value type."""
    if len(payload) < 4 or not payload.startswith(b"\xff\xd8") or not payload.endswith(b"\xff\xd9"):
        raise ArtworkApplicationError("artwork payload is not a valid JPEG representation")
    try:
        image = Image(payload, type=ImageType.front)
        if image.mime_type != "image/jpeg":
            raise ValueError("not a JPEG")
    except Exception as error:
        raise ArtworkApplicationError("artwork payload cannot be embedded") from error


def download_artwork(
    candidate: ArtworkCandidate,
    session: Any,
    *,
    max_bytes: int = MAX_ARTWORK_BYTES,
) -> bytes:
    """Download one prepared URL, with native JPEG fallback for an original."""
    urls = [candidate.selected_url]
    if candidate.effective_size == "original":
        urls.extend(
            candidate.thumbnail_urls[size]
            for size in (1200, 500, 250)
            if size in candidate.thumbnail_urls
            and candidate.thumbnail_urls[size] != candidate.selected_url
        )
    for index, url in enumerate(urls):
        payload = _download_url(url, session, max_bytes=max_bytes)
        try:
            validate_jpeg_bytes(payload)
        except ArtworkApplicationError:
            if index + 1 < len(urls):
                continue
            raise
        return payload
    raise ArtworkApplicationError("no valid prepared JPEG representation is available")


def _download_url(url: str, session: Any, *, max_bytes: int) -> bytes:
    try:
        response = session.get(url, stream=True, timeout=_TIMEOUT)
        response.raise_for_status()
        chunks = []
        length = 0
        for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
            if not chunk:
                continue
            length += len(chunk)
            if length > max_bytes:
                raise ArtworkApplicationError("artwork payload exceeds the internal byte limit")
            chunks.append(chunk)
    except ArtworkApplicationError:
        raise
    except Exception as error:
        raise ArtworkApplicationError("artwork download is unavailable") from error
    payload = b"".join(chunks)
    if not payload:
        raise ArtworkApplicationError("artwork payload is empty")
    return payload


def apply_artwork_plan(
    library: Library,
    album: Album,
    plan: ArtworkPlan,
    session: Any | None = None,
) -> ArtworkApplicationResult:
    """Apply one prepared plan without performing metadata lookup or analysis."""
    if not isinstance(album.id, int) or album.id != plan.album_id:
        raise ArtworkApplicationError("artwork plan does not match the Album")
    if plan.outcome != "RESOLVED":
        return ArtworkApplicationResult(plan.album_id, blocked_reason=plan.reason)
    temporary_paths: list[bytes] = []
    committed: list[bytes] = []
    try:
        _preflight_sidecars(plan)
        payload = _payload_for_plan(plan, session)
        validate_jpeg_bytes(payload)
        digest = hashlib.sha256(payload).digest()
        for destination in plan.sidecar_destinations:
            temporary = _write_sidecar_candidate(destination, payload, digest)
            temporary_paths.append(temporary)
        prepared_paths = tuple(temporary_paths)
        for destination, temporary in zip(
            plan.sidecar_destinations, prepared_paths, strict=True
        ):
            if not plan.replace_existing and os.path.lexists(destination):
                raise ArtworkApplicationError("cover.jpg appeared after artwork preview")
            os.replace(temporary, destination)
            temporary_paths.remove(temporary)
            _fsync_directory(destination)
            if _digest(destination) != digest:
                raise ArtworkApplicationError("committed cover.jpg failed verification")
            committed.append(destination)
    except ArtworkApplicationError as error:
        return ArtworkApplicationResult(
            plan.album_id,
            tuple(committed),
            blocked_reason=str(error),
            state_uncertain=bool(committed),
        )
    finally:
        for temporary in temporary_paths:
            _remove(temporary)

    artpath_committed = False
    if plan.canonical_artpath is not None:
        if _digest(plan.canonical_artpath) != hashlib.sha256(payload).digest():
            return ArtworkApplicationResult(
                plan.album_id,
                tuple(committed),
                blocked_reason="canonical cover.jpg failed verification",
                state_uncertain=bool(committed),
            )
        try:
            fresh_album = library.get_album(plan.album_id)
            if fresh_album is None:
                raise ArtworkApplicationError("artwork Album disappeared before artpath commit")
            fresh_album.artpath = plan.canonical_artpath
            fresh_album.store()
            artpath_committed = library.get_album(plan.album_id).artpath == plan.canonical_artpath
            if not artpath_committed:
                raise ArtworkApplicationError("Album.artpath failed verification")
        except ArtworkApplicationError as error:
            return ArtworkApplicationResult(
                plan.album_id,
                tuple(committed),
                blocked_reason=str(error),
                state_uncertain=bool(committed),
            )

    embedded = []
    blocked_reason = None
    state_uncertain = False
    retained = False
    for item_id in plan.embed_item_ids:
        item = library.get_item(item_id)
        if type(item) is not Item or item.album_id != plan.album_id:
            blocked_reason = "artwork embed target changed after preview"
            continue
        try:
            _embed_artwork(library, item, payload)
            embedded.append(item_id)
        except ArtworkApplicationError as error:
            blocked_reason = str(error)
            state_uncertain = state_uncertain or error.state_uncertain
            retained = retained or error.recovery_artifact_retained
    return ArtworkApplicationResult(
        plan.album_id,
        tuple(committed),
        tuple(embedded),
        artpath_committed,
        blocked_reason,
        state_uncertain,
        retained,
    )


def _payload_for_plan(plan: ArtworkPlan, session: Any | None) -> bytes:
    if plan.local_source is not None:
        try:
            with open(plan.local_source, "rb") as handle:
                payload = handle.read(MAX_ARTWORK_BYTES + 1)
        except OSError as error:
            raise ArtworkApplicationError("authoritative cover.jpg is unavailable") from error
        if len(payload) > MAX_ARTWORK_BYTES:
            raise ArtworkApplicationError("artwork payload exceeds the internal byte limit")
        return payload
    if plan.candidate is None:
        raise ArtworkApplicationError("artwork plan has no prepared source")
    return download_artwork(plan.candidate, session or requests.Session())


def _preflight_sidecars(plan: ArtworkPlan) -> None:
    for destination in plan.sidecar_destinations:
        parent = os.path.dirname(destination)
        if not os.path.isdir(parent):
            raise ArtworkApplicationError("artwork destination directory is unavailable")
        if os.path.lexists(destination):
            if not plan.replace_existing:
                raise ArtworkApplicationError("cover.jpg already exists")
            if not os.path.isfile(destination) or os.path.islink(destination):
                raise ArtworkApplicationError("existing cover.jpg is not a regular file")


def _write_sidecar_candidate(destination: bytes, payload: bytes, digest: bytes) -> bytes:
    descriptor, temporary = tempfile.mkstemp(
        prefix=b".noqlen-artwork-", dir=os.path.dirname(destination)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if _digest(temporary) != digest:
            raise ArtworkApplicationError("temporary cover.jpg failed verification")
        return temporary
    except BaseException:
        _remove(temporary)
        raise


def _embed_artwork(library: Library, item: Item, payload: bytes) -> None:
    path = item.path
    source_fingerprint = fingerprint_media_file(path)
    candidate = _temporary_sibling(path, b".noqlen-artwork-candidate-")
    backup = _temporary_sibling(path, b".noqlen-artwork-recovery-")
    replaced = False
    try:
        copy_regular_file_without_source_atime(path, candidate, destination_exists=False)
        media = MediaFile(os.fsdecode(candidate))
        media.images = [Image(payload, desc="Front Cover", type=ImageType.front)]
        media.save()
        _verify_embedded(candidate, payload)
        if fingerprint_media_file(path) != source_fingerprint:
            raise ArtworkApplicationError("artwork media source changed before embedding")
        copy_regular_file_without_source_atime(path, backup, destination_exists=False)
        os.replace(candidate, path)
        replaced = True
        _fsync_directory(path)
        _verify_embedded(path, payload)
        fresh = library.get_item(item.id)
        if type(fresh) is not Item or fresh.path != path:
            raise ArtworkApplicationError("artwork Item changed before mtime commit")
        fresh.mtime = os.stat(path, follow_symlinks=False).st_mtime
        fresh.store()
        plugins.send("after_write", item=fresh, path=path)
        plugins.send("database_change", lib=library, model=fresh)
        _remove(backup)
    except Exception as error:
        if replaced:
            try:
                os.replace(backup, path)
                backup = b""
                _fsync_directory(path)
                if fingerprint_media_file(path) != source_fingerprint:
                    raise OSError("restored media digest mismatch")
            except Exception as restore_error:
                raise ArtworkApplicationError(
                    "artwork embedding state is uncertain",
                    state_uncertain=True,
                    recovery_artifact_retained=bool(backup and os.path.exists(backup)),
                ) from restore_error
        if isinstance(error, ArtworkApplicationError):
            raise
        raise ArtworkApplicationError("artwork embedding failed") from error
    finally:
        _remove(candidate)
        _remove(backup)


def _verify_embedded(path: bytes, payload: bytes) -> None:
    images = MediaFile(os.fsdecode(path)).images
    if len(images) != 1 or images[0].data != payload or images[0].type != ImageType.front:
        raise ArtworkApplicationError("embedded artwork failed reopen verification")


def _temporary_sibling(path: bytes, prefix: bytes) -> bytes:
    descriptor, temporary = tempfile.mkstemp(prefix=prefix, dir=os.path.dirname(path))
    os.close(descriptor)
    os.unlink(temporary)
    return temporary


def _digest(path: bytes) -> bytes:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.digest()


def _fsync_directory(path: bytes) -> None:
    descriptor = os.open(os.path.dirname(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _remove(path: bytes | None) -> bool:
    if not path:
        return True
    try:
        os.unlink(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True
