"""Read-only integration helpers for persistent beets library Albums."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from beets import ui
from beets.library import Album

from beetsplug.noqlenmeta.domain import (
    ExternalIdentifier,
    MetadataValue,
    ReleaseEnrichmentContext,
    canonical_uuid,
)
from beetsplug.noqlenmeta.integration import (
    _add_release_catalog_current,
    _optional_text,
    _positive_release_id,
    _preview_value,
    _provider_display_name,
    _render_resolution_decision,
    _render_semantic_outcomes,
    _safe_preview_text,
    _text_tuple,
    _valid_year,
)
from beetsplug.noqlenmeta.library_mapping import (
    LibraryMappingBlocker,
    LibraryTargetChange,
    LibraryTargetPlan,
)
from beetsplug.noqlenmeta.semantic_enrichment import SemanticFieldOutcome

if TYPE_CHECKING:
    from beetsplug.noqlenmeta.library_application import LibraryApplicationResult

_DISCOGS_RELEASE_NAMESPACE = "discogs.release"
_MUSICBRAINZ_RELEASE_NAMESPACE = "musicbrainz.release"
_MUSICBRAINZ_RELEASE_GROUP_NAMESPACE = "musicbrainz.release_group"


def context_from_library_album(album: Album) -> ReleaseEnrichmentContext | None:
    """Copy persistent Album identity into the provider-independent domain."""
    artist = _optional_text(album.albumartist)
    title = _optional_text(album.album)
    if artist is None or title is None:
        return None

    external_ids: list[ExternalIdentifier] = []
    discogs_release_id = _positive_release_id(album.discogs_albumid)
    if discogs_release_id is not None:
        external_ids.append(
            ExternalIdentifier(_DISCOGS_RELEASE_NAMESPACE, discogs_release_id)
        )
    musicbrainz_release_id = canonical_uuid(album.mb_albumid)
    if musicbrainz_release_id is not None:
        external_ids.append(
            ExternalIdentifier(_MUSICBRAINZ_RELEASE_NAMESPACE, musicbrainz_release_id)
        )
    release_group_id = canonical_uuid(album.mb_releasegroupid)
    if release_group_id is not None:
        external_ids.append(
            ExternalIdentifier(_MUSICBRAINZ_RELEASE_GROUP_NAMESPACE, release_group_id)
        )

    return ReleaseEnrichmentContext(
        album_artist=artist,
        album_title=title,
        year=_valid_year(album.year),
        barcode=_optional_text(album.barcode),
        catalog_number=_optional_text(album.catalognum),
        external_ids=tuple(external_ids),
    )


def current_values_from_library_album(album: Album) -> dict[str, MetadataValue]:
    """Copy persistent Album metadata into provider-independent canonical fields."""
    current_values: dict[str, MetadataValue] = {}

    genres = _text_tuple(album.genres)
    if genres:
        current_values["genres"] = genres

    styles = _text_tuple(album.get("styles", None))
    if not styles:
        legacy_style = _optional_text(album.style)
        if legacy_style is not None:
            styles = (legacy_style,)
    if styles:
        current_values["styles"] = styles

    for field in ("artist_countries", "artist_areas", "artist_languages"):
        values = _text_tuple(album.get(field, None))
        if values:
            current_values[field] = values

    singular_fields = {
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

    _add_release_catalog_current(current_values, lambda field: album.get(field, None))

    return current_values


def render_library_target_plan(
    album: Album,
    plan: LibraryTargetPlan,
    application_result: LibraryApplicationResult | None = None,
    *,
    position: int | None = None,
    total: int | None = None,
    semantic_outcomes: Mapping[str, SemanticFieldOutcome] | None = None,
) -> None:
    """Print a safe persistent Album plan and truthful application state."""
    source = plan.source
    artist = _safe_preview_text(album.albumartist) or "unknown artist"
    title = _safe_preview_text(album.album) or "unknown album"
    lines = ["Noqlen Meta / library target preview:", ""]
    if position is not None and total is not None:
        lines.append(f"  [{position}/{total}] {artist} - {title}")
    else:
        lines.append(f"  album: {artist} - {title}")
    if application_result is None:
        application_status = "disabled (preview only)"
    elif application_result.is_blocked:
        application_status = "blocked"
    elif application_result.is_partial_application:
        application_status = (
            "partially stored in library database "
            f"({len(application_result.applied_changes)} fields)"
        )
    elif application_result.stored:
        application_status = (
            "stored in library database "
            f"({len(application_result.applied_changes)} fields)"
        )
    elif application_result.has_withheld_fields:
        application_status = "no eligible changes stored"
    else:
        application_status = "no changes"
    application_lines = []
    if application_result is not None:
        application_lines.append(f"  application mode: {application_result.mode.value}")
    application_lines.append(f"  application: {application_status}")
    lines.extend(
        (
            *application_lines,
            "  file tags: unchanged",
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
    lines.extend(_render_semantic_outcomes(semantic_outcomes or {}))
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
    if source.evidence:
        selected = source.evidence[0]
        lines.append(
            "    evidence: "
            f"{_safe_preview_text(selected.provider)}; "
            f"entity={_safe_preview_text(selected.subject.entity.value)}; "
            f"scope={_safe_preview_text(selected.acquisition_scope.value)}; "
            f"method={_safe_preview_text(selected.provenance.method.value)}"
        )
        if selected.confidence is not None:
            lines.append(f"    evidence confidence: {selected.confidence:.2f}")
        if len(source.evidence) > 1:
            lines.append(f"    corroboration: {len(source.evidence) - 1} additional source(s)")
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
