"""Generic path-private filesystem and MediaFile snapshot primitives."""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime

from mediafile import MediaFile


@dataclass(frozen=True, slots=True)
class MediaFileFingerprint:
    device: int
    inode: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    link_count: int


@dataclass(frozen=True, slots=True)
class FilesystemMetadata:
    mode: int
    uid: int
    gid: int
    atime_ns: int
    xattrs: tuple[tuple[bytes, bytes], ...]
    size: int


@dataclass(frozen=True, slots=True)
class MediaFileSnapshot:
    path: bytes = field(repr=False)
    fingerprint: MediaFileFingerprint
    values: tuple[tuple[str, object], ...] = field(repr=False)
    format_name: str | None
    filesystem_metadata: FilesystemMetadata


class AtimeSafeCopyError(RuntimeError):
    """The platform cannot guarantee a source-atime-safe copy."""


def fingerprint_media_file(
    path: bytes, *, _context: str = "media file"
) -> MediaFileFingerprint:
    info = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{_context} is not a regular file")
    if info.st_nlink != 1:
        raise ValueError(f"{_context} has multiple hard links")
    return _fingerprint(info)


def snapshot_media_file(
    path: bytes, *, fields: Iterable[str]
) -> MediaFileSnapshot:
    """Read selected logical media fields under one verifiable file snapshot."""
    before = fingerprint_media_file(path)
    metadata = filesystem_metadata(path)
    values: list[tuple[str, object]] = []
    with _read_mediafile_without_atime(path) as media:
        available = frozenset(MediaFile.fields())
        for media_field in sorted(set(fields)):
            if media_field not in available:
                raise ValueError(f"unknown MediaFile field {media_field!r}")
            values.append((media_field, freeze_media_value(getattr(media, media_field))))
        format_name = media.format
    after = fingerprint_media_file(path)
    if after != before:
        raise ValueError("media file changed while reading")
    return MediaFileSnapshot(path, before, tuple(values), format_name, metadata)


def copy_regular_file_without_source_atime(
    source: bytes,
    destination: bytes,
    *,
    destination_exists: bool,
    destination_descriptor: int | None = None,
    _context: str = "media file",
) -> None:
    """Copy one regular file without allowing the source read to advance atime."""
    if destination_exists and destination_descriptor is None:
        raise ValueError(f"{_context} existing destination descriptor is required")
    before: MediaFileFingerprint | None = None
    metadata: FilesystemMetadata | None = None
    source_descriptor: int | None = None
    opened_destination = destination_descriptor
    destination_identity: tuple[int, int] | None = None
    try:
        before = fingerprint_media_file(source, _context=_context)
        metadata = filesystem_metadata(source)
        source_descriptor = _open_source_without_atime(source, context=_context)
        source_info = os.fstat(source_descriptor)
        if _fingerprint(source_info) != before:
            raise ValueError(f"{_context} source changed before atime-safe copy")
        if opened_destination is None:
            destination_flags = os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
            destination_flags |= os.O_CREAT | os.O_EXCL
            opened_destination = os.open(destination, destination_flags, metadata.mode)
        destination_info = os.fstat(opened_destination)
        destination_path_info = os.stat(destination, follow_symlinks=False)
        destination_identity = (destination_info.st_dev, destination_info.st_ino)
        if destination_identity != (
            destination_path_info.st_dev,
            destination_path_info.st_ino,
        ):
            raise ValueError(f"{_context} candidate destination changed")
        os.ftruncate(opened_destination, 0)
        os.lseek(opened_destination, 0, os.SEEK_SET)
        while chunk := os.read(source_descriptor, 1024 * 1024):
            remaining = memoryview(chunk)
            while remaining:
                written = os.write(opened_destination, remaining)
                if written <= 0:
                    raise OSError(f"{_context} destination write failed")
                remaining = remaining[written:]
        _apply_copied_metadata_descriptor(opened_destination, before, metadata)
        os.fsync(opened_destination)
    finally:
        if source_descriptor is not None:
            os.close(source_descriptor)
        if opened_destination is not None:
            os.close(opened_destination)

    assert before is not None and metadata is not None
    destination_after = os.stat(destination, follow_symlinks=False)
    if destination_identity != (destination_after.st_dev, destination_after.st_ino):
        raise ValueError(f"{_context} candidate destination changed")
    verify_candidate_metadata(destination, metadata)
    after = fingerprint_media_file(source, _context=_context)
    if after != before or filesystem_metadata(source) != metadata:
        raise ValueError(f"{_context} source changed during atime-safe copy")


