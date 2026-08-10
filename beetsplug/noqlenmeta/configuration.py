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
        "acoustid": {
            "enabled": False,
            "reuse_existing": True,
            "compute_missing": False,
            "lookup": True,
            "use_for_identity": True,
            "min_score": 0.90,
            "min_margin": 0.05,
            "max_results": 5,
            "max_recordings_per_result": 10,
            "timeout_seconds": 15.0,
            "requests_per_second": 3.0,
            "cache_entries": 256,
            "fpcalc": "fpcalc",
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
