from dataclasses import FrozenInstanceError

import pytest
from beets.autotag.hooks import TrackInfo
from beets.library import Item

from beetsplug.noqlenmeta.changeplan import ChangePlan, PlannedChange
from beetsplug.noqlenmeta.domain import ExternalIdentifier, MetadataCandidate
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction
from beetsplug.noqlenmeta.track_mapping import (
    TRACK_FIELD_TARGETS,
    TrackFieldTarget,
    TrackMappingError,
    TrackTargetPlan,
    TrackTargetShape,
    map_change_plan_to_track_info,
)
from beetsplug.noqlenmeta.work_identity import WorkReference

SYNCED_TARGET_REASON = (
    "no lossless normal beets TrackInfo target preserves synchronized lyrics semantics"
)
UNKNOWN_TARGET_REASON = "no supported TrackInfo target exists for this canonical field"


def planned_change(field: str, value: object) -> PlannedChange:
    source = MetadataCandidate(
        field=field,
        value=value,  # type: ignore[arg-type]
        provider="lrclib",
        confidence=0.95,
        source_id="42",
    )
    return PlannedChange(field, None, source.value, source, f"resolved {field}")


def test_lyrics_maps_losslessly_to_track_info() -> None:
    value = "Synthetic line one\nSynthetic line two"
    change = planned_change("lyrics", value)
    source = ChangePlan(changes=(change,))

    result = map_change_plan_to_track_info(source)

    assert result.blocked_changes == ()
    assert len(result.mapped_changes) == 1
    mapped = result.mapped_changes[0]
    assert mapped.canonical_field == "lyrics"
    assert mapped.target_field == "lyrics"
    assert mapped.target_shape is TrackTargetShape.SCALAR_STRING
    assert mapped.target_value == value
    assert mapped.target_value is change.after
    assert mapped.source is change
    assert mapped.source.source is change.source
    assert result.source is source
    assert result.is_fully_mapped
    assert not result.requires_review


@pytest.mark.parametrize(
    ("field", "value", "target", "shape"),
    [
        ("bpm", 126.4, "bpm", TrackTargetShape.SCALAR_FLOAT),
        ("moods", ("Dark", "Energetic"), "moods", TrackTargetShape.STRING_LIST),
        (
            "lyrics_languages",
            ("English", "Korean"),
            "lyrics_languages",
            TrackTargetShape.STRING_LIST,
        ),
        (
            "artist_countries",
            ("BR", "US"),
            "artist_countries",
            TrackTargetShape.STRING_LIST,
        ),
    ],
)
def test_v2_track_targets_are_lossless(
    field: str, value: object, target: str, shape: TrackTargetShape
) -> None:
    result = map_change_plan_to_track_info(
        ChangePlan(changes=(planned_change(field, value),))
    )

    mapped = result.mapped_changes[0]
    assert mapped.target_field == target
    assert mapped.target_shape is shape
    assert mapped.target_value == value


def test_single_work_maps_id_and_safe_title_without_flattening() -> None:
    reference = WorkReference(
        "12345678-1234-5678-9234-567812345678",
        "Synthetic Work",
        "performance",
        None,
    )
    evidence = MetadataEvidence(
        field="works",
        value=(reference,),
        subject=SubjectRef(
            EntityKind.RECORDING,
            (
                ExternalIdentifier(
                    "musicbrainz.recording",
                    "22345678-1234-5678-9234-567812345678",
                ),
            ),
        ),
        provider="musicbrainz",
        acquisition_scope=ProviderScope.TRACK,
        source_id="22345678-1234-5678-9234-567812345678",
        provenance=AcquisitionProvenance(AcquisitionMethod.EXACT_LOOKUP),
    )
    change = PlannedChange("works", None, (reference,), evidence, "resolved")

    result = map_change_plan_to_track_info(ChangePlan(changes=(change,)))

    assert {mapped.target_field: mapped.target_value for mapped in result.mapped_changes} == {
        "mb_workids": (reference.mbid,),
        "mb_workid": reference.mbid,
        "work": "Synthetic Work",
    }


def test_actual_track_info_exposes_lossless_plain_lyrics_item_data_target() -> None:
    value = "Synthetic line one\nSynthetic line two"
    track = TrackInfo(artist="Synthetic Artist", title="Synthetic Track")

    track["lyrics"] = value

    assert track.item_data["lyrics"] == value


def test_synced_lyrics_is_not_a_standard_item_write_target() -> None:
    assert "lyrics" in Item._fields
    assert "lyrics" in Item._media_tag_fields
    assert "synced_lyrics" not in Item._fields
    assert "synced_lyrics" not in Item._media_tag_fields


def test_synced_lyrics_becomes_mapping_blocker_without_exception() -> None:
    change = planned_change("synced_lyrics", "[00:01.00] Synthetic line")

    result = map_change_plan_to_track_info(ChangePlan(changes=(change,)))

    assert result.mapped_changes == ()
    assert len(result.blocked_changes) == 1
    blocker = result.blocked_changes[0]
    assert blocker.source is change
    assert blocker.target_field is None
    assert blocker.reason == SYNCED_TARGET_REASON
    assert result.has_mapping_blockers
    assert not result.is_fully_mapped
    assert result.requires_review
    with pytest.raises(FrozenInstanceError):
        blocker.reason = "other"  # type: ignore[misc]


