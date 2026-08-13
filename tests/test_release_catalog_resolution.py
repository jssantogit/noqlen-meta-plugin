from itertools import permutations

from beetsplug.noqlenmeta.authority import (
    AUTHORITY_MATRIX,
    AuthorityMatrix,
    AuthorityRole,
    AuthorityRule,
)
from beetsplug.noqlenmeta.domain import ExternalIdentifier
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind, PartialDate
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.release_catalog import (
    ReleaseSecondaryType,
    ReleaseStatus,
    ReleaseType,
)
from beetsplug.noqlenmeta.release_catalog_resolution import resolve_release_catalog
from beetsplug.noqlenmeta.resolver import ResolutionAction


def evidence(
    field: str,
    value: object,
    provider: str,
    *,
    entity: EntityKind = EntityKind.RELEASE,
    confidence: float = 0.9,
) -> MetadataEvidence:
    return MetadataEvidence(
        field=field,
        value=value,  # type: ignore[arg-type]
        subject=SubjectRef(
            entity,
            (ExternalIdentifier(f"{provider}.{entity.value}", "entity-1"),),
        ),
        provider=provider,
        acquisition_scope=ProviderScope.RELEASE,
        source_id="entity-1",
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=confidence,
    )


def decision_for(items: list[MetadataEvidence], current: object | None = None):
    decisions = resolve_release_catalog({} if current is None else {items[0].field: current}, items)
    assert len(decisions) == 1
    return decisions[0]


def test_primary_can_create_value() -> None:
    primary = evidence("release_status", ReleaseStatus.OFFICIAL, "musicbrainz")

    decision = decision_for([primary])

    assert decision.action is ResolutionAction.PROPOSE
    assert decision.selected is primary


def test_secondary_can_create_when_primary_is_absent() -> None:
    secondary = evidence("date", PartialDate(2020, 5), "discogs")

    assert decision_for([secondary]).selected is secondary


def test_fallback_participates_only_without_primary_or_secondary() -> None:
    fallback = evidence("date", PartialDate(2020, 5, 17), "itunes")
    secondary = evidence("date", PartialDate(2020, 5), "discogs")

    decision = decision_for([fallback, secondary])

    assert decision.selected is secondary
    assert fallback in decision.alternatives


def test_corroboration_only_cannot_create_value() -> None:
    matrix = AuthorityMatrix(
        (
            AuthorityRule(
                "date",
                EntityKind.RELEASE,
                ProviderScope.RELEASE,
                "catalog",
                AuthorityRole.CORROBORATION_ONLY,
            ),
        )
    )
    item = evidence("date", PartialDate(2020), "catalog")

    decision = resolve_release_catalog({}, [item], authority=matrix)[0]

    assert decision.action is ResolutionAction.SKIP
    assert decision.selected is None


def test_compatible_primary_and_secondary_date_choose_greater_precision() -> None:
    primary = evidence("date", PartialDate(2020), "musicbrainz")
    secondary = evidence("date", PartialDate(2020, 5, 17), "discogs")

    decision = decision_for([primary, secondary])

    assert decision.action is ResolutionAction.PROPOSE
    assert decision.selected is secondary
    assert decision.value == PartialDate(2020, 5, 17)


def test_material_primary_secondary_conflict_is_review() -> None:
    primary = evidence("date", PartialDate(2020, 4), "musicbrainz")
    secondary = evidence("date", PartialDate(2020, 5), "discogs")

    decision = decision_for([primary, secondary])

    assert decision.action is ResolutionAction.REVIEW
    assert decision.selected is None


def test_existing_higher_precision_compatible_date_is_preserved() -> None:
    incoming = evidence("date", PartialDate(2020), "musicbrainz")

    decision = decision_for([incoming], PartialDate(2020, 5, 17))

    assert decision.action is ResolutionAction.KEEP
    assert decision.value == PartialDate(2020, 5, 17)


def test_incoming_higher_precision_date_proposes_enrichment() -> None:
    incoming = evidence("date", PartialDate(2020, 5, 17), "musicbrainz")

    decision = decision_for([incoming], PartialDate(2020))

    assert decision.action is ResolutionAction.PROPOSE
    assert decision.value == PartialDate(2020, 5, 17)


def test_existing_incompatible_date_is_review() -> None:
    incoming = evidence("date", PartialDate(2020), "musicbrainz")

    assert decision_for([incoming], PartialDate(2021)).action is ResolutionAction.REVIEW


def test_no_evidence_creates_no_deletion_decision() -> None:
    assert resolve_release_catalog({"date": PartialDate(2020)}, []) == ()


def test_exclusive_non_date_disagreement_is_review() -> None:
    first = evidence("edition", "Limited Edition", "discogs")
    second = evidence("edition", "Deluxe Edition", "discogs")

    assert decision_for([first, second]).action is ResolutionAction.REVIEW


def test_secondary_types_union_is_ordered_deduplicated_and_scope_safe() -> None:
    first = evidence(
        "release_secondary_types",
        (ReleaseSecondaryType.LIVE, ReleaseSecondaryType.COMPILATION),
        "musicbrainz",
        entity=EntityKind.RELEASE_GROUP,
    )
    second = evidence(
        "release_secondary_types",
        (ReleaseSecondaryType.COMPILATION, ReleaseSecondaryType.REMIX),
        "catalog",
        entity=EntityKind.RELEASE_GROUP,
    )
    matrix = AuthorityMatrix(
        (
            AuthorityRule(
                "release_secondary_types",
                EntityKind.RELEASE_GROUP,
                ProviderScope.RELEASE,
                "musicbrainz",
                AuthorityRole.PRIMARY,
            ),
            AuthorityRule(
                "release_secondary_types",
                EntityKind.RELEASE_GROUP,
                ProviderScope.RELEASE,
                "catalog",
                AuthorityRole.SECONDARY,
            ),
        )
    )

    decision = resolve_release_catalog({}, [second, first], authority=matrix)[0]

    assert decision.value == (
        ReleaseSecondaryType.LIVE,
        ReleaseSecondaryType.COMPILATION,
        ReleaseSecondaryType.REMIX,
    )


def test_resolution_is_deterministic_regardless_of_evidence_order() -> None:
    items = [
        evidence("date", PartialDate(2020), "musicbrainz"),
        evidence("date", PartialDate(2020, 5), "discogs"),
        evidence("date", PartialDate(2020, 5, 17), "itunes"),
    ]

    results = {
        resolve_release_catalog({}, list(order), authority=AUTHORITY_MATRIX)
        for order in permutations(items)
    }

    assert len(results) == 1


def test_provider_local_confidence_filters_only_that_evidence() -> None:
    weak_primary = evidence(
        "release_type",
        ReleaseType.ALBUM,
        "musicbrainz",
        entity=EntityKind.RELEASE_GROUP,
        confidence=0.79,
    )

    decision = decision_for([weak_primary])

    assert decision.action is ResolutionAction.SKIP
