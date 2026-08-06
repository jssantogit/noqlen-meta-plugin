from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.acoustid import (
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDExistingValues,
    AcoustIDFingerprintMaterial,
    AcoustIDFingerprintOrigin,
    AcoustIDLibraryTargetKind,
    AcoustIDResultGroup,
    AcoustIDSourceSnapshot,
    AcoustIDStoredValueState,
    AcoustIDTrackEvidence,
    FingerprintBackendResult,
    FingerprintPreparationResult,
    canonical_acoustid_uuid,
    canonical_recording_mbid,
)
from beetsplug.noqlenmeta.acoustid.domain import _MAX_FINGERPRINT_LENGTH


def identifier(number: int) -> str:
    return f"{number:08x}-0000-4000-8000-{number:012x}"


def snapshot() -> AcoustIDSourceSnapshot:
    return AcoustIDSourceSnapshot(device=1, inode=2, size=3, mtime_ns=4)


def group(score: float = 0.95) -> AcoustIDResultGroup:
    return AcoustIDResultGroup(identifier(1), score, (identifier(101),))


def evidence(**changes: object) -> AcoustIDTrackEvidence:
    values: dict[str, object] = {
        "local_key": "item:1",
        "fingerprint_origin": AcoustIDFingerprintOrigin.EXISTING,
        "result_groups": (group(),),
        "verdict": AcoustIDEvidenceVerdict.DECISIVE,
        "selected_acoustid_id": identifier(1),
        "selected_recording_mbid": identifier(101),
        "reason": AcoustIDEvidenceReason.RECORDING_DECISIVE,
        "top_score": 0.95,
        "runner_up_score": None,
        "margin": None,
        "eligible_result_count": 1,
        "eligible_recording_count": 1,
    }
    values.update(changes)
    return AcoustIDTrackEvidence(**values)  # type: ignore[arg-type]


def test_identifier_helpers_canonicalize_uppercase_uuid_text() -> None:
    value = identifier(42)

    assert canonical_acoustid_uuid(value.upper()) == value
    assert canonical_recording_mbid(value.upper()) == value


@pytest.mark.parametrize(
    "value",
    [None, 1, "", "not-a-uuid", f" {identifier(1)}", f"{identifier(1)}x", identifier(1)[:-1]],
)
@pytest.mark.parametrize("canonicalizer", [canonical_acoustid_uuid, canonical_recording_mbid])
def test_identifier_helpers_reject_malformed_or_surrounded_values(value, canonicalizer) -> None:
    with pytest.raises(ValueError, match="UUID"):
        canonicalizer(value)


def test_result_group_canonicalizes_deduplicates_and_orders_recordings() -> None:
    value = AcoustIDResultGroup(
        identifier(2).upper(),
        1,
        (identifier(103), identifier(101).upper(), identifier(103), identifier(102)),
    )

    assert value.acoustid_id == identifier(2)
    assert value.score == 1.0
    assert value.recording_mbids == (identifier(101), identifier(102), identifier(103))
    with pytest.raises(FrozenInstanceError):
        value.score = 0.5  # type: ignore[misc]


@pytest.mark.parametrize("score", [0.0, 1.0])
def test_result_group_accepts_score_boundaries(score: float) -> None:
    assert group(score).score == score


@pytest.mark.parametrize("score", [True, -0.01, 1.01, float("nan"), float("inf"), -float("inf")])
def test_result_group_rejects_invalid_scores(score: object) -> None:
    with pytest.raises(ValueError, match="score"):
        group(score)  # type: ignore[arg-type]


def test_result_group_rejects_empty_malformed_and_oversized_recordings() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        AcoustIDResultGroup(identifier(1), 0.9, ())
    with pytest.raises(ValueError, match="recording MBID"):
        AcoustIDResultGroup(identifier(1), 0.9, ("invalid",))
    with pytest.raises(ValueError, match="count limit"):
        AcoustIDResultGroup(identifier(1), 0.9, tuple(identifier(i) for i in range(1, 52)))
    assert len(
        AcoustIDResultGroup(
            identifier(1), 0.9, tuple(identifier(i) for i in range(1, 51))
        ).recording_mbids
    ) == 50


