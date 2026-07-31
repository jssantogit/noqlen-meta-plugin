"""Selected beets importer boundary for MusicBrainz identity audits."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from math import isfinite

from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.importer.actions import Action
from beets.library import Item

from .audit import (
    DEFAULT_IDENTITY_AUDIT_POLICY,
    IdentityAuditResult,
    MusicBrainzIdentitySource,
    audit_with_musicbrainz_source,
)
from .domain import IdentityAlbumContext, IdentityAuditPolicy, IdentityTrackContext

MISSING_ALBUM_ID_MARKER = "__noqlen_missing_mb_albumid__"
MISSING_RELEASE_GROUP_ID_MARKER = "__noqlen_missing_mb_releasegroupid__"
_MALFORMED_IDENTITY_MARKER = "__noqlen_malformed_identity__"
_IDENTITY_FIELDS = (
    "mb_albumid",
    "mb_releasegroupid",
    "mb_trackid",
    "mb_releasetrackid",
)
_CACHE_FIELDS = ("raw_data", "item_data")


class IdentityImportMatchKind(Enum):
    ALBUM = "album"
    TRACK = "track"


@dataclass(frozen=True, slots=True)
class SelectedIdentityTrack:
    local_key: str
    item: Item
    track_info: TrackInfo

    def __post_init__(self) -> None:
        if not isinstance(self.local_key, str) or not self.local_key:
            raise ValueError("identity local key must be a non-empty string")
        if type(self.item) is not Item:
            raise TypeError("selected identity Item has an unsupported type")
        if type(self.track_info) is not TrackInfo:
            raise TypeError("selected identity TrackInfo has an unsupported type")


@dataclass(frozen=True, slots=True)
class SelectedImportIdentity:
    kind: IdentityImportMatchKind
    tracks: tuple[SelectedIdentityTrack, ...]
    album_info: AlbumInfo | None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, IdentityImportMatchKind):
            raise TypeError("selected identity match kind is invalid")
        tracks = tuple(self.tracks)
        if not tracks or any(type(track) is not SelectedIdentityTrack for track in tracks):
            raise ValueError("selected identity tracks are invalid")
        keys = [track.local_key for track in tracks]
        if len(keys) != len(set(keys)):
            raise ValueError("selected identity local keys must be unique")
        if self.kind is IdentityImportMatchKind.ALBUM:
            if type(self.album_info) is not AlbumInfo:
                raise TypeError("album identity requires a supported AlbumInfo")
        elif len(tracks) != 1 or self.album_info is not None:
            raise ValueError("track identity requires one track and no AlbumInfo")
        object.__setattr__(self, "tracks", tracks)


@dataclass(frozen=True, slots=True)
class ImportIdentityAuditResult:
    selected: SelectedImportIdentity
    context: IdentityAlbumContext
    audit: IdentityAuditResult


@dataclass(frozen=True, slots=True)
class _CacheSnapshot:
    target: AlbumInfo | TrackInfo
    values: tuple[tuple[str, object], ...]


def selected_import_identity(task: object) -> SelectedImportIdentity | None:
    """Retain only the already-selected beets match and mapped pairs."""
    if getattr(task, "choice_flag", None) is not Action.APPLY:
        return None
    match = getattr(task, "match", None)
    if type(match) is AlbumMatch:
        tracks = tuple(
            SelectedIdentityTrack(f"track:{index:04d}", item, track_info)
            for index, (item, track_info) in enumerate(match.mapping.items(), start=1)
        )
        if not tracks:
            return None
        return SelectedImportIdentity(IdentityImportMatchKind.ALBUM, tracks, match.info)
    if type(match) is TrackMatch:
        return SelectedImportIdentity(
            IdentityImportMatchKind.TRACK,
            (SelectedIdentityTrack("track:0001", match.item, match.info),),
            None,
        )
    return None


@contextmanager
def _fresh_selected_identity_caches(
    selected: SelectedImportIdentity,
) -> Iterator[None]:
    """Recompute beets application surfaces and restore exact prior caches."""
    targets: tuple[AlbumInfo | TrackInfo, ...] = tuple(
        ([selected.album_info] if selected.album_info is not None else [])
        + [track.track_info for track in selected.tracks]
    )
    snapshots = tuple(
        _CacheSnapshot(
            target,
            tuple((key, target.__dict__[key]) for key in _CACHE_FIELDS if key in target.__dict__),
        )
        for target in targets
    )
    for snapshot in snapshots:
        for key in _CACHE_FIELDS:
            snapshot.target.__dict__.pop(key, None)
    try:
        yield
    finally:
        for snapshot in snapshots:
            for key in _CACHE_FIELDS:
                snapshot.target.__dict__.pop(key, None)
            snapshot.target.__dict__.update(snapshot.values)


def identity_context_from_selected_import(
    selected: SelectedImportIdentity,
    *,
    from_scratch: bool,
) -> IdentityAlbumContext | None:
    """Predict the identity normal beets would apply before Noqlen repair."""
    if type(selected) is not SelectedImportIdentity:
        raise TypeError("identity context requires a selected import identity")
    if type(from_scratch) is not bool:
        raise TypeError("from_scratch must be a bool")

    with _fresh_selected_identity_caches(selected):
        application_data = _selected_application_data(selected)

    effective = tuple(
        _effective_item_identity(track.item, data, from_scratch=from_scratch)
        for track, data in zip(selected.tracks, application_data, strict=True)
    )
    if selected.kind is IdentityImportMatchKind.ALBUM:
        return _album_context(selected, effective)
    return _singleton_context(selected, effective[0])


def audit_selected_import_identity(
    selected: SelectedImportIdentity,
    source: MusicBrainzIdentitySource,
    *,
    from_scratch: bool,
    policy: IdentityAuditPolicy = DEFAULT_IDENTITY_AUDIT_POLICY,
) -> ImportIdentityAuditResult | None:
    """Build one selected context and run one Block 024 identity audit."""
    context = identity_context_from_selected_import(selected, from_scratch=from_scratch)
    if context is None:
        return None
    audit = audit_with_musicbrainz_source(context, source, policy=policy)
    return ImportIdentityAuditResult(selected, context, audit)


def _selected_application_data(
    selected: SelectedImportIdentity,
) -> tuple[dict[str, object], ...]:
    if selected.kind is IdentityImportMatchKind.ALBUM:
        assert selected.album_info is not None
        return tuple(
            dict(track.track_info.merge_with_album(selected.album_info))
            for track in selected.tracks
        )
    return (dict(selected.tracks[0].track_info.item_data),)


def _effective_item_identity(
    item: Item,
    application_data: dict[str, object],
    *,
    from_scratch: bool,
) -> dict[str, str | None]:
    values: dict[str, object] = {}
    if not from_scratch:
        values.update(
            (field, item.get(field, None, with_album=False)) for field in _IDENTITY_FIELDS
        )
    for field in _IDENTITY_FIELDS:
        if field in application_data:
            values[field] = application_data[field]
    return {field: _existing_identity(values.get(field)) for field in _IDENTITY_FIELDS}


def _album_context(
    selected: SelectedImportIdentity,
    effective: tuple[dict[str, str | None], ...],
) -> IdentityAlbumContext | None:
    assert selected.album_info is not None
    album_artist = _text(selected.album_info.artist)
    album = _text(selected.album_info.album)
    if album_artist is None or album is None:
        return None
    tracks: list[IdentityTrackContext] = []
    for selected_track, current in zip(selected.tracks, effective, strict=True):
        info = selected_track.track_info
        title = _text(info.title)
        if title is None:
            return None
        tracks.append(
            IdentityTrackContext(
                local_key=selected_track.local_key,
                artist=_text(getattr(info, "artist", None)) or album_artist,
                title=title,
                length=_length(getattr(info, "length", None)),
                medium=_position(getattr(info, "medium", None)),
                medium_index=_position(getattr(info, "medium_index", None)),
                index=_position(getattr(info, "index", None)),
                current_recording_mbid=current["mb_trackid"],
                current_release_track_mbid=current["mb_releasetrackid"],
            )
        )
    return IdentityAlbumContext(
        album_artist=album_artist,
        album=album,
        tracks=tuple(tracks),
        current_release_mbids=_aggregate_album_identity(
            effective, "mb_albumid", MISSING_ALBUM_ID_MARKER
        ),
        current_release_group_mbids=_aggregate_album_identity(
            effective, "mb_releasegroupid", MISSING_RELEASE_GROUP_ID_MARKER
        ),
        year=_position(getattr(selected.album_info, "year", None)),
        country=_text(getattr(selected.album_info, "country", None)),
        label=_text(getattr(selected.album_info, "label", None)),
    )


def _singleton_context(
    selected: SelectedImportIdentity,
    current: dict[str, str | None],
) -> IdentityAlbumContext | None:
    selected_track = selected.tracks[0]
    info = selected_track.track_info
    title = _text(info.title)
    artist = _text(getattr(info, "artist", None)) or _text(
        selected_track.item.get("artist", None, with_album=False)
    )
    if title is None or artist is None:
        return None
    album = (
        _text(getattr(info, "album", None))
        or _text(selected_track.item.get("album", None, with_album=False))
        or title
    )
    track = IdentityTrackContext(
        local_key=selected_track.local_key,
        artist=artist,
        title=title,
        length=_length(getattr(info, "length", None)),
        medium=_position(getattr(info, "medium", None)),
        medium_index=_position(getattr(info, "medium_index", None)),
        index=_position(getattr(info, "index", None)),
        current_recording_mbid=current["mb_trackid"],
        current_release_track_mbid=current["mb_releasetrackid"],
    )
    return IdentityAlbumContext(
        album_artist=artist,
        album=album,
        tracks=(track,),
        current_release_mbids=(current["mb_albumid"],) if current["mb_albumid"] else (),
        current_release_group_mbids=(current["mb_releasegroupid"],)
        if current["mb_releasegroupid"]
        else (),
    )


def _aggregate_album_identity(
    effective: tuple[dict[str, str | None], ...], field: str, marker: str
) -> tuple[str, ...]:
    values = tuple(item[field] for item in effective)
    if all(value is None for value in values):
        return ()
    if all(value is not None for value in values):
        return tuple(value for value in values if value is not None)
    return tuple(value if value is not None else marker for value in values)


def _existing_identity(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    return _MALFORMED_IDENTITY_MARKER


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _length(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if result > 0 and isfinite(result) else None


def _position(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None
