"""Safe database application of track plans to persistent library Items."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from beets.dbcore.db import NotFoundError
from beets.library import Item

from beetsplug.noqlenmeta.credit_state import apply_credit_state
from beetsplug.noqlenmeta.track_application import TrackApplicationMode
from beetsplug.noqlenmeta.track_integration import current_values_from_library_item
from beetsplug.noqlenmeta.track_mapping import (
    TrackMappingError,
    TrackTargetChange,
    TrackTargetPlan,
    TrackTargetShape,
    map_change_plan_to_track_info,
)


class LibraryTrackApplicationError(RuntimeError):
    """An internal or safety contract failure during Item application."""


@dataclass(frozen=True, slots=True)
class LibraryTrackApplicationResult:
    """Immutable outcome of one persistent Item application attempt."""

    mode: TrackApplicationMode = TrackApplicationMode.STRICT
    applied_changes: tuple[TrackTargetChange, ...] = ()
    resolution_review_count: int = 0
    mapping_blocker_count: int = 0
    stored: bool = False

    @property
    def has_withheld_fields(self) -> bool:
        return self.resolution_review_count > 0 or self.mapping_blocker_count > 0

    @property
    def is_blocked(self) -> bool:
        return self.mode is TrackApplicationMode.STRICT and self.has_withheld_fields

    @property
    def is_partial_application(self) -> bool:
        return (
            self.mode is TrackApplicationMode.PARTIAL
            and self.stored
            and self.has_withheld_fields
        )

    @property
    def has_applied_changes(self) -> bool:
        return bool(self.applied_changes)


def apply_library_track_plan(
    item: Item,
    plan: TrackTargetPlan,
    mode: TrackApplicationMode = TrackApplicationMode.STRICT,
) -> LibraryTrackApplicationResult:
    """Atomically apply the mapped subset permitted by the explicit policy."""
    if not isinstance(item, Item):
        raise LibraryTrackApplicationError("application target must be a library Item")
    if not isinstance(plan, TrackTargetPlan):
        raise LibraryTrackApplicationError("application plan must be a TrackTargetPlan")
    if not isinstance(mode, TrackApplicationMode):
        raise LibraryTrackApplicationError("application mode must be a TrackApplicationMode")

    try:
        expected = map_change_plan_to_track_info(plan.source)
    except TrackMappingError as error:
        raise LibraryTrackApplicationError(
            "target plan source cannot be mapped canonically"
        ) from error
    if plan != expected:
        raise LibraryTrackApplicationError(
            "target plan does not match its canonical source mapping"
        )

    result = LibraryTrackApplicationResult(
        mode=mode,
        resolution_review_count=len(plan.source.reviews),
        mapping_blocker_count=len(plan.blocked_changes),
    )
    if result.is_blocked:
        return result
    if item._dirty:
        raise LibraryTrackApplicationError("library Item has pre-existing dirty metadata")

    try:
        fresh = item.get_fresh_from_db()
    except NotFoundError:
        raise LibraryTrackApplicationError(
            "library Item no longer exists in the database"
        ) from None

    current_values = current_values_from_library_item(fresh)
    for change in (*plan.mapped_changes, *plan.state_changes):
        canonical_field = (
            change.canonical_field if isinstance(change, TrackTargetChange) else change.field
        )
        current = current_values.get(canonical_field)
        before = change.source.before if isinstance(change, TrackTargetChange) else change.before
        if type(current) is not type(before) or current != before:
            raise LibraryTrackApplicationError(
                f"library metadata for {canonical_field!r} no longer matches the plan"
            )

    materialized: list[tuple[str, Any]] = []
    seen_targets: set[str] = set()
    for change in plan.mapped_changes:
        if change.target_field in seen_targets:
            raise LibraryTrackApplicationError(
                f"duplicate Item target field {change.target_field!r}"
            )
        seen_targets.add(change.target_field)
        value = _materialize_value(change)
        if change.target_field == "bpm" and Item._fields["bpm"].normalize(value) != value:
            raise LibraryTrackApplicationError(
                "beets Item.bpm cannot represent the planned fractional value losslessly"
            )
        materialized.append((change.target_field, value))

    for target_field, value in materialized:
        item[target_field] = value
    if not materialized and not plan.state_changes:
        return result

    if materialized:
        item.store()
    if not isinstance(item.id, int):
        raise LibraryTrackApplicationError("credit state requires a persisted Item")
    apply_credit_state(item._db, "item", item.id, plan.state_changes)
    return LibraryTrackApplicationResult(
        mode=mode,
        applied_changes=plan.mapped_changes,
        resolution_review_count=result.resolution_review_count,
        mapping_blocker_count=result.mapping_blocker_count,
        stored=True,
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
            raise LibraryTrackApplicationError(
                "string-list target requires canonical strings"
            )
        return list(value)
    if change.target_shape is TrackTargetShape.SCALAR_FLOAT:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
        ):
            raise LibraryTrackApplicationError(
                "scalar-float target requires a finite positive number"
            )
        return float(value)
    if change.target_shape is TrackTargetShape.SCALAR_STRING:
        if not isinstance(value, str) or not value or value != value.strip():
            raise LibraryTrackApplicationError(
                "scalar-string target requires a non-empty canonical string"
            )
        return value
    raise LibraryTrackApplicationError("unsupported Item target shape")
