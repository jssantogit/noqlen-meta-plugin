"""Read-only, lossless mapping from canonical changes to beets targets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.credit_resolution import CREDIT_FIELDS
from beetsplug.noqlenmeta.credits import ArtistCredit, CreditReference
from beetsplug.noqlenmeta.domain import MetadataValue
from beetsplug.noqlenmeta.release_catalog_mapping import map_release_catalog_plan


class BeetsMappingError(RuntimeError):
    """An impossible or inconsistent canonical-to-target mapping input."""


class BeetsTargetShape(Enum):
    """The supported value shapes exposed by the current AlbumInfo contract."""

    STRING_LIST = "string_list"
    SCALAR_STRING = "scalar_string"
    SCALAR_INT = "scalar_int"


def _validate_field_name(value: object, label: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip().lower():
        raise BeetsMappingError(f"{label} must be a canonical non-empty name")
    if not value.replace("_", "").isalnum():
        raise BeetsMappingError(f"{label} contains invalid characters")


@dataclass(frozen=True, slots=True)
class BeetsFieldTarget:
    """One explicit canonical-field to AlbumInfo-field mapping."""

    canonical_field: str
    target_field: str
    shape: BeetsTargetShape

    def __post_init__(self) -> None:
        _validate_field_name(self.canonical_field, "canonical field")
        _validate_field_name(self.target_field, "target field")
        if not isinstance(self.shape, BeetsTargetShape):
            raise BeetsMappingError("target shape must be a BeetsTargetShape")


_TARGETS = (
    BeetsFieldTarget("genres", "genres", BeetsTargetShape.STRING_LIST),
    BeetsFieldTarget("styles", "styles", BeetsTargetShape.STRING_LIST),
    BeetsFieldTarget("artist_countries", "artist_countries", BeetsTargetShape.STRING_LIST),
    BeetsFieldTarget("artist_areas", "artist_areas", BeetsTargetShape.STRING_LIST),
    BeetsFieldTarget("artist_languages", "artist_languages", BeetsTargetShape.STRING_LIST),
    BeetsFieldTarget("labels", "label", BeetsTargetShape.SCALAR_STRING),
    BeetsFieldTarget("catalog_numbers", "catalognum", BeetsTargetShape.SCALAR_STRING),
    BeetsFieldTarget("barcodes", "barcode", BeetsTargetShape.SCALAR_STRING),
    BeetsFieldTarget("country", "country", BeetsTargetShape.SCALAR_STRING),
    BeetsFieldTarget("year", "year", BeetsTargetShape.SCALAR_INT),
    BeetsFieldTarget("media", "media", BeetsTargetShape.SCALAR_STRING),
    BeetsFieldTarget("producers", "producers", BeetsTargetShape.STRING_LIST),
    BeetsFieldTarget("conductors", "conductors", BeetsTargetShape.STRING_LIST),
    BeetsFieldTarget("performers", "performers", BeetsTargetShape.STRING_LIST),
    BeetsFieldTarget("featured_artists", "featured_artists", BeetsTargetShape.STRING_LIST),
)

BEETS_FIELD_TARGETS: Mapping[str, BeetsFieldTarget] = MappingProxyType(
    {target.canonical_field: target for target in _TARGETS}
)


@dataclass(frozen=True, slots=True)
class BeetsTargetChange:
    """One canonical planned change represented losslessly for AlbumInfo."""

    canonical_field: str
    target_field: str
    target_shape: BeetsTargetShape
    target_value: MetadataValue
    source: PlannedChange


@dataclass(frozen=True, slots=True)
class BeetsMappingBlocker:
    """A valid canonical change unsupported losslessly by AlbumInfo."""

    source: PlannedChange
    target_field: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class BeetsTargetPlan:
    """Immutable read-only analysis of a ChangePlan against AlbumInfo targets."""

    source: ChangePlan
    mapped_changes: tuple[BeetsTargetChange, ...] = ()
    blocked_changes: tuple[BeetsMappingBlocker, ...] = ()
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


def map_change_plan_to_beets(plan: ChangePlan) -> BeetsTargetPlan:
    """Analyze canonical changes against the supported beets target contract."""
    if not isinstance(plan, ChangePlan):
        raise BeetsMappingError("source plan must be a ChangePlan")

    mapped: list[BeetsTargetChange] = []
    blocked: list[BeetsMappingBlocker] = []
    state_changes: list[PlannedChange] = []
    catalog_fields = {
        "date", "original_date", "release_type", "release_secondary_types",
        "release_status", "edition",
    }
    catalog_changes = tuple(change for change in plan.changes if change.field in catalog_fields)
    if catalog_changes:
        catalog_plan = map_release_catalog_plan(
            ChangePlan(catalog_changes, plan.reviews, plan.kept, plan.skipped)
        )
        for target in catalog_plan.changes:
            shape = (
                BeetsTargetShape.STRING_LIST
                if isinstance(target.value, tuple)
                else BeetsTargetShape.SCALAR_INT
                if isinstance(target.value, int)
                else BeetsTargetShape.SCALAR_STRING
            )
            mapped.append(
                BeetsTargetChange(
                    target.canonical_field,
                    target.target_field,
                    shape,
                    target.value,  # type: ignore[arg-type]
                    target.source,
                )
            )
    for change in sorted(plan.changes, key=lambda item: item.field):
        if change.field in catalog_fields:
            continue
        if change.field in CREDIT_FIELDS:
            state_changes.append(change)
            if change.field == "structured_artist_credits":
                if not isinstance(change.after, ArtistCredit):
                    raise BeetsMappingError(
                        "'structured_artist_credits' requires ArtistCredit"
                    )
                continue
            if not isinstance(change.after, tuple) or not all(
                isinstance(value, CreditReference) for value in change.after
            ):
                raise BeetsMappingError(f"{change.field!r} requires CreditReference values")
            target = BEETS_FIELD_TARGETS.get(change.field)
            if target is None:
                raise BeetsMappingError(
                    f"no selected-release credit projection exists for {change.field!r}"
                )
            names = tuple(dict.fromkeys(value.party.name for value in change.after))
            mapped.append(
                BeetsTargetChange(
                    change.field,
                    target.target_field,
                    target.shape,
                    names,
                    change,
                )
            )
            continue
        target = BEETS_FIELD_TARGETS.get(change.field)
        if target is None:
            blocked.append(
                BeetsMappingBlocker(
                    source=change,
                    target_field=None,
                    reason="no supported AlbumInfo target exists for this canonical field",
                )
            )
            continue

        value = _map_value(change, target)
        if value is None:
            blocked.append(
                BeetsMappingBlocker(
                    source=change,
                    target_field=target.target_field,
                    reason=(
                        "multiple canonical values cannot be represented losslessly "
                        "by the singular beets target"
                    ),
                )
            )
            continue
        mapped.append(
            BeetsTargetChange(
                canonical_field=change.field,
                target_field=target.target_field,
                target_shape=target.shape,
                target_value=value,
                source=change,
            )
        )

    return BeetsTargetPlan(plan, tuple(mapped), tuple(blocked), tuple(state_changes))


def _map_value(change: PlannedChange, target: BeetsFieldTarget) -> MetadataValue | None:
    value = change.after
    if target.shape is BeetsTargetShape.STRING_LIST:
        if not isinstance(value, tuple) or not value:
            raise BeetsMappingError(f"{change.field!r} requires a non-empty tuple of strings")
        # Keep plans immutable; a future apply boundary may materialize list(value).
        return value

    if target.shape is BeetsTargetShape.SCALAR_INT:
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 9999:
            raise BeetsMappingError(f"{change.field!r} requires an integer between 1 and 9999")
        return value

    if target.shape is not BeetsTargetShape.SCALAR_STRING:
        raise BeetsMappingError(f"unsupported target shape for {change.field!r}")
    if change.field == "country":
        if not isinstance(value, str):
            raise BeetsMappingError("'country' requires a string")
        return value
    if not isinstance(value, tuple) or not value:
        raise BeetsMappingError(f"{change.field!r} requires a non-empty tuple of strings")
    return value[0] if len(value) == 1 else None
