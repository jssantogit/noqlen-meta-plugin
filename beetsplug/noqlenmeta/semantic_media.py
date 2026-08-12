"""Lossless MediaFile descriptors for canonical semantic multivalues."""

from __future__ import annotations

from types import MappingProxyType

from mediafile import (
    ASFStorageStyle,
    ListMediaField,
    ListStorageStyle,
    MediaField,
    MP3ListDescStorageStyle,
    MP4ListStorageStyle,
)


def _descriptor(key: str) -> ListMediaField:
    return ListMediaField(
        MP3ListDescStorageStyle(desc=key, split_v23=True),
        MP4ListStorageStyle(f"----:com.apple.iTunes:{key}"),
        ListStorageStyle(key),
        ASFStorageStyle(f"Noqlen/{key}"),
    )


SEMANTIC_MEDIA_FIELDS: MappingProxyType[str, MediaField] = MappingProxyType(
    {
        field: _descriptor(f"NOQLEN_{field.upper()}")
        for field in (
            "styles",
            "moods",
            "lyrics_languages",
            "artist_languages",
            "artist_countries",
            "artist_areas",
        )
    }
)
