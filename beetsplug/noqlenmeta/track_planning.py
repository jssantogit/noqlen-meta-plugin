"""Read-only planning for tracks already selected by the beets importer."""

from __future__ import annotations

from collections.abc import Sequence
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


@dataclass(frozen=True, slots=True)
class ImportTrackPlanningResult:
    """Integration bundle around the canonical resolver and ChangePlan results."""

    selected: SelectedImportTrack
    context: TrackEnrichmentContext
    from_scratch: bool
    candidate_count: int
    decisions: tuple[FieldDecision, ...]
    change_plan: ChangePlan


def selected_metadata_current_values(
    selected: SelectedImportTrack,
) -> dict[str, MetadataValue]:
    """Read the exact selected metadata surface normal beets would apply."""
    if selected.album_info is not None:
        data = selected.track_info.merge_with_album(selected.album_info)
    else:
        data = selected.track_info.item_data
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
    current.update(selected_metadata_current_values(selected))
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
    collected = tuple(candidates)
    decisions = resolve_metadata(
        effective_current_values_for_import_track(
            selected,
            from_scratch=from_scratch,
        ),
        collected,
        policy,
    )
    return ImportTrackPlanningResult(
        selected=selected,
        context=context,
        from_scratch=from_scratch,
        candidate_count=len(collected),
        decisions=decisions,
        change_plan=build_change_plan(decisions),
    )


def _current_values_surviving_beets_clear(item: Item) -> dict[str, MetadataValue]:
    current = current_values_from_library_item(item)
    return {
        field: value
        for field, value in current.items()
        if field not in Item._media_tag_fields
    }
