import pytest
from beets.dbcore import types

from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import ExternalIdentifier
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind, PartialDate
from beetsplug.noqlenmeta.field_types import ALBUM_FIELD_TYPES
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.release_catalog import (
    ReleaseSecondaryType,
    ReleaseStatus,
    ReleaseType,
)
from beetsplug.noqlenmeta.release_catalog_mapping import (
    CatalogMappingError,
    CatalogTargetClass,
    map_release_catalog_plan,
)


def source(field: str, value: object, entity: EntityKind) -> MetadataEvidence:
    return MetadataEvidence(
        field=field,
        value=value,  # type: ignore[arg-type]
        subject=SubjectRef(
            entity,
            (ExternalIdentifier(f"catalog.{entity.value}", "entity-1"),),
        ),
        provider="catalog",
        acquisition_scope=ProviderScope.RELEASE,
        source_id="entity-1",
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
    )


def change(field: str, value: object, entity: EntityKind = EntityKind.RELEASE) -> PlannedChange:
    evidence = source(field, value, entity)
    return PlannedChange(field, None, value, evidence, "resolved", (evidence,))  # type: ignore[arg-type]


def targets(plan: ChangePlan) -> dict[str, object]:
    mapped = map_release_catalog_plan(plan)
    return {target.target_field: target.value for target in mapped.changes}


def targets_with_current(
    plan: ChangePlan, current: dict[str, object]
) -> dict[str, object]:
    mapped = map_release_catalog_plan(plan, current_values=current)
    return {target.target_field: target.value for target in mapped.changes}


def test_date_maps_only_known_components_and_derives_year() -> None:
    assert targets(ChangePlan(changes=(change("date", PartialDate(2020)),))) == {"year": 2020}
    assert targets(ChangePlan(changes=(change("date", PartialDate(2020, 5)),))) == {
        "year": 2020,
        "month": 5,
    }
    assert targets(ChangePlan(changes=(change("date", PartialDate(2020, 5, 17)),))) == {
        "year": 2020,
        "month": 5,
        "day": 17,
    }


def test_original_date_maps_only_known_original_components() -> None:
    plan = ChangePlan(
        changes=(
            change(
                "original_date",
                PartialDate(1999, 4),
                EntityKind.RELEASE_GROUP,
            ),
        )
    )

    assert targets(plan) == {"original_year": 1999, "original_month": 4}


def test_type_and_status_map_to_native_targets() -> None:
    plan = ChangePlan(
        changes=(
            change("release_type", ReleaseType.ALBUM, EntityKind.RELEASE_GROUP),
            change("release_status", ReleaseStatus.OFFICIAL),
        )
    )

    mapped = map_release_catalog_plan(plan)

    assert targets(plan) == {"albumtype": "Album", "albumstatus": "Official"}
    assert all(target.target_class is CatalogTargetClass.NATIVE for target in mapped.changes)


def test_secondary_types_preserve_separate_db_value_and_combined_native_projection() -> None:
    plan = ChangePlan(
        changes=(
            change("release_type", ReleaseType.ALBUM, EntityKind.RELEASE_GROUP),
            change(
                "release_secondary_types",
                (ReleaseSecondaryType.LIVE, ReleaseSecondaryType.COMPILATION),
                EntityKind.RELEASE_GROUP,
            ),
        )
    )

    mapped = map_release_catalog_plan(plan)

    assert targets(plan) == {
        "albumtype": "Album",
        "release_secondary_types": ("Live", "Compilation"),
        "albumtypes": ("Album", "Live", "Compilation"),
    }
    separate = next(
        target for target in mapped.changes if target.target_field == "release_secondary_types"
    )
    assert separate.target_class is CatalogTargetClass.TYPED_DB


def test_secondary_types_without_primary_do_not_invent_combined_projection() -> None:
    plan = ChangePlan(
        changes=(
            change(
                "release_secondary_types",
                (ReleaseSecondaryType.LIVE,),
                EntityKind.RELEASE_GROUP,
            ),
        )
    )

    assert targets(plan) == {"release_secondary_types": ("Live",)}


def test_secondary_change_uses_effective_kept_primary_for_combined_projection() -> None:
    plan = ChangePlan(
        changes=(
            change(
                "release_secondary_types",
                (ReleaseSecondaryType.LIVE,),
                EntityKind.RELEASE_GROUP,
            ),
        )
    )

    assert targets_with_current(plan, {"release_type": ReleaseType.ALBUM}) == {
        "release_secondary_types": ("Live",),
        "albumtypes": ("Album", "Live"),
    }


def test_primary_change_uses_effective_kept_secondary_for_combined_projection() -> None:
    plan = ChangePlan(
        changes=(change("release_type", ReleaseType.ALBUM, EntityKind.RELEASE_GROUP),)
    )

    assert targets_with_current(
        plan,
        {"release_secondary_types": (ReleaseSecondaryType.LIVE,)},
    ) == {
        "albumtype": "Album",
        "albumtypes": ("Album", "Live"),
    }


def test_edition_is_db_only() -> None:
    mapped = map_release_catalog_plan(ChangePlan(changes=(change("edition", "Limited Edition"),)))

    assert [
        (target.target_field, target.value, target.target_class) for target in mapped.changes
    ] == [("edition", "Limited Edition", CatalogTargetClass.TYPED_DB)]


def test_wave_1a_registers_only_required_album_flexible_fields() -> None:
    assert ALBUM_FIELD_TYPES["edition"] is types.STRING
    assert ALBUM_FIELD_TYPES["release_secondary_types"] is types.MULTI_VALUE_DSV


def test_v3_plan_rejects_year_as_an_independent_canonical_change() -> None:
    with pytest.raises(CatalogMappingError, match="derived projection"):
        map_release_catalog_plan(
            ChangePlan(
                changes=(
                    change("date", PartialDate(2020, 5, 17)),
                    change("year", 2019),
                )
            )
        )