def test_fingerprint_material_enforces_origin_snapshot_contract() -> None:
    existing = AcoustIDFingerprintMaterial(
        "item:1", "synthetic-fingerprint", 1, AcoustIDFingerprintOrigin.EXISTING
    )
    generated = AcoustIDFingerprintMaterial(
        "item:2",
        "synthetic-fingerprint",
        1.5,
        AcoustIDFingerprintOrigin.GENERATED,
        snapshot(),
    )

    assert existing.duration_seconds == 1.0
    assert generated.source_snapshot == snapshot()
    with pytest.raises(ValueError, match="prohibits"):
        AcoustIDFingerprintMaterial(
            "item:1", "synthetic", 1, AcoustIDFingerprintOrigin.EXISTING, snapshot()
        )
    with pytest.raises(ValueError, match="requires"):
        AcoustIDFingerprintMaterial(
            "item:1", "synthetic", 1, AcoustIDFingerprintOrigin.GENERATED
        )


@pytest.mark.parametrize("duration", [True, 0, -1, float("nan"), float("inf")])
def test_fingerprint_material_rejects_invalid_duration(duration: object) -> None:
    with pytest.raises(ValueError, match="duration_seconds"):
        AcoustIDFingerprintMaterial(
            "item:1", "synthetic", duration, AcoustIDFingerprintOrigin.EXISTING
        )  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "local_key",
    [None, "", " ", ".", "..", " . ", " .. ", "/private/item", "folder\\item", "x\0y"],
)
def test_domain_values_reject_nonempty_or_path_like_local_keys(local_key: object) -> None:
    with pytest.raises(ValueError, match="path-free"):
        AcoustIDFingerprintMaterial(
            local_key, "synthetic", 1, AcoustIDFingerprintOrigin.EXISTING
        )  # type: ignore[arg-type]


def test_fingerprint_length_boundary_and_representations_are_redacted() -> None:
    fingerprint = "f" * _MAX_FINGERPRINT_LENGTH
    value = AcoustIDFingerprintMaterial(
        "item:1", fingerprint, 1, AcoustIDFingerprintOrigin.EXISTING
    )

    assert fingerprint not in repr(value)
    assert fingerprint not in str(value)
    with pytest.raises(ValueError) as captured:
        AcoustIDFingerprintMaterial(
            "item:1", fingerprint + "secret", 1, AcoustIDFingerprintOrigin.EXISTING
        )
    assert "secret" not in str(captured.value)

    other = AcoustIDFingerprintMaterial(
        "item:1", fingerprint[:-1] + "x", 1, AcoustIDFingerprintOrigin.EXISTING
    )
    assert fingerprint not in repr((value, other))


@pytest.mark.parametrize("fingerprint", [None, "", " "])
def test_fingerprint_validation_errors_do_not_echo_sensitive_input(fingerprint: object) -> None:
    with pytest.raises(ValueError) as captured:
        AcoustIDFingerprintMaterial(
            "item:1", fingerprint, 1, AcoustIDFingerprintOrigin.EXISTING
        )  # type: ignore[arg-type]
    assert repr(fingerprint) not in str(captured.value)


@pytest.mark.parametrize("field", ["min_score", "min_margin"])
@pytest.mark.parametrize("value", [0, 1])
def test_policy_accepts_numeric_boundaries(field: str, value: int) -> None:
    policy = AcoustIDEvidencePolicy(0.9, 0.05, 5, 10)
    values = {
        "min_score": policy.min_score,
        "min_margin": policy.min_margin,
        "max_results": policy.max_results,
        "max_recordings_per_result": policy.max_recordings_per_result,
        field: value,
    }

    assert getattr(AcoustIDEvidencePolicy(**values), field) == float(value)


@pytest.mark.parametrize("field", ["min_score", "min_margin"])
@pytest.mark.parametrize("value", [True, -0.01, 1.01, float("nan"), float("inf")])
def test_policy_rejects_invalid_numeric_values(field: str, value: object) -> None:
    values = {
        "min_score": 0.9,
        "min_margin": 0.05,
        "max_results": 5,
        "max_recordings_per_result": 10,
        field: value,
    }
    with pytest.raises(ValueError, match=field):
        AcoustIDEvidencePolicy(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "lower", "upper"),
    [("max_results", 1, 20), ("max_recordings_per_result", 1, 50)],
)
def test_policy_accepts_integer_boundaries(field: str, lower: int, upper: int) -> None:
    baseline = {
        "min_score": 0.9,
        "min_margin": 0.05,
        "max_results": 5,
        "max_recordings_per_result": 10,
    }

    assert getattr(AcoustIDEvidencePolicy(**{**baseline, field: lower}), field) == lower
    assert getattr(AcoustIDEvidencePolicy(**{**baseline, field: upper}), field) == upper


