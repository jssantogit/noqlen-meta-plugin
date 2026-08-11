"""Read-only beets import integration helpers."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import TYPE_CHECKING, Any

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
    canonical_uuid,
)
from beetsplug.noqlenmeta.providers.specs import provider_display_name
from beetsplug.noqlenmeta.resolver import (
    FieldDecision,
    FieldRule,
    ResolutionAction,
    ResolutionPolicy,
    default_resolution_policy,
)
from beetsplug.noqlenmeta.semantic_enrichment import SemanticFieldOutcome

if TYPE_CHECKING:
    from beetsplug.noqlenmeta.beets_application import BeetsApplicationResult

_DISCOGS_RELEASE_NAMESPACE = "discogs.release"
_MUSICBRAINZ_RELEASE_NAMESPACE = "musicbrainz.release"
_DISCOGS_TOKEN_ENV = "NOQLENMETA_DISCOGS_TOKEN"


class ResolutionSettingsError(ValueError):
    """An invalid user-facing resolution policy override."""


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
    seen_ids: set[tuple[str, str]] = set()
    discogs_ids = [album_info.discogs_albumid]
    data_source = _optional_text(album_info.data_source)
    if data_source is not None and data_source.casefold() == "discogs":
        discogs_ids.append(album_info.album_id)
    for value in discogs_ids:
        release_id = _positive_release_id(value)
        if release_id is not None:
            key = (_DISCOGS_RELEASE_NAMESPACE, release_id)
        else:
            continue
        if key not in seen_ids:
            seen_ids.add(key)
            external_ids.append(ExternalIdentifier(_DISCOGS_RELEASE_NAMESPACE, release_id))

    musicbrainz_ids = [getattr(album_info, "mb_albumid", None)]
    if data_source is not None and data_source.casefold() == "musicbrainz":
        musicbrainz_ids.append(album_info.album_id)
    for value in musicbrainz_ids:
        release_id = canonical_uuid(value)
        if release_id is not None:
            key = (_MUSICBRAINZ_RELEASE_NAMESPACE, release_id)
        else:
            continue
        if key not in seen_ids:
            seen_ids.add(key)
            external_ids.append(ExternalIdentifier(_MUSICBRAINZ_RELEASE_NAMESPACE, release_id))

    return ReleaseEnrichmentContext(
        album_artist=artist,
        album_title=title,
        year=_valid_year(album_info.year),
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

    styles = _text_tuple(album_info.get("styles"))
    if not styles:
        legacy_style = _optional_text(album_info.style)
        if legacy_style is not None:
            styles = (legacy_style,)
    if styles:
        current_values["styles"] = styles

    for field in ("artist_countries", "artist_areas", "artist_languages"):
        values = _text_tuple(album_info.get(field))
        if values:
            current_values[field] = values

    singular_fields = {
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

    year = _valid_year(album_info.year)
    if year is not None:
        current_values["year"] = year

    return current_values


def resolution_policy_from_settings(
    field_settings: Mapping[str, bool],
    provider_settings: Mapping[str, bool],
    *,
    authority_settings: Mapping[str, Sequence[str]] | None = None,
    min_confidence_settings: Mapping[str, float] | None = None,
    preserve_existing_settings: Mapping[str, bool] | None = None,
) -> ResolutionPolicy:
    """Overlay user settings on the built-in resolution policy."""
    baseline = default_resolution_policy()
    advanced_settings: tuple[tuple[str, Mapping[str, object] | None], ...] = (
        ("authority", authority_settings),
        ("min_confidence", min_confidence_settings),
        ("preserve_existing", preserve_existing_settings),
    )
    normalized: dict[str, dict[str, object]] = {}
    for section, settings in advanced_settings:
        if settings is None:
            normalized[section] = {}
            continue
        if not isinstance(settings, Mapping):
            raise ResolutionSettingsError(f"resolution.{section} must be a mapping")

        section_values: dict[str, object] = {}
        for configured_field, value in settings.items():
            if not isinstance(configured_field, str) or not configured_field.strip():
                raise ResolutionSettingsError(
                    f"resolution.{section} field names must be non-empty strings"
                )
            field = configured_field.strip().lower()
            if field not in baseline.field_rules:
                raise ResolutionSettingsError(
                    f"resolution.{section} has unknown field {configured_field!r}"
                )
            if field in section_values:
                raise ResolutionSettingsError(
                    f"resolution.{section} field names must be unique after normalization"
                )
            section_values[field] = value
        normalized[section] = section_values

    field_rules: dict[str, FieldRule] = {}
    for field, rule in baseline.field_rules.items():
        configured_rule = replace(rule, enabled=field_settings.get(field, rule.enabled))
        changes: dict[str, object] = {}
        if field in normalized["authority"]:
            authority = normalized["authority"][field]
            if isinstance(authority, (str, bytes)) or not isinstance(authority, Sequence):
                raise ResolutionSettingsError(
                    f"resolution.authority.{field} must be a sequence of provider names"
                )
            if not authority:
                raise ResolutionSettingsError(
                    f"resolution.authority.{field} must not be empty; use fields.{field}: false"
                )
            changes["authority"] = tuple(authority)
        if field in normalized["min_confidence"]:
            changes["min_confidence"] = normalized["min_confidence"][field]
        if field in normalized["preserve_existing"]:
            changes["preserve_existing"] = normalized["preserve_existing"][field]

        try:
            configured_rule = replace(configured_rule, **changes)
        except (TypeError, ValueError) as error:
            raise ResolutionSettingsError(f"resolution override for {field!r}: {error}") from None

        if field in normalized["authority"]:
            unknown_providers = tuple(
                provider
                for provider in configured_rule.authority
                if provider not in baseline.providers
            )
            if unknown_providers:
                raise ResolutionSettingsError(
                    f"resolution.authority.{field} has unknown provider "
                    f"{unknown_providers[0]!r}"
                )
        field_rules[field] = configured_rule

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


def render_beets_target_plan(
    plan: BeetsTargetPlan,
    application_result: BeetsApplicationResult | None = None,
    semantic_outcomes: Mapping[str, SemanticFieldOutcome] | None = None,
) -> None:
    """Print a safe target plan and truthful selected-release application state."""
    source = plan.source
    if application_result is None:
        application_status = "disabled (preview only)"
    elif application_result.is_blocked:
        application_status = "blocked"
    elif application_result.is_partial_application:
        application_status = (
            "partially applied to selected release "
            f"({len(application_result.applied_changes)} fields)"
        )
    elif application_result.has_applied_changes:
        application_status = (
            "applied to selected release "
            f"({len(application_result.applied_changes)} fields)"
        )
    elif application_result.has_withheld_fields:
        application_status = "no eligible changes applied"
    else:
        application_status = "no changes"
    lines = [
        "Noqlen Meta / beets target plan:",
        "",
    ]
    if application_result is not None:
        lines.append(f"  application mode: {application_result.mode.value}")
    lines.extend(
        (
            f"  application: {application_status}",
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
        lines.extend(_render_target_change(change))
    for blocker in plan.blocked_changes:
        lines.extend(_render_mapping_blocker(blocker))
    for decision in (*source.reviews, *source.kept, *source.skipped):
        lines.extend(_render_resolution_decision(decision))
    lines.extend(_render_semantic_outcomes(semantic_outcomes or {}))
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


def _valid_year(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 9999:
        return value
    return None


def _safe_preview_text(value: object) -> str:
    printable = "".join(character if character.isprintable() else " " for character in str(value))
    return " ".join(printable.split())


def _provider_display_name(provider: object) -> str:
    safe_name = _safe_preview_text(provider)
    return provider_display_name(safe_name)


def _render_semantic_outcomes(
    outcomes: Mapping[str, SemanticFieldOutcome],
) -> tuple[str, ...]:
    if not outcomes:
        return ()
    lines = ["", "  semantic outcomes:"]
    lines.extend(
        f"    {_safe_preview_text(field)}: {outcome.status.value}; "
        f"{_safe_preview_text(outcome.reason)}"
        for field, outcome in sorted(outcomes.items())
    )
    return tuple(lines)


def _render_resolution_decision(decision: FieldDecision) -> tuple[str, ...]:
    lines = [
        "",
        f"  {_safe_preview_text(decision.field)}",
        f"    {decision.action.name}",
    ]
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
    return tuple(lines)


def _preview_value(value: MetadataValue) -> str:
    display: Any = ", ".join(value) if isinstance(value, tuple) else value
    return _safe_preview_text(display)
