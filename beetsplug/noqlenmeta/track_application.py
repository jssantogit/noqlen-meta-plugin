"""Safe application of lossless target plans to selected track metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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

    # Recompute through beets' real surfaces without changing caches on a failed attempt.
    missing_cache = object()
    raw_data_cache = selected.track_info.__dict__.pop("raw_data", missing_cache)
    item_data_cache = selected.track_info.__dict__.pop("item_data", missing_cache)
    try:
        current_values = effective_current_values_for_import_track(
            selected,
            from_scratch=from_scratch,
        )
    finally:
        selected.track_info.__dict__.pop("raw_data", None)
        selected.track_info.__dict__.pop("item_data", None)
        if raw_data_cache is not missing_cache:
            selected.track_info.__dict__["raw_data"] = raw_data_cache
        if item_data_cache is not missing_cache:
            selected.track_info.__dict__["item_data"] = item_data_cache
    for change in plan.mapped_changes:
        current = current_values.get(change.canonical_field)
        expected_before = change.source.before
        if type(current) is not type(expected_before) or current != expected_before:
            raise TrackApplicationError(
                f"selected metadata for {change.canonical_field!r} no longer matches the plan"
            )

    materialized: list[tuple[str, str]] = []
    seen_targets: set[str] = set()
    for change in plan.mapped_changes:
        if change.target_shape is not TrackTargetShape.SCALAR_STRING:
            raise TrackApplicationError("unsupported TrackInfo target shape")
        if not isinstance(change.target_value, str) or not change.target_value:
            raise TrackApplicationError("scalar-string target requires a non-empty string")
        if change.target_field in seen_targets:
            raise TrackApplicationError(
                f"duplicate TrackInfo target field {change.target_field!r}"
            )
        seen_targets.add(change.target_field)
        materialized.append((change.target_field, change.target_value))

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
