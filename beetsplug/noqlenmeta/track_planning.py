"""Read-only planning for tracks already selected by the beets importer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from types import MappingProxyType

from beets.library import Item

from beetsplug.noqlenmeta.changeplan import ChangePlan, build_change_plan, compose_change_plans
from beetsplug.noqlenmeta.credit_resolution import CREDIT_FIELDS, resolve_credits
from beetsplug.noqlenmeta.domain import (
    MetadataCandidate,
    MetadataValue,
    TrackEnrichmentContext,
)
from beetsplug.noqlenmeta.evidence import CanonicalValue, MetadataEvidence
from beetsplug.noqlenmeta.recording_identity_resolution import resolve_recording_identity
from beetsplug.noqlenmeta.resolver import (
    FieldDecision,
    ResolutionPolicy,
    resolve_metadata,
)
from beetsplug.noqlenmeta.semantic_enrichment import (
    SemanticFieldOutcome,
    reconcile_semantic_outcomes,
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
    "genres",
    "moods",
    "lyrics_languages",
    "artist_countries",
    "artist_areas",
    "artist_languages",
)
_TRACK_SOURCE_FIELDS = (
    *_TRACK_CURRENT_FIELDS,
    "isrcs",
    "isrc",
    "iswcs",
    "mb_workids",
    "mb_workid",
    "work",
    "recording_date",
)


@dataclass(frozen=True, slots=True)
class TrackPlanningResult:
    """Provider-independent track resolution and target plan."""

    context: TrackEnrichmentContext
    candidate_count: int
    decisions: tuple[FieldDecision, ...]
    change_plan: ChangePlan
    target_plan: TrackTargetPlan
    semantic_outcomes: Mapping[str, SemanticFieldOutcome] = dataclass_field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "semantic_outcomes", MappingProxyType(dict(self.semantic_outcomes))
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
    target_plan: TrackTargetPlan
    semantic_outcomes: Mapping[str, SemanticFieldOutcome] = dataclass_field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "semantic_outcomes", MappingProxyType(dict(self.semantic_outcomes))
        )


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
    selected_data = _selected_metadata_application_data(selected)
    effective: dict[str, object] = {}
    for field in _TRACK_SOURCE_FIELDS:
        if field in selected_data:
            effective[field] = selected_data[field]
            continue
        if not from_scratch or field not in Item._media_tag_fields:
            value = selected.item.get(field, None, with_album=False)
            if value is not None:
                effective[field] = value
    return _current_track_values(effective.get)


def build_import_track_planning_result(
    selected: SelectedImportTrack,
    context: TrackEnrichmentContext,
    *,
    from_scratch: bool,
    candidates: Sequence[MetadataCandidate],
    evidence: Sequence[MetadataEvidence] = (),
    policy: ResolutionPolicy,
    semantic_outcomes: Mapping[str, SemanticFieldOutcome] | None = None,
) -> ImportTrackPlanningResult:
    """Resolve validated candidates through the shared canonical planning path."""
    result = build_track_planning_result(
        context,
        effective_current_values_for_import_track(
            selected,
            from_scratch=from_scratch,
        ),
        candidates=candidates,
        evidence=evidence,
        policy=policy,
        semantic_outcomes=semantic_outcomes,
    )
    return ImportTrackPlanningResult(
        selected=selected,
        context=context,
        from_scratch=from_scratch,
        candidate_count=result.candidate_count,
        decisions=result.decisions,
        change_plan=result.change_plan,
        target_plan=result.target_plan,
        semantic_outcomes=result.semantic_outcomes,
    )


def build_track_planning_result(
    context: TrackEnrichmentContext,
    current_values: Mapping[str, CanonicalValue],
    *,
    candidates: Sequence[MetadataCandidate],
    evidence: Sequence[MetadataEvidence] = (),
    policy: ResolutionPolicy,
    semantic_outcomes: Mapping[str, SemanticFieldOutcome] | None = None,
) -> TrackPlanningResult:
    """Resolve one track through the shared canonical planning path."""
    collected = tuple(candidates)
    decisions = resolve_metadata(current_values, collected, policy)
    change_plan = compose_change_plans(
        build_change_plan(decisions),
        build_change_plan(
            resolve_recording_identity(
                current_values,
                tuple(item for item in evidence if item.field not in CREDIT_FIELDS),
            )
        ),
        build_change_plan(
            resolve_credits(
                current_values,
                tuple(item for item in evidence if item.field in CREDIT_FIELDS),
            )
        ),
    )
    target_plan = map_change_plan_to_track_info(change_plan)
    outcomes = reconcile_semantic_outcomes(
        semantic_outcomes or {},
        change_plan,
        tuple(blocker.source.field for blocker in target_plan.blocked_changes),
    )
    return TrackPlanningResult(
        context=context,
        candidate_count=len(collected),
        decisions=decisions,
        change_plan=change_plan,
        target_plan=target_plan,
        semantic_outcomes=outcomes,
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
