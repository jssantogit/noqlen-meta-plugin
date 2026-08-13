from beetsplug.noqlenmeta.domain import ExternalIdentifier
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import (
    EntityKind,
    IdentifierCollection,
    PartialDate,
)
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.recording_identity_resolution import resolve_recording_identity
from beetsplug.noqlenmeta.resolver import ResolutionAction
from beetsplug.noqlenmeta.work_identity import WorkReference

RECORDING = "12345678-1234-5678-9234-567812345678"
WORK_1 = "22345678-1234-5678-9234-567812345678"
WORK_2 = "32345678-1234-5678-9234-567812345678"


def identifiers(field: str, namespace: str, *values: str) -> MetadataEvidence:
    entity = EntityKind.RECORDING if field == "isrcs" else EntityKind.WORK
    entity_id = RECORDING if entity is EntityKind.RECORDING else WORK_1
    return MetadataEvidence(
        field=field,
        value=IdentifierCollection(tuple(ExternalIdentifier(namespace, value) for value in values)),
        subject=SubjectRef(
            entity,
            (ExternalIdentifier(f"musicbrainz.{entity.value}", entity_id),),
        ),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.TRACK,
        source_id=entity_id,
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=0.99,
    )


def work(mbid: str, title: str = "Synthetic Work") -> WorkReference:
    return WorkReference(mbid, title, "performance", None)


def work_evidence(*values: WorkReference) -> MetadataEvidence:
    return MetadataEvidence(
        field="works",
        value=values,
        subject=SubjectRef(
            EntityKind.RECORDING,
            (ExternalIdentifier("musicbrainz.recording", RECORDING),),
        ),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.TRACK,
        source_id=RECORDING,
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=0.99,
    )


def recording_date(value: PartialDate) -> MetadataEvidence:
    return MetadataEvidence(
        field="recording_date",
        value=value,
        subject=SubjectRef(
            EntityKind.RECORDING,
            (ExternalIdentifier("musicbrainz.recording", RECORDING),),
        ),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.TRACK,
        source_id=RECORDING,
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=0.99,
    )


def decision(current: object | None, *items: MetadataEvidence):
    values = {} if current is None else {items[0].field: current}
    return resolve_recording_identity(values, items)[0]


def test_identifier_sets_fill_missing_and_safe_superset() -> None:
    incoming = identifiers("isrcs", "isrc", "USAAA0100001", "USAAA0100002")

    assert decision(None, incoming).action is ResolutionAction.PROPOSE
    current = IdentifierCollection((ExternalIdentifier("isrc", "USAAA0100001"),))
    resolved = decision(current, incoming)
    assert resolved.action is ResolutionAction.PROPOSE
    assert resolved.value == incoming.value


def test_provider_subset_never_deletes_existing_identifier() -> None:
    incoming = identifiers("isrcs", "isrc", "USAAA0100001")
    current = IdentifierCollection(
        (
            ExternalIdentifier("isrc", "USAAA0100001"),
            ExternalIdentifier("isrc", "USAAA0100002"),
        )
    )

    resolved = decision(current, incoming)

    assert resolved.action is ResolutionAction.KEEP
    assert resolved.value == current


def test_partial_overlap_and_disjoint_identifiers_review() -> None:
    current = IdentifierCollection(
        (
            ExternalIdentifier("isrc", "USAAA0100001"),
            ExternalIdentifier("isrc", "USAAA0100002"),
        )
    )

    assert decision(
        current,
        identifiers("isrcs", "isrc", "USAAA0100002", "USAAA0100003"),
    ).action is ResolutionAction.REVIEW
    assert decision(
        current,
        identifiers("isrcs", "isrc", "USAAA0100003"),
    ).action is ResolutionAction.REVIEW


def test_iswcs_from_multiple_work_scopes_are_aggregated() -> None:
    first = identifiers("iswcs", "iswc", "T-123.456.789-0")
    second = identifiers("iswcs", "iswc", "T-123.456.780-1")
    second = MetadataEvidence(
        field=second.field,
        value=second.value,
        subject=SubjectRef(
            EntityKind.WORK,
            (ExternalIdentifier("musicbrainz.work", WORK_2),),
        ),
        provider=second.provider,
        acquisition_scope=second.acquisition_scope,
        source_id=WORK_2,
        provenance=second.provenance,
        confidence=second.confidence,
    )

    resolved = decision(None, second, first)

    assert resolved.action is ResolutionAction.PROPOSE
    assert {value.value for value in resolved.value.values} == {
        "T-123.456.780-1",
        "T-123.456.789-0",
    }
    assert resolved.contributing_evidence == (first, second)


def test_same_work_mbid_with_different_title_keeps_existing_display_title() -> None:
    current = (work(WORK_1, "Existing Title"),)

    resolved = decision(current, work_evidence(work(WORK_1, "Provider Title")))

    assert resolved.action is ResolutionAction.KEEP
    assert resolved.value == current


def test_new_work_superset_enriches_but_conflicting_work_reviews() -> None:
    current = (work(WORK_1),)
    enriched = decision(current, work_evidence(work(WORK_1), work(WORK_2)))
    conflict = decision(current, work_evidence(work(WORK_2)))

    assert enriched.action is ResolutionAction.PROPOSE
    assert conflict.action is ResolutionAction.REVIEW


def test_multiple_different_recording_dates_review() -> None:
    resolved = resolve_recording_identity(
        {},
        (recording_date(PartialDate(2020, 1, 2)), recording_date(PartialDate(2020, 1, 3))),
    )[0]

    assert resolved.action is ResolutionAction.REVIEW


def test_no_evidence_never_proposes_deletion() -> None:
    current = IdentifierCollection((ExternalIdentifier("isrc", "USAAA0100001"),))

    assert resolve_recording_identity({"isrcs": current}, ()) == ()
