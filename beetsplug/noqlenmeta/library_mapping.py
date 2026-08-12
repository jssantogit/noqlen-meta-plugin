"""Read-only, lossless mapping from canonical changes to library Album targets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from beetsplug.noqlenmeta.beets_mapping import BeetsTargetShape
from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import MetadataValue


class LibraryMappingError(RuntimeError):
    """An impossible or inconsistent canonical-to-library mapping input."""


def _validate_field_name(value: object, label: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip().lower():
        raise LibraryMappingError(f"{label} must be a canonical non-empty name")
    if not value.replace("_", "").isalnum():
        raise LibraryMappingError(f"{label} contains invalid characters")


@dataclass(frozen=True, slots=True)
class LibraryFieldTarget:
    """One explicit canonical-field to persistent Album-field mapping."""

    canonical_field: str
    target_field: str
    shape: BeetsTargetShape

    def __post_init__(self) -> None:
        _validate_field_name(self.canonical_field, "canonical field")
        _validate_field_name(self.target_field, "target field")
        if not isinstance(self.shape, BeetsTargetShape):
            raise LibraryMappingError("target shape must be a BeetsTargetShape")


_TARGETS = (
    LibraryFieldTarget("genres", "genres", BeetsTargetShape.STRING_LIST),
    LibraryFieldTarget("styles", "styles", BeetsTargetShape.STRING_LIST),
    LibraryFieldTarget("artist_countries", "artist_countries", BeetsTargetShape.STRING_LIST),
    LibraryFieldTarget("artist_areas", "artist_areas", BeetsTargetShape.STRING_LIST),
    LibraryFieldTarget("artist_languages", "artist_languages", BeetsTargetShape.STRING_LIST),
    LibraryFieldTarget("labels", "label", BeetsTargetShape.SCALAR_STRING),
    LibraryFieldTarget("catalog_numbers", "catalognum", BeetsTargetShape.SCALAR_STRING),
    LibraryFieldTarget("barcodes", "barcode", BeetsTargetShape.SCALAR_STRING),
    LibraryFieldTarget("country", "country", BeetsTargetShape.SCALAR_STRING),
    LibraryFieldTarget("year", "year", BeetsTargetShape.SCALAR_INT),
)

LIBRARY_FIELD_TARGETS: Mapping[str, LibraryFieldTarget] = MappingProxyType(
    {target.canonical_field: target for target in _TARGETS}
)


@dataclass(frozen=True, slots=True)
class LibraryTargetChange:
    """One canonical planned change represented losslessly for Album."""

    canonical_field: str
    target_field: str
    target_shape: BeetsTargetShape
    target_value: MetadataValue
    source: PlannedChange


@dataclass(frozen=True, slots=True)
class LibraryMappingBlocker:
    """A valid canonical change unsupported losslessly by Album."""

    source: PlannedChange
    target_field: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class LibraryTargetPlan:
    """Immutable analysis of a ChangePlan against persistent Album targets."""

    source: ChangePlan
    mapped_changes: tuple[LibraryTargetChange, ...] = ()
    blocked_changes: tuple[LibraryMappingBlocker, ...] = ()

    @property
    def has_mapping_blockers(self) -> bool:
        return bool(self.blocked_changes)

    @property
    def is_fully_mapped(self) -> bool:
        return not self.blocked_changes

    @property
    def requires_review(self) -> bool:
        return self.source.requires_review or self.has_mapping_blockers


def map_change_plan_to_library_album(plan: ChangePlan) -> LibraryTargetPlan:
    """Analyze canonical changes against the persistent Album contract."""
    if not isinstance(plan, ChangePlan):
        raise LibraryMappingError("source plan must be a ChangePlan")

    mapped: list[LibraryTargetChange] = []
    blocked: list[LibraryMappingBlocker] = []
    for change in sorted(plan.changes, key=lambda item: item.field):
        if change.field == "media":
            _require_text_tuple(change)
            blocked.append(
                LibraryMappingBlocker(
                    source=change,
                    target_field=None,
                    reason="persistent Album has no supported album-level media target",
                )
            )
            continue
        if change.field == "format_descriptions":
            _require_text_tuple(change)
            blocked.append(
                LibraryMappingBlocker(
                    source=change,
                    target_field=None,
                    reason="no supported persistent Album target",
                )
            )
            continue

        target = LIBRARY_FIELD_TARGETS.get(change.field)
        if target is None:
            blocked.append(
                LibraryMappingBlocker(
                    source=change,
                    target_field=None,
                    reason="no supported persistent Album target for this canonical field",
                )
            )
            continue

        value = _map_value(change, target)
        if value is None:
            blocked.append(
                LibraryMappingBlocker(
                    source=change,
                    target_field=target.target_field,
                    reason=(
                        "multiple canonical values cannot be represented losslessly "
                        "by the singular persistent Album target"
                    ),
                )
            )
            continue
        mapped.append(
            LibraryTargetChange(
                canonical_field=change.field,
                target_field=target.target_field,
                target_shape=target.shape,
                target_value=value,
                source=change,
            )
        )

    return LibraryTargetPlan(plan, tuple(mapped), tuple(blocked))


def _require_text_tuple(change: PlannedChange) -> tuple[str, ...]:
    value = change.after
    if (
        not isinstance(value, tuple)
        or not value
        or not all(_is_canonical_text(item) for item in value)
    ):
        raise LibraryMappingError(f"{change.field!r} requires a non-empty tuple of strings")
    return value


def _map_value(
    change: PlannedChange, target: LibraryFieldTarget
) -> MetadataValue | None:
    value = change.after
    if target.shape is BeetsTargetShape.STRING_LIST:
        return _require_text_tuple(change)

    if target.shape is BeetsTargetShape.SCALAR_INT:
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 9999:
            raise LibraryMappingError(
                f"{change.field!r} requires an integer between 1 and 9999"
            )
        return value

    if target.shape is not BeetsTargetShape.SCALAR_STRING:
        raise LibraryMappingError(f"unsupported target shape for {change.field!r}")
    if change.field == "country":
        if not _is_canonical_text(value):
            raise LibraryMappingError("'country' requires a string")
        return value
    values = _require_text_tuple(change)
    return values[0] if len(values) == 1 else None


def _is_canonical_text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()
