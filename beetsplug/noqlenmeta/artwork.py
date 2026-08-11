"""Artwork configuration and immutable domain values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from beetsplug.noqlenmeta.configuration import validate_artwork_config


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


def artwork_settings_from_config(value: object) -> ArtworkSettings:
    """Validate public artwork configuration and return immutable settings."""
    validate_artwork_config(value)
    assert isinstance(value, Mapping)
    return ArtworkSettings(
        size=ArtworkSize(value["size"]),
        replace_existing=value["replace_existing"],
    )
