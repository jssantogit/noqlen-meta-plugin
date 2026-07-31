"""Path-private filesystem and MediaFile snapshots for identity tag synchronization."""

from __future__ import annotations

import hashlib
import os
import stat
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime

from mediafile import MediaFile

from .tag_sync import IDENTITY_TAG_FIELDS


@dataclass(frozen=True, slots=True)
class IdentityTagFileFingerprint:
    device: int
    inode: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    link_count: int


@dataclass(frozen=True, slots=True)
class IdentityTagFilesystemMetadata:
    mode: int
    uid: int
    gid: int
    atime_ns: int
    xattrs: tuple[tuple[bytes, bytes], ...]


@dataclass(frozen=True, slots=True)
class IdentityTagFileSnapshot:
    fingerprint: IdentityTagFileFingerprint
    identity_values: tuple[tuple[str, object], ...] = field(repr=False)
    unrelated_values: tuple[tuple[str, object], ...] = field(repr=False)
    format_name: str | None
    filesystem_metadata: IdentityTagFilesystemMetadata


class IdentityTagAtimeCopyError(RuntimeError):
    pass


def fingerprint_identity_tag_file(path: bytes) -> IdentityTagFileFingerprint:
    info = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("identity tag file is not a regular file")
    if info.st_nlink != 1:
        raise ValueError("identity tag file has multiple hard links")
    return _fingerprint(info)


def snapshot_identity_tag_file(path: bytes) -> IdentityTagFileSnapshot:
    before = fingerprint_identity_tag_file(path)
    metadata = filesystem_metadata(path)
    with _read_mediafile_without_atime(path) as media:
        identity = tuple(
            (field, freeze_media_value(getattr(media, field)))
            for field in IDENTITY_TAG_FIELDS
        )
        unrelated_values = []
        for media_field in sorted(MediaFile.fields()):
            if media_field in IDENTITY_TAG_FIELDS:
                continue
            try:
                value = freeze_media_value(getattr(media, media_field))
            except Exception:
                continue
            unrelated_values.append((media_field, value))
        unrelated = tuple(unrelated_values)
        format_name = media.format
    after = fingerprint_identity_tag_file(path)
    if after != before:
        raise ValueError("identity tag source changed while reading")
    return IdentityTagFileSnapshot(before, identity, unrelated, format_name, metadata)


def copy_regular_file_without_source_atime(
    source: bytes,
    destination: bytes,
    *,
    destination_exists: bool,
    destination_descriptor: int | None = None,
) -> None:
    """Copy one regular file without allowing the source read to advance atime."""
    if destination_exists and destination_descriptor is None:
        raise ValueError("identity tag existing destination descriptor is required")
    before: IdentityTagFileFingerprint | None = None
    metadata: IdentityTagFilesystemMetadata | None = None
    source_descriptor: int | None = None
    opened_destination = destination_descriptor
    destination_identity: tuple[int, int] | None = None
    try:
        before = fingerprint_identity_tag_file(source)
        metadata = filesystem_metadata(source)
        source_descriptor = _open_source_without_atime(source)
        source_info = os.fstat(source_descriptor)
        if _fingerprint(source_info) != before:
            raise ValueError("identity tag source changed before atime-safe copy")
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
            raise ValueError("identity tag candidate destination changed")
        os.ftruncate(opened_destination, 0)
        os.lseek(opened_destination, 0, os.SEEK_SET)
        while chunk := os.read(source_descriptor, 1024 * 1024):
            remaining = memoryview(chunk)
            while remaining:
                written = os.write(opened_destination, remaining)
                if written <= 0:
                    raise OSError("identity tag destination write failed")
                remaining = remaining[written:]
        _apply_copied_metadata_descriptor(
            opened_destination, before, metadata
        )
        os.fsync(opened_destination)
    finally:
        if source_descriptor is not None:
            os.close(source_descriptor)
        if opened_destination is not None:
            os.close(opened_destination)

    assert before is not None and metadata is not None
    destination_after = os.stat(destination, follow_symlinks=False)
    if destination_identity != (destination_after.st_dev, destination_after.st_ino):
        raise ValueError("identity tag candidate destination changed")
    verify_candidate_metadata(destination, metadata)
    after = fingerprint_identity_tag_file(source)
    if after != before or filesystem_metadata(source) != metadata:
        raise ValueError("identity tag source changed during atime-safe copy")


def _open_source_without_atime(path: bytes) -> int:
    no_atime = getattr(os, "O_NOATIME", None)
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_atime is None or no_follow is None:
        raise IdentityTagAtimeCopyError(
            "identity tag atime-safe file copy is unsupported"
        )
    try:
        return os.open(path, os.O_RDONLY | no_atime | no_follow)
    except OSError as error:
        raise IdentityTagAtimeCopyError(
            "identity tag atime-safe file copy is unsupported"
        ) from error


def _apply_copied_metadata_descriptor(
    destination: int,
    source_fingerprint: IdentityTagFileFingerprint,
    source_metadata: IdentityTagFilesystemMetadata,
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
    flags = os.O_RDONLY | no_atime
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        yield MediaFile(stream)


def filesystem_metadata(path: bytes) -> IdentityTagFilesystemMetadata:
    info = os.stat(path, follow_symlinks=False)
    try:
        names = sorted(os.listxattr(path, follow_symlinks=False))
        xattrs = tuple(
            (os.fsencode(name), os.getxattr(path, name, follow_symlinks=False)) for name in names
        )
    except (AttributeError, NotImplementedError):
        xattrs = ()
    return IdentityTagFilesystemMetadata(
        stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid, info.st_atime_ns, xattrs
    )


def verify_candidate_metadata(
    path: bytes, expected: IdentityTagFilesystemMetadata
) -> None:
    current = filesystem_metadata(path)
    if (
        current.mode != expected.mode
        or current.uid != expected.uid
        or current.gid != expected.gid
        or current.atime_ns != expected.atime_ns
        or current.xattrs != expected.xattrs
    ):
        raise ValueError("filesystem metadata cannot be preserved safely")


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
    raise TypeError("identity tag contains an unsupported logical value")


def _fingerprint(info: os.stat_result) -> IdentityTagFileFingerprint:
    return IdentityTagFileFingerprint(
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_nlink,
    )
