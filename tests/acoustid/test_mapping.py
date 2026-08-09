from __future__ import annotations

from dataclasses import fields, replace

import pytest
from beets.library import Item

from beetsplug.noqlenmeta.acoustid import (
    AcoustIDDatabaseState,
    AcoustIDDatabaseTargetPlan,
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDExistingValues,
    AcoustIDFieldPlan,
    AcoustIDFingerprintMaterial,
    AcoustIDFingerprintOrigin,
    AcoustIDLibraryTargetKind,
    AcoustIDResultGroup,
    AcoustIDSourceSnapshot,
    AcoustIDTrackDatabasePlan,
    AcoustIDTrackEvidence,
    AcoustIDTrackOutcome,
    FingerprintPreparationResult,
    SelectedAcoustIDItem,
    SelectedAcoustIDTarget,
    canonical_acoustid_database_plan,
    classify_acoustid_evidence,
    snapshot_acoustid_target,
)

PRIVATE_PATH = b"/private/library/track.flac"
PRIVATE_FINGERPRINT = "private-synthetic-fingerprint"
ACOUSTID_ID = "00000001-0000-4000-8000-000000000001"
OTHER_ACOUSTID_ID = "00000002-0000-4000-8000-000000000002"
RECORDING_ID = "00000065-0000-4000-8000-000000000065"


def selected_item(
    number: int = 1,
    *,
    album_id: int | None = None,
    acoustid_id: object = None,
    fingerprint: object = None,
    length: object = 120,
) -> SelectedAcoustIDItem:
    item = Item(
        id=number,
        album_id=album_id,
        path=PRIVATE_PATH + str(number).encode(),
        length=length,
        acoustid_id=acoustid_id,
        acoustid_fingerprint=fingerprint,
    )
    return SelectedAcoustIDItem(
        f"library-item:{number}",
        number,
        album_id,
        item,
        item.path,
        AcoustIDExistingValues.from_stored(acoustid_id, fingerprint, length),
    )


def target(*items: SelectedAcoustIDItem) -> SelectedAcoustIDTarget:
    album_id = items[0].album_id
    kind = (
        AcoustIDLibraryTargetKind.ALBUM
        if album_id is not None
        else AcoustIDLibraryTargetKind.SINGLETON
    )
    return SelectedAcoustIDTarget(kind, album_id, items)


def source_snapshot() -> AcoustIDSourceSnapshot:
    return AcoustIDSourceSnapshot(1, 2, 3, 4)


def generated_material(local_key: str, value: str = PRIVATE_FINGERPRINT):
    return AcoustIDFingerprintMaterial(
        local_key,
        value,
        120,
        AcoustIDFingerprintOrigin.GENERATED,
        source_snapshot(),
    )


def decisive(
    local_key: str,
    origin=AcoustIDFingerprintOrigin.GENERATED,
    acoustid_id: str = ACOUSTID_ID,
):
    return classify_acoustid_evidence(
        local_key,
        origin,
        (AcoustIDResultGroup(acoustid_id, 0.99, (RECORDING_ID,)),),
        AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
    )


def outcome(
    item: SelectedAcoustIDItem,
    *,
    material=True,
    evidence="decisive",
    fingerprint: str = PRIVATE_FINGERPRINT,
    acoustid_id: str = ACOUSTID_ID,
):
    value = generated_material(item.local_key, fingerprint) if material else None
    preparation = FingerprintPreparationResult(
        item.local_key,
        value,
        (
            AcoustIDEvidenceReason.FINGERPRINT_GENERATED
            if value
            else AcoustIDEvidenceReason.FINGERPRINT_MISSING
        ),
    )
    if not value:
        return AcoustIDTrackOutcome(preparation, None)
    if evidence == "decisive":
        track_evidence = decisive(item.local_key, acoustid_id=acoustid_id)
    elif evidence == "unavailable":
        track_evidence = unavailable(item.local_key)
    elif evidence == "no_match":
        track_evidence = classify_acoustid_evidence(
            item.local_key,
            value.origin,
            (AcoustIDResultGroup(ACOUSTID_ID, 0.5, (RECORDING_ID,)),),
            AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
        )
    else:
        track_evidence = classify_acoustid_evidence(
            item.local_key,
            value.origin,
            (
                AcoustIDResultGroup(ACOUSTID_ID, 0.99, (RECORDING_ID,)),
                AcoustIDResultGroup(
                    OTHER_ACOUSTID_ID,
                    0.99,
                    ("00000066-0000-4000-8000-000000000066",),
                ),
            ),
            AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
        )
    return AcoustIDTrackOutcome(preparation, track_evidence)


def unavailable(local_key: str) -> AcoustIDTrackEvidence:
    return AcoustIDTrackEvidence(
        local_key,
        AcoustIDFingerprintOrigin.GENERATED,
        (),
        AcoustIDEvidenceVerdict.UNAVAILABLE,
        None,
        None,
        AcoustIDEvidenceReason.LOOKUP_FAILED,
        None,
        None,
        None,
        0,
        0,
    )


def mapped(item: SelectedAcoustIDItem, track_outcome: AcoustIDTrackOutcome):
    snapshot = snapshot_acoustid_target(target(item))
    return canonical_acoustid_database_plan(snapshot, (track_outcome,)).tracks[0]


