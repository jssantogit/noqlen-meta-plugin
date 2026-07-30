from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class IdentityVerdict(Enum):
    CONFIRMED = "confirmed"
    MISSING = "missing"
    CONFLICT = "conflict"
    AMBIGUOUS = "ambiguous"


class IdentityFieldStatus(Enum):
    CONFIRMED = "confirmed"
    MISSING = "missing"
    CONFLICT = "conflict"


class IdentityAuditError(RuntimeError):
    """Raised when an identity input or internal contract is invalid."""


def canonical_mbid(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return str(UUID(value.strip()))
    except (AttributeError, ValueError):
        return None


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not (cleaned := value.strip()):
        raise ValueError(f"{field} must be a non-empty string")
    return cleaned


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string or None")
    return value.strip() or None


def _positive_length(value: object, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be finite and positive")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{field} must be finite and positive")
    return result


def _positive_position(value: object, field: str, *, required: bool = False) -> int | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _existing_value(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string or None")
    return value.strip() or None


@dataclass(frozen=True, slots=True)
class IdentityTrackContext:
    local_key: str
    artist: str
    title: str
    length: float | None = None
    medium: int | None = None
    medium_index: int | None = None
    index: int | None = None
    current_recording_mbid: str | None = None
    current_release_track_mbid: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "local_key", _required_text(self.local_key, "local key"))
        object.__setattr__(self, "artist", _required_text(self.artist, "track artist"))
        object.__setattr__(self, "title", _required_text(self.title, "track title"))
        object.__setattr__(self, "length", _positive_length(self.length, "track length"))
        for field in ("medium", "medium_index", "index"):
            object.__setattr__(self, field, _positive_position(getattr(self, field), field))
        object.__setattr__(
            self,
            "current_recording_mbid",
            _existing_value(self.current_recording_mbid, "current recording MBID"),
        )
        object.__setattr__(
            self,
            "current_release_track_mbid",
            _existing_value(self.current_release_track_mbid, "current release-track MBID"),
        )


@dataclass(frozen=True, slots=True)
class IdentityAlbumContext:
    album_artist: str
    album: str
    tracks: tuple[IdentityTrackContext, ...]
    current_release_mbids: tuple[str, ...] = ()
    current_release_group_mbids: tuple[str, ...] = ()
    year: int | None = None
    country: str | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "album_artist", _required_text(self.album_artist, "album artist")
        )
        object.__setattr__(self, "album", _required_text(self.album, "album title"))
        tracks = tuple(self.tracks)
        if not tracks or any(not isinstance(track, IdentityTrackContext) for track in tracks):
            raise ValueError("tracks must contain at least one IdentityTrackContext")
        keys = [track.local_key for track in tracks]
        if len(keys) != len(set(keys)):
            raise ValueError("local keys must be unique")
        object.__setattr__(self, "tracks", tracks)
        for field in ("current_release_mbids", "current_release_group_mbids"):
            values = tuple(
                cleaned
                for value in getattr(self, field)
                if (cleaned := _existing_value(value, field)) is not None
            )
            object.__setattr__(self, field, values)
        if self.year is not None:
            object.__setattr__(self, "year", _positive_position(self.year, "year"))
        object.__setattr__(self, "country", _optional_text(self.country, "country"))
        object.__setattr__(self, "label", _optional_text(self.label, "label"))


@dataclass(frozen=True, slots=True)
class MusicBrainzTrackIdentity:
    recording_mbid: str
    release_track_mbid: str
    artist: str
    title: str
    length: float | None
    medium: int
    medium_index: int
    index: int

    def __post_init__(self) -> None:
        for field in ("recording_mbid", "release_track_mbid"):
            if (canonical := canonical_mbid(getattr(self, field))) is None:
                raise IdentityAuditError(f"candidate {field} is invalid")
            object.__setattr__(self, field, canonical)
        object.__setattr__(self, "artist", _required_text(self.artist, "candidate artist"))
        object.__setattr__(self, "title", _required_text(self.title, "candidate title"))
        object.__setattr__(self, "length", _positive_length(self.length, "candidate length"))
        for field in ("medium", "medium_index", "index"):
            object.__setattr__(
                self, field, _positive_position(getattr(self, field), field, required=True)
            )


@dataclass(frozen=True, slots=True)
class MusicBrainzReleaseIdentity:
    release_mbid: str
    release_group_mbid: str
    album_artist: str
    album: str
    tracks: tuple[MusicBrainzTrackIdentity, ...]
    status: str | None = None
    country: str | None = None
    year: int | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        for field in ("release_mbid", "release_group_mbid"):
            if (canonical := canonical_mbid(getattr(self, field))) is None:
                raise IdentityAuditError(f"candidate {field} is invalid")
            object.__setattr__(self, field, canonical)
        object.__setattr__(
            self, "album_artist", _required_text(self.album_artist, "candidate album artist")
        )
        object.__setattr__(self, "album", _required_text(self.album, "candidate album title"))
        tracks = tuple(self.tracks)
        if not tracks or any(not isinstance(track, MusicBrainzTrackIdentity) for track in tracks):
            raise IdentityAuditError("candidate must contain complete track identities")
        object.__setattr__(self, "tracks", tracks)
        for field in ("status", "country", "label"):
            object.__setattr__(self, field, _optional_text(getattr(self, field), field))
        if self.year is not None:
            object.__setattr__(self, "year", _positive_position(self.year, "year"))


@dataclass(frozen=True, slots=True)
class IdentityAuditPolicy:
    minimum_score: float = 90.0
    minimum_margin: float = 5.0
    minimum_pair_score: float = 75.0
    require_all_local_tracks_assigned: bool = True
    singleton_minimum_score: float = 95.0
    singleton_minimum_margin: float = 8.0

    def __post_init__(self) -> None:
        for field in (
            "minimum_score",
            "minimum_margin",
            "minimum_pair_score",
            "singleton_minimum_score",
            "singleton_minimum_margin",
        ):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{field} must be between 0 and 100")
            value = float(value)
            if not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError(f"{field} must be between 0 and 100")
            object.__setattr__(self, field, value)
        if not isinstance(self.require_all_local_tracks_assigned, bool):
            raise ValueError("require_all_local_tracks_assigned must be boolean")


@dataclass(frozen=True, slots=True)
class IdentityFieldFinding:
    field: str
    scope_key: str | None
    current_value: str | None
    expected_value: str
    status: IdentityFieldStatus
