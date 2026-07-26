"""Strict application of lossless target plans to selected beets metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beets.autotag.hooks import AlbumInfo

from beetsplug.noqlenmeta.beets_mapping import (
    BeetsMappingError,
    BeetsTargetChange,
    BeetsTargetPlan,
    BeetsTargetShape,
    map_change_plan_to_beets,
)
from beetsplug.noqlenmeta.integration import current_values_from_album_info


class BeetsApplicationError(RuntimeError):
    """An internal or safety contract failure during selected-release application."""


@dataclass(frozen=True, slots=True)
class BeetsApplicationResult:
    """Immutable outcome of one strict selected-release application attempt."""

    applied_changes: tuple[BeetsTargetChange, ...] = ()
    resolution_review_count: int = 0
    mapping_blocker_count: int = 0

    @property
    def is_blocked(self) -> bool:
        return self.resolution_review_count > 0 or self.mapping_blocker_count > 0

    @property
    def has_applied_changes(self) -> bool:
        return bool(self.applied_changes)


def apply_beets_target_plan(
    album_info: AlbumInfo,
    plan: BeetsTargetPlan,
) -> BeetsApplicationResult:
    """Apply a fully lossless, review-free plan to the selected AlbumInfo only."""
    if not isinstance(album_info, AlbumInfo):
        raise BeetsApplicationError("application target must be an AlbumInfo")
    if not isinstance(plan, BeetsTargetPlan):
        raise BeetsApplicationError("application plan must be a BeetsTargetPlan")

    try:
        expected = map_change_plan_to_beets(plan.source)
    except BeetsMappingError as error:
        raise BeetsApplicationError("target plan source cannot be mapped canonically") from error
    if plan != expected:
        raise BeetsApplicationError("target plan does not match its canonical source mapping")

    result = BeetsApplicationResult(
        resolution_review_count=len(plan.source.reviews),
        mapping_blocker_count=len(plan.blocked_changes),
    )
    if result.is_blocked:
        return result

    current_values = current_values_from_album_info(album_info)
    for change in plan.mapped_changes:
        current = current_values.get(change.canonical_field)
        if type(current) is not type(change.source.before) or current != change.source.before:
            raise BeetsApplicationError(
                f"selected metadata for {change.canonical_field!r} no longer matches the plan"
            )

    materialized = [
        (change.target_field, _materialize_value(change)) for change in plan.mapped_changes
    ]
    seen_targets: set[str] = set()
    for target_field, _ in materialized:
        if target_field in seen_targets:
            raise BeetsApplicationError(
                f"duplicate AlbumInfo target field {target_field!r}"
            )
        seen_targets.add(target_field)

    for target_field, value in materialized:
        setattr(album_info, target_field, value)

    if materialized:
        album_info.__dict__.pop("raw_data", None)
        album_info.__dict__.pop("item_data", None)

    return BeetsApplicationResult(
        applied_changes=plan.mapped_changes,
        resolution_review_count=result.resolution_review_count,
        mapping_blocker_count=result.mapping_blocker_count,
    )


def _materialize_value(change: BeetsTargetChange) -> Any:
    value = change.target_value
    if change.target_shape is BeetsTargetShape.STRING_LIST:
        if (
            not isinstance(value, tuple)
            or not value
            or any(not isinstance(item, str) or not item for item in value)
        ):
            raise BeetsApplicationError("string-list target requires a non-empty tuple of strings")
        return list(value)
    if change.target_shape is BeetsTargetShape.SCALAR_STRING:
        if not isinstance(value, str) or not value:
            raise BeetsApplicationError("scalar-string target requires a non-empty string")
        return value
    if change.target_shape is BeetsTargetShape.SCALAR_INT:
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 9999:
            raise BeetsApplicationError("scalar-int target requires an integer between 1 and 9999")
        return value
    raise BeetsApplicationError("unsupported AlbumInfo target shape")
