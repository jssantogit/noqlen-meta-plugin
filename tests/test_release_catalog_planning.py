from beetsplug.noqlenmeta.domain import ExternalIdentifier
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind, PartialDate
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.release_catalog_planning import plan_release_catalog
from beetsplug.noqlenmeta.resolver import ResolutionAction


def test_internal_pipeline_resolves_plans_and_maps_consistent_date_projection() -> None:
    primary = MetadataEvidence(
        field="date",
        value=PartialDate(2020),
        subject=SubjectRef(
            EntityKind.RELEASE,
            (ExternalIdentifier("musicbrainz.release", "release-1"),),
        ),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.RELEASE,
        source_id="release-1",
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=0.99,
    )
    secondary = MetadataEvidence(
        field="date",
        value=PartialDate(2020, 5, 17),
        subject=SubjectRef(
            EntityKind.RELEASE,
            (ExternalIdentifier("discogs.release", "42"),),
        ),
        provider="discogs",
        acquisition_scope=ProviderScope.RELEASE,
        source_id="42",
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=0.98,
    )

    result = plan_release_catalog({"date": PartialDate(2020)}, [secondary, primary])

    assert result.decisions[0].action is ResolutionAction.PROPOSE
    assert result.change_plan.changes[0].after == PartialDate(2020, 5, 17)
    assert {target.target_field: target.value for target in result.target_plan.changes} == {
        "year": 2020,
        "month": 5,
        "day": 17,
    }
