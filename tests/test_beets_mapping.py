from dataclasses import FrozenInstanceError

import pytest
from beets.autotag.hooks import AlbumInfo

from beetsplug.noqlenmeta.beets_mapping import (
    BEETS_FIELD_TARGETS,
    BeetsFieldTarget,
    BeetsMappingError,
    BeetsTargetPlan,
    BeetsTargetShape,
    map_change_plan_to_beets,
)
from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction


def planned_change(field: str, value: object) -> PlannedChange:
    source = MetadataCandidate(
        field=field,
        value=value,  # type: ignore[arg-type]
        provider="discogs",
        confidence=0.92,
        source_id="123456",
        source_url="https://www.discogs.com/release/123456",
    )
    return PlannedChange(field, None, source.value, source, f"resolved {field}")


def mapped_change(field: str, value: object) -> BeetsTargetPlan:
    return map_change_plan_to_beets(ChangePlan(changes=(planned_change(field, value),)))


@pytest.mark.parametrize(
    ("canonical", "target", "shape"),
    [
        ("genres", "genres", BeetsTargetShape.STRING_LIST),
        ("styles", "styles", BeetsTargetShape.STRING_LIST),
        ("labels", "label", BeetsTargetShape.SCALAR_STRING),
        ("catalog_numbers", "catalognum", BeetsTargetShape.SCALAR_STRING),
        ("barcodes", "barcode", BeetsTargetShape.SCALAR_STRING),
        ("country", "country", BeetsTargetShape.SCALAR_STRING),
        ("year", "year", BeetsTargetShape.SCALAR_INT),
        ("media", "media", BeetsTargetShape.SCALAR_STRING),
    ],
)
def test_declared_target_contract(
    canonical: str, target: str, shape: BeetsTargetShape
) -> None:
    assert BEETS_FIELD_TARGETS[canonical] == BeetsFieldTarget(canonical, target, shape)


def test_target_contract_matches_real_album_info() -> None:
    info = AlbumInfo(
        [],
        genres=["Rock", "Metal"],
        style="Progressive Metal",
        label="Roadrunner",
        catalognum="RR-123",
        barcode="0123456789012",
        country="DE",
        year=2005,
        media="CD",
    )

    assert info.genres == ["Rock", "Metal"]
    assert info.style == "Progressive Metal"
    assert info.label == "Roadrunner"
    assert info.catalognum == "RR-123"
    assert info.barcode == "0123456789012"
    assert info.country == "DE"
    assert info.year == 2005
    assert info.media == "CD"


def test_target_definitions_are_immutable() -> None:
    with pytest.raises(TypeError):
        BEETS_FIELD_TARGETS["genres"] = BeetsFieldTarget(  # type: ignore[index]
            "genres", "genre", BeetsTargetShape.SCALAR_STRING
        )
    with pytest.raises(FrozenInstanceError):
        BEETS_FIELD_TARGETS["genres"].target_field = "genre"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value", "target", "target_value"),
    [
        ("genres", ("Rock", "Metal"), "genres", ("Rock", "Metal")),
        (
            "styles",
            ("Progressive Metal", "Technical Death Metal"),
            "styles",
            ("Progressive Metal", "Technical Death Metal"),
        ),
        ("labels", ("Roadrunner",), "label", "Roadrunner"),
        ("catalog_numbers", ("RR-123",), "catalognum", "RR-123"),
        ("barcodes", ("0123456789012",), "barcode", "0123456789012"),
        ("country", "DE", "country", "DE"),
        ("year", 2005, "year", 2005),
        ("media", ("CD",), "media", "CD"),
    ],
)
def test_lossless_mapping(
    field: str, value: object, target: str, target_value: object
) -> None:
    result = mapped_change(field, value)

    assert result.blocked_changes == ()
    assert len(result.mapped_changes) == 1
    assert result.mapped_changes[0].target_field == target
    assert result.mapped_changes[0].target_value == target_value
    if field in {"genres", "styles"}:
        assert isinstance(result.mapped_changes[0].target_value, tuple)


@pytest.mark.parametrize(
    ("field", "target"),
    [
        ("labels", "label"),
        ("catalog_numbers", "catalognum"),
        ("barcodes", "barcode"),
        ("media", "media"),
    ],
)
def test_multiple_values_block_singular_targets(field: str, target: str) -> None:
    change = planned_change(field, ("First", "Second"))

    result = map_change_plan_to_beets(ChangePlan(changes=(change,)))

    assert result.mapped_changes == ()
    assert result.blocked_changes[0].source is change
    assert result.blocked_changes[0].target_field == target
    assert "multiple canonical values" in result.blocked_changes[0].reason


