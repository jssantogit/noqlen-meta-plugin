from dataclasses import replace

import pytest
from beets import plugins
from beets.library import Item, Library
from beets.util import cached_classproperty

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.credit_state import read_credit_state
from beetsplug.noqlenmeta.credits import CreditParty, CreditReference, CreditRole
from beetsplug.noqlenmeta.domain import ExternalIdentifier, MetadataCandidate
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind
from beetsplug.noqlenmeta.library_track_application import (
    LibraryTrackApplicationError,
    apply_library_track_plan,
)
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.track_application import TrackApplicationMode
from beetsplug.noqlenmeta.track_mapping import map_change_plan_to_track_info


@pytest.fixture
def library() -> Library:
    return Library(":memory:", set_music_dir=False)


@pytest.fixture
def loaded_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plugins, "_instances", [NoqlenMetaPlugin()])
    monkeypatch.delitem(cached_classproperty.cache, (Item, "_types"), raising=False)


def add_item(library: Library, **values: object) -> Item:
    item = Item(
        artist="Synthetic Artist",
        title="Synthetic Track",
        path=b"synthetic.flac",
        **values,
    )
    library.add(item)
    return library.get_item(item.id)


def planned_change(field: str, after: object, before: object = None) -> PlannedChange:
    candidate = MetadataCandidate(field, after, "catalog", 0.95, "42")  # type: ignore[arg-type]
    return PlannedChange(
        field,
        before,  # type: ignore[arg-type]
        candidate.value,
        candidate,
        f"resolved {field}",
    )


def target_plan(*changes: PlannedChange):
    return map_change_plan_to_track_info(ChangePlan(changes=changes))


def test_multivalue_item_field_persists(
    loaded_plugin: None, library: Library
) -> None:
    item = add_item(library)
    plan = target_plan(planned_change("moods", ("Dark", "Energetic")))

    result = apply_library_track_plan(item, plan)

    fresh = library.get_item(item.id)
    assert fresh["moods"] == ["Dark", "Energetic"]
    assert result.stored


def test_integral_bpm_round_trips_as_canonical_float(library: Library) -> None:
    item = add_item(library)

    result = apply_library_track_plan(item, target_plan(planned_change("bpm", 126.0)))

    fresh = library.get_item(item.id)
    assert result.stored
    assert fresh.bpm == 126


def test_fractional_bpm_round_trips_as_canonical_float(
    loaded_plugin: None, library: Library
) -> None:
    item = add_item(library)

    result = apply_library_track_plan(item, target_plan(planned_change("bpm", 126.4)))

    assert result.stored
    assert library.get_item(item.id).bpm == 126.4


def test_credit_apply_persists_query_projection_and_structured_state(
    loaded_plugin: None, library: Library
) -> None:
    item = add_item(library)
    artist_id = "11111111-1111-4111-8111-111111111111"
    recording_id = "22222222-2222-4222-8222-222222222222"
    reference = CreditReference(
        CreditParty("Performer", artist_id),
        CreditRole.PERFORMER,
        EntityKind.RECORDING,
        instrument="electric guitar",
        source_entity_id=recording_id,
    )
    evidence = MetadataEvidence(
        "performers",
        (reference,),
        SubjectRef(
            EntityKind.RECORDING,
            (ExternalIdentifier("musicbrainz.recording", recording_id),),
        ),
        "musicbrainz",
        ProviderScope.TRACK,
        recording_id,
        AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
    )
    change = PlannedChange("performers", None, (reference,), evidence, "resolved")

    result = apply_library_track_plan(item, target_plan(change))

    assert result.stored
    assert library.get_item(item.id)["performers"] == ["Performer"]
    assert read_credit_state(library, "item", item.id) == {"performers": (reference,)}


def test_stale_database_state_is_rejected(library: Library) -> None:
    item = add_item(library, lyrics="Before")
    plan = target_plan(planned_change("lyrics", "After", "Before"))
    external = library.get_item(item.id)
    external.lyrics = "External"
    external.store()

    with pytest.raises(LibraryTrackApplicationError, match="no longer matches"):
        apply_library_track_plan(item, plan)

    assert library.get_item(item.id).lyrics == "External"


def test_dirty_item_is_rejected(library: Library) -> None:
    item = add_item(library)
    item.title = "Dirty"

    with pytest.raises(LibraryTrackApplicationError, match="pre-existing dirty"):
        apply_library_track_plan(item, target_plan(planned_change("lyrics", "After")))


def test_strict_blocker_prevents_mapped_change(library: Library) -> None:
    item = add_item(library)
    plan = target_plan(
        planned_change("lyrics", "Plain"),
        planned_change("synced_lyrics", "[00:01.00] Synced"),
    )

    result = apply_library_track_plan(item, plan)

    assert result.is_blocked
    assert library.get_item(item.id).lyrics == ""


def test_partial_mode_stores_mapped_subset(library: Library) -> None:
    item = add_item(library)
    plan = target_plan(
        planned_change("lyrics", "Plain"),
        planned_change("synced_lyrics", "[00:01.00] Synced"),
    )

    result = apply_library_track_plan(item, plan, TrackApplicationMode.PARTIAL)

    assert result.is_partial_application
    assert library.get_item(item.id).lyrics == "Plain"


def test_forged_plan_is_rejected(library: Library) -> None:
    item = add_item(library)
    plan = target_plan(planned_change("lyrics", "Plain"))
    forged = replace(
        plan,
        mapped_changes=(replace(plan.mapped_changes[0], target_value="Forged"),),
    )

    with pytest.raises(LibraryTrackApplicationError, match="canonical source mapping"):
        apply_library_track_plan(item, forged)

    assert library.get_item(item.id).lyrics == ""
