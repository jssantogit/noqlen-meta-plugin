"""Read-only, lossless mapping from canonical changes to TrackInfo targets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from types import MappingProxyType

from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.credit_resolution import CREDIT_FIELDS
from beetsplug.noqlenmeta.credits import ArtistCredit, CreditReference
from beetsplug.noqlenmeta.domain import MetadataValue
from beetsplug.noqlenmeta.field_contracts import IdentifierCollection, PartialDate
from beetsplug.noqlenmeta.work_identity import WorkReference


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
    TrackFieldTarget("isrcs", "isrcs", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("iswcs", "iswcs", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("works", "mb_workids", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("recording_date", "recording_date", TrackTargetShape.SCALAR_STRING),
    TrackFieldTarget("composers", "composers", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("lyricists", "lyricists", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("arrangers", "arrangers", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("producers", "producers", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("conductors", "conductors", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("performers", "performers", TrackTargetShape.STRING_LIST),
    TrackFieldTarget("featured_artists", "featured_artists", TrackTargetShape.STRING_LIST),
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
    state_changes: tuple[PlannedChange, ...] = ()

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
    state_changes: list[PlannedChange] = []
    for change in sorted(plan.changes, key=lambda item: item.field):
        if change.field in CREDIT_FIELDS:
            state_changes.append(change)
            if change.field == "structured_artist_credits":
                if not isinstance(change.after, ArtistCredit):
                    raise TrackMappingError(
                        "'structured_artist_credits' requires ArtistCredit"
                    )
                continue
            if not isinstance(change.after, tuple) or not all(
                isinstance(value, CreditReference) for value in change.after
            ):
                raise TrackMappingError(f"{change.field!r} requires CreditReference values")
            names = tuple(dict.fromkeys(value.party.name for value in change.after))
            mapped.append(
                _target_change(change, change.field, TrackTargetShape.STRING_LIST, names)
            )
            id_target = {
                "composers": "composers_ids",
                "lyricists": "lyricists_ids",
                "arrangers": "arrangers_ids",
            }.get(change.field)
            ids = tuple(value.party.mbid for value in change.after)
            if id_target is not None and all(ids):
                mapped.append(
                    _target_change(
                        change,
                        id_target,
                        TrackTargetShape.STRING_LIST,
                        tuple(dict.fromkeys(ids)),  # type: ignore[arg-type]
                    )
                )
            continue
        if change.field in {"isrcs", "iswcs"}:
            if not isinstance(change.after, IdentifierCollection):
                raise TrackMappingError(f"{change.field!r} requires IdentifierCollection")
            values = tuple(identifier.value for identifier in change.after.values)
            mapped.append(
                _target_change(change, change.field, TrackTargetShape.STRING_LIST, values)
            )
            if change.field == "isrcs" and len(values) == 1:
                mapped.append(
                    _target_change(
                        change, "isrc", TrackTargetShape.SCALAR_STRING, values[0]
                    )
                )
            continue
        if change.field == "works":
            if not isinstance(change.after, tuple) or not all(
                isinstance(value, WorkReference) for value in change.after
            ):
                raise TrackMappingError("'works' requires WorkReference values")
            values = tuple(value.mbid for value in change.after)
            mapped.append(
                _target_change(change, "mb_workids", TrackTargetShape.STRING_LIST, values)
            )
            if len(values) == 1:
                mapped.append(
                    _target_change(
                        change, "mb_workid", TrackTargetShape.SCALAR_STRING, values[0]
                    )
                )
                title = change.after[0].title
                if title is not None:
                    mapped.append(
                        _target_change(
                            change, "work", TrackTargetShape.SCALAR_STRING, title
                        )
                    )
            continue
        if change.field == "recording_date":
            if not isinstance(change.after, PartialDate):
                raise TrackMappingError("'recording_date' requires PartialDate")
            mapped.append(
                _target_change(
                    change,
                    "recording_date",
                    TrackTargetShape.SCALAR_STRING,
                    _partial_date_text(change.after),
                )
            )
            continue
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

    return TrackTargetPlan(plan, tuple(mapped), tuple(blocked), tuple(state_changes))


def _target_change(
    source: PlannedChange, target: str, shape: TrackTargetShape, value: MetadataValue
) -> TrackTargetChange:
    return TrackTargetChange(source.field, target, shape, value, source)


def _partial_date_text(value: PartialDate) -> str:
    if value.month is None:
        return f"{value.year:04d}"
    if value.day is None:
        return f"{value.year:04d}-{value.month:02d}"
    return f"{value.year:04d}-{value.month:02d}-{value.day:02d}"
