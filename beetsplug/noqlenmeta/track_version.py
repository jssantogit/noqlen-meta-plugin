"""Explicit-only V3 Recording version/mix state.

A dedicated MusicBrainz Recording disambiguation comment may name one known
version exactly. Never search the displayed title or extract keyword fragments.
Store normalized kind and verbatim source description separately, database-only.
"""

from __future__ import annotations

from dataclasses import dataclass

from beets.library import Item, Library

from beetsplug.noqlenmeta.database_transaction import atomic_credit_application
from beetsplug.noqlenmeta.domain import canonical_uuid

_KNOWN_TYPES = {
    "radio edit": "radio_edit",
    "extended mix": "extended_mix",
    "instrumental version": "instrumental",
    "live version": "live",
    "demo version": "demo",
    "acoustic version": "acoustic",
    "album version": "album_version",
    "single version": "single_version",
    "remix": "remix",
}


@dataclass(frozen=True, slots=True)
class TrackVersion:
    kind: str
    description: str
    recording_mbid: str

    def __post_init__(self) -> None:
        if self.kind not in frozenset(_KNOWN_TYPES.values()):
            raise ValueError("unsupported normalized track version")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("track version description must be explicit")
        mbid = canonical_uuid(self.recording_mbid)
        if mbid is None:
            raise ValueError("track version requires exact Recording identity")
        object.__setattr__(self, "recording_mbid", mbid)


@dataclass(frozen=True, slots=True)
class TrackVersionPlan:
    item_id: int
    audio_path: bytes
    original_title: str
    recording_mbid: str
    original_type: object
    original_description: object
    version: TrackVersion
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class TrackVersionResult:
    item_id: int
    status: str
    applied: bool = False
    reason: str = ""


def parse_recording_version(payload: object, recording_id: str) -> TrackVersion | None:
    if not isinstance(payload, dict) or canonical_uuid(payload.get("id")) != canonical_uuid(
        recording_id
    ):
        return None
    comment = payload.get("disambiguation")
    if not isinstance(comment, str):
        return None
    description = comment.strip()
    kind = _KNOWN_TYPES.get(description.casefold())
    if kind is None:
        return None
    return TrackVersion(kind, description, recording_id)


def plan_track_version(item: Item, version: TrackVersion) -> TrackVersionPlan:
    if not isinstance(item.id, int) or not isinstance(item.path, bytes):
        raise ValueError("track version requires a persisted Item")
    current_type = item.get("track_version_type")
    current_desc = item.get("track_version_description")
    recording_id = canonical_uuid(item.get("mb_trackid"))
    if recording_id is None or recording_id != version.recording_mbid:
        status, reason = "BLOCKED", "Recording identity does not match version source"
    elif current_type is None and current_desc is None:
        status, reason = "PROPOSE", "explicit exact-recording version metadata"
    elif current_type == version.kind and current_desc == version.description:
        status, reason = "KEEP", "existing version matches exact Recording"
    else:
        status, reason = "REVIEW", "existing version would be replaced or flattened"
    return TrackVersionPlan(
        item.id, item.path, item.title, recording_id or "",
        current_type, current_desc, version, status, reason,
    )


def apply_track_version_plan(library: Library, plan: TrackVersionPlan) -> TrackVersionResult:
    if plan.status != "PROPOSE":
        return TrackVersionResult(plan.item_id, plan.status, reason=plan.reason)
    fresh = library.get_item(plan.item_id)
    if (
        fresh is None
        or fresh.path != plan.audio_path
        or fresh.title != plan.original_title
        or canonical_uuid(fresh.get("mb_trackid")) != plan.recording_mbid
        or fresh.get("track_version_type") != plan.original_type
        or fresh.get("track_version_description") != plan.original_description
    ):
        return TrackVersionResult(plan.item_id, "BLOCKED", reason="Item changed since preview")
    with atomic_credit_application(library):
        fresh["track_version_type"] = plan.version.kind
        fresh["track_version_description"] = plan.version.description
        fresh.store()
    return TrackVersionResult(plan.item_id, "COMMITTED", applied=True)
