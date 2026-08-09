from __future__ import annotations

from dataclasses import replace

import pytest
from beets.library import Item, Library

from beetsplug.noqlenmeta.acoustid import (
    AcoustIDDatabaseState,
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDExistingValues,
    AcoustIDFingerprintOrigin,
    AcoustIDLibraryTargetKind,
    AcoustIDResultGroup,
    AcoustIDSourceSnapshot,
    AcoustIDTrackEvidence,
    FingerprintBackendFailure,
    FingerprintBackendResult,
    FingerprintBackendUnavailable,
    SelectedAcoustIDItem,
    SelectedAcoustIDTarget,
    classify_acoustid_evidence,
    default_acoustid_settings,
    plan_acoustid_target,
    select_acoustid_targets,
)

PRIVATE_PATH = b"/private/library/workflow.flac"
PRIVATE_FINGERPRINT = "private-generated-fingerprint"
PRIVATE_KEY = "private-client-key"
ACOUSTID_ID = "00000001-0000-4000-8000-000000000001"
RECORDING_ID = "00000065-0000-4000-8000-000000000065"


def selected(*, fingerprint: object = None, acoustid_id: object = None):
    item = Item(
        id=1,
        album_id=None,
        path=PRIVATE_PATH,
        length=120,
        acoustid_id=acoustid_id,
        acoustid_fingerprint=fingerprint,
    )
    selected_item = SelectedAcoustIDItem(
        "library-item:1",
        1,
        None,
        item,
        item.path,
        AcoustIDExistingValues.from_stored(acoustid_id, fingerprint, item.length),
    )
    return SelectedAcoustIDTarget(AcoustIDLibraryTargetKind.SINGLETON, None, (selected_item,))


def snapshot() -> AcoustIDSourceSnapshot:
    return AcoustIDSourceSnapshot(1, 2, 3, 4)


class Backend:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.paths = []

    def fingerprint(self, path):
        self.paths.append(path)
        if self.error:
            raise self.error
        return FingerprintBackendResult(120, PRIVATE_FINGERPRINT)


class Lookup:
    def __init__(self, verdict: str) -> None:
        self.verdict = verdict
        self.materials = []

    def lookup(self, material):
        self.materials.append(material)
        if self.verdict == "decisive":
            return classify_acoustid_evidence(
                material.local_key,
                material.origin,
                (AcoustIDResultGroup(ACOUSTID_ID, 0.99, (RECORDING_ID,)),),
                AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
            )
        if self.verdict == "no_match":
            return classify_acoustid_evidence(
                material.local_key,
                material.origin,
                (AcoustIDResultGroup(ACOUSTID_ID, 0.5, (RECORDING_ID,)),),
                AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
            )
        if self.verdict == "ambiguous":
            return classify_acoustid_evidence(
                material.local_key,
                material.origin,
                (
                    AcoustIDResultGroup(ACOUSTID_ID, 0.99, (RECORDING_ID,)),
                    AcoustIDResultGroup(
                        "00000002-0000-4000-8000-000000000002",
                        0.99,
                        ("00000066-0000-4000-8000-000000000066",),
                    ),
                ),
                AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
            )
        reasons = {
            "disabled": AcoustIDEvidenceReason.LOOKUP_DISABLED,
            "missing_key": AcoustIDEvidenceReason.CLIENT_KEY_MISSING,
            "unavailable": AcoustIDEvidenceReason.LOOKUP_FAILED,
        }
        return AcoustIDTrackEvidence(
            material.local_key,
            material.origin,
            (),
            AcoustIDEvidenceVerdict.UNAVAILABLE,
            None,
            None,
            reasons[self.verdict],
            None,
            None,
            None,
            0,
            0,
        )


def plan(target, lookup, *, backend=None, settings=None, authority=False):
    backend = backend or Backend()
    return plan_acoustid_target(
        target,
        settings or default_acoustid_settings(),
        authority,
        lambda: backend,
        lookup,  # type: ignore[arg-type]
        snapshot_function=lambda path: snapshot(),
    )


def test_reused_fingerprint_is_looked_up_without_backend_or_new_proposal() -> None:
    calls = []
    lookup = Lookup("decisive")
    target = selected(fingerprint="stored-private")
    result = plan_acoustid_target(
        target,
        default_acoustid_settings(),
        False,
        lambda: calls.append("backend"),  # type: ignore[arg-type,func-returns-value]
        lookup,  # type: ignore[arg-type]
        snapshot_function=lambda path: calls.append("snapshot"),  # type: ignore[arg-type,func-returns-value]
    )

    assert calls == []
    assert result.outcomes[0].preparation.reason is AcoustIDEvidenceReason.FINGERPRINT_REUSED
    assert result.outcomes[0].preparation.material.origin is AcoustIDFingerprintOrigin.EXISTING
    assert (
        result.database_plan.tracks[0].acoustid_fingerprint.state
        is AcoustIDDatabaseState.KEEP
    )


