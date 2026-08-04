from itertools import permutations

import pytest

from beetsplug.noqlenmeta.acoustid import (
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDFingerprintOrigin,
    AcoustIDResultGroup,
    classify_acoustid_evidence,
)


def identifier(number: int) -> str:
    return f"{number:08x}-0000-4000-8000-{number:012x}"


def group(number: int, score: float, *recordings: int) -> AcoustIDResultGroup:
    return AcoustIDResultGroup(
        identifier(number), score, tuple(identifier(recording) for recording in recordings)
    )


def policy(**changes: object) -> AcoustIDEvidencePolicy:
    values: dict[str, object] = {
        "min_score": 0.9,
        "min_margin": 0.05,
        "max_results": 5,
        "max_recordings_per_result": 10,
    }
    values.update(changes)
    return AcoustIDEvidencePolicy(**values)  # type: ignore[arg-type]


def classify(
    groups: tuple[AcoustIDResultGroup, ...], custom_policy: AcoustIDEvidencePolicy | None = None
):
    return classify_acoustid_evidence(
        "item:1", AcoustIDFingerprintOrigin.EXISTING, groups, custom_policy or policy()
    )


def test_no_eligible_result_is_no_match() -> None:
    result = classify((group(1, 0.89, 101),))

    assert result.verdict is AcoustIDEvidenceVerdict.NO_MATCH
    assert result.reason is AcoustIDEvidenceReason.NO_RESULT_ABOVE_MINIMUM
    assert result.top_score is None
    assert result.eligible_result_count == 0


def test_one_recording_is_decisive_and_exact_minimum_score_passes() -> None:
    result = classify((group(1, 0.9, 101),))

    assert result.verdict is AcoustIDEvidenceVerdict.DECISIVE
    assert result.reason is AcoustIDEvidenceReason.RECORDING_DECISIVE
    assert result.selected_acoustid_id == identifier(1)
    assert result.selected_recording_mbid == identifier(101)
    assert result.top_score == 0.9


def test_exact_margin_passes_and_below_margin_is_ambiguous() -> None:
    exact = classify((group(1, 0.95, 101), group(2, 0.9, 102)))
    below = classify((group(1, 0.949, 101), group(2, 0.9, 102)))

    assert exact.verdict is AcoustIDEvidenceVerdict.DECISIVE
    assert exact.margin == 0.95 - 0.9
    assert below.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS
    assert below.reason is AcoustIDEvidenceReason.INSUFFICIENT_MARGIN


def test_equal_top_support_across_recordings_is_competing() -> None:
    result = classify((group(1, 0.95, 101), group(2, 0.95, 102)))

    assert result.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS
    assert result.reason is AcoustIDEvidenceReason.COMPETING_RECORDINGS
    assert result.margin == 0.0


def test_duplicate_support_uses_highest_score_without_accumulating() -> None:
    result = classify(
        (group(1, 0.91, 101), group(2, 0.91, 101), group(3, 0.9, 102))
    )

    assert result.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS
    assert result.top_score == 0.91
    assert result.runner_up_score == 0.9
    assert result.reason is AcoustIDEvidenceReason.INSUFFICIENT_MARGIN


def test_duplicate_acoustid_ids_do_not_consume_the_result_bound() -> None:
    duplicate = group(1, 0.99, 101)
    result = classify(
        (duplicate, duplicate, group(2, 0.98, 102)),
        policy(max_results=2, min_margin=0),
    )

    assert len(result.result_groups) == 2
    assert result.eligible_recording_count == 2


def test_duplicate_acoustid_id_with_different_score_is_rejected_generically() -> None:
    groups = (group(1, 0.99, 101), group(1, 0.98, 101))

    with pytest.raises(ValueError, match="conflicting duplicate AcoustID result groups") as error:
        classify(groups)
    assert identifier(1) not in str(error.value)


def test_duplicate_acoustid_id_with_different_recordings_is_rejected_generically() -> None:
    groups = (group(1, 0.99, 101), group(1, 0.99, 102))

    with pytest.raises(ValueError, match="conflicting duplicate AcoustID result groups") as error:
        classify(groups)
    assert identifier(101) not in str(error.value)
    assert identifier(102) not in str(error.value)


def test_duplicate_acoustid_conflict_is_input_order_independent() -> None:
    groups = (group(1, 0.99, 101), group(1, 0.98, 102))
    messages = []
    for ordered in permutations(groups):
        with pytest.raises(ValueError) as error:
            classify(ordered)
        messages.append(str(error.value))

    assert messages == ["conflicting duplicate AcoustID result groups"] * 2


def test_one_group_with_multiple_recordings_is_competing() -> None:
    result = classify((group(1, 0.95, 102, 101),))

    assert result.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS
    assert result.reason is AcoustIDEvidenceReason.COMPETING_RECORDINGS


def test_same_recording_acoustid_tie_uses_canonical_uuid() -> None:
    result = classify((group(2, 0.95, 101), group(1, 0.95, 101)))

    assert result.verdict is AcoustIDEvidenceVerdict.DECISIVE
    assert result.selected_acoustid_id == identifier(1)


def test_input_order_does_not_change_evidence() -> None:
    groups = (group(3, 0.91, 103), group(1, 0.99, 101), group(2, 0.92, 102))
    results = [classify(order) for order in permutations(groups)]

    assert all(result == results[0] for result in results)
    assert results[0].selected_recording_mbid == identifier(101)


def test_result_bound_is_applied_by_score_then_uuid() -> None:
    groups = (group(3, 0.95, 103), group(2, 0.96, 102), group(1, 0.96, 101))
    result = classify(groups, policy(max_results=2, min_margin=0))

    assert tuple(item.acoustid_id for item in result.result_groups) == (
        identifier(1),
        identifier(2),
    )
    assert result.reason is AcoustIDEvidenceReason.COMPETING_RECORDINGS


def test_recording_bound_uses_canonical_recording_order() -> None:
    result = classify(
        (group(1, 0.95, 103, 101, 102),),
        policy(max_recordings_per_result=2),
    )

    assert result.result_groups[0].recording_mbids == (identifier(101), identifier(102))
    assert result.eligible_recording_count == 2
    assert result.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS


def test_strictly_below_margin_never_passes_as_exact() -> None:
    result = classify(
        (group(1, 0.9499999999995, 101), group(2, 0.9, 102)),
        policy(min_margin=0.05),
    )

    assert result.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS
    assert result.reason is AcoustIDEvidenceReason.INSUFFICIENT_MARGIN
