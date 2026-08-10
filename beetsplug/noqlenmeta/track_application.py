"""Safe application of lossless target plans to selected track metadata."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any

from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.library import Item

from beetsplug.noqlenmeta.track_integration import SelectedImportTrack
from beetsplug.noqlenmeta.track_mapping import (
    TrackMappingError,
    TrackTargetChange,
    TrackTargetPlan,
    TrackTargetShape,
    map_change_plan_to_track_info,
)
from beetsplug.noqlenmeta.track_planning import effective_current_values_for_import_track


class TrackApplicationError(RuntimeError):
    """Internal or safety contract failure during selected-track application."""


class TrackApplicationMode(Enum):
    """Explicit selected-track application policies."""

    STRICT = "strict"
    PARTIAL = "partial"


def parse_track_application_mode(value: str) -> TrackApplicationMode:
    """Parse one configured track application mode without unsafe fallback."""
    if not isinstance(value, str):
        raise TrackApplicationError("track application mode must be 'strict' or 'partial'")
    normalized = value.strip().lower()
    try:
        return TrackApplicationMode(normalized)
    except ValueError:
        raise TrackApplicationError(
            "invalid track application mode; expected 'strict' or 'partial'"
        ) from None


@dataclass(frozen=True, slots=True)
class TrackApplicationResult:
    """Immutable outcome of one selected-track application attempt."""

    mode: TrackApplicationMode = TrackApplicationMode.STRICT
    applied_changes: tuple[TrackTargetChange, ...] = ()
    resolution_review_count: int = 0
    mapping_blocker_count: int = 0

    @property
    def has_withheld_fields(self) -> bool:
        return self.resolution_review_count > 0 or self.mapping_blocker_count > 0

    @property
    def is_blocked(self) -> bool:
        return self.mode is TrackApplicationMode.STRICT and self.has_withheld_fields

    @property
    def has_applied_changes(self) -> bool:
        return bool(self.applied_changes)

    @property
    def is_partial_application(self) -> bool:
        return (
            self.mode is TrackApplicationMode.PARTIAL
            and self.has_applied_changes
            and self.has_withheld_fields
        )


@dataclass(frozen=True, slots=True)
class _CacheSnapshot:
    target: TrackInfo | AlbumInfo
    values: tuple[tuple[str, object], ...]


@contextmanager
def _fresh_selected_application_caches(
    selected: SelectedImportTrack,
) -> Iterator[None]:
    """Temporarily refresh only caches used by selected metadata application."""
    cache_keys = ("raw_data", "item_data")
    targets = (selected.track_info,) + (
        (selected.album_info,) if selected.album_info is not None else ()
    )
    snapshots = tuple(
        _CacheSnapshot(
            target,
            tuple((key, target.__dict__[key]) for key in cache_keys if key in target.__dict__),
        )
        for target in targets
    )
    for snapshot in snapshots:
        for key in cache_keys:
            snapshot.target.__dict__.pop(key, None)
    try:
        yield
    finally:
        for snapshot in snapshots:
            for key in cache_keys:
                snapshot.target.__dict__.pop(key, None)
            snapshot.target.__dict__.update(snapshot.values)


def apply_track_target_plan(
    selected: SelectedImportTrack,
    plan: TrackTargetPlan,
    *,
    from_scratch: bool,
    mode: TrackApplicationMode = TrackApplicationMode.STRICT,
) -> TrackApplicationResult:
    """Atomically apply the mapped subset to the already-selected TrackInfo."""
    if not isinstance(selected, SelectedImportTrack):
        raise TrackApplicationError("application target must be a SelectedImportTrack")
    if not isinstance(selected.track_info, TrackInfo):
        raise TrackApplicationError("selected track target must be a TrackInfo")
    if not isinstance(selected.item, Item):
        raise TrackApplicationError("selected track Item has an invalid type")
    if selected.album_info is not None and not isinstance(selected.album_info, AlbumInfo):
        raise TrackApplicationError("selected track AlbumInfo has an invalid type")
    if not isinstance(plan, TrackTargetPlan):
        raise TrackApplicationError("application plan must be a TrackTargetPlan")
    if type(from_scratch) is not bool:
        raise TrackApplicationError("from_scratch must be a bool")
    if not isinstance(mode, TrackApplicationMode):
        raise TrackApplicationError("application mode must be a TrackApplicationMode")

    try:
        expected = map_change_plan_to_track_info(plan.source)
    except TrackMappingError as error:
        raise TrackApplicationError("target plan source cannot be mapped canonically") from error
    if plan != expected:
        raise TrackApplicationError("target plan does not match its canonical source mapping")

    result = TrackApplicationResult(
        mode=mode,
        resolution_review_count=len(plan.source.reviews),
        mapping_blocker_count=len(plan.blocked_changes),
    )
    if result.is_blocked:
        return result

    with _fresh_selected_application_caches(selected):
        current_values = effective_current_values_for_import_track(
            selected,
            from_scratch=from_scratch,
        )
    for change in plan.mapped_changes:
        current = current_values.get(change.canonical_field)
        expected_before = change.source.before
        if type(current) is not type(expected_before) or current != expected_before:
            raise TrackApplicationError(
                f"selected metadata for {change.canonical_field!r} no longer matches the plan"
            )

    materialized: list[tuple[str, Any]] = []
    seen_targets: set[str] = set()
    for change in plan.mapped_changes:
        if change.target_field in seen_targets:
            raise TrackApplicationError(
                f"duplicate TrackInfo target field {change.target_field!r}"
            )
        seen_targets.add(change.target_field)
        materialized.append((change.target_field, _materialize_value(change)))

    for target_field, value in materialized:
        selected.track_info[target_field] = value

    if materialized:
        selected.track_info.__dict__.pop("raw_data", None)
        selected.track_info.__dict__.pop("item_data", None)

    return TrackApplicationResult(
        mode=mode,
        applied_changes=plan.mapped_changes,
        resolution_review_count=result.resolution_review_count,
        mapping_blocker_count=result.mapping_blocker_count,
    )


def _materialize_value(change: TrackTargetChange) -> Any:
    value = change.target_value
    if change.target_shape is TrackTargetShape.STRING_LIST:
        if (
            not isinstance(value, tuple)
            or not value
            or any(
                not isinstance(item, str) or not item or item != item.strip()
                for item in value
            )
        ):
            raise TrackApplicationError("string-list target requires canonical strings")
        return list(value)
    if change.target_shape is TrackTargetShape.SCALAR_FLOAT:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
        ):
            raise TrackApplicationError("scalar-float target requires a finite positive number")
        return float(value)
    if change.target_shape is TrackTargetShape.SCALAR_STRING:
        if not isinstance(value, str) or not value or value != value.strip():
            raise TrackApplicationError(
                "scalar-string target requires a non-empty string in canonical form"
            )
        return value
    raise TrackApplicationError("unsupported TrackInfo target shape")
