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