def test_exact_album_and_singleton_snapshots_preserve_membership_order_and_raw_values() -> None:
    first = selected_item(2, album_id=7, acoustid_id="bad-a", fingerprint=" private ")
    second = selected_item(1, album_id=7, acoustid_id=ACOUSTID_ID, fingerprint=None)
    album_snapshot = snapshot_acoustid_target(target(first, second))
    singleton_snapshot = snapshot_acoustid_target(target(selected_item(3)))

    assert album_snapshot.kind is AcoustIDLibraryTargetKind.ALBUM
    assert album_snapshot.album_id == 7
    assert [item.item_id for item in album_snapshot.items] == [2, 1]
    assert [item.album_id for item in album_snapshot.items] == [7, 7]
    assert album_snapshot.items[0].acoustid_id == "bad-a"
    assert album_snapshot.items[0].acoustid_fingerprint == " private "
    assert singleton_snapshot.kind is AcoustIDLibraryTargetKind.SINGLETON
    assert singleton_snapshot.album_id is None


def test_raw_malformed_change_remains_exactly_detectable_and_private() -> None:
    item = selected_item(acoustid_id="bad-a", fingerprint=" private-bad-a ")
    before = snapshot_acoustid_target(target(item))
    item.item.acoustid_id = "bad-b"
    item.item.acoustid_fingerprint = " private-bad-b "
    after = snapshot_acoustid_target(target(item))

    assert before != after
    assert before.items[0].acoustid_id == "bad-a"
    assert after.items[0].acoustid_id == "bad-b"
    rendered = repr((before, after))
    assert "/private" not in rendered
    assert "private-bad-a" not in rendered
    assert "private-bad-b" not in rendered


@pytest.mark.parametrize(
    ("field_name", "changed"),
    [
        ("acoustid_fingerprint", "changed-valid-fingerprint"),
        ("length", 121),
    ],
)
def test_snapshot_rejects_changes_that_would_stale_fingerprint_preparation(
    field_name: str, changed: object
) -> None:
    item = selected_item(fingerprint=PRIVATE_FINGERPRINT)
    setattr(item.item, field_name, changed)

    with pytest.raises(ValueError, match="changed before planning"):
        snapshot_acoustid_target(target(item))


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (None, AcoustIDDatabaseState.PROPOSE),
        (ACOUSTID_ID.upper(), AcoustIDDatabaseState.KEEP),
        (OTHER_ACOUSTID_ID, AcoustIDDatabaseState.REVIEW),
        ("malformed-current", AcoustIDDatabaseState.REVIEW),
    ],
)
def test_decisive_identifier_mapping(current: object, expected: AcoustIDDatabaseState) -> None:
    item = selected_item(acoustid_id=current)
    assert mapped(item, outcome(item)).acoustid_id.state is expected


@pytest.mark.parametrize("evidence", ["unavailable", "no_match", "ambiguous"])
def test_non_decisive_lookup_never_clears_identifier(evidence: str) -> None:
    item = selected_item(acoustid_id=OTHER_ACOUSTID_ID)
    plan = mapped(item, outcome(item, evidence=evidence))
    assert plan.acoustid_id.state is AcoustIDDatabaseState.KEEP


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (None, AcoustIDDatabaseState.PROPOSE),
        (PRIVATE_FINGERPRINT, AcoustIDDatabaseState.KEEP),
        ("different-private", AcoustIDDatabaseState.REVIEW),
        (" malformed-private ", AcoustIDDatabaseState.REVIEW),
    ],
)
def test_generated_fingerprint_mapping(current: object, expected: AcoustIDDatabaseState) -> None:
    item = selected_item(fingerprint=current)
    plan = mapped(item, outcome(item, evidence="unavailable"))
    assert plan.acoustid_fingerprint.state is expected


def test_same_fingerprint_is_keep_even_when_stored_length_was_not_reusable() -> None:
    item = selected_item(fingerprint=PRIVATE_FINGERPRINT, length=None)
    assert mapped(item, outcome(item)).acoustid_fingerprint.state is AcoustIDDatabaseState.KEEP


def test_missing_material_preserves_current_fingerprint() -> None:
    item = selected_item(fingerprint="stored-private")
    plan = mapped(item, outcome(item, material=False))
    assert plan.acoustid_fingerprint.state is AcoustIDDatabaseState.KEEP


def test_plan_is_canonical_reproducible_and_has_no_musicbrainz_surface() -> None:
    item = selected_item()
    snapshot = snapshot_acoustid_target(target(item))
    outcomes = (outcome(item),)
    canonical = canonical_acoustid_database_plan(snapshot, outcomes)
    tampered = replace(
        canonical,
        tracks=(
            AcoustIDTrackDatabasePlan(
                item.local_key,
                AcoustIDFieldPlan(AcoustIDDatabaseState.KEEP),
                AcoustIDFieldPlan(AcoustIDDatabaseState.KEEP),
            ),
        ),
    )

    assert canonical == canonical_acoustid_database_plan(snapshot, outcomes)
    assert tampered != canonical_acoustid_database_plan(snapshot, outcomes)
    assert {field.name for field in fields(AcoustIDTrackDatabasePlan)} == {
        "local_key",
        "acoustid_id",
        "acoustid_fingerprint",
    }
    assert "mb_" not in repr(AcoustIDDatabaseTargetPlan)


def test_canonical_plan_binds_exact_proposed_identifier_and_fingerprint() -> None:
    item = selected_item()
    snapshot = snapshot_acoustid_target(target(item))
    first = canonical_acoustid_database_plan(snapshot, (outcome(item),))
    second = canonical_acoustid_database_plan(
        snapshot,
        (
            outcome(
                item,
                fingerprint="different-private-proposal",
                acoustid_id=OTHER_ACOUSTID_ID,
            ),
        ),
    )

    assert first != second
    assert PRIVATE_FINGERPRINT not in repr(first)
    assert "different-private-proposal" not in repr(second)