@pytest.mark.parametrize("field", ["max_results", "max_recordings_per_result"])
@pytest.mark.parametrize("value", [True, 0, 51])
def test_policy_rejects_invalid_integer_bounds(field: str, value: object) -> None:
    values = {
        "min_score": 0.9,
        "min_margin": 0.05,
        "max_results": 5,
        "max_recordings_per_result": 10,
        field: value,
    }
    with pytest.raises(ValueError, match=field):
        AcoustIDEvidencePolicy(**values)  # type: ignore[arg-type]


def test_track_evidence_enforces_decisive_and_non_decisive_identifiers() -> None:
    assert evidence().selected_recording_mbid == identifier(101)
    with pytest.raises(ValueError, match="both selected"):
        evidence(selected_acoustid_id=None)
    with pytest.raises(ValueError, match="recording_decisive"):
        evidence(reason=AcoustIDEvidenceReason.COMPETING_RECORDINGS)
    with pytest.raises(ValueError, match="prohibits selected"):
        evidence(
            verdict=AcoustIDEvidenceVerdict.NO_MATCH,
            reason=AcoustIDEvidenceReason.NO_RESULT_ABOVE_MINIMUM,
            top_score=None,
            eligible_result_count=0,
            eligible_recording_count=0,
        )


def test_track_evidence_enforces_non_decisive_reasons_and_counts() -> None:
    with pytest.raises(ValueError, match="no_result_above_minimum"):
        evidence(
            verdict=AcoustIDEvidenceVerdict.NO_MATCH,
            selected_acoustid_id=None,
            selected_recording_mbid=None,
            reason=AcoustIDEvidenceReason.LOOKUP_FAILED,
            top_score=None,
            eligible_result_count=0,
            eligible_recording_count=0,
        )
    with pytest.raises(ValueError, match="unavailable reason"):
        evidence(
            verdict=AcoustIDEvidenceVerdict.UNAVAILABLE,
            selected_acoustid_id=None,
            selected_recording_mbid=None,
            reason=AcoustIDEvidenceReason.STALE_TARGET,
            top_score=None,
            eligible_result_count=0,
            eligible_recording_count=0,
        )
    with pytest.raises(ValueError, match="inconsistent"):
        evidence(eligible_result_count=2)


def test_track_evidence_rejects_fabricated_or_contradictory_states() -> None:
    with pytest.raises(ValueError, match="selected identifiers"):
        evidence(selected_acoustid_id=identifier(2))
    with pytest.raises(ValueError, match="counts are inconsistent"):
        evidence(eligible_recording_count=0)
    with pytest.raises(ValueError, match="one eligible recording"):
        evidence(runner_up_score=0.9, margin=0.05, eligible_recording_count=1)
    with pytest.raises(ValueError, match="competing score"):
        evidence(
            verdict=AcoustIDEvidenceVerdict.AMBIGUOUS,
            selected_acoustid_id=None,
            selected_recording_mbid=None,
            reason=AcoustIDEvidenceReason.COMPETING_RECORDINGS,
            top_score=None,
            eligible_result_count=0,
            eligible_recording_count=0,
        )


def test_track_evidence_rejects_impossible_eligible_count_relationships() -> None:
    with pytest.raises(ValueError, match="counts are inconsistent"):
        evidence(eligible_result_count=0, eligible_recording_count=1)
    with pytest.raises(ValueError, match="multiple eligible recordings"):
        evidence(
            result_groups=(group(), AcoustIDResultGroup(identifier(2), 0.9, (identifier(102),))),
            eligible_result_count=2,
            eligible_recording_count=2,
        )


def test_track_evidence_rejects_decisive_group_with_two_top_recordings() -> None:
    top_group = AcoustIDResultGroup(identifier(1), 0.95, (identifier(101), identifier(102)))

    with pytest.raises(ValueError, match="top-scoring result groups"):
        evidence(
            result_groups=(top_group,),
            runner_up_score=0.95,
            margin=0.0,
            eligible_recording_count=2,
        )


