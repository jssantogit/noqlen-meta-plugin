"""Privacy-safe rendering for identity tag plans and results."""

from __future__ import annotations

from beets import ui

from .library import LibraryIdentityTargetKind
from .tag_application import IdentityTagApplicationResult
from .tag_mapping import IdentityTagFieldStatus, IdentityTagFilePlan


def render_identity_tag_plan(
    plan: IdentityTagFilePlan,
    result: IdentityTagApplicationResult | None,
    *,
    write_requested: bool,
    position: int,
    total: int,
) -> None:
    selected = plan.database.selected
    item = selected.item
    target_kind = (
        LibraryIdentityTargetKind.ALBUM.value
        if selected.album_id is not None
        else LibraryIdentityTargetKind.SINGLETON.value
    )
    if plan.blocked_reason is not None:
        file_status = "unavailable"
    elif not plan.changes:
        file_status = "synchronized"
    else:
        file_status = "changes planned"
    lines = [
        f"Noqlen MusicBrainz identity tags [{position}/{total}]",
        f"  target: {target_kind}",
        f"  library entry: {_safe_text(item.artist)} - {_safe_text(item.title)}",
        f"  format: {plan.file_snapshot.format_name if plan.file_snapshot else 'unavailable'}",
        f"  database identity: {'blocked' if plan.database.blocked_reason else 'ready'}",
        f"  file status: {file_status}",
        f"  planned tag changes: {len(plan.changes)}",
        f"  application: {_application_status(plan, result, write_requested)}",
        "  write capability: verified during temporary-copy round trip",
    ]
    expected = plan.database.expected
    if expected is not None:
        changes = {change.field: change for change in plan.changes}
        for field, value in expected.as_tuple():
            change = changes.get(field)
            status = change.status if change else IdentityTagFieldStatus.KEEP
            lines.extend((f"  {field}", f"    status: {status.value}", f"    expected: {value}"))
    ui.print_("\n".join(lines))


def _safe_text(value: object) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else "unknown"


def _application_status(
    plan: IdentityTagFilePlan,
    result: IdentityTagApplicationResult | None,
    write_requested: bool,
) -> str:
    if not write_requested:
        return "disabled"
    if result is None:
        return "unavailable"
    if result.is_blocked:
        return "blocked"
    if result.is_noop:
        return "synchronized/no changes"
    return f"replaced and verified ({len(result.applied_fields)} changed field(s))"
