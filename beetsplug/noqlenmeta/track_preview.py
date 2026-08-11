"""Safe user-visible rendering for importer track plans."""

from __future__ import annotations

from beets import ui

from beetsplug.noqlenmeta.domain import MetadataValue, TrackEnrichmentContext
from beetsplug.noqlenmeta.integration import _render_semantic_outcomes, _safe_preview_text
from beetsplug.noqlenmeta.providers.specs import provider_display_name
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction
from beetsplug.noqlenmeta.track_application import TrackApplicationResult
from beetsplug.noqlenmeta.track_mapping import TrackMappingBlocker, TrackTargetChange
from beetsplug.noqlenmeta.track_planning import ImportTrackPlanningResult


def render_import_track_plan(
    result: ImportTrackPlanningResult,
    application_result: TrackApplicationResult | None = None,
) -> None:
    """Print a deterministic plan without ever exposing lyric content."""
    plan = result.change_plan
    target_plan = result.target_plan
    lines = [
        "Noqlen Meta / track plan:",
        "",
        f"  track: {_track_heading(result.context)}",
        f"  from_scratch: {'yes' if result.from_scratch else 'no'}",
        *_application_lines(application_result),
        f"  provider candidates: {result.candidate_count}",
        f"  planned changes: {len(plan.changes)}",
        f"  mapped changes: {len(target_plan.mapped_changes)}",
        f"  mapping blockers: {len(target_plan.blocked_changes)}",
        f"  resolution review: {len(plan.reviews)}",
        f"  unchanged: {len(plan.kept)}",
        f"  skipped: {len(plan.skipped)}",
    ]
    if result.candidate_count == 0:
        lines.extend(("", "  no eligible track metadata candidates returned"))
    mapped_by_field = {
        change.canonical_field: change for change in target_plan.mapped_changes
    }
    blocked_by_field = {
        blocker.source.field: blocker for blocker in target_plan.blocked_changes
    }
    for decision in result.decisions:
        lines.extend(
            _render_decision(
                decision,
                mapped_by_field.get(decision.field),
                blocked_by_field.get(decision.field),
            )
        )
    lines.extend(_render_semantic_outcomes(result.semantic_outcomes))
    ui.print_("\n".join(lines))


def _application_lines(result: TrackApplicationResult | None) -> tuple[str, ...]:
    if result is None:
        return ("  application: disabled (track planning only)",)
    if result.is_blocked:
        status = "blocked"
    elif result.is_partial_application:
        status = "partial"
    elif result.has_applied_changes:
        status = "applied"
    else:
        status = "no changes"
    return (
        f"  application mode: {result.mode.value}",
        f"  applied changes: {len(result.applied_changes)}",
        f"  withheld resolution reviews: {result.resolution_review_count}",
        f"  withheld mapping blockers: {result.mapping_blocker_count}",
        f"  application status: {status}",
    )


def render_incomplete_track_note() -> None:
    """Explain a skipped selected mapping without exposing local file identity."""
    ui.print_("Noqlen Meta / track plan:\n\n  track skipped: incomplete selected identity")


def _track_heading(context: TrackEnrichmentContext) -> str:
    position = ".".join(
        str(value) if value is not None else "?"
        for value in (context.disc_number, context.track_number)
    )
    return _safe_preview_text(f"{position}  {context.artist} - {context.title}")


def _render_decision(
    decision: FieldDecision,
    mapped: TrackTargetChange | None,
    blocker: TrackMappingBlocker | None,
) -> tuple[str, ...]:
    lines = [
        "",
        f"  {_safe_preview_text(decision.field)}",
        f"    {decision.action.name}",
        f"    current: {_content_summary(decision.current_value)}",
    ]
    if decision.selected is not None:
        lines.extend(
            (
                f"    candidate: {_content_summary(decision.selected.value)}",
                "    source: "
                f"{_safe_preview_text(provider_display_name(decision.selected.provider))}",
                f"    confidence: {decision.selected.confidence:.2f}",
            )
        )
    elif decision.action is ResolutionAction.REVIEW and decision.alternatives:
        providers = sorted(
            {
                _safe_preview_text(provider_display_name(candidate.provider))
                for candidate in decision.alternatives
            }
        )
        lines.append(
            f"    contenders: {len(decision.alternatives)} from {', '.join(providers)}"
        )
    lines.append(f"    reason: {_safe_preview_text(decision.reason)}")
    if mapped is not None:
        lines.extend(
            (
                f"    target: TrackInfo.{_safe_preview_text(mapped.target_field)}",
                "    mapping: lossless",
            )
        )
    elif blocker is not None:
        lines.extend(
            (
                "    target: unavailable",
                f"    mapping blocker: {_safe_preview_text(blocker.reason)}",
            )
        )
    return tuple(lines)


def _content_summary(value: MetadataValue | None) -> str:
    if value is None:
        return "missing"
    if isinstance(value, str):
        return f"present ({len(value)} characters, {value.count(chr(10)) + 1} lines)"
    return "present"