@pytest.mark.parametrize("competing_score", [0.95, 0.96])
def test_track_evidence_rejects_other_recording_at_or_above_decisive_top(
    competing_score: float,
) -> None:
    competing = AcoustIDResultGroup(identifier(2), competing_score, (identifier(102),))

    with pytest.raises(ValueError):
        evidence(
            result_groups=(group(), competing),
            runner_up_score=0.9,
            margin=0.95 - 0.9,
            eligible_result_count=2,
            eligible_recording_count=2,
        )


@pytest.mark.parametrize("runner_up_score", [0.8, 0.945])
def test_track_evidence_rejects_runner_up_inconsistent_with_recording_support(
    runner_up_score: float,
) -> None:
    competing = AcoustIDResultGroup(identifier(2), 0.94, (identifier(102),))

    with pytest.raises(ValueError, match="recording support"):
        evidence(
            result_groups=(group(), competing),
            runner_up_score=runner_up_score,
            margin=0.95 - runner_up_score,
            eligible_result_count=2,
            eligible_recording_count=2,
        )


def test_track_evidence_rejects_top_score_inconsistent_with_recording_support() -> None:
    competing = AcoustIDResultGroup(identifier(2), 0.94, (identifier(102),))

    with pytest.raises(ValueError, match="recording support"):
        evidence(
            result_groups=(group(), competing),
            top_score=0.96,
            runner_up_score=0.94,
            margin=0.02,
            eligible_result_count=2,
            eligible_recording_count=2,
        )


def test_track_evidence_rejects_fabricated_margin() -> None:
    competing = AcoustIDResultGroup(identifier(2), 0.94, (identifier(102),))

    with pytest.raises(ValueError, match="margin is inconsistent"):
        evidence(
            result_groups=(group(), competing),
            runner_up_score=0.94,
            margin=0.02,
            eligible_result_count=2,
            eligible_recording_count=2,
        )


def test_one_eligible_recording_allows_lower_support_in_result_groups() -> None:
    below_minimum = AcoustIDResultGroup(identifier(2), 0.5, (identifier(102),))

    value = evidence(result_groups=(group(), below_minimum))

    assert value.top_score == 0.95
    assert value.runner_up_score is None
    assert value.margin is None


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_existing_values_classify_missing_ids(raw: object) -> None:
    values = AcoustIDExistingValues.from_stored(raw, None, None)

    assert values.acoustid_id_state is AcoustIDStoredValueState.MISSING
    assert values.acoustid_id is None


def test_existing_values_canonicalize_valid_id_and_redact_malformed_id() -> None:
    valid = AcoustIDExistingValues.from_stored(identifier(7).upper(), None, None)
    private_id = "malformed-private-id"
    malformed = AcoustIDExistingValues.from_stored(private_id, None, None)

    assert valid.acoustid_id_state is AcoustIDStoredValueState.VALID
    assert valid.acoustid_id == identifier(7)
    assert malformed.acoustid_id_state is AcoustIDStoredValueState.MALFORMED
    assert malformed.acoustid_id is None
    assert private_id not in repr(malformed)


@pytest.mark.parametrize(
    ("raw", "state"),
    [
        (None, AcoustIDStoredValueState.MISSING),
        ("", AcoustIDStoredValueState.MISSING),
        ("   ", AcoustIDStoredValueState.MISSING),
        (" fingerprint", AcoustIDStoredValueState.MALFORMED),
        ("fingerprint ", AcoustIDStoredValueState.MALFORMED),
        (123, AcoustIDStoredValueState.MALFORMED),
    ],
)
def test_existing_values_classify_fingerprint_state(raw: object, state) -> None:
    values = AcoustIDExistingValues.from_stored(None, raw, 10)

    assert values.fingerprint_state is state
    assert not values.is_fingerprint_reusable


def test_existing_fingerprint_uses_shared_exact_length_limit() -> None:
    exact = "x" * _MAX_FINGERPRINT_LENGTH
    valid = AcoustIDExistingValues.from_stored(None, exact, 10)
    oversized = AcoustIDExistingValues.from_stored(None, exact + "x", 10)

    assert valid.fingerprint_state is AcoustIDStoredValueState.VALID
    assert valid.is_fingerprint_reusable
    assert oversized.fingerprint_state is AcoustIDStoredValueState.MALFORMED
    assert exact not in repr(valid)


@pytest.mark.parametrize(
    "duration", [None, True, "10", 0, -1, float("nan"), float("inf"), -float("inf")]
)
def test_existing_duration_must_be_finite_and_positive(duration: object) -> None:
    values = AcoustIDExistingValues.from_stored(None, "synthetic-private-fingerprint", duration)

    assert values.duration_seconds is None
    assert not values.is_fingerprint_reusable


