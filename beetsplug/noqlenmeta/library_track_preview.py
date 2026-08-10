"""Safe user-visible rendering for persistent Item track plans."""

from __future__ import annotations

from beets import ui
from beets.library import Item

from beetsplug.noqlenmeta.integration import _safe_preview_text
from beetsplug.noqlenmeta.library_track_application import LibraryTrackApplicationResult
from beetsplug.noqlenmeta.track_mapping import TrackTargetPlan


def render_library_track_plan(
    item: Item,
    plan: TrackTargetPlan,
    result: LibraryTrackApplicationResult | None = None,
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
    ui.print_("\n".join(lines))
