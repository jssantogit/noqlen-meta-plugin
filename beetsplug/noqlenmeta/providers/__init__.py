"""Production metadata provider contracts."""

from beetsplug.noqlenmeta.providers.base import (
    ArtistMetadataProvider,
    ProviderError,
    ReleaseMetadataProvider,
    TrackMetadataProvider,
)

__all__ = [
    "ArtistMetadataProvider",
    "ProviderError",
    "ReleaseMetadataProvider",
    "TrackMetadataProvider",
]
