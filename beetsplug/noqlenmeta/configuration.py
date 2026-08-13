"""Public configuration defaults for Noqlen Meta."""

from __future__ import annotations

import math
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
            "date": True,
            "original_date": True,
            "release_type": True,
            "release_secondary_types": True,
            "release_status": True,
            "edition": True,
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
            "isrcs": True,
            "works": True,
            "iswcs": True,
            "recording_date": True,
        },
        "genres": {
            "num_genres": 1,
            "promote_styles": True,
        },
        "moods": {
            "max_moods": 1,
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
            "coverartarchive": {
                "enabled": True,
            },
        },
        "artwork": {
            "size": "original",
            "replace_existing": False,
        },
        "bpm": {
            "round": False,
            "recalculate_existing": False,
            "octave_normalization": False,
            "octave_range": {"min": 70, "max": 180},
        },
        "resolution": {
            "authority": {},
            "min_confidence": {},
            "preserve_existing": {},
        },
        "local_analysis": {
            "bpm": {
                "enabled": False,
                "analysis_mode": "full",
                "window_seconds": 90,
            },
            "mood": {"enabled": False},
        },
    }


def _finite_positive_number(value: object) -> bool:
    return type(value) in {int, float} and math.isfinite(value) and value > 0


def validate_artwork_config(value: object) -> None:
    """Validate the public artwork policy."""
    if not isinstance(value, Mapping) or set(value) != {"size", "replace_existing"}:
        raise ValueError("artwork configuration is invalid")
    if value["size"] not in {"original", "1200", "500", "250"}:
        raise ValueError("artwork.size is invalid")
    if type(value["replace_existing"]) is not bool:
        raise ValueError("artwork.replace_existing must be a boolean")


def validate_bpm_config(value: object) -> None:
    """Validate the public BPM persistence policy."""
    expected = {"round", "recalculate_existing", "octave_normalization", "octave_range"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("bpm configuration is invalid")
    for key in ("round", "recalculate_existing", "octave_normalization"):
        if type(value[key]) is not bool:
            raise ValueError(f"bpm.{key} must be a boolean")
    octave_range = value["octave_range"]
    if not isinstance(octave_range, Mapping) or set(octave_range) != {"min", "max"}:
        raise ValueError("bpm.octave_range is invalid")
    minimum = octave_range["min"]
    maximum = octave_range["max"]
    if not _finite_positive_number(minimum) or not _finite_positive_number(maximum):
        raise ValueError("bpm.octave_range bounds must be finite positive numbers")
    if minimum >= maximum:
        raise ValueError("bpm.octave_range.min must be less than max")


def validate_local_bpm_config(value: object) -> None:
    """Validate local BPM analysis without loading its optional backend."""
    expected = {"enabled", "analysis_mode", "window_seconds"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("local_analysis.bpm is invalid")
    if type(value["enabled"]) is not bool:
        raise ValueError("local_analysis.bpm.enabled must be a boolean")
    if value["analysis_mode"] not in {"full", "window"}:
        raise ValueError("local_analysis.bpm.analysis_mode is invalid")
    if not _finite_positive_number(value["window_seconds"]):
        raise ValueError("local_analysis.bpm.window_seconds must be finite and positive")


def validate_local_analysis_config(value: object) -> None:
    """Validate local analysis configuration without loading optional backends."""
    if not isinstance(value, Mapping) or set(value) != {"bpm", "mood"}:
        raise ValueError("local_analysis must contain bpm and mood sections")
    bpm = value["bpm"]
    mood = value["mood"]
    validate_local_bpm_config(bpm)
    if not isinstance(mood, Mapping) or set(mood) != {"enabled"}:
        raise ValueError("local_analysis.mood is invalid")
    if type(mood["enabled"]) is not bool:
        raise ValueError("local_analysis.mood is invalid")
