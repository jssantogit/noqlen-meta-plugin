"""V3 recording-level instrumental semantics: explicit evidence, no guessing."""

import pytest

from beetsplug.noqlenmeta.changeplan import build_change_plan
from beetsplug.noqlenmeta.domain import ExternalIdentifier
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.recording_semantic_resolution import (
    resolve_recording_semantics,
)
from beetsplug.noqlenmeta.resolver import ResolutionAction

RECORDING = "11111111-1111-4111-8111-111111111111"


def evidence(
    value: object = True,
    *,
    provider: str = "musicbrainz",
    entity: EntityKind = EntityKind.RECORDING,
) -> MetadataEvidence:
    return MetadataEvidence(
        "instrumental",
        value,  # type: ignore[arg-type]
        SubjectRef(entity, (ExternalIdentifier("musicbrainz.recording", RECORDING),)),
        provider,
        ProviderScope.TRACK,
        RECORDING,
        AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=0.99,
    )


def advisory(value: object = "explicit") -> MetadataEvidence:
    return MetadataEvidence(
        "explicitness",
        value,  # type: ignore[arg-type]
        SubjectRef(
            EntityKind.RECORDING,
            (ExternalIdentifier("itunes.track", "123456"),),
        ),
        "itunes",
        ProviderScope.TRACK,
        "123456",
        AcquisitionProvenance(AcquisitionMethod.STRUCTURALLY_VALIDATED),
        confidence=0.95,
    )


@pytest.mark.parametrize("value", ["explicit", "clean"])
def test_itunes_advisory_populates_missing_and_keeps_agreement(value: str) -> None:
    missing = resolve_recording_semantics({}, (advisory(value),))[0]
    assert missing.action is ResolutionAction.PROPOSE
    assert build_change_plan((missing,)).changes[0].after == value
    agreeing = resolve_recording_semantics(
        {"explicitness": value}, (advisory(value),)
    )[0]
    assert agreeing.action is ResolutionAction.KEEP


def test_explicitness_never_replaces_existing_conflicting_advisory() -> None:
    decision = resolve_recording_semantics(
        {"explicitness": "clean"}, (advisory("explicit"),)
    )[0]
    assert decision.action is ResolutionAction.REVIEW
    assert decision.resolved_value == "clean"


def test_materially_disagreeing_itunes_track_evidence_requires_review() -> None:
    decision = resolve_recording_semantics(
        {}, (advisory("clean"), advisory("explicit"))
    )[0]
    assert decision.action is ResolutionAction.REVIEW
    assert decision.resolved_value is None


@pytest.mark.parametrize("value", ["notExplicit", "unknown", False, True, ""])
def test_invalid_explicitness_state_is_rejected(value: object) -> None:
    with pytest.raises(ValueError, match="explicit or clean"):
        resolve_recording_semantics({}, (advisory(value),))


def test_untrusted_provider_cannot_assert_clean_or_explicit() -> None:
    original = advisory("clean")
    from dataclasses import replace

    assert resolve_recording_semantics(
        {}, (replace(original, provider="not-itunes"),)
    ) == ()


def test_explicit_instrumental_true_is_proposed_and_preserves_unknown() -> None:
    decision = resolve_recording_semantics({}, (evidence(),))[0]
    assert decision.action is ResolutionAction.PROPOSE
    assert decision.resolved_value is True
    assert build_change_plan((decision,)).changes[0].after is True


def test_equal_true_is_kept_but_conflicting_explicit_false_needs_review() -> None:
    assert resolve_recording_semantics(
        {"instrumental": True}, (evidence(),)
    )[0].action is ResolutionAction.KEEP

    contradictory = resolve_recording_semantics(
        {"instrumental": False}, (evidence(),)
    )[0]
    assert contradictory.action is ResolutionAction.REVIEW
    assert contradictory.resolved_value is False


def test_musicbrainz_primary_outranks_secondary_lrclib_evidence() -> None:
    selected = resolve_recording_semantics(
        {}, (evidence(provider="lrclib"), evidence(provider="musicbrainz"))
    )[0]
    assert selected.action is ResolutionAction.PROPOSE
    assert selected.selected_source.provider == "musicbrainz"
    assert len(selected.contributing_evidence) == 2


def test_ineligible_source_and_false_by_absence_do_not_create_assertions() -> None:
    assert resolve_recording_semantics(
        {}, (evidence(provider="unsupported"),)
    ) == ()
    with pytest.raises(ValueError, match="explicit true"):
        resolve_recording_semantics({}, (evidence(value=False),))
