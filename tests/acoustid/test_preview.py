from __future__ import annotations

import os
import socket
import subprocess

from beets.library import Item, Library

from beetsplug.noqlenmeta.acoustid import (
    AcoustIDDatabaseState,
    AcoustIDDatabaseTargetPlan,
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDExistingValues,
    AcoustIDFieldPlan,
    AcoustIDFingerprintMaterial,
    AcoustIDFingerprintOrigin,
    AcoustIDLibraryTargetKind,
    AcoustIDResultGroup,
    AcoustIDSourceSnapshot,
    AcoustIDTargetResult,
    AcoustIDTrackDatabasePlan,
    AcoustIDTrackOutcome,
    FingerprintPreparationResult,
    SelectedAcoustIDItem,
    SelectedAcoustIDTarget,
    classify_acoustid_evidence,
    render_acoustid_preview,
    snapshot_acoustid_target,
)

PRIVATE_PATH = b"/private/library/preview.flac"
PRIVATE_FINGERPRINT = "private-preview-fingerprint"
PRIVATE_KEY = "private-preview-client-key"
ACOUSTID_ID = "abcdef01-0000-4000-8000-000000000001"
RECORDING_ID = "00000065-0000-4000-8000-000000000065"


def result() -> AcoustIDTargetResult:
    selected_items = []
    outcomes = []
    states = (
        (AcoustIDDatabaseState.KEEP, AcoustIDDatabaseState.KEEP),
        (AcoustIDDatabaseState.KEEP, AcoustIDDatabaseState.PROPOSE),
        (AcoustIDDatabaseState.REVIEW, AcoustIDDatabaseState.PROPOSE),
        (AcoustIDDatabaseState.REVIEW, AcoustIDDatabaseState.BLOCKED),
    )
    for number in range(1, 5):
        item = Item(
            id=number,
            album_id=9,
            path=PRIVATE_PATH + str(number).encode(),
            length=120,
        )
        selected_items.append(
            SelectedAcoustIDItem(
                f"library-item:{number}",
                number,
                9,
                item,
                item.path,
                AcoustIDExistingValues.from_stored(None, None, 120),
            )
        )
        material = AcoustIDFingerprintMaterial(
            f"library-item:{number}",
            PRIVATE_FINGERPRINT,
            120,
            AcoustIDFingerprintOrigin.GENERATED,
            AcoustIDSourceSnapshot(1, number, 3, 4),
        )
        preparation = FingerprintPreparationResult(
            material.local_key, material, AcoustIDEvidenceReason.FINGERPRINT_GENERATED
        )
        evidence = classify_acoustid_evidence(
            material.local_key,
            material.origin,
            (AcoustIDResultGroup(ACOUSTID_ID, 0.99, (RECORDING_ID,)),),
            AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
        )
        outcomes.append(AcoustIDTrackOutcome(preparation, evidence))
    selected = SelectedAcoustIDTarget(
        AcoustIDLibraryTargetKind.ALBUM, 9, tuple(selected_items)
    )
    plan = AcoustIDDatabaseTargetPlan(
        tuple(
            AcoustIDTrackDatabasePlan(
                item.local_key,
                AcoustIDFieldPlan(
                    id_state, ACOUSTID_ID if id_state in {
                        AcoustIDDatabaseState.PROPOSE,
                        AcoustIDDatabaseState.REVIEW,
                    } else None
                ),
                AcoustIDFieldPlan(
                    fingerprint_state,
                    PRIVATE_FINGERPRINT if fingerprint_state in {
                        AcoustIDDatabaseState.PROPOSE,
                        AcoustIDDatabaseState.REVIEW,
                    } else None,
                ),
            )
            for item, (id_state, fingerprint_state) in zip(
                selected_items, states, strict=True
            )
        )
    )
    return AcoustIDTargetResult(
        selected, snapshot_acoustid_target(selected), tuple(outcomes), plan
    )


def test_preview_uses_frozen_vocabulary_severity_and_safe_summary() -> None:
    rendered = render_acoustid_preview(result())

    assert "Fingerprint GENERATED" in rendered
    assert "Lookup      DECISIVE" in rendered
    assert "Database    KEEP" in rendered
    assert "Database    PROPOSE" in rendered
    assert "Database    REVIEW" in rendered
    assert "Database    BLOCKED" in rendered
    assert "Summary     KEEP=1 PROPOSE=1 REVIEW=1 BLOCKED=1" in rendered
    assert f"Recording    {RECORDING_ID}" in rendered
    assert "AcoustID     abcdef01" in rendered
    assert ACOUSTID_ID not in rendered
    assert "Reason      existing_value_conflict" in rendered
    assert "Reason      recording_decisive" in rendered


def test_preview_is_private_and_performs_no_io_or_mutation(monkeypatch) -> None:
    prepared = result()

    def forbidden(*args, **kwargs):
        raise AssertionError("preview attempted I/O or mutation")

    monkeypatch.setattr(Library, "items", forbidden)
    monkeypatch.setattr(Item, "store", forbidden)
    monkeypatch.setattr(Item, "write", forbidden)
    monkeypatch.setattr(os, "stat", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    rendered = render_acoustid_preview(prepared)

    assert "/private" not in rendered
    assert PRIVATE_FINGERPRINT not in rendered
    assert PRIVATE_KEY not in rendered
    assert "raw backend output" not in rendered
    assert "raw HTTP payload" not in rendered
