"""Read-only, lossless mapping from canonical changes to TrackInfo targets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from types import MappingProxyType

from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import MetadataValue


class TrackMappingError(RuntimeError):
    """An impossible or inconsistent canonical-to-track mapping input."""


class TrackTargetShape(Enum):
    """The supported value shapes exposed by the current TrackInfo contract."""

    SCALAR_STRING = "scalar_string"
    STRING_LIST = "string_list"
    SCALAR_FLOAT = "scalar_float"


def _validate_field_name(value: object, label: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip().lower():
        raise TrackMappingError(f"{label} must be a canonical non-empty name")
    if not value.replace("_", "").isalnum():
        raise TrackMappingError(f"{label} contains invalid characters")


@dataclass(frozen=True, slots=True)
class TrackFieldTarget:
    """One explicit canonical-field to TrackInfo-field mapping."""

    canonical_field: str
    target_field: str
    shape: TrackTargetShape

    def __post_init__(self) -> None:
        _validate_field_name(self.canonical_field, "canonical field")
        _validate_field_name(self.target_field, "target field")
        if not isinstance(self.shape, TrackTargetShape):
            raise TrackMappingError("target shape must be a TrackTargetShape")


_TARGETS = (
    TrackFieldTarget("lyrics", "lyrics", TrackTargetShape.SCALAR_STRING),
    TrackFieldTarget("bpm", "bpm", TrackTargetShape.SCALAR_FLOAT),
    TrackFieldTarget("genres", "genres", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("moods", "moods", TrackTargetShape.STRING_LIST),
    TrackFieldTarget(
        "lyrics_languages", "lyrics_languages", TrackTargetShape.STRING_LIST
    ),
    TrackFieldTarget(
        "artist_countries", "artist_countries", TrackTargetShape.STRING_LIST
    ),
    TrackFieldTarget("artist_areas", "artist_areas", TrackTargetShape.STRING_LIST),
    TrackFieldTarget(
        "artist_languages", "artist_languages", TrackTargetShape.STRING_LIST
    ),
)

TRACK_FIELD_TARGETS: Mapping[str, TrackFieldTarget] = MappingProxyType(
    {target.canonical_field: target for target in _TARGETS}
)


@dataclass(frozen=True, slots=True)
class TrackTargetChange:
    """One canonical planned change represented losslessly for TrackInfo."""

    canonical_field: str
    target_field: str
    target_shape: TrackTargetShape
    target_value: MetadataValue
    source: PlannedChange


@dataclass(frozen=True, slots=True)
class TrackMappingBlocker:
    """A valid canonical change unsupported losslessly by TrackInfo."""

    source: PlannedChange
    target_field: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class TrackTargetPlan:
    """Immutable analysis of a ChangePlan against selected TrackInfo targets."""

    source: ChangePlan
    mapped_changes: tuple[TrackTargetChange, ...] = ()
    blocked_changes: tuple[TrackMappingBlocker, ...] = ()

    @property
    def has_mapping_blockers(self) -> bool:
        return bool(self.blocked_changes)

    @property
    def is_fully_mapped(self) -> bool:
        return not self.blocked_changes

    @property
    def requires_review(self) -> bool:
        return self.source.requires_review or self.has_mapping_blockers


def map_change_plan_to_track_info(plan: ChangePlan) -> TrackTargetPlan:
    """Analyze canonical changes against the supported TrackInfo contract."""
    if not isinstance(plan, ChangePlan):
        raise TrackMappingError("source plan must be a ChangePlan")

    mapped: list[TrackTargetChange] = []
    blocked: list[TrackMappingBlocker] = []
    for change in sorted(plan.changes, key=lambda item: item.field):
        if change.field == "synced_lyrics":
            blocked.append(
                TrackMappingBlocker(
                    source=change,
                    target_field=None,
                    reason=(
                        "no lossless normal beets TrackInfo target preserves "
                        "synchronized lyrics semantics"
                    ),
                )
            )
            continue

        target = TRACK_FIELD_TARGETS.get(change.field)
        if target is None:
            blocked.append(
                TrackMappingBlocker(
                    source=change,
                    target_field=None,
                    reason="no supported TrackInfo target exists for this canonical field",
                )
            )
            continue

        value = change.after
        if target.shape is TrackTargetShape.STRING_LIST:
            if (
                not isinstance(value, tuple)
                or not value
                or any(
                    not isinstance(item, str) or not item or item != item.strip()
                    for item in value
                )
            ):
                raise TrackMappingError(
                    f"{change.field!r} requires a non-empty tuple of canonical strings"
                )
        elif target.shape is TrackTargetShape.SCALAR_FLOAT:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
            ):
                raise TrackMappingError(
                    f"{change.field!r} requires a finite positive number"
                )
            value = float(value)
        elif target.shape is TrackTargetShape.SCALAR_STRING:
            if not isinstance(value, str) or not value or value != value.strip():
                raise TrackMappingError(
                    f"{change.field!r} requires a non-empty canonical string"
                )
        else:
            raise TrackMappingError(f"unsupported target shape for {change.field!r}")
        mapped.append(
            TrackTargetChange(
                canonical_field=change.field,
                target_field=target.target_field,
                target_shape=target.shape,
                target_value=value,
                source=change,
            )
        )

    return TrackTargetPlan(plan, tuple(mapped), tuple(blocked))
