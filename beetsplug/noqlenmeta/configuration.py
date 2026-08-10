"""Public configuration defaults for Noqlen Meta."""

from __future__ import annotations

from collections.abc import Mapping
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
            "moods": True,
            "bpm": True,
            "lyrics_languages": True,
            "artist_countries": True,
            "artist_areas": False,
            "artist_languages": True,
            "lyrics": False,
            "synced_lyrics": False,
            "cover": True,
        },
        "providers": {
            "discogs": {
                "enabled": False,
                "user_token": "",
            },
            "musicbrainz": {
                "enabled": True,
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
        "local_analysis": {
            "bpm": {"enabled": True, "mode": "fallback"},
            "mood": {"enabled": False},
        },
    }


def validate_local_analysis_config(value: object) -> None:
    """Validate the inert Foundation analysis structure without loading a backend."""
    if not isinstance(value, Mapping) or set(value) != {"bpm", "mood"}:
        raise ValueError("local_analysis must contain bpm and mood sections")
    bpm = value["bpm"]
    mood = value["mood"]
    if not isinstance(bpm, Mapping) or set(bpm) != {"enabled", "mode"}:
        raise ValueError("local_analysis.bpm is invalid")
    if type(bpm["enabled"]) is not bool or bpm["mode"] != "fallback":
        raise ValueError("local_analysis.bpm is invalid")
    if not isinstance(mood, Mapping) or set(mood) != {"enabled"}:
        raise ValueError("local_analysis.mood is invalid")
    if type(mood["enabled"]) is not bool:
        raise ValueError("local_analysis.mood is invalid")
