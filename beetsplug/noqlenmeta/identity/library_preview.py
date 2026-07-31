"""Privacy-safe rendering for persisted library identity audit results."""

from __future__ import annotations

from beets import ui

from .domain import IdentityFieldStatus, IdentityVerdict, canonical_mbid
from .library import (
    LibraryIdentityAuditResult,
    LibraryIdentityTargetKind,
    SelectedLibraryIdentityTarget,
    is_library_identity_marker,
)
from .library_application import LibraryIdentityApplicationResult
from .library_mapping import LibraryIdentityTargetPlan
from .scoring import IdentityCandidateEvaluation


def render_library_identity_audit(
    result: LibraryIdentityAuditResult,
    target_plan: LibraryIdentityTargetPlan,
    application_result: LibraryIdentityApplicationResult | None,
    *,
    apply_requested: bool,
    position: int,
    total: int,
) -> None:
    audit = result.audit
    evidence = audit.selected_evaluation or (audit.evaluations[0] if audit.evaluations else None)
    lines = [
        f"Noqlen MusicBrainz identity [{position}/{total}]",
        f"  target: {result.selected.kind.value}",
        f"  library entry: {_display_name(result.selected)}",
        f"  verdict: {audit.verdict.value}",
        f"  reason: {audit.reason}",
        f"  candidate count: {len(audit.evaluations)}",
        f"  top score: {_score(audit.evaluations, 0)}",
        f"  second score / margin: {_second_score(audit.evaluations)}",
        f"  assigned tracks: {len(evidence.assignment.assignments) if evidence else 0}",
        "  unmatched local tracks: "
        f"{len(evidence.assignment.unmatched_local_keys) if evidence else 0}",
        "  unmatched candidate tracks: "
        f"{len(evidence.assignment.unmatched_candidate_indices) if evidence else 0}",
        f"  repair ready: {'yes' if audit.repair_ready else 'no'}",
        "  planned logical findings: "
        f"{sum(f.status is not IdentityFieldStatus.CONFIRMED for f in audit.field_findings)}",
        f"  planned database field writes: {len(target_plan.changes)}",
        "  application: "
        f"{_application_status(application_result, apply_requested, audit.verdict)}",
    ]
    if audit.verdict is IdentityVerdict.AMBIGUOUS:
        for index, evaluation in enumerate(audit.evaluations[:2], start=1):
            lines.extend(
                (
                    f"  candidate {index} release: {evaluation.candidate.release_mbid}",
                    "  candidate "
                    f"{index} release group: {evaluation.candidate.release_group_mbid}",
                    f"  candidate {index} score: {evaluation.score.total:.2f}",
                )
            )
    for finding in audit.field_findings:
        track_label = "album"
        if finding.scope_key is not None:
            track_label = f"track {_track_number(result, finding.scope_key)}"
        current = _safe_current(result, finding.field, finding.scope_key)
        lines.extend(
            (
                f"  {track_label} {finding.field}",
                f"    status: {finding.status.value}",
                f"    current: {current}",
                f"    expected: {finding.expected_value}",
            )
        )
    ui.print_("\n".join(lines))


def render_unavailable_library_identity_target(
    selected: SelectedLibraryIdentityTarget,
    *,
    position: int,
    total: int,
    source_unavailable: bool,
) -> None:
    reason = (
        "MusicBrainz identity audit unavailable"
        if source_unavailable
        else "insufficient library identity structure"
    )
    ui.print_(
        "\n".join(
            (
                f"Noqlen MusicBrainz identity [{position}/{total}]",
                f"  target: {selected.kind.value}",
                f"  library entry: {_display_name(selected)}",
                "  verdict: unavailable",
                f"  reason: {reason}",
                "  candidate count: 0",
                "  repair ready: no",
                "  planned logical findings: 0",
                "  planned database field writes: 0",
                "  application: unavailable",
            )
        )
    )


def _display_name(selected: SelectedLibraryIdentityTarget) -> str:
    if selected.kind is LibraryIdentityTargetKind.ALBUM:
        assert selected.album is not None
        artist = _safe_text(selected.album.albumartist)
        title = _safe_text(selected.album.album)
    else:
        item = selected.items[0].item
        artist = _safe_text(item.artist)
        title = _safe_text(item.title)
    return f"{artist} - {title}"


def _safe_text(value: object) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else "unknown"


def _score(evaluations: tuple[IdentityCandidateEvaluation, ...], index: int) -> str:
    if len(evaluations) <= index:
        return "unavailable"
    return f"{evaluations[index].score.total:.2f}"


def _second_score(evaluations: tuple[IdentityCandidateEvaluation, ...]) -> str:
    if len(evaluations) < 2:
        return "unavailable"
    top = evaluations[0].score.total
    second = evaluations[1].score.total
    return f"{second:.2f} / {top - second:.2f}"


def _track_number(result: LibraryIdentityAuditResult, local_key: str) -> int:
    for index, track in enumerate(result.context.tracks, start=1):
        if track.local_key == local_key:
            return index
    return 0


def _safe_current(
    result: LibraryIdentityAuditResult, field: str, scope_key: str | None
) -> str:
    if scope_key is None:
        values = (
            result.context.current_release_mbids
            if field == "mb_albumid"
            else result.context.current_release_group_mbids
        )
        if not values:
            return "missing"
        if any(is_library_identity_marker(value) for value in values):
            return "mixed/missing"
        canonical = tuple(canonical_mbid(value) for value in values)
        if any(value is None for value in canonical):
            return "malformed"
        canonical_values = tuple(value for value in canonical if value is not None)
        return (
            canonical_values[0]
            if len(set(canonical_values)) == 1
            else "multiple/conflict"
        )
    track = next(track for track in result.context.tracks if track.local_key == scope_key)
    value = (
        track.current_recording_mbid
        if field == "mb_trackid"
        else track.current_release_track_mbid
    )
    if value is None:
        return "missing"
    if is_library_identity_marker(value):
        return "malformed"
    return canonical_mbid(value) or "malformed"


def _application_status(
    result: LibraryIdentityApplicationResult | None,
    apply_requested: bool,
    verdict: IdentityVerdict,
) -> str:
    if not apply_requested:
        return "disabled"
    if result is None:
        return "unavailable"
    if result.is_blocked:
        return "blocked"
    if verdict is IdentityVerdict.CONFIRMED:
        return "confirmed/no changes"
    return f"stored {len(result.applied_changes)} database field(s)"
