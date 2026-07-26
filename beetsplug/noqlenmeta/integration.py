"""Read-only beets import integration helpers."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from beets import ui
from beets.autotag.hooks import AlbumInfo
from beets.importer.actions import Action

from beetsplug.noqlenmeta.beets_mapping import (
    BeetsMappingBlocker,
    BeetsTargetChange,
    BeetsTargetPlan,
)
from beetsplug.noqlenmeta.domain import (
    ExternalIdentifier,
    MetadataValue,
    ReleaseEnrichmentContext,
)
from beetsplug.noqlenmeta.providers.specs import provider_display_name
from beetsplug.noqlenmeta.resolver import (
    ResolutionAction,
    ResolutionPolicy,
    default_resolution_policy,
)

_DISCOGS_RELEASE_NAMESPACE = "discogs.release"
_DISCOGS_TOKEN_ENV = "NOQLENMETA_DISCOGS_TOKEN"


def resolve_discogs_token(configured_token: str) -> str | None:
    """Resolve a token without exposing it outside the provider boundary."""
    environment_token = os.environ.get(_DISCOGS_TOKEN_ENV, "").strip()
    if environment_token:
        return environment_token
    configured_token = configured_token.strip()
    return configured_token or None


def context_from_album_info(album_info: AlbumInfo) -> ReleaseEnrichmentContext | None:
    """Copy useful selected-release identity into the provider-independent domain."""
    artist = _optional_text(album_info.artist)
    title = _optional_text(album_info.album)
    if artist is None or title is None:
        return None

    external_ids: list[ExternalIdentifier] = []
    seen_ids: set[str] = set()
    discogs_ids = [album_info.discogs_albumid]
    data_source = _optional_text(album_info.data_source)
    if data_source is not None and data_source.casefold() == "discogs":
        discogs_ids.append(album_info.album_id)
    for value in discogs_ids:
        release_id = _positive_release_id(value)
        if release_id is not None and release_id not in seen_ids:
            seen_ids.add(release_id)
            external_ids.append(ExternalIdentifier(_DISCOGS_RELEASE_NAMESPACE, release_id))

    year = album_info.year
    if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
        year = None

    return ReleaseEnrichmentContext(
        album_artist=artist,
        album_title=title,
        year=year,
        barcode=_optional_text(album_info.barcode),
        catalog_number=_optional_text(album_info.catalognum),
        external_ids=tuple(external_ids),
    )


def current_values_from_album_info(album_info: AlbumInfo) -> dict[str, MetadataValue]:
    """Copy selected beets metadata into provider-independent canonical fields."""
    current_values: dict[str, MetadataValue] = {}

    genres = _text_tuple(album_info.genres)
    if genres:
        current_values["genres"] = genres

    singular_fields = {
        "styles": album_info.style,
        "labels": album_info.label,
        "catalog_numbers": album_info.catalognum,
        "barcodes": album_info.barcode,
        "media": album_info.media,
    }
    for field, value in singular_fields.items():
        text = _optional_text(value)
        if text is not None:
            current_values[field] = (text,)

    country = _optional_text(album_info.country)
    if country is not None:
        current_values["country"] = country

    year = album_info.year
    if isinstance(year, int) and not isinstance(year, bool) and 1 <= year <= 9999:
        current_values["year"] = year

    return current_values


def resolution_policy_from_settings(
    field_settings: Mapping[str, bool],
    provider_settings: Mapping[str, bool],
) -> ResolutionPolicy:
    """Apply simple user enablement settings to the advanced default policy."""
    baseline = default_resolution_policy()
    field_rules = {
        field: replace(rule, enabled=field_settings.get(field, rule.enabled))
        for field, rule in baseline.field_rules.items()
    }
    providers = {
        provider: provider_settings.get(provider, enabled)
        for provider, enabled in baseline.providers.items()
    }
    return ResolutionPolicy(field_rules, providers)


def eligible_album_info(task: object) -> AlbumInfo | None:
    """Return selected album metadata only for a real album APPLY choice."""
    if not getattr(task, "is_album", False):
        return None
    if getattr(task, "choice_flag", None) is not Action.APPLY:
        return None
    match = getattr(task, "match", None)
    album_info = getattr(match, "info", None)
    return album_info if isinstance(album_info, AlbumInfo) else None


def render_beets_target_plan(plan: BeetsTargetPlan) -> None:
    """Print a safe, target-aware description of the read-only mapping plan."""
    source = plan.source
    lines = [
        "Noqlen Meta / beets target plan:",
        "",
        f"  planned changes: {len(source.changes)}",
        f"  losslessly mapped: {len(plan.mapped_changes)}",
        f"  mapping blockers: {len(plan.blocked_changes)}",
        f"  resolution review: {len(source.reviews)}",
        f"  unchanged: {len(source.kept)}",
        f"  skipped: {len(source.skipped)}",
        f"  mapping complete: {'yes' if plan.is_fully_mapped else 'no'}",
    ]
    for change in plan.mapped_changes:
        lines.extend(_render_target_change(change))
    for blocker in plan.blocked_changes:
        lines.extend(_render_mapping_blocker(blocker))
    for decision in (*source.reviews, *source.kept, *source.skipped):
        lines.extend(
            ("", f"  {_safe_preview_text(decision.field)}", f"    {decision.action.name}")
        )
        if decision.current_value is not None:
            lines.append(f"    current: {_preview_value(decision.current_value)}")
        if decision.selected is not None:
            lines.extend(
                (
                    f"    candidate: {_preview_value(decision.selected.value)}",
                    f"    source: {_provider_display_name(decision.selected.provider)}",
                    f"    confidence: {decision.selected.confidence:.2f}",
                )
            )
        elif decision.action is ResolutionAction.REVIEW and decision.alternatives:
            providers = sorted(
                {_provider_display_name(item.provider) for item in decision.alternatives}
            )
            lines.append(
                f"    contenders: {len(decision.alternatives)} from {', '.join(providers)}"
            )
        lines.append(f"    reason: {_safe_preview_text(decision.reason)}")
    ui.print_("\n".join(lines))


def _render_target_change(change: BeetsTargetChange) -> tuple[str, ...]:
    source = change.source
    lines = ["", f"  {_safe_preview_text(change.canonical_field)}", "    PROPOSE"]
    if source.before is not None:
        lines.append(f"    current: {_preview_value(source.before)}")
    lines.extend(
        (
            f"    target: {_safe_preview_text(change.target_field)}",
            f"    target shape: {change.target_shape.value.replace('_', '-')}",
            f"    proposed: {_preview_value(change.target_value)}",
            f"    source: {_provider_display_name(source.source.provider)}",
            f"    confidence: {source.source.confidence:.2f}",
            f"    reason: {_safe_preview_text(source.reason)}",
        )
    )
    return tuple(lines)


def _render_mapping_blocker(blocker: BeetsMappingBlocker) -> tuple[str, ...]:
    target = blocker.target_field if blocker.target_field is not None else "unsupported"
    return (
        "",
        f"  {_safe_preview_text(blocker.source.field)}",
        "    BLOCKED",
        f"    target: {_safe_preview_text(target)}",
        f"    proposed: {_preview_value(blocker.source.after)}",
        f"    reason: {_safe_preview_text(blocker.reason)}",
    )


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _text_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        return ()
    return tuple(text for item in value if (text := _optional_text(item)) is not None)


def _positive_release_id(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    text = str(value).strip() if isinstance(value, (int, str)) else ""
    if not re.fullmatch(r"[0-9]+", text):
        return None
    try:
        return str(int(text)) if int(text) > 0 else None
    except ValueError:
        return None


def _safe_preview_text(value: object) -> str:
    printable = "".join(character if character.isprintable() else " " for character in str(value))
    return " ".join(printable.split())


def _provider_display_name(provider: object) -> str:
    safe_name = _safe_preview_text(provider)
    return provider_display_name(safe_name)


def _preview_value(value: MetadataValue) -> str:
    display: Any = ", ".join(value) if isinstance(value, tuple) else value
    return _safe_preview_text(display)
