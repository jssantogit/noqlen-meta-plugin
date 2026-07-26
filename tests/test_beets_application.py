from dataclasses import FrozenInstanceError, replace

import pytest
from beets.autotag.hooks import AlbumInfo

import beetsplug.noqlenmeta.beets_application as application_module
from beetsplug.noqlenmeta.beets_application import (
    BeetsApplicationError,
    apply_beets_target_plan,
)
from beetsplug.noqlenmeta.beets_mapping import (
    BeetsTargetPlan,
    map_change_plan_to_beets,
)
from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction


def album_info(**overrides: object) -> AlbumInfo:
    values: dict[str, object] = {"artist": "Artist", "album": "Album"}
    values.update(overrides)
    return AlbumInfo([], **values)


def planned_change(field: str, after: object, before: object = None) -> PlannedChange:
    candidate = MetadataCandidate(
        field,
        after,  # type: ignore[arg-type]
        "discogs",
        0.95,
        "123456",
    )
    return PlannedChange(
        field,
        before,  # type: ignore[arg-type]
        candidate.value,
        candidate,
        f"resolved {field}",
    )


def target_plan(
    *changes: PlannedChange,
    reviews: tuple[FieldDecision, ...] = (),
) -> BeetsTargetPlan:
    return map_change_plan_to_beets(ChangePlan(changes=changes, reviews=reviews))


def review(field: str = "labels") -> FieldDecision:
    return FieldDecision(
        field,
        None,
        None,
        ResolutionAction.REVIEW,
        "requires review",
    )


def test_successful_genres_application_materializes_fresh_list() -> None:
    info = album_info()
    plan = target_plan(planned_change("genres", ("Rock", "Metal")))
    immutable_value = plan.mapped_changes[0].target_value

    result = apply_beets_target_plan(info, plan)

    assert info.genres == ["Rock", "Metal"]
    assert isinstance(info.genres, list)
    assert info.genres is not immutable_value
    assert result.applied_changes == plan.mapped_changes
    assert result.has_applied_changes
    assert not result.is_blocked


@pytest.mark.parametrize(
    ("field", "value", "target", "expected"),
    [
        ("styles", ("Progressive Metal",), "style", "Progressive Metal"),
        ("labels", ("Roadrunner",), "label", "Roadrunner"),
        ("catalog_numbers", ("RR-123",), "catalognum", "RR-123"),
        ("barcodes", ("0123456789012",), "barcode", "0123456789012"),
        ("country", "DE", "country", "DE"),
        ("year", 2005, "year", 2005),
        ("media", ("CD",), "media", "CD"),
    ],
)
def test_successful_scalar_application(
    field: str,
    value: object,
    target: str,
    expected: object,
) -> None:
    info = album_info()

    result = apply_beets_target_plan(info, target_plan(planned_change(field, value)))

    assert getattr(info, target) == expected
    assert result.has_applied_changes


def test_application_result_is_immutable_and_retains_provenance() -> None:
    change = planned_change("genres", ("Rock",))
    result = apply_beets_target_plan(album_info(), target_plan(change))

    assert result.applied_changes[0].source is change
    assert result.applied_changes[0].source.source is change.source
    with pytest.raises(FrozenInstanceError):
        result.applied_changes = ()  # type: ignore[misc]


def test_empty_plan_is_a_successful_no_op() -> None:
    info = album_info(genres=["Existing"])
    snapshot = dict(info)

    result = apply_beets_target_plan(info, target_plan())

    assert dict(info) == snapshot
    assert not result.is_blocked
    assert not result.has_applied_changes


@pytest.mark.parametrize(
    ("reviews", "label_values", "review_count", "blocker_count"),
    [
        ((review(),), None, 1, 0),
        ((), ("Label A", "Label B"), 0, 1),
        ((review(),), ("Label A", "Label B"), 1, 1),
    ],
)
def test_review_or_mapping_blocker_prevents_all_mutation(
    reviews: tuple[FieldDecision, ...],
    label_values: tuple[str, ...] | None,
    review_count: int,
    blocker_count: int,
) -> None:
    info = album_info(genres=["Existing"], label="Existing Label")
    changes = [planned_change("genres", ("Rock",), ("Existing",))]
    if label_values is not None:
        changes.append(planned_change("labels", label_values, ("Existing Label",)))

    result = apply_beets_target_plan(info, target_plan(*changes, reviews=reviews))

    assert info.genres == ["Existing"]
    assert info.label == "Existing Label"
    assert result.applied_changes == ()
    assert result.resolution_review_count == review_count
    assert result.mapping_blocker_count == blocker_count
    assert result.is_blocked


def test_stale_before_state_fails_before_any_mutation() -> None:
    info = album_info(genres=["Rock"], year=None)
    plan = target_plan(
        planned_change("genres", ("Metal",), ("Rock",)),
        planned_change("year", 2005),
    )
    info.year = 1999

    with pytest.raises(BeetsApplicationError, match="no longer matches"):
        apply_beets_target_plan(info, plan)

    assert info.genres == ["Rock"]
    assert info.year == 1999


def test_inconsistent_target_plan_fails_without_mutation() -> None:
    info = album_info()
    plan = target_plan(planned_change("genres", ("Rock",)))
    forged_change = replace(plan.mapped_changes[0], target_value=("Jazz",))
    forged = replace(plan, mapped_changes=(forged_change,))

    with pytest.raises(BeetsApplicationError, match="canonical source mapping"):
        apply_beets_target_plan(info, forged)

    assert info.genres is None


def test_duplicate_target_fields_fail_before_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    info = album_info()
    plan = target_plan(
        planned_change("genres", ("Rock",)),
        planned_change("year", 2005),
    )
    duplicate = replace(plan.mapped_changes[1], target_field="genres")
    forged = replace(plan, mapped_changes=(plan.mapped_changes[0], duplicate))
    monkeypatch.setattr(application_module, "map_change_plan_to_beets", lambda source: forged)

    with pytest.raises(BeetsApplicationError, match="duplicate AlbumInfo target"):
        apply_beets_target_plan(info, forged)

    assert info.genres is None
    assert info.year is None


def test_invalid_target_shape_fails_before_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    info = album_info()
    plan = target_plan(planned_change("genres", ("Rock",)))
    malformed_change = replace(plan.mapped_changes[0], target_value="Rock")
    malformed = replace(plan, mapped_changes=(malformed_change,))
    monkeypatch.setattr(application_module, "map_change_plan_to_beets", lambda source: malformed)

    with pytest.raises(BeetsApplicationError, match="string-list target"):
        apply_beets_target_plan(info, malformed)

    assert info.genres is None


def test_successful_application_invalidates_album_info_metadata_caches() -> None:
    info = album_info(genres=[])
    before_raw = info.raw_data
    before_items = info.item_data
    assert before_raw["genres"] == []
    assert "genres" not in before_items
    assert "raw_data" in info.__dict__
    assert "item_data" in info.__dict__

    apply_beets_target_plan(info, target_plan(planned_change("genres", ("Rock", "Metal"))))

    assert "raw_data" not in info.__dict__
    assert "item_data" not in info.__dict__
    assert info.raw_data["genres"] == ["Rock", "Metal"]
    assert info.item_data["genres"] == ["Rock", "Metal"]
    assert info.raw_data is not before_raw
    assert info.item_data is not before_items
