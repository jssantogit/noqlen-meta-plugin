from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.changeplan import (
    ChangePlan,
    ChangePlanError,
    PlannedChange,
    build_change_plan,
)
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction


def candidate(
    field: str = "genres",
    value: object = ("Rock", "Metal"),
) -> MetadataCandidate:
    return MetadataCandidate(
        field=field,
        value=value,  # type: ignore[arg-type]
        provider="itunes",
        confidence=0.94,
        source_id="1097861387",
        source_url="https://music.apple.com/album/1097861387",
    )


def decision(
    field: str,
    action: ResolutionAction,
    *,
    current: object | None = None,
    selected: MetadataCandidate | None = None,
    alternatives: tuple[MetadataCandidate, ...] = (),
) -> FieldDecision:
    return FieldDecision(
        field=field,
        current_value=current,  # type: ignore[arg-type]
        selected=selected,
        action=action,
        reason=f"resolved {field}",
        alternatives=alternatives,
    )


def test_propose_becomes_one_planned_change_with_provenance() -> None:
    source = candidate()
    resolved = decision(
        "genres",
        ResolutionAction.PROPOSE,
        current=("Existing",),
        selected=source,
    )

    plan = build_change_plan([resolved])

    assert plan.has_changes
    assert plan.is_conflict_free
    assert not plan.requires_review
    assert plan.changes == (
        PlannedChange(
            field="genres",
            before=("Existing",),
            after=("Rock", "Metal"),
            source=source,
            reason="resolved genres",
        ),
    )
    change = plan.changes[0]
    assert change.source is source
    assert change.source.provider == "itunes"
    assert change.source.confidence == 0.94
    assert change.source.source_id == "1097861387"
    assert change.source.source_url == "https://music.apple.com/album/1097861387"


def test_propose_retains_missing_current_value() -> None:
    plan = build_change_plan(
        [decision("genres", ResolutionAction.PROPOSE, selected=candidate())]
    )

    assert plan.changes[0].before is None


@pytest.mark.parametrize(
    ("action", "category"),
    [
        (ResolutionAction.KEEP, "kept"),
        (ResolutionAction.SKIP, "skipped"),
    ],
)
def test_non_change_actions_are_retained_without_a_change(
    action: ResolutionAction, category: str
) -> None:
    resolved = decision("genres", action, selected=candidate())

    plan = build_change_plan([resolved])

    assert plan.changes == ()
    assert getattr(plan, category) == (resolved,)


@pytest.mark.parametrize("with_selected", [True, False])
def test_review_is_an_explicit_blocker_with_or_without_selection(
    with_selected: bool,
) -> None:
    contender = candidate()
    resolved = decision(
        "genres",
        ResolutionAction.REVIEW,
        selected=contender if with_selected else None,
        alternatives=() if with_selected else (contender,),
    )

    plan = build_change_plan([resolved])

    assert plan.reviews == (resolved,)
    assert plan.changes == ()
    assert plan.requires_review
    assert not plan.is_conflict_free


def test_mixed_plan_preserves_all_categories_and_value_shapes() -> None:
    genres = candidate("genres", ("Rock", "Metal"))
    year = candidate("year", 1997)
    resolved = [
        decision("styles", ResolutionAction.SKIP),
        decision("labels", ResolutionAction.REVIEW, selected=candidate("labels", ("Label",))),
        decision("year", ResolutionAction.PROPOSE, selected=year),
        decision("media", ResolutionAction.KEEP, selected=candidate("media", ("CD",))),
        decision("genres", ResolutionAction.PROPOSE, selected=genres),
    ]

    plan = build_change_plan(resolved)

    assert [change.field for change in plan.changes] == ["genres", "year"]
    assert plan.changes[0].after == ("Rock", "Metal")
    assert isinstance(plan.changes[0].after, tuple)
    assert plan.changes[1].after == 1997
    assert isinstance(plan.changes[1].after, int)
    assert len(plan.reviews) == len(plan.kept) == len(plan.skipped) == 1
    assert plan.has_changes
    assert plan.requires_review
    assert not plan.is_conflict_free


def test_invalid_propose_without_selected_candidate_fails() -> None:
    with pytest.raises(ChangePlanError, match="has no selected candidate"):
        build_change_plan([decision("genres", ResolutionAction.PROPOSE)])


def test_duplicate_field_decisions_fail() -> None:
    source = candidate()
    with pytest.raises(ChangePlanError, match="duplicate decision"):
        build_change_plan(
            [
                decision("genres", ResolutionAction.PROPOSE, selected=source),
                decision("genres", ResolutionAction.KEEP, selected=source),
            ]
        )


def test_selected_candidate_field_mismatch_fails() -> None:
    with pytest.raises(ChangePlanError, match="does not match"):
        build_change_plan(
            [decision("genres", ResolutionAction.PROPOSE, selected=candidate("year", 1997))]
        )


def test_planned_change_value_mismatch_fails() -> None:
    with pytest.raises(ChangePlanError, match="planned value"):
        PlannedChange("genres", None, ("Jazz",), candidate(), "invalid plan")


def test_build_does_not_mutate_inputs_and_results_are_immutable() -> None:
    source = candidate()
    resolved = decision("genres", ResolutionAction.PROPOSE, selected=source)
    decisions = [resolved]

    plan = build_change_plan(decisions)

    assert decisions == [resolved]
    assert resolved.selected is source
    with pytest.raises(FrozenInstanceError):
        plan.changes = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        plan.changes[0].after = ("Changed",)  # type: ignore[misc]


def test_plan_order_is_deterministic_regardless_of_decision_order() -> None:
    resolved = [
        decision("year", ResolutionAction.PROPOSE, selected=candidate("year", 1997)),
        decision("styles", ResolutionAction.SKIP),
        decision("labels", ResolutionAction.REVIEW),
        decision("genres", ResolutionAction.PROPOSE, selected=candidate()),
        decision("media", ResolutionAction.KEEP, selected=candidate("media", ("CD",))),
    ]

    assert build_change_plan(resolved) == build_change_plan(list(reversed(resolved)))


def test_empty_plan_is_conflict_free_without_changes() -> None:
    plan = ChangePlan()

    assert not plan.has_changes
    assert not plan.requires_review
    assert plan.is_conflict_free
