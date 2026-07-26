"""Strict database application of persistent library Album target plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beets.dbcore.db import NotFoundError
from beets.library import Album

from beetsplug.noqlenmeta.beets_mapping import BeetsTargetShape
from beetsplug.noqlenmeta.library_integration import current_values_from_library_album
from beetsplug.noqlenmeta.library_mapping import (
    LibraryMappingError,
    LibraryTargetChange,
    LibraryTargetPlan,
    map_change_plan_to_library_album,
)


class LibraryApplicationError(RuntimeError):
    """An internal or safety contract failure during library application."""


@dataclass(frozen=True, slots=True)
class LibraryApplicationResult:
    """Immutable outcome of one strict persistent Album application attempt."""

    applied_changes: tuple[LibraryTargetChange, ...] = ()
    resolution_review_count: int = 0
    mapping_blocker_count: int = 0
    stored: bool = False

    @property
    def is_blocked(self) -> bool:
        return self.resolution_review_count > 0 or self.mapping_blocker_count > 0

    @property
    def has_applied_changes(self) -> bool:
        return bool(self.applied_changes)


def apply_library_target_plan(
    album: Album,
    plan: LibraryTargetPlan,
) -> LibraryApplicationResult:
    """Strictly apply one canonical target plan to the beets library database."""
    if not isinstance(album, Album):
        raise LibraryApplicationError("application target must be a library Album")
    if not isinstance(plan, LibraryTargetPlan):
        raise LibraryApplicationError("application plan must be a LibraryTargetPlan")

    try:
        expected = map_change_plan_to_library_album(plan.source)
    except LibraryMappingError as error:
        raise LibraryApplicationError("target plan source cannot be mapped canonically") from error
    if plan != expected:
        raise LibraryApplicationError("target plan does not match its canonical source mapping")

    result = LibraryApplicationResult(
        resolution_review_count=len(plan.source.reviews),
        mapping_blocker_count=len(plan.blocked_changes),
    )
    if result.is_blocked:
        return result

    if album._dirty:
        raise LibraryApplicationError("library Album has pre-existing dirty metadata")

    try:
        fresh_album = album.get_fresh_from_db()
    except NotFoundError:
        raise LibraryApplicationError(
            "library Album no longer exists in the database"
        ) from None

    current_values = current_values_from_library_album(fresh_album)
    for change in plan.mapped_changes:
        current = current_values.get(change.canonical_field)
        if type(current) is not type(change.source.before) or current != change.source.before:
            raise LibraryApplicationError(
                f"library metadata for {change.canonical_field!r} no longer matches the plan"
            )

    materialized = [
        (change.target_field, _materialize_value(change))
        for change in plan.mapped_changes
    ]
    seen_targets: set[str] = set()
    for target_field, _ in materialized:
        if target_field in seen_targets:
            raise LibraryApplicationError(f"duplicate Album target field {target_field!r}")
        seen_targets.add(target_field)

    for target_field, value in materialized:
        setattr(album, target_field, value)

    if not materialized:
        return result

    album.store(inherit=True)
    return LibraryApplicationResult(
        applied_changes=plan.mapped_changes,
        resolution_review_count=result.resolution_review_count,
        mapping_blocker_count=result.mapping_blocker_count,
        stored=True,
    )


def _materialize_value(change: LibraryTargetChange) -> Any:
    value = change.target_value
    if change.target_shape is BeetsTargetShape.STRING_LIST:
        if (
            not isinstance(value, tuple)
            or not value
            or any(
                not isinstance(item, str) or not item or item != item.strip()
                for item in value
            )
        ):
            raise LibraryApplicationError("string-list target requires canonical strings")
        return list(value)
    if change.target_shape is BeetsTargetShape.SCALAR_STRING:
        if not isinstance(value, str) or not value or value != value.strip():
            raise LibraryApplicationError("scalar-string target requires a canonical string")
        return value
    if change.target_shape is BeetsTargetShape.SCALAR_INT:
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 9999:
            raise LibraryApplicationError(
                "scalar-int target requires an integer between 1 and 9999"
            )
        return value
    raise LibraryApplicationError("unsupported Album target shape")