def test_existing_duration_normalizes_to_float_and_id_alone_is_not_material() -> None:
    reusable = AcoustIDExistingValues.from_stored(None, "synthetic-private-fingerprint", 12)
    id_only = AcoustIDExistingValues.from_stored(identifier(1), None, 12)

    assert reusable.duration_seconds == 12.0
    assert reusable.is_fingerprint_reusable
    assert not id_only.is_fingerprint_reusable
    assert not hasattr(id_only, "verdict")


def test_existing_values_reject_inconsistent_direct_construction_without_disclosure() -> None:
    private_fingerprint = "private-fingerprint"
    with pytest.raises(ValueError) as captured:
        AcoustIDExistingValues(
            AcoustIDStoredValueState.MALFORMED,
            identifier(1),
            AcoustIDStoredValueState.MALFORMED,
            private_fingerprint,
            None,
        )
    assert private_fingerprint not in str(captured.value)
    with pytest.raises(ValueError):
        AcoustIDExistingValues(
            AcoustIDStoredValueState.VALID,
            None,
            AcoustIDStoredValueState.MISSING,
            None,
            None,
        )


@pytest.mark.parametrize("duration", [True, "1", 0, -1, float("nan"), float("inf")])
def test_backend_result_rejects_invalid_duration(duration: object) -> None:
    with pytest.raises(ValueError, match="duration"):
        FingerprintBackendResult(duration, "private-fingerprint")  # type: ignore[arg-type]


@pytest.mark.parametrize("fingerprint", [None, 1, "", " "])
def test_backend_result_rejects_invalid_fingerprint_without_disclosure(fingerprint: object) -> None:
    with pytest.raises(ValueError) as captured:
        FingerprintBackendResult(1, fingerprint)  # type: ignore[arg-type]
    assert repr(fingerprint) not in str(captured.value)


def test_backend_result_is_redacted_and_accepts_shared_limit() -> None:
    fingerprint = "z" * _MAX_FINGERPRINT_LENGTH
    result = FingerprintBackendResult(1, fingerprint)

    assert result.duration_seconds == 1.0
    assert fingerprint not in repr(result)
    assert fingerprint not in str(result)
    with pytest.raises(ValueError):
        FingerprintBackendResult(1, fingerprint + "z")


def test_preparation_result_enforces_reason_material_and_origin() -> None:
    existing = AcoustIDFingerprintMaterial(
        "library-item:1", "private-existing", 1, AcoustIDFingerprintOrigin.EXISTING
    )
    generated = AcoustIDFingerprintMaterial(
        "library-item:1",
        "private-generated",
        1,
        AcoustIDFingerprintOrigin.GENERATED,
        snapshot(),
    )

    assert FingerprintPreparationResult(
        "library-item:1", existing, AcoustIDEvidenceReason.FINGERPRINT_REUSED
    ).material is existing
    assert FingerprintPreparationResult(
        "library-item:1", generated, AcoustIDEvidenceReason.FINGERPRINT_GENERATED
    ).material is generated
    with pytest.raises(ValueError):
        FingerprintPreparationResult(
            "library-item:1", None, AcoustIDEvidenceReason.FINGERPRINT_REUSED
        )
    with pytest.raises(ValueError):
        FingerprintPreparationResult(
            "library-item:1", existing, AcoustIDEvidenceReason.FINGERPRINT_GENERATED
        )
    with pytest.raises(ValueError):
        FingerprintPreparationResult(
            "library-item:2", existing, AcoustIDEvidenceReason.FINGERPRINT_REUSED
        )
    with pytest.raises(ValueError):
        FingerprintPreparationResult(
            "library-item:1", existing, AcoustIDEvidenceReason.FINGERPRINT_FAILED
        )
    with pytest.raises(ValueError):
        FingerprintPreparationResult(
            "library-item:1", None, AcoustIDEvidenceReason.LOOKUP_FAILED
        )


def test_new_string_enums_have_frozen_serialized_values() -> None:
    assert AcoustIDLibraryTargetKind.ALBUM.value == "album"
    assert AcoustIDLibraryTargetKind.SINGLETON.value == "singleton"
    assert [state.value for state in AcoustIDStoredValueState] == [
        "missing",
        "valid",
        "malformed",
    ]
