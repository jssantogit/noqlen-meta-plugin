"""Safe user-visible rendering for persistent Item track plans."""

from __future__ import annotations

from collections.abc import Mapping

from beets import ui
from beets.library import Item

from beetsplug.noqlenmeta.integration import _render_semantic_outcomes, _safe_preview_text
from beetsplug.noqlenmeta.library_track_application import LibraryTrackApplicationResult
from beetsplug.noqlenmeta.semantic_enrichment import SemanticFieldOutcome
from beetsplug.noqlenmeta.track_mapping import TrackTargetPlan


def render_library_track_plan(
    item: Item,
    plan: TrackTargetPlan,
    result: LibraryTrackApplicationResult | None = None,
    semantic_outcomes: Mapping[str, SemanticFieldOutcome] | None = None,
) -> None:
    """Render Item database effects without paths or metadata contents."""
    identity = _safe_preview_text(f"{item.artist} - {item.title}")
    status = "planning only"
    if result is not None:
        if result.is_blocked:
            status = "blocked"
        elif result.is_partial_application:
            status = "partial"
        elif result.stored:
            status = "applied"
        else:
            status = "no changes"
    lines = [
        "Noqlen Meta / library track plan:",
        "",
        f"  track: {identity}",
        f"  database target: Item {item.id}",
        f"  mapped changes: {len(plan.mapped_changes)}",
        f"  mapping blockers: {len(plan.blocked_changes)}",
        f"  resolution review: {len(plan.source.reviews)}",
        f"  application: {status}",
    ]
    lines.extend(
        f"  target: Item.{_safe_preview_text(change.target_field)}"
        for change in plan.mapped_changes
    )
    for change in plan.mapped_changes:
        if not change.source.evidence:
            continue
        selected = change.source.evidence[0]
        detail = (
            f"  evidence: {_safe_preview_text(selected.provider)}; "
            f"entity={_safe_preview_text(selected.subject.entity.value)}; "
            f"scope={_safe_preview_text(selected.acquisition_scope.value)}; "
            f"method={_safe_preview_text(selected.provenance.method.value)}"
        )
        if selected.confidence is not None:
            detail += f"; confidence={selected.confidence:.2f}"
        if len(change.source.evidence) > 1:
            detail += f"; corroboration={len(change.source.evidence) - 1}"
        lines.append(detail)
    lines.extend(_render_semantic_outcomes(semantic_outcomes or {}))
    ui.print_("\n".join(lines))
