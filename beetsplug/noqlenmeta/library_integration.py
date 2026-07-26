"""Read-only integration helpers for persistent beets library Albums."""

from __future__ import annotations

from beets import ui
from beets.library import Album

from beetsplug.noqlenmeta.domain import (
    ExternalIdentifier,
    MetadataValue,
    ReleaseEnrichmentContext,
)
from beetsplug.noqlenmeta.integration import (
    _optional_text,
    _positive_release_id,
    _preview_value,
    _provider_display_name,
    _render_resolution_decision,
    _safe_preview_text,
    _text_tuple,
    _valid_year,
)
from beetsplug.noqlenmeta.library_mapping import (
    LibraryMappingBlocker,
    LibraryTargetChange,
    LibraryTargetPlan,
)

_DISCOGS_RELEASE_NAMESPACE = "discogs.release"


def context_from_library_album(album: Album) -> ReleaseEnrichmentContext | None:
    """Copy persistent Album identity into the provider-independent domain."""
    artist = _optional_text(album.albumartist)
    title = _optional_text(album.album)
    if artist is None or title is None:
        return None

    external_ids: tuple[ExternalIdentifier, ...] = ()
    release_id = _positive_release_id(album.discogs_albumid)
    if release_id is not None:
        external_ids = (ExternalIdentifier(_DISCOGS_RELEASE_NAMESPACE, release_id),)

    return ReleaseEnrichmentContext(
        album_artist=artist,
        album_title=title,
        year=_valid_year(album.year),
        barcode=_optional_text(album.barcode),
        catalog_number=_optional_text(album.catalognum),
        external_ids=external_ids,
    )


def current_values_from_library_album(album: Album) -> dict[str, MetadataValue]:
    """Copy persistent Album metadata into provider-independent canonical fields."""
    current_values: dict[str, MetadataValue] = {}

    genres = _text_tuple(album.genres)
    if genres:
        current_values["genres"] = genres

    singular_fields = {
        "styles": album.style,
        "labels": album.label,
        "catalog_numbers": album.catalognum,
        "barcodes": album.barcode,
    }
    for field, value in singular_fields.items():
        text = _optional_text(value)
        if text is not None:
            current_values[field] = (text,)

    country = _optional_text(album.country)
    if country is not None:
        current_values["country"] = country

    year = _valid_year(album.year)
    if year is not None:
        current_values["year"] = year

    return current_values


def render_library_target_plan(
    album: Album,
    plan: LibraryTargetPlan,
    *,
    position: int | None = None,
    total: int | None = None,
) -> None:
    """Print a safe, unconditionally read-only persistent Album preview."""
    source = plan.source
    artist = _safe_preview_text(album.albumartist) or "unknown artist"
    title = _safe_preview_text(album.album) or "unknown album"
    lines = ["Noqlen Meta / library target preview:", ""]
    if position is not None and total is not None:
        lines.append(f"  [{position}/{total}] {artist} - {title}")
    else:
        lines.append(f"  album: {artist} - {title}")
    lines.extend(
        (
            f"  planned changes: {len(source.changes)}",
            f"  losslessly mapped: {len(plan.mapped_changes)}",
            f"  mapping blockers: {len(plan.blocked_changes)}",
            f"  resolution review: {len(source.reviews)}",
            f"  unchanged: {len(source.kept)}",
            f"  skipped: {len(source.skipped)}",
            f"  mapping complete: {'yes' if plan.is_fully_mapped else 'no'}",
        )
    )
    for change in plan.mapped_changes:
        lines.extend(_render_library_change(change))
    for blocker in plan.blocked_changes:
        lines.extend(_render_library_blocker(blocker))
    for decision in (*source.reviews, *source.kept, *source.skipped):
        lines.extend(_render_resolution_decision(decision))
    ui.print_("\n".join(lines))


def _render_library_change(change: LibraryTargetChange) -> tuple[str, ...]:
    source = change.source
    lines = ["", f"  {_safe_preview_text(change.canonical_field)}", "    PROPOSE"]
    if source.before is not None:
        lines.append(f"    current: {_preview_value(source.before)}")
    lines.extend(
        (
            f"    target: {_safe_preview_text(change.target_field)}",
            f"    proposed: {_preview_value(change.target_value)}",
            f"    source: {_provider_display_name(source.source.provider)}",
            f"    confidence: {source.source.confidence:.2f}",
            f"    reason: {_safe_preview_text(source.reason)}",
        )
    )
    return tuple(lines)


def _render_library_blocker(blocker: LibraryMappingBlocker) -> tuple[str, ...]:
    target = blocker.target_field if blocker.target_field is not None else "unsupported"
    return (
        "",
        f"  {_safe_preview_text(blocker.source.field)}",
        "    BLOCKED",
        f"    target: {_safe_preview_text(target)}",
        f"    proposed: {_preview_value(blocker.source.after)}",
        f"    reason: {_safe_preview_text(blocker.reason)}",
    )
