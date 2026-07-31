"""Privacy-safe importer identity audit rendering."""

from __future__ import annotations

from beets import ui

from .domain import IdentityAlbumContext, IdentityFieldFinding, IdentityVerdict, canonical_mbid
from .importer import (
    MISSING_ALBUM_ID_MARKER,
    MISSING_RELEASE_GROUP_ID_MARKER,
    ImportIdentityAuditResult,
)
from .importer_application import IdentityImportApplicationResult
from .importer_mapping import IdentityImportTargetPlan


def render_import_identity_audit(
    result: ImportIdentityAuditResult,
    target_plan: IdentityImportTargetPlan,
    application_result: IdentityImportApplicationResult | None = None,
) -> None:
    """Render audit evidence without paths, opaque keys, queries, or raw malformed values."""
    audit = result.audit
    evidence_evaluation = audit.selected_evaluation
    if evidence_evaluation is None and audit.evaluations:
        evidence_evaluation = audit.evaluations[0]
    lines = [
        "MusicBrainz identity audit",
        f"  match kind: {'album' if result.selected.kind.value == 'album' else 'singleton'}",
        f"  verdict: {audit.verdict.value}",
        f"  reason: {audit.reason}",
        f"  candidate count: {len(audit.evaluations)}",
    ]
    if audit.evaluations:
        lines.append(f"  top score: {audit.evaluations[0].score.total:.2f}")
    if len(audit.evaluations) > 1:
        top = audit.evaluations[0].score.total
        second = audit.evaluations[1].score.total
        lines.extend((f"  second score: {second:.2f}", f"  margin: {top - second:.2f}"))
    if evidence_evaluation is not None:
        assignment = evidence_evaluation.assignment
        lines.extend(
            (
                f"  assigned tracks: {len(assignment.assignments)}",
                f"  unmatched local tracks: {len(assignment.unmatched_local_keys)}",
                f"  unmatched candidate tracks: {len(assignment.unmatched_candidate_indices)}",
            )
        )
    else:
        lines.extend(
            (
                "  assigned tracks: 0",
                "  unmatched local tracks: 0",
                "  unmatched candidate tracks: 0",
            )
        )
    lines.extend(
        (
            f"  repair ready: {'yes' if audit.repair_ready else 'no'}",
            f"  planned identity changes: {len(target_plan.changes)}",
            f"  application: {_application_status(application_result)}",
        )
    )
    if audit.verdict is IdentityVerdict.AMBIGUOUS:
        for index, evaluation in enumerate(audit.evaluations[:2], start=1):
            lines.extend(
                (
                    f"  candidate {index} release: {evaluation.candidate.release_mbid}",
                    "  candidate "
                    f"{index} release group: {evaluation.candidate.release_group_mbid}",
                    f"  candidate {index} score: {evaluation.score.total:.2f}",
                    "  candidate "
                    f"{index} assigned: {len(evaluation.assignment.assignments)}",
                )
            )
    for finding in audit.field_findings:
        lines.extend(_finding_lines(finding, result.context))
    ui.print_("\n".join(lines))


def render_incomplete_import_identity_note() -> None:
    ui.print_(
        "Noqlen Meta: selected import has insufficient identity structure for "
        "MusicBrainz audit"
    )


def _finding_lines(
    finding: IdentityFieldFinding, context: IdentityAlbumContext
) -> tuple[str, ...]:
    if finding.scope_key is None:
        label = f"album {finding.field}"
        if finding.field == "mb_albumid":
            current = _safe_album_current(context.current_release_mbids)
        elif finding.field == "mb_releasegroupid":
            current = _safe_album_current(context.current_release_group_mbids)
        else:
            current = _safe_current(finding.current_value)
    else:
        track_number = 1
        tracks = getattr(context, "tracks", ())
        for index, track in enumerate(tracks, start=1):
            if track.local_key == finding.scope_key:
                track_number = index
                break
        label = f"track {track_number} {finding.field}"
        current = _safe_current(finding.current_value)
    return (
        f"  {label}",
        f"    status: {finding.status.value}",
        f"    current: {current}",
        f"    expected: {finding.expected_value}",
    )


def _safe_album_current(values: tuple[str, ...]) -> str:
    if not values:
        return "missing"
    markers = (MISSING_ALBUM_ID_MARKER, MISSING_RELEASE_GROUP_ID_MARKER)
    if any(value in markers for value in values):
        return "mixed/missing"
    canonical = tuple(canonical_mbid(value) for value in values)
    if any(value is None for value in canonical):
        return "malformed"
    canonical_values = tuple(value for value in canonical if value is not None)
    unique = set(canonical_values)
    if len(unique) == 1:
        return canonical_values[0]
    return "multiple/conflict"


def _safe_current(value: str | None) -> str:
    if value is None:
        return "missing"
    if MISSING_ALBUM_ID_MARKER in value or MISSING_RELEASE_GROUP_ID_MARKER in value:
        return "mixed/missing"
    canonical = canonical_mbid(value)
    return canonical if canonical is not None else "malformed"


def _application_status(result: IdentityImportApplicationResult | None) -> str:
    if result is None:
        return "disabled"
    if result.is_blocked:
        return "blocked"
    if result.is_confirmed_noop:
        return "confirmed/no changes"
    return f"applied {len(result.applied_changes)} changes"
