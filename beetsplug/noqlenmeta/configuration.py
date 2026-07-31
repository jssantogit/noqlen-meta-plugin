"""Public configuration defaults for Noqlen Meta."""

from __future__ import annotations

from typing import Any


def default_config() -> dict[str, Any]:
    """Return a fresh complete configuration tree for one plugin instance."""
    return {
        "preview": True,
        "apply": False,
        "apply_mode": "strict",
        "identity": {
            "enabled": False,
            "preview": True,
            "apply": False,
        },
        "fields": {
            "genres": True,
            "styles": True,
            "labels": True,
            "catalog_numbers": True,
            "barcodes": True,
            "country": True,
            "year": True,
            "media": True,
            "format_descriptions": True,
            "mood": False,
            "lyrics": False,
            "synced_lyrics": False,
            "cover": False,
        },
        "providers": {
            "discogs": {
                "enabled": False,
                "user_token": "",
            },
            "musicbrainz": {
                "enabled": False,
            },
            "lastfm": {
                "enabled": False,
            },
            "itunes": {
                "enabled": False,
                "storefront": "us",
            },
            "lrclib": {
                "enabled": False,
            },
        },
        "resolution": {
            "authority": {},
            "min_confidence": {},
            "preserve_existing": {},
        },
    }
