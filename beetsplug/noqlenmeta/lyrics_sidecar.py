"""V3 lossless synchronized-lyrics sidecars, independent of media tags.

The plan snapshots an Item path and the absence of its target. Application
rechecks the library Item and uses a staged, atomic no-clobber hard link.
Existing sidecars are never replaced, including dangling symlinks.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from beets.library import Item, Library

from beetsplug.noqlenmeta.changeplan import PlannedChange

_MAX_LRC_BYTES = 1_000_000
_TIME_TAG = re.compile(r"^\[\d{2,}:[0-5]\d(?:\.\d{1,3})?\]")
_SAFE_STATUSES = frozenset({"PROPOSE", "KEEP", "REVIEW", "BLOCKED"})


class LyricsSidecarError(RuntimeError):
    """A stale, malformed or unsafe sidecar cannot be committed."""


@dataclass(frozen=True, slots=True)
class LyricsSidecarPlan:
    item_id: int
    audio_path: bytes
    sidecar_path: bytes
    status: str
    reason: str
    payload: bytes
    source: PlannedChange

    def __post_init__(self) -> None:
        if self.status not in _SAFE_STATUSES:
            raise ValueError("invalid lyrics sidecar disposition")
        if self.source.field != "synced_lyrics":
            raise ValueError("sidecar source must be synced_lyrics")


@dataclass(frozen=True, slots=True)
class LyricsSidecarResult:
    item_id: int
    status: str
    created: bool = False


def _valid_timed_text(value: object) -> bytes | None:
    if not isinstance(value, str) or "\x00" in value:
        return None
    content = value.encode("utf-8")
    if not content or len(content) > _MAX_LRC_BYTES:
        return None
    if not any(_TIME_TAG.match(line) for line in value.splitlines()):
        return None
    return content


def _sidecar_path(audio_path: bytes) -> bytes:
    return os.path.splitext(audio_path)[0] + b".lrc"


def plan_lyrics_sidecar(item: Item, change: PlannedChange) -> LyricsSidecarPlan:
    """Preview the sidecar operation; never read or change the audio tags."""
    if change.field != "synced_lyrics":
        raise ValueError("sidecar source must be synced_lyrics")
    if not isinstance(item.id, int) or not isinstance(item.path, bytes):
        raise ValueError("lyrics sidecar requires a persisted Item with a byte path")
    payload = _valid_timed_text(change.after)
    audio_path = item.path
    sidecar = _sidecar_path(audio_path)
    status = "PROPOSE"
    reason = "verified timed lyrics can be created without replacing a sidecar"
    if payload is None:
        status, reason = "BLOCKED", "content has no valid timed LRC representation"
    elif not os.path.isfile(audio_path):
        status, reason = "BLOCKED", "audio source does not exist as a regular file"
    elif os.path.lexists(sidecar):
        if os.path.islink(sidecar) or not os.path.isfile(sidecar):
            status, reason = "REVIEW", "an existing non-regular sidecar must be preserved"
        else:
            try:
                with open(sidecar, "rb") as existing:
                    # Limit reads; never compare unbounded existing content.
                    content = existing.read(_MAX_LRC_BYTES + 1)
            except OSError:
                status, reason = "REVIEW", "existing sidecar could not be inspected"
            else:
                if content == payload:
                    status, reason = "KEEP", "existing sidecar is byte-identical"
                else:
                    status, reason = "REVIEW", "existing sidecar differs from candidate"
    return LyricsSidecarPlan(
        item.id, audio_path, sidecar, status, reason, payload or b"", change
    )


def apply_lyrics_sidecar_plan(
    library: Library, plan: LyricsSidecarPlan
) -> LyricsSidecarResult:
    """Create one verified .lrc atomically; never overwrite a pre-existing path."""
    if not isinstance(plan, LyricsSidecarPlan):
        raise LyricsSidecarError("sidecar plan has an invalid type")
    if plan.status != "PROPOSE":
        return LyricsSidecarResult(plan.item_id, plan.status)

    fresh = library.get_item(plan.item_id)
    if fresh is None or fresh.path != plan.audio_path:
        raise LyricsSidecarError("library Item path changed after preview")
    if _sidecar_path(fresh.path) != plan.sidecar_path:
        raise LyricsSidecarError("sidecar target changed after preview")
    if _valid_timed_text(plan.source.after) != plan.payload:
        raise LyricsSidecarError("lyrics sidecar payload changed after preview")
    if not os.path.isfile(plan.audio_path):
        raise LyricsSidecarError("audio file changed after preview")
    if os.path.lexists(plan.sidecar_path):
        raise LyricsSidecarError("sidecar exists or changed after preview")
    directory = os.path.dirname(plan.sidecar_path)
    if not os.path.isdir(directory) or os.path.islink(directory):
        raise LyricsSidecarError("sidecar parent directory is unsafe")

    stage: bytes | None = None
    try:
        fd, stage = tempfile.mkstemp(prefix=b".noqlenmeta-lrc-", dir=directory)
        with os.fdopen(fd, "wb") as destination:
            destination.write(plan.payload)
            destination.flush()
            os.fsync(destination.fileno())
        # os.link is atomic and fails if target exists. Unlike replace(),
        # concurrent files or symlinks cannot be overwritten.
        os.link(stage, plan.sidecar_path)
    except FileExistsError:
        raise LyricsSidecarError("sidecar exists or changed after preview") from None
    except OSError as error:
        raise LyricsSidecarError(
            f"sidecar creation failed: {type(error).__name__}"
        ) from None
    finally:
        if stage is not None:
            try:
                os.unlink(stage)
            except FileNotFoundError:
                pass
    return LyricsSidecarResult(plan.item_id, "COMMITTED", created=True)
