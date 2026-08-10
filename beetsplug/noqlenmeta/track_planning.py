"""Read-only planning for tracks already selected by the beets importer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from beets.library import Item

from beetsplug.noqlenmeta.changeplan import ChangePlan, build_change_plan
from beetsplug.noqlenmeta.domain import (
    MetadataCandidate,
    MetadataValue,
    TrackEnrichmentContext,
)
from beetsplug.noqlenmeta.resolver import (
    FieldDecision,
    ResolutionPolicy,
    resolve_metadata,
)
from beetsplug.noqlenmeta.track_integration import (
    SelectedImportTrack,
    _current_track_values,
    current_values_from_library_item,
)
from beetsplug.noqlenmeta.track_mapping import (
    TrackTargetPlan,
    map_change_plan_to_track_info,
)

_TRACK_CURRENT_FIELDS = (
    "lyrics",
    "synced_lyrics",
    "bpm",
    "moods",
    "lyrics_languages",
    "artist_countries",
    "artist_areas",
    "artist_languages",
)


@dataclass(frozen=True, slots=True)
class TrackPlanningResult:
    """Provider-independent track resolution and target plan."""

    context: TrackEnrichmentContext
    candidate_count: int
    decisions: tuple[FieldDecision, ...]
    change_plan: ChangePlan
    target_plan: TrackTargetPlan


@dataclass(frozen=True, slots=True)
class ImportTrackPlanningResult:
    """Integration bundle around the canonical resolver and ChangePlan results."""

    selected: SelectedImportTrack
    context: TrackEnrichmentContext
    from_scratch: bool
    candidate_count: int
    decisions: tuple[FieldDecision, ...]
    change_plan: ChangePlan
    target_plan: TrackTargetPlan


def selected_metadata_current_values(
    selected: SelectedImportTrack,
) -> dict[str, MetadataValue]:
    """Read canonical non-empty values from beets' selected application mapping."""
    data = _selected_metadata_application_data(selected)
    return _current_track_values(data.get)


def effective_current_values_for_import_track(
    selected: SelectedImportTrack,
    *,
    from_scratch: bool,
) -> dict[str, MetadataValue]:
    """Predict canonical Item values immediately after normal beets application."""
    if from_scratch:
        current = _current_values_surviving_beets_clear(selected.item)
    else:
        current = current_values_from_library_item(selected.item)

    selected_data = _selected_metadata_application_data(selected)
    selected_values = _current_track_values(selected_data.get)
    for field in _TRACK_CURRENT_FIELDS:
        if field not in selected_data:
            continue
        if field in selected_values:
            current[field] = selected_values[field]
        else:
            current.pop(field, None)
    return current


def build_import_track_planning_result(
    selected: SelectedImportTrack,
    context: TrackEnrichmentContext,
    *,
    from_scratch: bool,
    candidates: Sequence[MetadataCandidate],
    policy: ResolutionPolicy,
) -> ImportTrackPlanningResult:
    """Resolve validated candidates through the shared canonical planning path."""
    result = build_track_planning_result(
        context,
        effective_current_values_for_import_track(
            selected,
            from_scratch=from_scratch,
        ),
        candidates=candidates,
        policy=policy,
    )
    return ImportTrackPlanningResult(
        selected=selected,
        context=context,
        from_scratch=from_scratch,
        candidate_count=result.candidate_count,
        decisions=result.decisions,
        change_plan=result.change_plan,
        target_plan=result.target_plan,
    )


def build_track_planning_result(
    context: TrackEnrichmentContext,
    current_values: Mapping[str, MetadataValue],
    *,
    candidates: Sequence[MetadataCandidate],
    policy: ResolutionPolicy,
) -> TrackPlanningResult:
    """Resolve one track through the shared canonical planning path."""
    collected = tuple(candidates)
    decisions = resolve_metadata(current_values, collected, policy)
    change_plan = build_change_plan(decisions)
    return TrackPlanningResult(
        context=context,
        candidate_count=len(collected),
        decisions=decisions,
        change_plan=change_plan,
        target_plan=map_change_plan_to_track_info(change_plan),
    )


def _current_values_surviving_beets_clear(item: Item) -> dict[str, MetadataValue]:
    current = current_values_from_library_item(item)
    return {
        field: value
        for field, value in current.items()
        if field not in Item._media_tag_fields
    }


def _selected_metadata_application_data(
    selected: SelectedImportTrack,
) -> Mapping[str, object]:
    if selected.album_info is not None:
        return selected.track_info.merge_with_album(selected.album_info)
    return selected.track_info.item_data
