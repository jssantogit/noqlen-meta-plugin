"""Fresh database preparation for database-to-file identity synchronization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from beets.library import Item, Library

from .domain import canonical_mbid
from .library import (
    LibraryIdentityTargetKind,
    SelectedLibraryIdentityTarget,
    refresh_library_identity_target,
)

IDENTITY_TAG_FIELDS = (
    "mb_albumid",
    "mb_releasegroupid",
    "mb_trackid",
    "mb_releasetrackid",
)


class IdentityTagDatabaseVerdict(Enum):
    READY = "ready"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SelectedIdentityTagFile:
    item_id: int
    album_id: int | None
    local_key: str = field(repr=False)
    item: Item = field(repr=False)
    path: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.item_id, bool) or not isinstance(self.item_id, int) or self.item_id <= 0:
            raise ValueError("identity tag Item ID is invalid")
        if type(self.item) is not Item or self.item.id != self.item_id:
            raise TypeError("identity tag selected Item is invalid")
        if self.item.album_id != self.album_id:
            raise ValueError("identity tag Album membership is invalid")
        if type(self.path) is not bytes or not self.path or self.item.path != self.path:
            raise ValueError("identity tag file path is invalid")
        if self.local_key != f"identity-tag-item:{self.item_id}":
            raise ValueError("identity tag local key is invalid")

@dataclass(frozen=True, slots=True)
class IdentityTagDatabaseSnapshot:
    item_id: int
    album_id: int | None
    path: bytes = field(repr=False)
    mtime: float
    mb_albumid: object = field(repr=False)
    mb_releasegroupid: object = field(repr=False)
    mb_trackid: object = field(repr=False)
    mb_releasetrackid: object = field(repr=False)

@dataclass(frozen=True, slots=True)
class IdentityTagTargetDatabaseSnapshot:
    kind: LibraryIdentityTargetKind
    album_id: int | None
    album_identity: tuple[object, object] | None = field(repr=False)
    item_snapshots: tuple[IdentityTagDatabaseSnapshot, ...]


@dataclass(frozen=True, slots=True)
class IdentityTagExpectedValues:
    mb_albumid: str
    mb_releasegroupid: str
    mb_trackid: str
    mb_releasetrackid: str

    def as_tuple(self) -> tuple[tuple[str, str], ...]:
        return tuple((field, getattr(self, field)) for field in IDENTITY_TAG_FIELDS)


@dataclass(frozen=True, slots=True)
class IdentityTagPreparedDatabaseFile:
    selected: SelectedIdentityTagFile
    database_snapshot: IdentityTagDatabaseSnapshot
    expected: IdentityTagExpectedValues | None
    target_snapshot: IdentityTagTargetDatabaseSnapshot
    blocked_reason: str | None = None

    @property
    def verdict(self) -> IdentityTagDatabaseVerdict:
        return (
            IdentityTagDatabaseVerdict.BLOCKED
            if self.blocked_reason is not None
            else IdentityTagDatabaseVerdict.READY
        )


@dataclass(frozen=True, slots=True)
class IdentityTagPreparedDatabaseTarget:
    kind: LibraryIdentityTargetKind
    album_id: int | None
    files: tuple[IdentityTagPreparedDatabaseFile, ...]
    snapshot: IdentityTagTargetDatabaseSnapshot
    blocked_reason: str | None = None


def prepare_identity_tag_database_target(
    library: Library, selected: SelectedLibraryIdentityTarget
) -> IdentityTagPreparedDatabaseTarget:
    """Refresh and validate one complete database identity target."""
    try:
        fresh = refresh_library_identity_target(library, selected)
    except Exception as error:
        raise ValueError("identity tag database target is unavailable") from error

    database_snapshots = tuple(_database_snapshot(entry.item) for entry in fresh.items)
    album_identity = None
    if fresh.album is not None:
        album_identity = (fresh.album.mb_albumid, fresh.album.mb_releasegroupid)
    target_snapshot = IdentityTagTargetDatabaseSnapshot(
        fresh.kind, fresh.album_id, album_identity, database_snapshots
    )
    reason = _coherence_reason(target_snapshot)
    selected_files = tuple(
        SelectedIdentityTagFile(
            entry.item_id,
            fresh.album_id,
            f"identity-tag-item:{entry.item_id}",
            entry.item,
            entry.item.path,
        )
        for entry in fresh.items
    )
    prepared_files = tuple(
        IdentityTagPreparedDatabaseFile(
            selected_file,
            snapshot,
            None if reason else _expected(snapshot),
            target_snapshot,
            reason,
        )
        for selected_file, snapshot in zip(selected_files, database_snapshots, strict=True)
    )
    return IdentityTagPreparedDatabaseTarget(
        fresh.kind, fresh.album_id, prepared_files, target_snapshot, reason
    )


def verify_identity_tag_database_target(
    library: Library, prepared: IdentityTagPreparedDatabaseTarget
) -> None:
    """Require the complete fresh target to equal its planning snapshot."""
    if type(prepared) is not IdentityTagPreparedDatabaseTarget:
        raise TypeError("identity tag database target plan is invalid")
    selected = _library_target_from_prepared(prepared)
    fresh = prepare_identity_tag_database_target(library, selected)
    if fresh.snapshot != prepared.snapshot or fresh.blocked_reason != prepared.blocked_reason:
        raise ValueError("identity tag database target is stale")


def _library_target_from_prepared(
    prepared: IdentityTagPreparedDatabaseTarget,
) -> SelectedLibraryIdentityTarget:
    from .library import SelectedLibraryIdentityItem

    items = tuple(
        SelectedLibraryIdentityItem(
            f"library-item:{entry.selected.item_id}",
            entry.selected.item_id,
            entry.selected.item,
        )
        for entry in prepared.files
    )
    album = prepared.files[0].selected.item.get_album() if prepared.album_id is not None else None
    if prepared.album_id is not None and album is None:
        raise ValueError("identity tag Album is unavailable")
    return SelectedLibraryIdentityTarget(prepared.kind, prepared.album_id, album, items)


def _database_snapshot(item: Item) -> IdentityTagDatabaseSnapshot:
    path = item.path
    if type(path) is not bytes or not path:
        raise ValueError("identity tag database path is empty")
    return IdentityTagDatabaseSnapshot(
        item.id,
        item.album_id or None,
        path,
        float(item.mtime or 0.0),
        item.get("mb_albumid", with_album=False),
        item.get("mb_releasegroupid", with_album=False),
        item.get("mb_trackid", with_album=False),
        item.get("mb_releasetrackid", with_album=False),
    )


def _coherence_reason(snapshot: IdentityTagTargetDatabaseSnapshot) -> str | None:
    if not snapshot.item_snapshots:
        return "database identity incomplete or inconsistent"
    canonical_items: list[tuple[str, str, str, str]] = []
    for item in snapshot.item_snapshots:
        values = tuple(canonical_mbid(getattr(item, field)) for field in IDENTITY_TAG_FIELDS)
        if any(value is None for value in values):
            return "database identity incomplete or inconsistent"
        canonical = tuple(value for value in values if value is not None)
        raw = tuple(getattr(item, field) for field in IDENTITY_TAG_FIELDS)
        if canonical != raw:
            return "database identity incomplete or inconsistent"
        canonical_items.append(canonical)  # type: ignore[arg-type]
    if snapshot.kind is LibraryIdentityTargetKind.ALBUM:
        if snapshot.album_id is None or snapshot.album_identity is None:
            return "database identity incomplete or inconsistent"
        album_values = tuple(canonical_mbid(value) for value in snapshot.album_identity)
        if any(value is None for value in album_values) or album_values != snapshot.album_identity:
            return "database identity incomplete or inconsistent"
        release_ids = {values[0] for values in canonical_items}
        group_ids = {values[1] for values in canonical_items}
        if release_ids != {album_values[0]} or group_ids != {album_values[1]}:
            return "database identity incomplete or inconsistent"
        release_tracks = [values[3] for values in canonical_items]
        if len(set(release_tracks)) != len(release_tracks):
            return "database release-track identity is duplicated"
    return None


def _expected(snapshot: IdentityTagDatabaseSnapshot) -> IdentityTagExpectedValues:
    values = tuple(canonical_mbid(getattr(snapshot, field)) for field in IDENTITY_TAG_FIELDS)
    if any(value is None for value in values):
        raise ValueError("identity tag database identity is invalid")
    return IdentityTagExpectedValues(*values)  # type: ignore[arg-type]
