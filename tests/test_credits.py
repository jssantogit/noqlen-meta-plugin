import pytest

from beetsplug.noqlenmeta.credits import (
    ArtistCredit,
    ArtistCreditNode,
    CreditParty,
    CreditReference,
    CreditRole,
    canonical_credit_references,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind

ARTIST_ONE = "11111111-1111-4111-8111-111111111111"
ARTIST_TWO = "22222222-2222-4222-8222-222222222222"
RELATION = "33333333-3333-4333-8333-333333333333"


def test_credit_party_preserves_canonical_and_credited_names() -> None:
    party = CreditParty("Canonical Artist", ARTIST_ONE, "Credited Artist")

    assert party.name == "Canonical Artist"
    assert party.mbid == ARTIST_ONE
    assert party.credited_as == "Credited Artist"
    assert CreditParty("Canonical Artist", credited_as="  ").credited_as is None


@pytest.mark.parametrize("name", ["", "  ", None])
def test_credit_party_requires_a_name(name: object) -> None:
    with pytest.raises(ValueError, match="name"):
        CreditParty(name)  # type: ignore[arg-type]


def test_credit_party_rejects_non_uuid_mbid_without_name_inference() -> None:
    with pytest.raises(ValueError, match="MBID"):
        CreditParty("Canonical Artist", "Canonical Artist")


@pytest.mark.parametrize(
    ("role", "scope"),
    [
        (CreditRole.COMPOSER, EntityKind.WORK),
        (CreditRole.COMPOSER, EntityKind.RECORDING),
        (CreditRole.LYRICIST, EntityKind.WORK),
        (CreditRole.ARRANGER, EntityKind.RECORDING),
        (CreditRole.PRODUCER, EntityKind.RELEASE),
        (CreditRole.CONDUCTOR, EntityKind.RECORDING),
        (CreditRole.PERFORMER, EntityKind.RELEASE),
        (CreditRole.FEATURED_ARTIST, EntityKind.RECORDING),
        (CreditRole.GUEST_ARTIST, EntityKind.RELEASE),
    ],
)
def test_credit_reference_accepts_only_semantic_role_scopes(
    role: CreditRole, scope: EntityKind
) -> None:
    assert CreditReference(CreditParty("Artist"), role, scope).scope is scope


def test_credit_reference_rejects_invalid_scope_and_non_performer_instrument() -> None:
    with pytest.raises(ValueError, match="scope"):
        CreditReference(CreditParty("Artist"), CreditRole.COMPOSER, EntityKind.RELEASE)
    with pytest.raises(ValueError, match="instrument"):
        CreditReference(
            CreditParty("Artist"),
            CreditRole.PRODUCER,
            EntityKind.RECORDING,
            instrument="electric guitar",
        )


def test_credit_reference_preserves_relationship_structure() -> None:
    reference = CreditReference(
        CreditParty("Artist", ARTIST_ONE, "Alias"),
        CreditRole.PERFORMER,
        EntityKind.RECORDING,
        instrument="electric guitar",
        relation_type="instrument",
        relation_type_id=RELATION,
        source_entity_id="recording-source",
        attributes=("solo", "guest"),
        direction="backward",
        ordering_key=2,
    )

    assert reference.instrument == "electric guitar"
    assert reference.relation_type_id == RELATION
    assert reference.attributes == ("solo", "guest")
    assert reference.direction == "backward"
    assert reference.ordering_key == 2


def test_credit_reference_type_id_fails_closed() -> None:
    with pytest.raises(ValueError, match="type ID"):
        CreditReference(
            CreditParty("Artist"),
            CreditRole.PRODUCER,
            EntityKind.RECORDING,
            relation_type_id="invalid",
        )


def test_structural_dedup_keeps_instruments_and_distinct_mbids() -> None:
    guitar = CreditReference(
        CreditParty("Same Name", ARTIST_ONE),
        CreditRole.PERFORMER,
        EntityKind.RECORDING,
        instrument="guitar",
    )
    vocals = CreditReference(
        CreditParty("Same Name", ARTIST_ONE, "Credited Name"),
        CreditRole.PERFORMER,
        EntityKind.RECORDING,
        instrument="vocals",
    )
    other = CreditReference(
        CreditParty("Same Name", ARTIST_TWO),
        CreditRole.PERFORMER,
        EntityKind.RECORDING,
        instrument="guitar",
    )

    assert canonical_credit_references((vocals, guitar, guitar, other)) == (
        guitar,
        vocals,
        other,
    )


def test_artist_credit_preserves_exact_order_names_and_join_phrases() -> None:
    credit = ArtistCredit(
        EntityKind.RECORDING,
        (
            ArtistCreditNode(ARTIST_ONE, "Artist A", "Alias A", " feat. ", 0),
            ArtistCreditNode(ARTIST_TWO, "Artist B", "Artist B", "", 1),
        ),
        source_entity_id="recording-source",
    )

    assert credit.nodes[0].credited_name == "Alias A"
    assert credit.nodes[0].join_phrase == " feat. "
    assert tuple(node.position for node in credit.nodes) == (0, 1)


@pytest.mark.parametrize("scope", [EntityKind.WORK, EntityKind.ARTIST])
def test_artist_credit_rejects_non_release_recording_scope(scope: EntityKind) -> None:
    with pytest.raises(ValueError, match="scope"):
        ArtistCredit(scope, (ArtistCreditNode(ARTIST_ONE, "Artist", "Artist", "", 0),))


def test_artist_credit_requires_contiguous_positions() -> None:
    with pytest.raises(ValueError, match="positions"):
        ArtistCredit(
            EntityKind.RELEASE,
            (ArtistCreditNode(ARTIST_ONE, "Artist", "Artist", "", 1),),
        )