def test_unknown_canonical_field_becomes_generic_mapping_blocker() -> None:
    change = planned_change("mood", ("Synthetic Mood",))

    result = map_change_plan_to_track_info(ChangePlan(changes=(change,)))

    assert result.mapped_changes == ()
    assert result.blocked_changes[0].source is change
    assert result.blocked_changes[0].target_field is None
    assert result.blocked_changes[0].reason == UNKNOWN_TARGET_REASON


def test_resolver_review_is_not_duplicated_as_mapping_blocker() -> None:
    review = FieldDecision(
        "lyrics", None, None, ResolutionAction.REVIEW, "synthetic conflict"
    )
    source = ChangePlan(reviews=(review,))

    result = map_change_plan_to_track_info(source)

    assert result.source is source
    assert result.mapped_changes == ()
    assert result.blocked_changes == ()
    assert result.requires_review
    assert result.is_fully_mapped


def test_mapping_is_deterministic_and_does_not_mutate_source() -> None:
    changes = (
        planned_change("synced_lyrics", "[00:01.00] Synthetic line"),
        planned_change("lyrics", "Synthetic plain line"),
        planned_change("mood", ("Synthetic Mood",)),
    )
    source = ChangePlan(changes=changes)
    candidate_snapshots = tuple(change.source for change in changes)

    result = map_change_plan_to_track_info(source)
    reversed_result = map_change_plan_to_track_info(
        ChangePlan(changes=tuple(reversed(changes)))
    )

    assert source.changes == changes
    assert tuple(change.source for change in changes) == candidate_snapshots
    assert [change.canonical_field for change in result.mapped_changes] == ["lyrics"]
    assert [blocker.source.field for blocker in result.blocked_changes] == [
        "mood",
        "synced_lyrics",
    ]
    assert result.mapped_changes == reversed_result.mapped_changes
    assert result.blocked_changes == reversed_result.blocked_changes


def test_target_registry_and_mapping_results_are_immutable() -> None:
    assert TRACK_FIELD_TARGETS == {
        "lyrics": TrackFieldTarget("lyrics", "lyrics", TrackTargetShape.SCALAR_STRING),
        "bpm": TrackFieldTarget("bpm", "bpm", TrackTargetShape.SCALAR_FLOAT),
        "genres": TrackFieldTarget("genres", "genres", TrackTargetShape.STRING_LIST),
        "moods": TrackFieldTarget("moods", "moods", TrackTargetShape.STRING_LIST),
        "lyrics_languages": TrackFieldTarget(
            "lyrics_languages", "lyrics_languages", TrackTargetShape.STRING_LIST
        ),
        "artist_countries": TrackFieldTarget(
            "artist_countries", "artist_countries", TrackTargetShape.STRING_LIST
        ),
        "artist_areas": TrackFieldTarget(
            "artist_areas", "artist_areas", TrackTargetShape.STRING_LIST
        ),
        "artist_languages": TrackFieldTarget(
            "artist_languages", "artist_languages", TrackTargetShape.STRING_LIST
        ),
        "isrcs": TrackFieldTarget("isrcs", "isrcs", TrackTargetShape.STRING_LIST),
        "iswcs": TrackFieldTarget("iswcs", "iswcs", TrackTargetShape.STRING_LIST),
        "works": TrackFieldTarget("works", "mb_workids", TrackTargetShape.STRING_LIST),
        "recording_date": TrackFieldTarget(
            "recording_date", "recording_date", TrackTargetShape.SCALAR_STRING
        ),
    }
    result = map_change_plan_to_track_info(
        ChangePlan(changes=(planned_change("lyrics", "Synthetic plain line"),))
    )

    with pytest.raises(TypeError):
        TRACK_FIELD_TARGETS["synced_lyrics"] = TrackFieldTarget(  # type: ignore[index]
            "synced_lyrics", "synced_lyrics", TrackTargetShape.SCALAR_STRING
        )
    with pytest.raises(FrozenInstanceError):
        TRACK_FIELD_TARGETS["lyrics"].target_field = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.mapped_changes = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.mapped_changes[0].target_value = "Other"  # type: ignore[misc]
    assert isinstance(result, TrackTargetPlan)


@pytest.mark.parametrize(
    ("canonical", "target", "shape"),
    [
        ("Lyrics", "lyrics", TrackTargetShape.SCALAR_STRING),
        ("lyrics", "track field", TrackTargetShape.SCALAR_STRING),
        ("lyrics", "lyrics", object()),
    ],
)
def test_invalid_target_descriptor_raises_mapping_error(
    canonical: str, target: str, shape: object
) -> None:
    with pytest.raises(TrackMappingError):
        TrackFieldTarget(canonical, target, shape)  # type: ignore[arg-type]


def test_invalid_mapping_source_raises_mapping_error() -> None:
    with pytest.raises(TrackMappingError, match="ChangePlan"):
        map_change_plan_to_track_info(object())  # type: ignore[arg-type]
