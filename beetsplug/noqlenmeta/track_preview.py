"""Safe user-visible rendering for read-only importer track plans."""

from __future__ import annotations

from beets import ui

from beetsplug.noqlenmeta.domain import MetadataValue, TrackEnrichmentContext
from beetsplug.noqlenmeta.integration import _safe_preview_text
from beetsplug.noqlenmeta.providers.specs import provider_display_name
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction
from beetsplug.noqlenmeta.track_planning import ImportTrackPlanningResult


def render_import_track_plan(result: ImportTrackPlanningResult) -> None:
    """Print a deterministic plan without ever exposing lyric content."""
    plan = result.change_plan
    lines = [
        "Noqlen Meta / track plan:",
        "",
        f"  track: {_track_heading(result.context)}",
        f"  from_scratch: {'yes' if result.from_scratch else 'no'}",
        "  application: disabled (track planning only)",
        f"  provider candidates: {result.candidate_count}",
        f"  planned changes: {len(plan.changes)}",
        f"  resolution review: {len(plan.reviews)}",
        f"  unchanged: {len(plan.kept)}",
        f"  skipped: {len(plan.skipped)}",
    ]
    if result.candidate_count == 0:
        lines.extend(("", "  no eligible track metadata candidates returned"))
    for decision in result.decisions:
        lines.extend(_render_decision(decision))
    ui.print_("\n".join(lines))


def render_incomplete_track_note() -> None:
    """Explain a skipped selected mapping without exposing local file identity."""
    ui.print_("Noqlen Meta / track plan:\n\n  track skipped: incomplete selected identity")


def _track_heading(context: TrackEnrichmentContext) -> str:
    position = ".".join(
        str(value) if value is not None else "?"
        for value in (context.disc_number, context.track_number)
    )
    return _safe_preview_text(f"{position}  {context.artist} - {context.title}")


def _render_decision(decision: FieldDecision) -> tuple[str, ...]:
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
    return tuple(lines)


def _content_summary(value: MetadataValue | None) -> str:
    if value is None:
        return "missing"
    if isinstance(value, str):
        return f"present ({len(value)} characters, {value.count(chr(10)) + 1} lines)"
    return "present"
