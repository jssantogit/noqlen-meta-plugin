"""Fresh, immutable beets library boundary for MusicBrainz identity audits."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from beets.library import Album, Item, Library

from .audit import (
    DEFAULT_IDENTITY_AUDIT_POLICY,
    IdentityAuditResult,
    MusicBrainzIdentitySource,
    audit_with_musicbrainz_source,
)
from .domain import IdentityAlbumContext, IdentityAuditPolicy, IdentityTrackContext

_MISSING_ALBUM_ID = "__noqlen_library_missing_album_id__"
_MISSING_RELEASE_GROUP_ID = "__noqlen_library_missing_release_group_id__"
_MALFORMED_IDENTITY = "__noqlen_library_malformed_identity__"

_ALBUM_SNAPSHOT_FIELDS = (
    "id",
    "albumartist",
    "album",
    "year",
    "country",
    "label",
    "mb_albumid",
    "mb_releasegroupid",
)
_ITEM_SNAPSHOT_FIELDS = (
    "id",
    "album_id",
    "artist",
    "albumartist",
    "album",
    "title",
    "length",
    "disc",
    "track",
    "year",
    "country",
    "label",
    "mb_albumid",
    "mb_releasegroupid",
    "mb_trackid",
    "mb_releasetrackid",
)


class LibraryIdentityTargetKind(Enum):
    ALBUM = "album"
    SINGLETON = "singleton"


@dataclass(frozen=True, slots=True)
class SelectedLibraryIdentityItem:
    local_key: str
    item_id: int
    item: Item

    def __post_init__(self) -> None:
        _positive_id(self.item_id, "Item")
        if type(self.item) is not Item or self.item.id != self.item_id:
            raise TypeError("selected library identity Item is invalid")
        if self.local_key != f"library-item:{self.item_id}":
            raise ValueError("selected library identity local key is invalid")


@dataclass(frozen=True, slots=True)
class SelectedLibraryIdentityTarget:
    kind: LibraryIdentityTargetKind
    album_id: int | None
    album: Album | None
    items: tuple[SelectedLibraryIdentityItem, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, LibraryIdentityTargetKind):
            raise TypeError("library identity target kind is invalid")
        items = tuple(self.items)
        if not items or any(type(item) is not SelectedLibraryIdentityItem for item in items):
            raise ValueError("library identity target requires supported Items")
        if len({item.item_id for item in items}) != len(items):
            raise ValueError("library identity target Items are duplicated")
        if len({item.local_key for item in items}) != len(items):
            raise ValueError("library identity local keys are duplicated")
        if self.kind is LibraryIdentityTargetKind.ALBUM:
            album_id = _positive_id(self.album_id, "Album")
            if type(self.album) is not Album or self.album.id != album_id:
                raise TypeError("album identity target requires a supported Album")
            if any(item.item.album_id != album_id for item in items):
                raise ValueError("album identity target contains an unrelated Item")
        elif self.album_id is not None or self.album is not None or len(items) != 1:
            raise ValueError("singleton identity target requires one standalone Item")
        elif _optional_id(items[0].item.album_id) is not None:
            raise ValueError("singleton identity target Item belongs to an Album")
        object.__setattr__(self, "items", items)


@dataclass(frozen=True, slots=True)
class LibraryIdentityExactItemSnapshot:
    item_id: int
    album_id: int | None
    fields: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class LibraryIdentityExactSnapshot:
    kind: LibraryIdentityTargetKind
    album_id: int | None
    album_fields: tuple[tuple[str, object], ...]
    item_snapshots: tuple[LibraryIdentityExactItemSnapshot, ...]


@dataclass(frozen=True, slots=True)
class LibraryIdentityContextResult:
    selected: SelectedLibraryIdentityTarget
    exact_snapshot: LibraryIdentityExactSnapshot
    context: IdentityAlbumContext


@dataclass(frozen=True, slots=True)
class LibraryIdentityAuditResult:
    context_result: LibraryIdentityContextResult
    audit: IdentityAuditResult

    def __post_init__(self) -> None:
        if self.audit.context != self.context_result.context:
            raise ValueError("library identity audit context is inconsistent")

    @property
    def selected(self) -> SelectedLibraryIdentityTarget:
        return self.context_result.selected

    @property
    def exact_snapshot(self) -> LibraryIdentityExactSnapshot:
        return self.context_result.exact_snapshot

    @property
    def context(self) -> IdentityAlbumContext:
        return self.context_result.context


def select_library_identity_targets(
    library: Library, query: object = None
) -> tuple[SelectedLibraryIdentityTarget, ...]:
    """Select an Item query and expand it to fresh complete Albums and singletons."""
    if type(library) is not Library:
        raise TypeError("library identity selection requires a supported Library")
    matched = tuple(library.items(query))
    if any(type(item) is not Item for item in matched):
        raise TypeError("library identity query returned an unsupported Item")
    album_ids = sorted({_positive_id(item.album_id, "Album") for item in matched if item.album_id})
    singleton_ids = sorted({_positive_id(item.id, "Item") for item in matched if not item.album_id})

    albums = tuple(_fresh_album_target(library, album_id) for album_id in album_ids)
    singletons = tuple(_fresh_singleton_target(library, item_id) for item_id in singleton_ids)
    return (*albums, *singletons)


def all_library_identity_targets(library: Library) -> tuple[SelectedLibraryIdentityTarget, ...]:
    return select_library_identity_targets(library)


def refresh_library_identity_target(
    library: Library, selected: SelectedLibraryIdentityTarget
) -> SelectedLibraryIdentityTarget:
    """Re-fetch one complete target while preserving its database-ID local keys."""
    if type(selected) is not SelectedLibraryIdentityTarget:
        raise TypeError("library identity refresh requires a selected target")
    if selected.kind is LibraryIdentityTargetKind.ALBUM:
        assert selected.album_id is not None
        fresh = _fresh_album_target(library, selected.album_id)
    else:
        fresh = _fresh_singleton_target(library, selected.items[0].item_id)
    if tuple(item.item_id for item in fresh.items) != tuple(
        item.item_id for item in selected.items
    ):
        raise ValueError("library identity target membership changed")
    return fresh


def exact_snapshot_from_library_target(
    selected: SelectedLibraryIdentityTarget,
) -> LibraryIdentityExactSnapshot:
    """Capture exact path-free values used by context, comparison, mapping, and ordering."""
    album_fields: tuple[tuple[str, object], ...] = ()
    if selected.album is not None:
        album_fields = tuple(
            (field, getattr(selected.album, field)) for field in _ALBUM_SNAPSHOT_FIELDS
        )
    item_snapshots = tuple(
        LibraryIdentityExactItemSnapshot(
            selected_item.item_id,
            _optional_id(selected_item.item.album_id),
            tuple((field, getattr(selected_item.item, field)) for field in _ITEM_SNAPSHOT_FIELDS),
        )
        for selected_item in selected.items
    )
    return LibraryIdentityExactSnapshot(
        selected.kind,
        selected.album_id,
        album_fields,
        item_snapshots,
    )


def identity_context_from_library_target(
    selected: SelectedLibraryIdentityTarget,
) -> LibraryIdentityContextResult | None:
    """Build a pure Block 024 context and its independent exact stale snapshot."""
    if type(selected) is not SelectedLibraryIdentityTarget:
        raise TypeError("library identity context requires a selected target")
    snapshot = exact_snapshot_from_library_target(selected)
    context = (
        _album_context(selected)
        if selected.album is not None
        else _singleton_context(selected)
    )
    if context is None:
        return None
    return LibraryIdentityContextResult(selected, snapshot, context)


def audit_library_identity_target(
    selected: SelectedLibraryIdentityTarget,
    source: MusicBrainzIdentitySource,
    *,
    policy: IdentityAuditPolicy = DEFAULT_IDENTITY_AUDIT_POLICY,
) -> LibraryIdentityAuditResult | None:
    """Audit one complete fresh target with exactly one retained-source call."""
    context_result = identity_context_from_library_target(selected)
    if context_result is None:
        return None
    audit = audit_with_musicbrainz_source(context_result.context, source, policy=policy)
    return LibraryIdentityAuditResult(context_result, audit)


def _fresh_album_target(library: Library, album_id: int) -> SelectedLibraryIdentityTarget:
    album = library.get_album(album_id)
    if type(album) is not Album:
        raise ValueError("library identity Album no longer exists")
    album = album.get_fresh_from_db()
    items = tuple(album.items())
    if not items:
        raise ValueError("library identity Album has no Items")
    fresh_items = tuple(item.get_fresh_from_db() for item in items)
    if any(type(item) is not Item or item.album_id != album_id for item in fresh_items):
        raise ValueError("library identity Album membership changed")
    ordered = tuple(sorted(fresh_items, key=_item_order_key))
    return SelectedLibraryIdentityTarget(
        LibraryIdentityTargetKind.ALBUM,
        album_id,
        album,
        tuple(_selected_item(item) for item in ordered),
    )


def _fresh_singleton_target(library: Library, item_id: int) -> SelectedLibraryIdentityTarget:
    item = library.get_item(item_id)
    if type(item) is not Item:
        raise ValueError("library identity Item no longer exists")
    item = item.get_fresh_from_db()
    if _optional_id(item.album_id) is not None:
        raise ValueError("library identity singleton membership changed")
    return SelectedLibraryIdentityTarget(
        LibraryIdentityTargetKind.SINGLETON,
        None,
        None,
        (_selected_item(item),),
    )


def _selected_item(item: Item) -> SelectedLibraryIdentityItem:
    item_id = _positive_id(item.id, "Item")
    return SelectedLibraryIdentityItem(f"library-item:{item_id}", item_id, item)


def _album_context(selected: SelectedLibraryIdentityTarget) -> IdentityAlbumContext | None:
    assert selected.album is not None
    album_artist = _text(selected.album.albumartist)
    album_title = _text(selected.album.album)
    if album_artist is None or album_title is None:
        return None
    complete_positions = _has_complete_unique_positions(selected)
    tracks: list[IdentityTrackContext] = []
    for ordinal, selected_item in enumerate(selected.items, start=1):
        item = selected_item.item
        title = _text(item.title)
        if title is None:
            return None
        tracks.append(
            IdentityTrackContext(
                local_key=selected_item.local_key,
                artist=_text(item.artist) or album_artist,
                title=title,
                length=_length(item.length),
                medium=_position(item.disc),
                medium_index=_position(item.track),
                index=ordinal if complete_positions else None,
                current_recording_mbid=_identity(item.mb_trackid),
                current_release_track_mbid=_identity(item.mb_releasetrackid),
            )
        )
    release_values = (selected.album.mb_albumid,) + tuple(
        item.item.mb_albumid for item in selected.items
    )
    group_values = (selected.album.mb_releasegroupid,) + tuple(
        item.item.mb_releasegroupid for item in selected.items
    )
    return IdentityAlbumContext(
        album_artist,
        album_title,
        tuple(tracks),
        _aggregate_identity(release_values, _MISSING_ALBUM_ID),
        _aggregate_identity(group_values, _MISSING_RELEASE_GROUP_ID),
        _position(selected.album.year),
        _text(selected.album.country),
        _text(selected.album.label),
    )


def _singleton_context(selected: SelectedLibraryIdentityTarget) -> IdentityAlbumContext | None:
    selected_item = selected.items[0]
    item = selected_item.item
    artist = _text(item.artist)
    title = _text(item.title)
    if artist is None or title is None:
        return None
    album_title = _text(item.album) or title
    track = IdentityTrackContext(
        selected_item.local_key,
        artist,
        title,
        _length(item.length),
        _position(item.disc),
        _position(item.track),
        _position(item.track),
        _identity(item.mb_trackid),
        _identity(item.mb_releasetrackid),
    )
    return IdentityAlbumContext(
        artist,
        album_title,
        (track,),
        _single_identity(item.mb_albumid),
        _single_identity(item.mb_releasegroupid),
        _position(item.year),
        _text(item.country),
        _text(item.label),
    )


def _has_complete_unique_positions(selected: SelectedLibraryIdentityTarget) -> bool:
    positions = tuple(
        (_position(item.item.disc), _position(item.item.track)) for item in selected.items
    )
    return all(disc is not None and track is not None for disc, track in positions) and len(
        set(positions)
    ) == len(positions)


def _item_order_key(item: Item) -> tuple[int, int, int]:
    maximum = 2**63 - 1
    return (_position(item.disc) or maximum, _position(item.track) or maximum, item.id)


def _aggregate_identity(values: tuple[object, ...], marker: str) -> tuple[str, ...]:
    normalized = tuple(_identity(value) for value in values)
    if all(value is None for value in normalized):
        return ()
    return tuple(value if value is not None else marker for value in normalized)


def _single_identity(value: object) -> tuple[str, ...]:
    identity = _identity(value)
    return (identity,) if identity is not None else ()


def _identity(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    return _MALFORMED_IDENTITY


def is_library_identity_marker(value: object) -> bool:
    """Internal preview helper; markers are never source, mapping, or display values."""
    return value in {_MISSING_ALBUM_ID, _MISSING_RELEASE_GROUP_ID, _MALFORMED_IDENTITY}


def _positive_id(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"library identity {label} ID is invalid")
    return value


def _optional_id(value: object) -> int | None:
    if value in (None, 0):
        return None
    return _positive_id(value, "Album")


def _text(value: object) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _position(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _length(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if result > 0 and isfinite(result) else None


# Narrow compatibility aliases retained for external tests written against early Block 026 drafts.
selected_library_identity_targets = select_library_identity_targets
snapshot_library_identity_target = exact_snapshot_from_library_target
LibraryIdentityTarget = SelectedLibraryIdentityTarget
LibraryIdentityTargetSnapshot = LibraryIdentityExactSnapshot
