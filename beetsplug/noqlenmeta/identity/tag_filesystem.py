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
