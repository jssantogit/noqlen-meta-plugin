"""Identity-specific logical snapshots over generic safe media primitives."""

from __future__ import annotations

import os as os
from dataclasses import dataclass, field

from mediafile import MediaFile

from beetsplug.noqlenmeta.media_snapshot import (
    AtimeSafeCopyError,
    FilesystemMetadata,
    MediaFileFingerprint,
    _read_mediafile_without_atime,
    filesystem_metadata,
    fingerprint_media_file,
    freeze_media_value,
)
from beetsplug.noqlenmeta.media_snapshot import (
    copy_regular_file_without_source_atime as _copy_regular_file_without_source_atime,
)
from beetsplug.noqlenmeta.media_snapshot import (
    verify_candidate_metadata as verify_candidate_metadata,
)

from .tag_sync import IDENTITY_TAG_FIELDS

IdentityTagFileFingerprint = MediaFileFingerprint
IdentityTagFilesystemMetadata = FilesystemMetadata
IdentityTagAtimeCopyError = AtimeSafeCopyError


@dataclass(frozen=True, slots=True)
class IdentityTagFileSnapshot:
    fingerprint: IdentityTagFileFingerprint
    identity_values: tuple[tuple[str, object], ...] = field(repr=False)
    unrelated_values: tuple[tuple[str, object], ...] = field(repr=False)
    format_name: str | None
    filesystem_metadata: IdentityTagFilesystemMetadata


def fingerprint_identity_tag_file(path: bytes) -> IdentityTagFileFingerprint:
    return fingerprint_media_file(path, _context="identity tag file")


def snapshot_identity_tag_file(path: bytes) -> IdentityTagFileSnapshot:
    before = fingerprint_identity_tag_file(path)
    metadata = filesystem_metadata(path)
    with _read_mediafile_without_atime(path) as media:
        identity = tuple(
            (media_field, freeze_media_value(getattr(media, media_field)))
            for media_field in IDENTITY_TAG_FIELDS
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
    _copy_regular_file_without_source_atime(
        source,
        destination,
        destination_exists=destination_exists,
        destination_descriptor=destination_descriptor,
        _context="identity tag",
    )