@pytest.mark.parametrize(
    ("verdict", "evidence_verdict", "id_state"),
    [
        ("decisive", AcoustIDEvidenceVerdict.DECISIVE, AcoustIDDatabaseState.PROPOSE),
        ("unavailable", AcoustIDEvidenceVerdict.UNAVAILABLE, AcoustIDDatabaseState.KEEP),
        ("disabled", AcoustIDEvidenceVerdict.UNAVAILABLE, AcoustIDDatabaseState.KEEP),
        ("missing_key", AcoustIDEvidenceVerdict.UNAVAILABLE, AcoustIDDatabaseState.KEEP),
        ("no_match", AcoustIDEvidenceVerdict.NO_MATCH, AcoustIDDatabaseState.KEEP),
        ("ambiguous", AcoustIDEvidenceVerdict.AMBIGUOUS, AcoustIDDatabaseState.KEEP),
    ],
)
def test_generated_fingerprint_preserves_lookup_outcomes(
    verdict: str,
    evidence_verdict: AcoustIDEvidenceVerdict,
    id_state: AcoustIDDatabaseState,
) -> None:
    result = plan(selected(), Lookup(verdict), authority=True)

    assert result.outcomes[0].preparation.reason is AcoustIDEvidenceReason.FINGERPRINT_GENERATED
    assert result.outcomes[0].evidence.verdict is evidence_verdict
    assert result.database_plan.tracks[0].acoustid_id.state is id_state
    assert (
        result.database_plan.tracks[0].acoustid_fingerprint.state
        is AcoustIDDatabaseState.PROPOSE
    )
    assert len(result.generated_source_snapshots) == 1
    assert result.generated_source_snapshots[0].snapshot == snapshot()


def test_missing_fingerprint_without_authority_skips_backend_and_lookup() -> None:
    calls = []
    lookup = Lookup("decisive")
    result = plan_acoustid_target(
        selected(),
        default_acoustid_settings(),
        False,
        lambda: calls.append("backend"),  # type: ignore[arg-type,func-returns-value]
        lookup,  # type: ignore[arg-type]
        snapshot_function=lambda path: calls.append("snapshot"),  # type: ignore[arg-type,func-returns-value]
    )

    assert calls == []
    assert lookup.materials == []
    assert result.outcomes[0].preparation.reason is AcoustIDEvidenceReason.FINGERPRINT_MISSING
    assert result.outcomes[0].evidence is None
    assert result.database_plan.tracks[0].state is AcoustIDDatabaseState.KEEP


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (FingerprintBackendFailure(), AcoustIDEvidenceReason.FINGERPRINT_FAILED),
        (
            FingerprintBackendUnavailable(),
            AcoustIDEvidenceReason.FINGERPRINT_BACKEND_UNAVAILABLE,
        ),
    ],
)
def test_backend_failure_is_safe_and_preserves_database_state(error, reason) -> None:
    lookup = Lookup("decisive")
    result = plan(
        selected(acoustid_id=ACOUSTID_ID),
        lookup,
        authority=True,
        backend=Backend(error),
    )

    assert result.outcomes[0].preparation.reason is reason
    assert result.outcomes[0].evidence is None
    assert lookup.materials == []
    assert result.database_plan.tracks[0].state is AcoustIDDatabaseState.KEEP


def test_stale_generated_source_is_explicitly_blocked() -> None:
    snapshots = iter((snapshot(), replace(snapshot(), size=99)))
    result = plan_acoustid_target(
        selected(),
        replace(default_acoustid_settings(), compute_missing=True),
        False,
        lambda: Backend(),
        Lookup("decisive"),  # type: ignore[arg-type]
        snapshot_function=lambda path: next(snapshots),
    )

    assert result.outcomes[0].preparation.reason is AcoustIDEvidenceReason.STALE_SOURCE_FILE
    assert result.database_plan.tracks[0].state is AcoustIDDatabaseState.BLOCKED


def test_target_result_order_and_repr_are_private() -> None:
    first_item = Item(
        id=1,
        album_id=9,
        path=PRIVATE_PATH,
        length=120,
        acoustid_fingerprint=None,
    )
    second_item = Item(
        id=2,
        album_id=9,
        path=PRIVATE_PATH + b"2",
        length=120,
        acoustid_fingerprint=None,
    )
    album_first = SelectedAcoustIDItem(
        "library-item:1",
        1,
        9,
        first_item,
        first_item.path,
        AcoustIDExistingValues.from_stored(None, None, 120),
    )
    album_second = SelectedAcoustIDItem(
        "library-item:2",
        2,
        9,
        second_item,
        second_item.path,
        AcoustIDExistingValues.from_stored(None, None, 120),
    )
    target = SelectedAcoustIDTarget(
        AcoustIDLibraryTargetKind.ALBUM, 9, (album_first, album_second)
    )
    result = plan(target, Lookup("unavailable"), authority=True)

    assert [outcome.local_key for outcome in result.outcomes] == [
        "library-item:1",
        "library-item:2",
    ]
    rendered = repr(result)
    assert "/private" not in rendered
    assert PRIVATE_FINGERPRINT not in rendered
    assert PRIVATE_KEY not in rendered
    assert "raw-provider-payload" not in rendered


def test_stage_04a_performs_no_database_or_audio_file_mutation(
    tmp_path, monkeypatch
) -> None:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(path=PRIVATE_PATH, length=120, acoustid_fingerprint="stored-private")
    library.add(item)
    target = select_acoustid_targets(library, f"id:{item.id}")[0]
    statements = []
    library._connection().set_trace_callback(statements.append)

    def forbidden(*args, **kwargs):
        raise AssertionError("Stage 04A attempted a mutation")

    monkeypatch.setattr(Item, "store", forbidden)
    monkeypatch.setattr(Item, "write", forbidden)
    result = plan(target, Lookup("disabled"))

    assert result.database_plan.tracks[0].state is AcoustIDDatabaseState.KEEP
    assert not any(statement.lstrip().upper().startswith("UPDATE") for statement in statements)
    assert not any(
        statement.lstrip().upper().startswith(("BEGIN", "SAVEPOINT"))
        for statement in statements
    )
