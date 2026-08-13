"""Pure target planning for accepted internal V3 release catalog changes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import cast

from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.field_contracts import PartialDate
from beetsplug.noqlenmeta.release_catalog import (
    ReleaseSecondaryType,
    ReleaseStatus,
    ReleaseType,
)


class CatalogMappingError(RuntimeError):
    pass


class CatalogTargetClass(Enum):
    NATIVE = "native"
    TYPED_DB = "typed_db"


@dataclass(frozen=True, slots=True)
class CatalogTargetChange:
    canonical_field: str
    target_field: str
    value: object
    target_class: CatalogTargetClass
    source: PlannedChange


@dataclass(frozen=True, slots=True)
class ReleaseCatalogTargetPlan:
    source: ChangePlan
    changes: tuple[CatalogTargetChange, ...] = ()


def map_release_catalog_plan(
    plan: ChangePlan,
    *,
    current_values: Mapping[str, object] | None = None,
) -> ReleaseCatalogTargetPlan:
    """Project Wave 1A canonical changes without performing resolution or writes."""
    if not isinstance(plan, ChangePlan):
        raise CatalogMappingError("source must be a ChangePlan")
    mapped: list[CatalogTargetChange] = []
    current = dict(current_values or {})
    for decision in plan.kept:
        if decision.field in {"release_type", "release_secondary_types"}:
            current.setdefault(decision.field, decision.current_value)
    primary_value = current.get("release_type")
    primary = primary_value if isinstance(primary_value, ReleaseType) else None
    secondary_value = current.get("release_secondary_types")
    secondary = (
        secondary_value
        if isinstance(secondary_value, tuple)
        and all(isinstance(value, ReleaseSecondaryType) for value in secondary_value)
        else None
    )
    primary_changed = False
    secondary_changed = False
    for change in plan.changes:
        if change.field in {"year", "original_year"}:
            raise CatalogMappingError(
                f"{change.field} is a derived projection, not an independent V3 value"
            )
        if change.field == "date":
            mapped.extend(_date_targets(change, "year", "month", "day"))
        elif change.field == "original_date":
            mapped.extend(
                _date_targets(
                    change,
                    "original_year",
                    "original_month",
                    "original_day",
                )
            )
        elif change.field == "release_type":
            if not isinstance(change.after, ReleaseType):
                raise CatalogMappingError("release_type requires ReleaseType")
            primary = change.after
            primary_changed = True
            mapped.append(_target(change, "albumtype", primary.value, CatalogTargetClass.NATIVE))
        elif change.field == "release_secondary_types":
            if not isinstance(change.after, tuple) or not all(
                isinstance(value, ReleaseSecondaryType) for value in change.after
            ):
                raise CatalogMappingError(
                    "release_secondary_types requires ReleaseSecondaryType values"
                )
            secondary = cast(tuple[ReleaseSecondaryType, ...], change.after)
            secondary_changed = True
            mapped.append(
                _target(
                    change,
                    "release_secondary_types",
                    tuple(value.value for value in secondary),
                    CatalogTargetClass.TYPED_DB,
                )
            )
        elif change.field == "release_status":
            if not isinstance(change.after, ReleaseStatus):
                raise CatalogMappingError("release_status requires ReleaseStatus")
            mapped.append(
                _target(
                    change,
                    "albumstatus",
                    change.after.value,
                    CatalogTargetClass.NATIVE,
                )
            )
        elif change.field == "edition":
            if not isinstance(change.after, str) or not change.after:
                raise CatalogMappingError("edition requires a string")
            mapped.append(_target(change, "edition", change.after, CatalogTargetClass.TYPED_DB))
        else:
            raise CatalogMappingError(f"unsupported release catalog field: {change.field}")

    if primary is not None and secondary is not None and (primary_changed or secondary_changed):
        source_field = "release_secondary_types" if secondary_changed else "release_type"
        source = next(change for change in plan.changes if change.field == source_field)
        mapped.append(
            _target(
                source,
                "albumtypes",
                (primary.value, *(value.value for value in secondary)),
                CatalogTargetClass.NATIVE,
            )
        )
    return ReleaseCatalogTargetPlan(
        plan,
        tuple(sorted(mapped, key=lambda target: target.target_field)),
    )


def _date_targets(
    change: PlannedChange, year_field: str, month_field: str, day_field: str
) -> tuple[CatalogTargetChange, ...]:
    if not isinstance(change.after, PartialDate):
        raise CatalogMappingError(f"{change.field} requires PartialDate")
    values = [(year_field, change.after.year)]
    if change.after.month is not None:
        values.append((month_field, change.after.month))
    if change.after.day is not None:
        values.append((day_field, change.after.day))
    return tuple(
        _target(change, field, value, CatalogTargetClass.NATIVE) for field, value in values
    )


def _target(
    source: PlannedChange,
    field: str,
    value: object,
    target_class: CatalogTargetClass,
) -> CatalogTargetChange:
    return CatalogTargetChange(source.field, field, value, target_class, source)