@pytest.mark.parametrize("field", ["format_descriptions", "mood"])
def test_valid_unmapped_field_becomes_unsupported_target_blocker(field: str) -> None:
    change = planned_change(field, ("Atmospheric",))

    result = map_change_plan_to_beets(ChangePlan(changes=(change,)))

    assert result.mapped_changes == ()
    assert result.blocked_changes[0].source is change
    assert result.blocked_changes[0].target_field is None
    assert "no supported AlbumInfo target" in result.blocked_changes[0].reason


@pytest.mark.parametrize(
    ("field", "valid_value", "malformed"),
    [
        ("genres", ("Rock",), "Rock"),
        ("country", "DE", ("DE",)),
        ("year", 2005, "2005"),
        ("year", 2005, True),
        ("styles", ("Rock",), ()),
    ],
)
def test_malformed_canonical_shapes_raise_mapping_error(
    field: str, valid_value: object, malformed: object
) -> None:
    change = planned_change(field, valid_value)
    object.__setattr__(change, "after", malformed)

    with pytest.raises(BeetsMappingError):
        map_change_plan_to_beets(ChangePlan(changes=(change,)))


def test_target_plan_retains_source_review_and_truthful_status() -> None:
    review = FieldDecision(
        "labels",
        ("Existing",),
        None,
        ResolutionAction.REVIEW,
        "conflicting candidates",
    )
    source = ChangePlan(reviews=(review,))

    result = map_change_plan_to_beets(source)

    assert result.source is source
    assert result.source.reviews == (review,)
    assert result.is_fully_mapped
    assert not result.has_mapping_blockers
    assert result.requires_review


def test_mapping_blocker_requires_review_and_mapped_changes_may_coexist() -> None:
    source = ChangePlan(
        changes=(
            planned_change("labels", ("Label A", "Label B")),
            planned_change("genres", ("Rock", "Metal")),
        )
    )

    result = map_change_plan_to_beets(source)

    assert result.has_mapping_blockers
    assert not result.is_fully_mapped
    assert result.requires_review
    assert [change.canonical_field for change in result.mapped_changes] == ["genres"]
    assert [blocker.source.field for blocker in result.blocked_changes] == ["labels"]


def test_fully_mapped_plan_without_source_review_does_not_require_review() -> None:
    result = mapped_change("genres", ("Rock", "Metal"))

    assert result.is_fully_mapped
    assert not result.requires_review


def test_mapping_order_is_deterministic_and_source_plan_is_not_changed() -> None:
    changes = (
        planned_change("year", 2005),
        planned_change("labels", ("A", "B")),
        planned_change("genres", ("Rock",)),
        planned_change("format_descriptions", ("CD",)),
    )
    source = ChangePlan(changes=changes)

    result = map_change_plan_to_beets(source)
    reversed_result = map_change_plan_to_beets(ChangePlan(changes=tuple(reversed(changes))))

    assert source.changes == changes
    assert [change.canonical_field for change in result.mapped_changes] == ["genres", "year"]
    assert [blocker.source.field for blocker in result.blocked_changes] == [
        "format_descriptions",
        "labels",
    ]
    assert result.mapped_changes == reversed_result.mapped_changes
    assert result.blocked_changes == reversed_result.blocked_changes


def test_result_is_immutable_and_preserves_planned_change_provenance_identity() -> None:
    change = planned_change("genres", ("Rock", "Metal"))
    result = map_change_plan_to_beets(ChangePlan(changes=(change,)))

    assert result.mapped_changes[0].source is change
    assert result.mapped_changes[0].source.source is change.source
    with pytest.raises(FrozenInstanceError):
        result.mapped_changes = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.mapped_changes[0].target_value = ("Jazz",)  # type: ignore[misc]


def test_invalid_mapping_definition_raises_mapping_error() -> None:
    with pytest.raises(BeetsMappingError):
        BeetsFieldTarget("genres", "Genre Field", BeetsTargetShape.STRING_LIST)


def test_mapper_does_not_mutate_source_values() -> None:
    change = planned_change("genres", ("Rock", "Metal"))
    source = ChangePlan(changes=(change,))

    result = map_change_plan_to_beets(source)

    assert change.after == ("Rock", "Metal")
    assert result.mapped_changes[0].target_value is change.after
    assert isinstance(result, BeetsTargetPlan)
