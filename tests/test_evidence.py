from dataclasses import FrozenInstanceError

import pytest

from beetsplug.noqlenmeta.domain import ExternalIdentifier, MetadataCandidate
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind, IdentifierCollection
from beetsplug.noqlenmeta.providers.specs import ProviderScope


def subject(entity: EntityKind, namespace: str) -> SubjectRef:
    return SubjectRef(entity, (ExternalIdentifier(namespace, "entity-1"),))


def test_release_evidence_cannot_claim_a_recording_field() -> None:
    with pytest.raises(ValueError, match="asserted entity"):
        MetadataEvidence(
            field="isrcs",
            value=IdentifierCollection((ExternalIdentifier("isrc", "USAAA2600001"),)),
            subject=subject(EntityKind.RELEASE, "musicbrainz.release"),
            provider="musicbrainz",
            acquisition_scope=ProviderScope.RELEASE,
            source_id="release-1",
            provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
            confidence=0.99,
        )


def test_work_evidence_preserves_work_scope_after_recording_traversal() -> None:
    work = subject(EntityKind.WORK, "musicbrainz.work")
    evidence = MetadataEvidence(
        field="iswcs",
        value=IdentifierCollection((ExternalIdentifier("iswc", "T-000.000.001-0"),)),
        subject=work,
        provider="musicbrainz",
        acquisition_scope=ProviderScope.TRACK,
        source_id="work-1",
        provenance=AcquisitionProvenance(
            AcquisitionMethod.SUPPORTING_TRAVERSAL,
            supporting_entity=EntityKind.RECORDING,
        ),
        confidence=0.99,
    )

    assert evidence.subject is work
    assert evidence.subject.entity is EntityKind.WORK
    assert evidence.acquisition_scope is ProviderScope.TRACK
    assert evidence.provenance.supporting_entity is EntityKind.RECORDING


def test_acquisition_scope_can_differ_from_asserted_entity() -> None:
    evidence = MetadataEvidence(
        field="original_date",
        value="2020",
        subject=subject(EntityKind.RELEASE_GROUP, "musicbrainz.release_group"),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.RELEASE,
        source_id="release-group-1",
        provenance=AcquisitionProvenance(AcquisitionMethod.STRUCTURALLY_VALIDATED),
    )

    assert evidence.subject.entity is EntityKind.RELEASE_GROUP
    assert evidence.acquisition_scope is ProviderScope.RELEASE


@pytest.mark.parametrize("confidence", [None, 0.0, 0.87, 1.0])
def test_confidence_remains_optional_and_provider_local(confidence: float | None) -> None:
    evidence = MetadataEvidence(
        field="edition",
        value="Deluxe Edition",
        subject=subject(EntityKind.RELEASE, "discogs.release"),
        provider="discogs",
        acquisition_scope=ProviderScope.RELEASE,
        source_id="42",
        provenance=AcquisitionProvenance(AcquisitionMethod.SEARCHED_CANDIDATE),
        confidence=confidence,
    )

    assert evidence.confidence == confidence


def test_provenance_is_not_part_of_the_canonical_value() -> None:
    evidence = MetadataEvidence(
        field="edition",
        value="Limited Edition",
        subject=subject(EntityKind.RELEASE, "discogs.release"),
        provider="discogs",
        acquisition_scope=ProviderScope.RELEASE,
        source_id="42",
        source_url="https://discogs.invalid/releases/42",
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=0.98,
    )

    assert evidence.value == "Limited Edition"
    assert evidence.provenance not in (evidence.value,)
    with pytest.raises(FrozenInstanceError):
        evidence.provider = "changed"  # type: ignore[misc]


def test_evidence_rejects_arbitrary_canonical_values() -> None:
    with pytest.raises(TypeError, match="canonical value"):
        MetadataEvidence(
            field="edition",
            value={"name": "Deluxe"},  # type: ignore[arg-type]
            subject=subject(EntityKind.RELEASE, "discogs.release"),
            provider="discogs",
            acquisition_scope=ProviderScope.RELEASE,
            source_id="42",
            provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        )


def test_subject_requires_typed_identity_and_deduplicates() -> None:
    identifier = ExternalIdentifier("musicbrainz.recording", "recording-1")
    with pytest.raises(ValueError, match="at least one"):
        SubjectRef(EntityKind.RECORDING, ())
    with pytest.raises(ValueError, match="unique"):
        SubjectRef(EntityKind.RECORDING, (identifier, identifier))


def test_all_acquisition_provenance_kinds_are_explicit() -> None:
    assert set(AcquisitionMethod) == {
        AcquisitionMethod.EXACT_LOOKUP,
        AcquisitionMethod.STRUCTURALLY_VALIDATED,
        AcquisitionMethod.SEARCHED_CANDIDATE,
        AcquisitionMethod.SUPPORTING_TRAVERSAL,
    }


def test_v2_metadata_candidate_contract_remains_unchanged() -> None:
    candidate = MetadataCandidate("year", 2026, "musicbrainz", 0.99, "release-1")

    assert candidate.field == "year"
    assert candidate.value == 2026
    assert candidate.confidence == 0.99
