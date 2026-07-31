from dataclasses import replace

import pytest
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.library import Item

from beetsplug.noqlenmeta.identity import (
    MISSING_ALBUM_ID_MARKER,
    MISSING_RELEASE_GROUP_ID_MARKER,
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


def _album_result(local_context, candidates):
    audit = audit_musicbrainz_identity(local_context, candidates)
    selected_tracks = tuple(
        SelectedIdentityTrack(
            f"selected-{index}",
            Item(),
            TrackInfo(artist="Example Artist", title=f"Track {index}"),
        )
        for index in range(1, len(local_context.tracks) + 1)
    )
    selected = SelectedImportIdentity(
        IdentityImportMatchKind.ALBUM,
        selected_tracks,
        AlbumInfo(
            [track.track_info for track in selected_tracks],
            artist="Example Artist",
            album="Example Album",
        ),
    )
    result = ImportIdentityAuditResult(selected, local_context, audit)
    plan = map_identity_audit_to_import_targets(
        audit, match_kind=IdentityImportMatchKind.ALBUM
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


def test_confirmed_repeated_album_ids_render_canonical_value_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_release = mbid(100)
    expected_group = mbid(200)
    local = context(
        2,
        tracks=tuple(
            local_track(
                index,
                recording=mbid(1000 + index),
                release_track=mbid(2000 + index),
            )
            for index in range(1, 3)
        ),
        release_ids=(expected_release, expected_release),
        release_group_ids=(expected_group, expected_group),
    )
    result, plan = _album_result(local, (candidate(2),))

    rendered = _render(monkeypatch, result, plan)

    assert "verdict: confirmed" in rendered
    assert rendered.count(f"current: {expected_release}") == 1
    assert rendered.count(f"current: {expected_group}") == 1
    assert "current: malformed" not in rendered


def test_repeated_conflicting_album_ids_render_canonical_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrong_release = mbid(901)
    wrong_group = mbid(902)
    local = context(
        2,
        release_ids=(wrong_release, wrong_release),
        release_group_ids=(wrong_group, wrong_group),
    )
    result, plan = _album_result(local, (candidate(2),))

    rendered = _render(monkeypatch, result, plan)

    assert "verdict: conflict" in rendered
    assert f"current: {wrong_release}" in rendered
    assert f"current: {wrong_group}" in rendered
    assert f"expected: {mbid(100)}" in rendered
    assert f"expected: {mbid(200)}" in rendered
    assert "current: malformed" not in rendered


def test_distinct_canonical_album_ids_render_fixed_conflict_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = mbid(901)
    second = mbid(902)
    local = context(
        2,
        release_ids=(first, second),
        release_group_ids=(mbid(903), mbid(904)),
    )
    result, plan = _album_result(local, (candidate(2),))

    rendered = _render(monkeypatch, result, plan)

    assert rendered.count("current: multiple/conflict") == 2
    assert f"{first} | {second}" not in rendered


def test_mixed_album_identity_markers_render_fixed_safe_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local = context(
        2,
        release_ids=(mbid(100), MISSING_ALBUM_ID_MARKER),
        release_group_ids=(mbid(200), MISSING_RELEASE_GROUP_ID_MARKER),
    )
    result, plan = _album_result(local, (candidate(2),))

    rendered = _render(monkeypatch, result, plan)

    assert rendered.count("current: mixed/missing") == 2
    assert MISSING_ALBUM_ID_MARKER not in rendered
    assert MISSING_RELEASE_GROUP_ID_MARKER not in rendered


def test_ambiguous_complete_assignment_uses_top_ranked_evidence_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = (
        candidate(2, release=mbid(301), release_group=mbid(401)),
        candidate(2, release=mbid(302), release_group=mbid(402)),
    )
    result, plan = _album_result(context(2), candidates)

    rendered = _render(monkeypatch, result, plan)

    assert result.audit.verdict is IdentityVerdict.AMBIGUOUS
    assert "assigned tracks: 2" in rendered
    assert "unmatched local tracks: 0" in rendered
    assert "unmatched candidate tracks: 0" in rendered
    assert "repair ready: no" in rendered
    assert "planned identity changes: 0" in rendered


def test_ambiguous_unmatched_counts_use_top_ranked_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, plan = _album_result(context(1), (candidate(2),))
    top_assignment = result.audit.evaluations[0].assignment

    rendered = _render(monkeypatch, result, plan)

    assert result.audit.verdict is IdentityVerdict.AMBIGUOUS
    assert f"assigned tracks: {len(top_assignment.assignments)}" in rendered
    assert f"unmatched local tracks: {len(top_assignment.unmatched_local_keys)}" in rendered
    assert (
        "unmatched candidate tracks: "
        f"{len(top_assignment.unmatched_candidate_indices)}" in rendered
    )


def test_no_candidates_keep_zero_assignment_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, plan = _result(context(1), ())

    rendered = _render(monkeypatch, result, plan)

    assert "candidate count: 0" in rendered
    assert "assigned tracks: 0" in rendered
    assert "unmatched local tracks: 0" in rendered
    assert "unmatched candidate tracks: 0" in rendered


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
