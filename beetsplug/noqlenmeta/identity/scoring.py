from __future__ import annotations

from dataclasses import dataclass

from .assignment import IdentityAssignmentResult, assign_identity_tracks, text_similarity
from .domain import IdentityAlbumContext, MusicBrainzReleaseIdentity

ALBUM_ARTIST_WEIGHT = 20.0
ALBUM_TITLE_WEIGHT = 20.0
TRACK_COUNT_WEIGHT = 15.0
TRACK_TITLES_WEIGHT = 25.0
TRACK_DURATIONS_WEIGHT = 10.0
TRACK_ORDER_WEIGHT = 10.0


@dataclass(frozen=True, slots=True)
class IdentityScoreBreakdown:
    album_artist: float
    album_title: float
    track_count: float
    track_titles: float
    track_durations: float
    track_order: float
    total: float


@dataclass(frozen=True, slots=True)
class IdentityCandidateEvaluation:
    candidate: MusicBrainzReleaseIdentity
    assignment: IdentityAssignmentResult
    score: IdentityScoreBreakdown


def evaluate_identity_candidate(
    context: IdentityAlbumContext, candidate: MusicBrainzReleaseIdentity
) -> IdentityCandidateEvaluation:
    assignment = assign_identity_tracks(context.tracks, candidate.tracks)
    by_key = {item.local_key: item for item in assignment.assignments}
    local_count = len(context.tracks)
    candidate_count = len(candidate.tracks)
    qualities: dict[str, tuple[float, float] | None] = {
        "album_artist": (
            ALBUM_ARTIST_WEIGHT,
            text_similarity(context.album_artist, candidate.album_artist) / 100.0,
        ),
        "album_title": (
            ALBUM_TITLE_WEIGHT,
            text_similarity(context.album, candidate.album) / 100.0,
        ),
        "track_count": (
            TRACK_COUNT_WEIGHT,
            min(local_count, candidate_count) / max(local_count, candidate_count),
        ),
        "track_titles": (
            TRACK_TITLES_WEIGHT,
            sum(
                by_key[track.local_key].title_score
                for track in context.tracks
                if track.local_key in by_key
            )
            / (100.0 * local_count),
        ),
        "track_durations": None,
        "track_order": None,
    }
    duration_scores = tuple(
        item.duration_score
        for item in assignment.assignments
        if item.duration_score is not None
    )
    if duration_scores:
        duration_quality = sum(duration_scores) / (100.0 * len(duration_scores))
        qualities["track_durations"] = (TRACK_DURATIONS_WEIGHT, duration_quality)
    positioned_tracks = [
        track
        for track in context.tracks
        if track.index is not None
        or (track.medium is not None and track.medium_index is not None)
    ]
    if positioned_tracks:
        order_quality = sum(
            by_key[track.local_key].position_score
            for track in positioned_tracks
            if track.local_key in by_key
        ) / (100.0 * len(positioned_tracks))
        qualities["track_order"] = (TRACK_ORDER_WEIGHT, order_quality)
    available_weight = sum(value[0] for value in qualities.values() if value is not None)
    components = {
        field: 0.0 if value is None else 100.0 * value[0] * value[1] / available_weight
        for field, value in qualities.items()
    }
    total = max(0.0, min(100.0, sum(components.values())))
    return IdentityCandidateEvaluation(
        candidate,
        assignment,
        IdentityScoreBreakdown(total=total, **components),
    )


def rank_identity_candidates(
    context: IdentityAlbumContext, candidates: tuple[MusicBrainzReleaseIdentity, ...]
) -> tuple[IdentityCandidateEvaluation, ...]:
    evaluations = [evaluate_identity_candidate(context, candidate) for candidate in candidates]
    return tuple(
        sorted(
            evaluations,
            key=lambda item: (
                -item.score.total,
                -len(item.assignment.assignments),
                item.candidate.release_mbid,
            ),
        )
    )