def _open_source_without_atime(path: bytes, *, context: str) -> int:
    no_atime = getattr(os, "O_NOATIME", None)
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_atime is None or no_follow is None:
        raise AtimeSafeCopyError(f"{context} atime-safe file copy is unsupported")
    try:
        return os.open(path, os.O_RDONLY | no_atime | no_follow)
    except OSError as error:
        raise AtimeSafeCopyError(
            f"{context} atime-safe file copy is unsupported"
        ) from error


def _apply_copied_metadata_descriptor(
    destination: int,
    source_fingerprint: MediaFileFingerprint,
    source_metadata: FilesystemMetadata,
) -> None:
    current = os.fstat(destination)
    if (current.st_uid, current.st_gid) != (source_metadata.uid, source_metadata.gid):
        os.fchown(destination, source_metadata.uid, source_metadata.gid)
    os.fchmod(destination, source_metadata.mode)
    expected_xattrs = {name: value for name, value in source_metadata.xattrs}
    try:
        for name in os.listxattr(destination):
            encoded = os.fsencode(name)
            if encoded not in expected_xattrs:
                os.removexattr(destination, name)
        for name, value in source_metadata.xattrs:
            os.setxattr(destination, name, value)
    except (AttributeError, NotImplementedError):
        if expected_xattrs:
            raise ValueError("filesystem metadata cannot be preserved safely") from None
    os.utime(destination, ns=(source_metadata.atime_ns, source_fingerprint.mtime_ns))


@contextmanager
def _read_mediafile_without_atime(path: bytes):
    no_atime = getattr(os, "O_NOATIME", None)
    if no_atime is None:
        raise OSError("atime-safe media reads are unsupported")
    flags = os.O_RDONLY | no_atime | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        yield MediaFile(stream)


def filesystem_metadata(path: bytes) -> FilesystemMetadata:
    info = os.stat(path, follow_symlinks=False)
    try:
        names = sorted(os.listxattr(path, follow_symlinks=False))
        xattrs = tuple(
            (os.fsencode(name), os.getxattr(path, name, follow_symlinks=False))
            for name in names
        )
    except (AttributeError, NotImplementedError):
        xattrs = ()
    return FilesystemMetadata(
        stat.S_IMODE(info.st_mode),
        info.st_uid,
        info.st_gid,
        info.st_atime_ns,
        xattrs,
        info.st_size,
    )


def verify_candidate_metadata(path: bytes, expected: FilesystemMetadata) -> None:
    current = filesystem_metadata(path)
    if (
        current.mode != expected.mode
        or current.uid != expected.uid
        or current.gid != expected.gid
        or current.atime_ns != expected.atime_ns
        or current.xattrs != expected.xattrs
    ):
        raise ValueError("filesystem metadata cannot be preserved safely")


def digest_regular_file_without_atime(path: bytes) -> bytes:
    """Hash one regular file without following links or advancing source atime."""
    no_atime = getattr(os, "O_NOATIME", None)
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_atime is None or no_follow is None:
        raise OSError("atime-safe file reads are unsupported")
    descriptor = os.open(path, os.O_RDONLY | no_atime | no_follow)
    digest = hashlib.sha256()
    with os.fdopen(descriptor, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def freeze_media_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool, bytes)):
        return value
    if isinstance(value, (date, datetime)):
        return (type(value).__name__, value.isoformat())
    if isinstance(value, (tuple, list)):
        return tuple(freeze_media_value(entry) for entry in value)
    if isinstance(value, dict):
        return tuple(
            sorted(
                (freeze_media_value(key), freeze_media_value(entry))
                for key, entry in value.items()
            )
        )
    data = getattr(value, "data", None)
    if isinstance(data, bytes):
        return (
            type(value).__module__,
            type(value).__name__,
            hashlib.sha256(data).hexdigest(),
            freeze_media_value(getattr(value, "type", None)),
            freeze_media_value(getattr(value, "mime_type", None)),
            freeze_media_value(getattr(value, "desc", None)),
        )
    raise TypeError("media tag contains an unsupported logical value")


def _fingerprint(info: os.stat_result) -> MediaFileFingerprint:
    return MediaFileFingerprint(
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_nlink,
    )
