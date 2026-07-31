from dataclasses import replace

import pytest
from beets.autotag.hooks import TrackInfo
from beets.library import Item

from beetsplug.noqlenmeta.identity import (
    IdentityImportApplicationResult,
    IdentityImportMatchKind,
    IdentityVerdict,
    ImportIdentityAuditResult,
    SelectedIdentityTrack,
    SelectedImportIdentity,
    audit_musicbrainz_identity,
    map_identity_audit_to_import_targets,
)
from beetsplug.noqlenmeta.identity.importer_preview import (
    render_import_identity_audit,
    render_incomplete_import_identity_note,
)

from .helpers import candidate, context, local_track, mbid

PRIVATE_KEY = "private-local-key"
PRIVATE_PATH = b"/private/music/example.flac"
PRIVATE_RAW_VALUE = "raw-malformed-private-value"


def _selected() -> SelectedImportIdentity:
    return SelectedImportIdentity(
        IdentityImportMatchKind.TRACK,
        (
            SelectedIdentityTrack(
                PRIVATE_KEY,
                Item(path=PRIVATE_PATH),
                TrackInfo(artist="Example Artist", title="Track 1", album="Example Album"),
            ),
        ),
        None,
    )


def _result(local_context, candidates):
    audit = audit_musicbrainz_identity(local_context, candidates)
    selected = _selected()
    result = ImportIdentityAuditResult(selected, local_context, audit)
    plan = map_identity_audit_to_import_targets(
        audit, match_kind=IdentityImportMatchKind.TRACK
    )
    return result, plan


def _render(
    monkeypatch: pytest.MonkeyPatch,
    result: ImportIdentityAuditResult,
    plan,
    application_result: IdentityImportApplicationResult | None = None,
) -> str:
    output: list[str] = []
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.identity.importer_preview.ui.print_", output.append
    )
    render_import_identity_audit(result, plan, application_result)
    assert len(output) == 1
    return output[0]


def test_preview_sanitizes_local_keys_paths_and_raw_malformed_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local = context(
        1,
        tracks=(
            local_track(
                1,
                recording=PRIVATE_RAW_VALUE,
                release_track=mbid(999),
            ),
        ),
        release_ids=(PRIVATE_RAW_VALUE,),
    )
    result, plan = _result(local, (candidate(1),))

    rendered = _render(monkeypatch, result, plan)

    assert "verdict: conflict" in rendered
    assert "status: conflict" in rendered
    assert "current: malformed" in rendered
    assert PRIVATE_KEY not in rendered
    assert PRIVATE_PATH.decode() not in rendered
    assert PRIVATE_RAW_VALUE not in rendered


def test_ambiguous_preview_limits_candidate_details_to_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    releases = (mbid(301), mbid(302), mbid(303))
    candidates = tuple(
        candidate(1, release=release, release_group=mbid(400 + index))
        for index, release in enumerate(releases, start=1)
    )
    result, plan = _result(context(1), candidates)

    rendered = _render(monkeypatch, result, plan)

    assert "verdict: ambiguous" in rendered
    assert "candidate count: 3" in rendered
    assert "candidate 1 release:" in rendered
    assert "candidate 2 release:" in rendered
    assert "candidate 3 release:" not in rendered
    assert releases[2] not in rendered


@pytest.mark.parametrize(
    ("application_result", "expected"),
    [
        (None, "application: disabled"),
        (
            IdentityImportApplicationResult(
                IdentityVerdict.AMBIGUOUS, blocked_reason="synthetic"
            ),
            "application: blocked",
        ),
        (
            IdentityImportApplicationResult(IdentityVerdict.CONFIRMED),
            "application: confirmed/no changes",
        ),
    ],
)
def test_preview_renders_application_status_without_internal_details(
    monkeypatch: pytest.MonkeyPatch,
    application_result: IdentityImportApplicationResult | None,
    expected: str,
) -> None:
    result, plan = _result(context(1), ())

    rendered = _render(monkeypatch, result, plan, application_result)

    assert expected in rendered
    assert "synthetic" not in rendered


def test_preview_renders_applied_change_count(monkeypatch: pytest.MonkeyPatch) -> None:
    result, plan = _result(context(1), (candidate(1),))
    application_result = IdentityImportApplicationResult(
        IdentityVerdict.MISSING, plan.changes
    )

    rendered = _render(monkeypatch, result, plan, application_result)

    assert f"application: applied {len(plan.changes)} changes" in rendered


def test_preview_reports_assignment_status_and_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = replace(candidate(1), tracks=(replace(candidate(1).tracks[0], length=None),))
    result, plan = _result(context(1), (remote,))

    rendered = _render(monkeypatch, result, plan)

    assert "match kind: singleton" in rendered
    assert "candidate count: 1" in rendered
    assert "top score:" in rendered
    assert "assigned tracks: 1" in rendered
    assert "unmatched local tracks: 0" in rendered
    assert "unmatched candidate tracks: 0" in rendered
    assert "repair ready: yes" in rendered
    assert f"planned identity changes: {len(plan.changes)}" in rendered


def test_incomplete_note_is_fixed_and_privacy_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.identity.importer_preview.ui.print_", output.append
    )

    render_incomplete_import_identity_note()

    assert output == [
        "Noqlen Meta: selected import has insufficient identity structure for "
        "MusicBrainz audit"
    ]
    assert PRIVATE_KEY not in output[0]
    assert PRIVATE_PATH.decode() not in output[0]
    assert PRIVATE_RAW_VALUE not in output[0]
