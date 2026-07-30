from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from .domain import IdentityTrackContext, MusicBrainzTrackIdentity

TITLE_WEIGHT = 60.0
DURATION_WEIGHT = 25.0
ARTIST_WEIGHT = 10.0
POSITION_WEIGHT = 5.0


@dataclass(frozen=True, slots=True)
class IdentityTrackAssignment:
    local_key: str
    candidate_index: int
    pair_score: float
    title_score: float
    duration_score: float | None
    artist_score: float | None
    position_score: float


@dataclass(frozen=True, slots=True)
class IdentityAssignmentResult:
    assignments: tuple[IdentityTrackAssignment, ...]
    unmatched_local_keys: tuple[str, ...]
    unmatched_candidate_indices: tuple[int, ...]
    ambiguous: bool = False


def normalize_identity_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    characters = [character if character.isalnum() else " " for character in normalized]
    return " ".join("".join(characters).split())


def text_similarity(left: str, right: str) -> float:
    return 100.0 * SequenceMatcher(
        None, normalize_identity_text(left), normalize_identity_text(right), autojunk=False
    ).ratio()


def duration_similarity(left: float, right: float) -> float:
    difference = abs(left - right)
    if difference <= 2:
        return 100.0
    if difference <= 4:
        return 100.0 - (difference - 2) * 5.0
    if difference <= 10:
        return 90.0 - (difference - 4) * 5.0
    if difference <= 30:
        return 60.0 - (difference - 10) * 3.0
    return 0.0


def _position_similarity(
    local: IdentityTrackContext, candidate: MusicBrainzTrackIdentity
) -> tuple[float, bool]:
    if local.medium is not None and local.medium_index is not None:
        if local.medium == candidate.medium and local.medium_index == candidate.medium_index:
            return 100.0, True
        if local.index is not None and local.index == candidate.index:
            return 50.0, True
        return 0.0, True
    if local.index is not None:
        return (50.0 if local.index == candidate.index else 0.0), True
    return 0.0, False


def score_track_pair(
    local: IdentityTrackContext, candidate: MusicBrainzTrackIdentity
) -> IdentityTrackAssignment:
    title = text_similarity(local.title, candidate.title)
    components = [(TITLE_WEIGHT, title)]
    duration = None
    if local.length is not None and candidate.length is not None:
        duration = duration_similarity(local.length, candidate.length)
        components.append((DURATION_WEIGHT, duration))
    artist = None
    if local.artist and candidate.artist:
        artist = text_similarity(local.artist, candidate.artist)
        components.append((ARTIST_WEIGHT, artist))
    position, position_available = _position_similarity(local, candidate)
    if position_available:
        components.append((POSITION_WEIGHT, position))
    available_weight = sum(weight for weight, _ in components)
    pair_score = sum(weight * score for weight, score in components) / available_weight
    return IdentityTrackAssignment(
        local_key=local.local_key,
        candidate_index=-1,
        pair_score=max(0.0, min(100.0, pair_score)),
        title_score=title,
        duration_score=duration,
        artist_score=artist,
        position_score=position,
    )


def assign_identity_tracks(
    local_tracks: tuple[IdentityTrackContext, ...],
    candidate_tracks: tuple[MusicBrainzTrackIdentity, ...],
) -> IdentityAssignmentResult:
    if not local_tracks or not candidate_tracks:
        return IdentityAssignmentResult(
            (),
            tuple(track.local_key for track in local_tracks),
            tuple(range(len(candidate_tracks))),
        )
    pair_rows = [
        [score_track_pair(local, candidate) for candidate in candidate_tracks]
        for local in local_tracks
    ]
    costs = [[100.0 - pair.pair_score for pair in row] for row in pair_rows]
    pairs = _rectangular_minimum_assignment(costs)
    ambiguous = _has_equal_cost_alternative(costs, pairs)
    assignments = tuple(
        IdentityTrackAssignment(
            local_key=local_tracks[local_index].local_key,
            candidate_index=candidate_index,
            pair_score=pair_rows[local_index][candidate_index].pair_score,
            title_score=pair_rows[local_index][candidate_index].title_score,
            duration_score=pair_rows[local_index][candidate_index].duration_score,
            artist_score=pair_rows[local_index][candidate_index].artist_score,
            position_score=pair_rows[local_index][candidate_index].position_score,
        )
        for local_index, candidate_index in sorted(pairs)
    )
    assigned_local = {local_index for local_index, _ in pairs}
    assigned_candidate = {candidate_index for _, candidate_index in pairs}
    return IdentityAssignmentResult(
        assignments=assignments,
        unmatched_local_keys=tuple(
            track.local_key
            for index, track in enumerate(local_tracks)
            if index not in assigned_local
        ),
        unmatched_candidate_indices=tuple(
            index for index in range(len(candidate_tracks)) if index not in assigned_candidate
        ),
        ambiguous=ambiguous,
    )


def _has_equal_cost_alternative(
    costs: list[list[float]], pairs: list[tuple[int, int]]
) -> bool:
    baseline = sum(costs[row][column] for row, column in pairs)
    for excluded_row, excluded_column in pairs:
        alternative_costs = [row.copy() for row in costs]
        alternative_costs[excluded_row][excluded_column] = 1_000_000.0
        alternative = _rectangular_minimum_assignment(alternative_costs)
        alternative_total = sum(costs[row][column] for row, column in alternative)
        if all(
            (row, column) != (excluded_row, excluded_column)
            for row, column in alternative
        ) and abs(alternative_total - baseline) <= 1e-9:
            return True
    return False


def _rectangular_minimum_assignment(costs: list[list[float]]) -> list[tuple[int, int]]:
    row_count = len(costs)
    column_count = len(costs[0])
    transposed = row_count > column_count
    matrix = (
        [[costs[row][column] for row in range(row_count)] for column in range(column_count)]
        if transposed
        else costs
    )
    rows = len(matrix)
    columns = len(matrix[0])
    u = [0.0] * (rows + 1)
    v = [0.0] * (columns + 1)
    matching = [0] * (columns + 1)
    previous = [0] * (columns + 1)
    for row in range(1, rows + 1):
        matching[0] = row
        column = 0
        minimums = [float("inf")] * (columns + 1)
        used = [False] * (columns + 1)
        while True:
            used[column] = True
            current_row = matching[column]
            delta = float("inf")
            next_column = 0
            for candidate_column in range(1, columns + 1):
                if used[candidate_column]:
                    continue
                current = (
                    matrix[current_row - 1][candidate_column - 1]
                    - u[current_row]
                    - v[candidate_column]
                )
                if current < minimums[candidate_column]:
                    minimums[candidate_column] = current
                    previous[candidate_column] = column
                if minimums[candidate_column] < delta:
                    delta = minimums[candidate_column]
                    next_column = candidate_column
            for candidate_column in range(columns + 1):
                if used[candidate_column]:
                    u[matching[candidate_column]] += delta
                    v[candidate_column] -= delta
                else:
                    minimums[candidate_column] -= delta
            column = next_column
            if matching[column] == 0:
                break
        while True:
            next_column = previous[column]
            matching[column] = matching[next_column]
            column = next_column
            if column == 0:
                break
    pairs = [
        (matching[column] - 1, column - 1)
        for column in range(1, columns + 1)
        if matching[column]
    ]
    if transposed:
        return [(column, row) for row, column in pairs]
    return pairs
