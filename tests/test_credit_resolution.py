from beetsplug.noqlenmeta.credit_resolution import resolve_credits
from beetsplug.noqlenmeta.credits import (
    ArtistCredit,
    ArtistCreditNode,
    CreditParty,
    CreditReference,
    CreditRole,
)
from beetsplug.noqlenmeta.domain import ExternalIdentifier
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.resolver import ResolutionAction

RECORDING_ID = "11111111-1111-4111-8111-111111111111"
ARTIST_ID = "22222222-2222-4222-8222-222222222222"
OTHER_ARTIST_ID = "33333333-3333-4333-8333-333333333333"


def evidence(
    field: str,
    value: object,
    *,
    provider: str = "musicbrainz",
    entity: EntityKind = EntityKind.RECORDING,
    scope: ProviderScope = ProviderScope.TRACK,
) -> MetadataEvidence:
    return MetadataEvidence(
        field,
        value,  # type: ignore[arg-type]
        SubjectRef(entity, (ExternalIdentifier(f"test.{entity.value}", RECORDING_ID),)),
        provider,
        scope,
        f"{provider}-source",
        AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=0.99,
    )


def credit(
    name: str,
    role: CreditRole,
    *,
    mbid: str | None = ARTIST_ID,
    credited_as: str | None = None,
    instrument: str | None = None,
    scope: EntityKind = EntityKind.RECORDING,
    source_entity_id: str = RECORDING_ID,
) -> CreditReference:
    return CreditReference(
        CreditParty(name, mbid, credited_as),
        role,
        scope,
        instrument=instrument,
        source_entity_id=source_entity_id,
    )


def test_missing_credit_is_proposed_and_equal_credit_is_kept() -> None:
    producer = credit("Producer", CreditRole.PRODUCER)
    item = evidence("producers", (producer,))

    proposed = resolve_credits({}, (item,))[0]
    kept = resolve_credits({"producers": (producer,)}, (item,))[0]

    assert proposed.action is ResolutionAction.PROPOSE
    assert proposed.value == (producer,)
    assert kept.action is ResolutionAction.KEEP


def test_existing_superset_and_provider_subset_never_delete() -> None:
    first = credit("First", CreditRole.PRODUCER)
    second = credit("Second", CreditRole.PRODUCER, mbid=OTHER_ARTIST_ID)

    decision = resolve_credits(
        {"producers": (first, second)},
        (evidence("producers", (first,)),),
    )[0]

    assert decision.action is ResolutionAction.KEEP
    assert decision.value == (first, second)


def test_partial_overlap_unions_non_conflicting_credits() -> None:
    first = credit("First", CreditRole.PRODUCER)
    second = credit("Second", CreditRole.PRODUCER, mbid=OTHER_ARTIST_ID)

    decision = resolve_credits(
        {"producers": (first,)},
        (evidence("producers", (second,)),),
    )[0]

    assert decision.action is ResolutionAction.PROPOSE
    assert {value.party.name for value in decision.value} == {"First", "Second"}


def test_same_performer_different_instruments_are_preserved() -> None:
    guitar = credit("Performer", CreditRole.PERFORMER, instrument="guitar")
    vocals = credit("Performer", CreditRole.PERFORMER, instrument="vocals")

    decision = resolve_credits(
        {}, (evidence("performers", (vocals, guitar)),)
    )[0]

    assert [value.instrument for value in decision.value] == ["guitar", "vocals"]


def test_same_name_different_mbids_are_not_merged() -> None:
    first = credit("Same", CreditRole.PRODUCER)
    second = credit("Same", CreditRole.PRODUCER, mbid=OTHER_ARTIST_ID)

    decision = resolve_credits({}, (evidence("producers", (first, second)),))[0]

    assert len(decision.value) == 2


def test_same_mbid_credited_as_variants_corroborate_one_identity() -> None:
    canonical = credit("Canonical", CreditRole.PRODUCER, credited_as="Alias One")
    variant = credit("Canonical", CreditRole.PRODUCER, credited_as="Alias Two")

    decision = resolve_credits(
        {},
        (
            evidence("producers", (canonical,)),
            evidence("producers", (variant,)),
        ),
    )[0]

    assert len(decision.value) == 1
    assert decision.value[0].party.credited_as_variants == ("Alias One", "Alias Two")
    assert len(decision.contributors) == 2


def test_secondary_discogs_can_supply_or_corroborate_release_credit() -> None:
    producer = credit(
        "Producer",
        CreditRole.PRODUCER,
        mbid=None,
        scope=EntityKind.RELEASE,
        source_entity_id="123",
    )
    item = evidence(
        "producers",
        (producer,),
        provider="discogs",
        entity=EntityKind.RELEASE,
        scope=ProviderScope.RELEASE,
    )

    decision = resolve_credits({}, (item,))[0]

    assert decision.action is ResolutionAction.PROPOSE


def test_artist_credit_disagreement_requires_review() -> None:
    current = ArtistCredit(
        EntityKind.RECORDING,
        (ArtistCreditNode(ARTIST_ID, "Artist", "Artist", "", 0),),
        RECORDING_ID,
    )
    incoming = ArtistCredit(
        EntityKind.RECORDING,
        (ArtistCreditNode(ARTIST_ID, "Artist", "Alias", "", 0),),
        RECORDING_ID,
    )

    decision = resolve_credits(
        {"structured_artist_credits": current},
        (evidence("structured_artist_credits", incoming),),
    )[0]

    assert decision.action is ResolutionAction.REVIEW
    assert decision.value == current


def test_provider_omission_produces_no_decision() -> None:
    producer = credit("Producer", CreditRole.PRODUCER)

    assert resolve_credits({"producers": (producer,)}, ()) == ()
