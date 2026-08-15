from pathlib import Path

import pytest
from beets.library import Album, Item, Library

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.changeplan import PlannedChange
from beetsplug.noqlenmeta.credit_state import apply_credit_state, read_credit_state
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

RECORDING_ID = "11111111-1111-4111-8111-111111111111"
ARTIST_ID = "22222222-2222-4222-8222-222222222222"
RELEASE_ID = "33333333-3333-4333-8333-333333333333"


@pytest.fixture
def library_item(tmp_path: Path) -> tuple[Library, Item]:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(path=b"synthetic.flac", artist="Artist", title="Track")
    library.add(item)
    return library, item


def change(field: str, value: object) -> PlannedChange:
    evidence = MetadataEvidence(
        field,
        value,  # type: ignore[arg-type]
        SubjectRef(
            EntityKind.RECORDING,
            (ExternalIdentifier("musicbrainz.recording", RECORDING_ID),),
        ),
        "musicbrainz",
        ProviderScope.TRACK,
        RECORDING_ID,
        AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
        confidence=0.99,
    )
    return PlannedChange(field, None, value, evidence, "synthetic", (evidence,))  # type: ignore[arg-type]


def test_v2_library_read_does_not_create_credit_tables(library_item) -> None:
    library, item = library_item

    assert read_credit_state(library, "item", item.id) == {}
    with library.transaction() as tx:
        rows = tx.query(
            "SELECT name FROM sqlite_master WHERE name LIKE 'noqlenmeta_credit%'"
        )
    assert rows == []


def test_structured_reference_round_trips_without_flat_encoding(library_item) -> None:
    library, item = library_item
    reference = CreditReference(
        CreditParty("Canonical", ARTIST_ID, "Alias", ("Alias", "Second Alias")),
        CreditRole.PERFORMER,
        EntityKind.RECORDING,
        instrument="electric guitar",
        relation_type="instrument",
        relation_type_id="59054b12-01ac-43ee-a618-285fd397e461",
        source_entity_id=RECORDING_ID,
        attributes=("guest", "solo"),
        direction="backward",
        ordering_key=2,
    )

    assert apply_credit_state(library, "item", item.id, (change("performers", (reference,)),)) == 1

    assert read_credit_state(library, "item", item.id) == {"performers": (reference,)}
    assert apply_credit_state(library, "item", item.id, (change("performers", (reference,)),)) == 0


def test_artist_credit_nodes_round_trip_with_exact_join_phrase(library_item) -> None:
    library, item = library_item
    artist_credit = ArtistCredit(
        EntityKind.RECORDING,
        (
            ArtistCreditNode(ARTIST_ID, "Artist", "Alias", " feat. ", 0),
            ArtistCreditNode(RECORDING_ID, "Guest", "Guest", "", 1),
        ),
        RECORDING_ID,
    )

    apply_credit_state(
        library,
        "item",
        item.id,
        (change("structured_artist_credits", artist_credit),),
    )

    assert read_credit_state(library, "item", item.id) == {
        "structured_artist_credits": artist_credit
    }


def test_unknown_schema_version_fails_closed(library_item) -> None:
    library, item = library_item
    reference = CreditReference(
        CreditParty("Producer", ARTIST_ID),
        CreditRole.PRODUCER,
        EntityKind.RECORDING,
    )
    apply_credit_state(library, "item", item.id, (change("producers", (reference,)),))
    with library.transaction() as tx:
        tx.mutate("UPDATE noqlenmeta_credit_schema SET version=99")

    with pytest.raises(RuntimeError, match="schema version"):
        read_credit_state(library, "item", item.id)


def test_item_import_hook_persists_prepared_state_without_reacquisition(
    library_item,
) -> None:
    library, item = library_item
    item.mb_trackid = RECORDING_ID
    item.store()
    reference = CreditReference(
        CreditParty("Producer", ARTIST_ID),
        CreditRole.PRODUCER,
        EntityKind.RECORDING,
        source_entity_id=RECORDING_ID,
    )
    prepared = change("producers", (reference,))
    plugin = NoqlenMetaPlugin()
    plugin._queue_import_credit_state("item", RECORDING_ID, (prepared,))

    plugin._item_imported(library, library.get_item(item.id))

    assert read_credit_state(library, "item", item.id) == {"producers": (reference,)}
    assert plugin._pending_import_credits == {}


def test_album_import_hook_persists_each_owner_once(tmp_path: Path) -> None:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(
        path=b"synthetic.flac",
        artist="Artist",
        title="Track",
        album="Album",
        mb_trackid=RECORDING_ID,
        mb_albumid=RELEASE_ID,
    )
    album: Album = library.add_album((item,))
    album.mb_albumid = RELEASE_ID
    album.store(inherit=False)
    recording_reference = CreditReference(
        CreditParty("Track Producer", ARTIST_ID),
        CreditRole.PRODUCER,
        EntityKind.RECORDING,
        source_entity_id=RECORDING_ID,
    )
    release_reference = CreditReference(
        CreditParty("Release Producer", ARTIST_ID),
        CreditRole.PRODUCER,
        EntityKind.RELEASE,
        source_entity_id=RELEASE_ID,
    )
    plugin = NoqlenMetaPlugin()
    plugin._queue_import_credit_state(
        "item", RECORDING_ID, (change("producers", (recording_reference,)),)
    )
    plugin._queue_import_credit_state(
        "album", RELEASE_ID, (change("producers", (release_reference,)),)
    )

    stored_item = tuple(album.items())[0]
    plugin._item_imported(library, stored_item)
    plugin._album_imported(library, album)

    assert read_credit_state(library, "item", stored_item.id) == {
        "producers": (recording_reference,)
    }
    assert read_credit_state(library, "album", album.id) == {
        "producers": (release_reference,)
    }
    assert plugin._pending_import_credits == {}
