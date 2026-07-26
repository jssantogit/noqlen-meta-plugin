from dataclasses import FrozenInstanceError

import pytest
from beets.library import Album

from beetsplug.noqlenmeta.beets_mapping import BeetsTargetShape
from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.library_mapping import (
    LIBRARY_FIELD_TARGETS,
    LibraryFieldTarget,
    LibraryMappingError,
    LibraryTargetPlan,
    map_change_plan_to_library_album,
)
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction


def planned_change(field: str, value: object) -> PlannedChange:
    source = MetadataCandidate(
        field=field,
        value=value,  # type: ignore[arg-type]
        provider="discogs",
        confidence=0.92,
        source_id="123456",
    )
    return PlannedChange(field, None, source.value, source, f"resolved {field}")


def mapped_change(field: str, value: object) -> LibraryTargetPlan:
    return map_change_plan_to_library_album(
        ChangePlan(changes=(planned_change(field, value),))
    )


@pytest.mark.parametrize(
    ("canonical", "target", "shape"),
    [
        ("genres", "genres", BeetsTargetShape.STRING_LIST),
        ("styles", "style", BeetsTargetShape.SCALAR_STRING),
        ("labels", "label", BeetsTargetShape.SCALAR_STRING),
        ("catalog_numbers", "catalognum", BeetsTargetShape.SCALAR_STRING),
        ("barcodes", "barcode", BeetsTargetShape.SCALAR_STRING),
        ("country", "country", BeetsTargetShape.SCALAR_STRING),
        ("year", "year", BeetsTargetShape.SCALAR_INT),
    ],
)
def test_declared_library_target_contract(
    canonical: str, target: str, shape: BeetsTargetShape
) -> None:
    assert LIBRARY_FIELD_TARGETS[canonical] == LibraryFieldTarget(canonical, target, shape)
    assert target in Album._fields


@pytest.mark.parametrize(
    ("field", "value", "target", "target_value"),
    [
        ("genres", ("Rock", "Metal"), "genres", ("Rock", "Metal")),
        ("styles", ("Progressive Metal",), "style", "Progressive Metal"),
        ("labels", ("Roadrunner",), "label", "Roadrunner"),
        ("catalog_numbers", ("RR-123",), "catalognum", "RR-123"),
        ("barcodes", ("0123456789012",), "barcode", "0123456789012"),
        ("country", "DE", "country", "DE"),
        ("year", 2005, "year", 2005),
    ],
)
def test_lossless_library_mapping(
    field: str, value: object, target: str, target_value: object
) -> None:
    result = mapped_change(field, value)

    assert result.blocked_changes == ()
    assert result.mapped_changes[0].target_field == target
    assert result.mapped_changes[0].target_value == target_value
    if field == "genres":
        assert result.mapped_changes[0].target_value is result.source.changes[0].after


@pytest.mark.parametrize(
    ("field", "target"),
    [
        ("styles", "style"),
        ("labels", "label"),
        ("catalog_numbers", "catalognum"),
        ("barcodes", "barcode"),
    ],
)
def test_multiple_values_block_singular_library_targets(field: str, target: str) -> None:
    change = planned_change(field, ("First", "Second"))

    result = map_change_plan_to_library_album(ChangePlan(changes=(change,)))

    assert result.mapped_changes == ()
    assert result.blocked_changes[0].source is change
    assert result.blocked_changes[0].target_field == target
    assert "multiple canonical values" in result.blocked_changes[0].reason


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("media", "no supported album-level media target"),
        ("format_descriptions", "no supported persistent Album target"),
        ("mood", "no supported persistent Album target"),
    ],
)
def test_valid_unsupported_library_field_becomes_blocker(field: str, reason: str) -> None:
    change = planned_change(field, ("Atmospheric",))

    result = map_change_plan_to_library_album(ChangePlan(changes=(change,)))

    assert result.mapped_changes == ()
    assert result.blocked_changes[0].source is change
    assert result.blocked_changes[0].target_field is None
    assert reason in result.blocked_changes[0].reason


@pytest.mark.parametrize(
    ("field", "valid_value", "malformed"),
    [
        ("genres", ("Rock",), "Rock"),
        ("country", "DE", ("DE",)),
        ("year", 2005, "2005"),
        ("year", 2005, True),
        ("styles", ("Rock",), ()),
        ("genres", ("Rock",), (" ",)),
        ("country", "DE", " DE "),
    ],
)
def test_malformed_library_mapping_shapes_raise_error(
    field: str, valid_value: object, malformed: object
) -> None:
    change = planned_change(field, valid_value)
    object.__setattr__(change, "after", malformed)

    with pytest.raises(LibraryMappingError):
        map_change_plan_to_library_album(ChangePlan(changes=(change,)))


def test_library_target_plan_status_order_immutability_and_provenance() -> None:
    review = FieldDecision(
        "labels", ("Existing",), None, ResolutionAction.REVIEW, "conflict"
    )
    changes = (
        planned_change("year", 2005),
        planned_change("media", ("CD",)),
        planned_change("genres", ("Rock",)),
    )
    source = ChangePlan(changes=changes, reviews=(review,))

    result = map_change_plan_to_library_album(source)

    assert result.source is source
    assert [change.canonical_field for change in result.mapped_changes] == ["genres", "year"]
    assert [blocker.source.field for blocker in result.blocked_changes] == ["media"]
    assert result.mapped_changes[0].source is changes[2]
    assert result.has_mapping_blockers
    assert not result.is_fully_mapped
    assert result.requires_review
    with pytest.raises(FrozenInstanceError):
        result.mapped_changes = ()  # type: ignore[misc]


def test_library_mapping_is_deterministic_and_does_not_mutate_source() -> None:
    changes = (
        planned_change("labels", ("A", "B")),
        planned_change("genres", ("Rock",)),
        planned_change("format_descriptions", ("CD",)),
    )
    source = ChangePlan(changes=changes)

    result = map_change_plan_to_library_album(source)
    reversed_result = map_change_plan_to_library_album(
        ChangePlan(changes=tuple(reversed(changes)))
    )

    assert source.changes == changes
    assert result.mapped_changes == reversed_result.mapped_changes
    assert result.blocked_changes == reversed_result.blocked_changes
