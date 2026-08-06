from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import InitVar, dataclass, field
from enum import Enum
from uuid import UUID

from beets.library import Item

_UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_MAX_FINGERPRINT_LENGTH = 1_000_000
_MAX_RESULT_GROUPS = 20
_MAX_RECORDINGS_PER_RESULT = 50


class AcoustIDFingerprintOrigin(str, Enum):
    EXISTING = "existing"
    GENERATED = "generated"


class AcoustIDLibraryTargetKind(str, Enum):
    ALBUM = "album"
    SINGLETON = "singleton"


class AcoustIDStoredValueState(str, Enum):
    MISSING = "missing"
    VALID = "valid"
    MALFORMED = "malformed"


class AcoustIDEvidenceVerdict(str, Enum):
    UNAVAILABLE = "unavailable"
    NO_MATCH = "no_match"
    AMBIGUOUS = "ambiguous"
    DECISIVE = "decisive"


class AcoustIDEvidenceReason(str, Enum):
    FINGERPRINT_REUSED = "fingerprint_reused"
    FINGERPRINT_GENERATED = "fingerprint_generated"
    FINGERPRINT_MISSING = "fingerprint_missing"
    FINGERPRINT_BACKEND_UNAVAILABLE = "fingerprint_backend_unavailable"
    FINGERPRINT_FAILED = "fingerprint_failed"
    LOOKUP_DISABLED = "lookup_disabled"
    CLIENT_KEY_MISSING = "client_key_missing"
    LOOKUP_FAILED = "lookup_failed"
    NO_RESULT_ABOVE_MINIMUM = "no_result_above_minimum"
    COMPETING_RECORDINGS = "competing_recordings"
    INSUFFICIENT_MARGIN = "insufficient_margin"
    RECORDING_DECISIVE = "recording_decisive"
    EXISTING_VALUE_CONFLICT = "existing_value_conflict"
    STALE_TARGET = "stale_target"
    STALE_SOURCE_FILE = "stale_source_file"


_UNAVAILABLE_REASONS = frozenset(
    {
        AcoustIDEvidenceReason.FINGERPRINT_MISSING,
        AcoustIDEvidenceReason.FINGERPRINT_BACKEND_UNAVAILABLE,
        AcoustIDEvidenceReason.FINGERPRINT_FAILED,
        AcoustIDEvidenceReason.LOOKUP_DISABLED,
        AcoustIDEvidenceReason.CLIENT_KEY_MISSING,
        AcoustIDEvidenceReason.LOOKUP_FAILED,
    }
)


def canonical_acoustid_uuid(value: object) -> str:
    return _canonical_uuid(value, "AcoustID UUID")


def canonical_recording_mbid(value: object) -> str:
    return _canonical_uuid(value, "recording MBID")


def _canonical_uuid(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _UUID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a canonical UUID string")
    return str(UUID(value))


def _local_key(value: object) -> str:
    normalized = value.strip() if isinstance(value, str) else None
    if (
        normalized is None
        or not normalized
        or normalized in {".", ".."}
        or any(character in normalized for character in ("/", "\\", "\0"))
    ):
        raise ValueError("local_key must be a non-empty path-free string")
    return normalized


def _fingerprint_text(value: object, *, reject_surrounding_whitespace: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("fingerprint must be a non-empty string")
    if reject_surrounding_whitespace and value != value.strip():
        raise ValueError("fingerprint must not contain surrounding whitespace")
    if len(value) > _MAX_FINGERPRINT_LENGTH:
        raise ValueError("fingerprint exceeds the defensive length limit")
    return value


def _positive_database_id(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"selected AcoustID {label} ID is invalid")
    return value


def _optional_album_id(value: object) -> int | None:
    if value in (None, 0):
        return None
    return _positive_database_id(value, "Album")


def _positive_duration(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    duration = float(value)
    return duration if math.isfinite(duration) and duration > 0 else None


@dataclass(frozen=True, slots=True)
class AcoustIDExistingValues:
    acoustid_id_state: AcoustIDStoredValueState
    acoustid_id: str | None
    fingerprint_state: AcoustIDStoredValueState
    fingerprint: InitVar[str | None]
    duration_seconds: float | None
    _fingerprint: str | None = field(init=False, repr=False)

    def __post_init__(self, fingerprint: str | None) -> None:
        if not isinstance(self.acoustid_id_state, AcoustIDStoredValueState):
            raise ValueError("stored AcoustID ID state is invalid")
        if self.acoustid_id_state is AcoustIDStoredValueState.VALID:
            object.__setattr__(self, "acoustid_id", canonical_acoustid_uuid(self.acoustid_id))
        elif self.acoustid_id is not None:
            raise ValueError("non-valid stored AcoustID ID prohibits a value")
        if not isinstance(self.fingerprint_state, AcoustIDStoredValueState):
            raise ValueError("stored fingerprint state is invalid")
        if self.fingerprint_state is AcoustIDStoredValueState.VALID:
            validated = _fingerprint_text(fingerprint, reject_surrounding_whitespace=True)
        elif fingerprint is not None:
            raise ValueError("non-valid stored fingerprint prohibits material")
        else:
            validated = None
        object.__setattr__(self, "_fingerprint", validated)
        duration = _positive_duration(self.duration_seconds)
        if self.duration_seconds is not None and duration is None:
            raise ValueError("existing duration must be finite and positive or None")
        object.__setattr__(self, "duration_seconds", duration)

    @classmethod
    def from_stored(
        cls, acoustid_id: object, fingerprint: object, duration_seconds: object
    ) -> AcoustIDExistingValues:
        id_state, canonical_id = _stored_acoustid_id(acoustid_id)
        fingerprint_state, valid_fingerprint = _stored_fingerprint(fingerprint)
        return cls(
            id_state,
            canonical_id,
            fingerprint_state,
            valid_fingerprint,
            _positive_duration(duration_seconds),
        )

    @property
    def is_fingerprint_reusable(self) -> bool:
        return self._fingerprint is not None and self.duration_seconds is not None

    def _reusable_fingerprint(self) -> str | None:
        return self._fingerprint if self.is_fingerprint_reusable else None


def _stored_acoustid_id(value: object) -> tuple[AcoustIDStoredValueState, str | None]:
    if value is None or isinstance(value, str) and not value.strip():
        return AcoustIDStoredValueState.MISSING, None
    try:
        return AcoustIDStoredValueState.VALID, canonical_acoustid_uuid(value)
    except ValueError:
        return AcoustIDStoredValueState.MALFORMED, None


def _stored_fingerprint(value: object) -> tuple[AcoustIDStoredValueState, str | None]:
    if value is None or isinstance(value, str) and not value.strip():
        return AcoustIDStoredValueState.MISSING, None
    try:
        return (
            AcoustIDStoredValueState.VALID,
            _fingerprint_text(value, reject_surrounding_whitespace=True),
        )
    except ValueError:
        return AcoustIDStoredValueState.MALFORMED, None


@dataclass(frozen=True, slots=True)
class SelectedAcoustIDItem:
    local_key: str
    item_id: int
    album_id: int | None
    item: Item = field(repr=False, compare=False, hash=False)
    media_path: bytes | str = field(repr=False, compare=False, hash=False)
    existing_values: AcoustIDExistingValues

    def __post_init__(self) -> None:
        item_id = _positive_database_id(self.item_id, "Item")
        album_id = _optional_album_id(self.album_id)
        if self.local_key != f"library-item:{item_id}":
            raise ValueError("selected AcoustID local key is invalid")
        if type(self.item) is not Item or self.item.id != item_id:
            raise TypeError("selected AcoustID Item is invalid")
        if _optional_album_id(self.item.album_id) != album_id:
            raise ValueError("selected AcoustID Item membership is invalid")
        item_path = self.item.path
        if type(item_path) not in (bytes, str) or not item_path:
            raise ValueError("selected AcoustID media path is invalid")
        if (
            type(self.media_path) not in (bytes, str)
            or not self.media_path
            or self.media_path != item_path
        ):
            raise ValueError("selected AcoustID media path is invalid")
        if not isinstance(self.existing_values, AcoustIDExistingValues):
            raise ValueError("selected AcoustID existing values are invalid")
        expected_values = AcoustIDExistingValues.from_stored(
            self.item.acoustid_id,
            self.item.acoustid_fingerprint,
            self.item.length,
        )
        if self.existing_values != expected_values:
            raise ValueError("selected AcoustID existing values are invalid")
        object.__setattr__(self, "album_id", album_id)


@dataclass(frozen=True, slots=True)
class SelectedAcoustIDTarget:
    kind: AcoustIDLibraryTargetKind
    album_id: int | None
    items: tuple[SelectedAcoustIDItem, ...]
    _refresh_source: object = field(default=None, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, AcoustIDLibraryTargetKind):
            raise ValueError("selected AcoustID target kind is invalid")
        items = tuple(self.items)
        if not items or any(type(item) is not SelectedAcoustIDItem for item in items):
            raise ValueError("selected AcoustID target requires supported Items")
        if len({item.item_id for item in items}) != len(items) or len(
            {item.local_key for item in items}
        ) != len(items):
            raise ValueError("selected AcoustID target Items are duplicated")
        if self.kind is AcoustIDLibraryTargetKind.ALBUM:
            album_id = _positive_database_id(self.album_id, "Album")
            if any(item.album_id != album_id for item in items):
                raise ValueError("selected AcoustID Album contains an unrelated Item")
        elif self.album_id is not None or len(items) != 1 or items[0].album_id is not None:
            raise ValueError("selected AcoustID singleton requires one standalone Item")
        object.__setattr__(self, "items", items)


@dataclass(frozen=True, slots=True)
class FingerprintBackendResult:
    duration_seconds: float
    fingerprint: InitVar[str]
    _fingerprint: str = field(init=False, repr=False)

    def __post_init__(self, fingerprint: str) -> None:
        duration = _positive_duration(self.duration_seconds)
        if duration is None:
            raise ValueError("backend duration must be finite and positive")
        object.__setattr__(self, "duration_seconds", duration)
        object.__setattr__(self, "_fingerprint", _fingerprint_text(fingerprint))

    def _fingerprint_text(self) -> str:
        return self._fingerprint


def _bounded_float(value: object, field_name: str, lower: float, upper: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite number from {lower} through {upper}")
    normalized = float(value)
    if not math.isfinite(normalized) or not lower <= normalized <= upper:
        raise ValueError(f"{field_name} must be a finite number from {lower} through {upper}")
    return normalized


def _bounded_int(value: object, field_name: str, lower: int, upper: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
        raise ValueError(f"{field_name} must be an integer from {lower} through {upper}")
    return value


@dataclass(frozen=True, slots=True)
class AcoustIDSourceSnapshot:
    device: int
    inode: int
    size: int
    mtime_ns: int

    def __post_init__(self) -> None:
        for field_name in ("device", "inode", "size", "mtime_ns"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{field_name} must be an integer")
        for field_name in ("device", "inode", "size"):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")


@dataclass(frozen=True, slots=True)
class AcoustIDFingerprintMaterial:
    local_key: str
    fingerprint: InitVar[str]
    duration_seconds: float
    origin: AcoustIDFingerprintOrigin
    source_snapshot: AcoustIDSourceSnapshot | None = None
    _fingerprint: str = field(init=False, repr=False)

    def __post_init__(self, fingerprint: str) -> None:
        object.__setattr__(self, "local_key", _local_key(self.local_key))
        object.__setattr__(self, "_fingerprint", _fingerprint_text(fingerprint))
        if isinstance(self.duration_seconds, bool) or not isinstance(
            self.duration_seconds, (int, float)
        ):
            raise ValueError("duration_seconds must be finite and positive")
        duration = float(self.duration_seconds)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("duration_seconds must be finite and positive")
        object.__setattr__(self, "duration_seconds", duration)
        if not isinstance(self.origin, AcoustIDFingerprintOrigin):
            raise ValueError("origin must be an AcoustIDFingerprintOrigin")
        if self.source_snapshot is not None and not isinstance(
            self.source_snapshot, AcoustIDSourceSnapshot
        ):
            raise ValueError("source_snapshot must be an AcoustIDSourceSnapshot or None")
        if self.origin is AcoustIDFingerprintOrigin.EXISTING and self.source_snapshot is not None:
            raise ValueError("existing fingerprint material prohibits a source snapshot")
        if self.origin is AcoustIDFingerprintOrigin.GENERATED and self.source_snapshot is None:
            raise ValueError("generated fingerprint material requires a source snapshot")


@dataclass(frozen=True, slots=True)
class FingerprintPreparationResult:
    local_key: str
    material: AcoustIDFingerprintMaterial | None
    reason: AcoustIDEvidenceReason

    def __post_init__(self) -> None:
        object.__setattr__(self, "local_key", _local_key(self.local_key))
        if not isinstance(self.reason, AcoustIDEvidenceReason):
            raise ValueError("fingerprint preparation reason is invalid")
        successful = {
            AcoustIDEvidenceReason.FINGERPRINT_REUSED,
            AcoustIDEvidenceReason.FINGERPRINT_GENERATED,
        }
        unsuccessful = {
            AcoustIDEvidenceReason.FINGERPRINT_MISSING,
            AcoustIDEvidenceReason.FINGERPRINT_BACKEND_UNAVAILABLE,
            AcoustIDEvidenceReason.FINGERPRINT_FAILED,
            AcoustIDEvidenceReason.STALE_SOURCE_FILE,
        }
        if self.reason not in successful | unsuccessful:
            raise ValueError("fingerprint preparation reason is unsupported")
        if self.reason in unsuccessful:
            if self.material is not None:
                raise ValueError("unsuccessful fingerprint preparation prohibits material")
            return
        if not isinstance(self.material, AcoustIDFingerprintMaterial):
            raise ValueError("successful fingerprint preparation requires material")
        if self.material.local_key != self.local_key:
            raise ValueError("fingerprint preparation material local key is inconsistent")
        expected_origin = (
            AcoustIDFingerprintOrigin.EXISTING
            if self.reason is AcoustIDEvidenceReason.FINGERPRINT_REUSED
            else AcoustIDFingerprintOrigin.GENERATED
        )
        if self.material.origin is not expected_origin:
            raise ValueError("fingerprint preparation material origin is inconsistent")


@dataclass(frozen=True, slots=True)
class AcoustIDResultGroup:
    acoustid_id: str
    score: float
    recording_mbids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "acoustid_id", canonical_acoustid_uuid(self.acoustid_id))
        object.__setattr__(self, "score", _bounded_float(self.score, "score", 0.0, 1.0))
        if isinstance(self.recording_mbids, (str, bytes)):
            raise ValueError("recording_mbids must be a non-empty collection")
        try:
            values = tuple(self.recording_mbids)
        except TypeError as error:
            raise ValueError("recording_mbids must be a non-empty collection") from error
        normalized = tuple(sorted({canonical_recording_mbid(value) for value in values}))
        if not normalized:
            raise ValueError("recording_mbids must be a non-empty collection")
        if len(normalized) > _MAX_RECORDINGS_PER_RESULT:
            raise ValueError("recording_mbids exceeds the defensive count limit")
        object.__setattr__(self, "recording_mbids", normalized)


@dataclass(frozen=True, slots=True)
class AcoustIDEvidencePolicy:
    min_score: float
    min_margin: float
    max_results: int
    max_recordings_per_result: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_score", _bounded_float(self.min_score, "min_score", 0, 1))
        object.__setattr__(
            self, "min_margin", _bounded_float(self.min_margin, "min_margin", 0, 1)
        )
        object.__setattr__(
            self, "max_results", _bounded_int(self.max_results, "max_results", 1, 20)
        )
        object.__setattr__(
            self,
            "max_recordings_per_result",
            _bounded_int(
                self.max_recordings_per_result,
                "max_recordings_per_result",
                1,
                50,
            ),
        )


@dataclass(frozen=True, slots=True)
class AcoustIDTrackEvidence:
    local_key: str
    fingerprint_origin: AcoustIDFingerprintOrigin | None
    result_groups: tuple[AcoustIDResultGroup, ...]
    verdict: AcoustIDEvidenceVerdict
    selected_acoustid_id: str | None
    selected_recording_mbid: str | None
    reason: AcoustIDEvidenceReason
    top_score: float | None
    runner_up_score: float | None
    margin: float | None
    eligible_result_count: int
    eligible_recording_count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "local_key", _local_key(self.local_key))
        if self.fingerprint_origin is not None and not isinstance(
            self.fingerprint_origin, AcoustIDFingerprintOrigin
        ):
            raise ValueError("fingerprint_origin must be an AcoustIDFingerprintOrigin or None")
        groups = tuple(self.result_groups)
        if any(not isinstance(group, AcoustIDResultGroup) for group in groups):
            raise ValueError("result_groups must contain AcoustIDResultGroup values")
        if len(groups) > _MAX_RESULT_GROUPS:
            raise ValueError("result_groups exceeds the defensive count limit")
        object.__setattr__(self, "result_groups", groups)
        if not isinstance(self.verdict, AcoustIDEvidenceVerdict):
            raise ValueError("verdict must be an AcoustIDEvidenceVerdict")
        if not isinstance(self.reason, AcoustIDEvidenceReason):
            raise ValueError("reason must be an AcoustIDEvidenceReason")
        self._validate_numbers()
        self._validate_verdict()

    def _validate_numbers(self) -> None:
        for field_name in ("top_score", "runner_up_score", "margin"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _bounded_float(value, field_name, 0, 1))
        for field_name in ("eligible_result_count", "eligible_recording_count"):
            object.__setattr__(
                self,
                field_name,
                _bounded_int(getattr(self, field_name), field_name, 0, 1000),
            )
        if self.eligible_result_count > len(self.result_groups):
            raise ValueError("eligible_result_count is inconsistent with result_groups")
        available_recordings = {
            recording_mbid
            for group in self.result_groups
            for recording_mbid in group.recording_mbids
        }
        if self.eligible_recording_count > len(available_recordings):
            raise ValueError("eligible_recording_count is inconsistent with result_groups")
        if (self.eligible_result_count == 0) != (self.eligible_recording_count == 0):
            raise ValueError("eligible result and recording counts are inconsistent")
        if self.eligible_recording_count == 1 and (
            self.runner_up_score is not None or self.margin is not None
        ):
            raise ValueError("one eligible recording prohibits runner-up score information")
        if self.eligible_recording_count >= 2 and (
            self.runner_up_score is None or self.margin is None
        ):
            raise ValueError("multiple eligible recordings require runner-up score information")
        if self.eligible_recording_count >= 2:
            support: dict[str, float] = {}
            for group in self.result_groups:
                for recording_mbid in group.recording_mbids:
                    support[recording_mbid] = max(support.get(recording_mbid, 0.0), group.score)
            strongest_support = sorted(support.values(), reverse=True)
            if (
                self.top_score != strongest_support[0]
                or self.runner_up_score != strongest_support[1]
            ):
                raise ValueError("score information is inconsistent with recording support")
        if self.runner_up_score is not None:
            if self.top_score is None or self.runner_up_score > self.top_score:
                raise ValueError("runner_up_score is inconsistent with top_score")
            expected_margin = self.top_score - self.runner_up_score
            if self.margin != expected_margin:
                raise ValueError("margin is inconsistent with score values")
        elif self.margin is not None:
            raise ValueError("margin requires a runner_up_score")

    def _validate_verdict(self) -> None:
        selected = self.selected_acoustid_id is not None or self.selected_recording_mbid is not None
        if self.verdict is AcoustIDEvidenceVerdict.DECISIVE:
            if self.selected_acoustid_id is None or self.selected_recording_mbid is None:
                raise ValueError("decisive evidence requires both selected identifiers")
            object.__setattr__(
                self, "selected_acoustid_id", canonical_acoustid_uuid(self.selected_acoustid_id)
            )
            object.__setattr__(
                self,
                "selected_recording_mbid",
                canonical_recording_mbid(self.selected_recording_mbid),
            )
            if self.reason is not AcoustIDEvidenceReason.RECORDING_DECISIVE:
                raise ValueError("decisive evidence requires recording_decisive")
            if (
                self.top_score is None
                or self.eligible_result_count < 1
                or self.eligible_recording_count < 1
            ):
                raise ValueError("decisive evidence requires eligible score information")
            supporting_groups = tuple(
                group
                for group in self.result_groups
                if self.selected_recording_mbid in group.recording_mbids
            )
            if not supporting_groups or not any(
                group.acoustid_id == self.selected_acoustid_id
                and group.score == self.top_score
                for group in supporting_groups
            ):
                raise ValueError("selected identifiers are inconsistent with result_groups")
            if self.top_score != max(group.score for group in supporting_groups):
                raise ValueError("top_score is inconsistent with selected recording support")
            if any(
                group.score == self.top_score and len(group.recording_mbids) > 1
                for group in supporting_groups
            ):
                raise ValueError("decisive evidence conflicts with top-scoring result groups")
            if any(
                group.score >= self.top_score
                and any(
                    recording_mbid != self.selected_recording_mbid
                    for recording_mbid in group.recording_mbids
                )
                for group in self.result_groups
            ):
                raise ValueError("decisive evidence conflicts with competing result groups")
            if self.runner_up_score == self.top_score:
                raise ValueError("decisive evidence requires a unique top score")
        elif selected:
            raise ValueError("non-decisive evidence prohibits selected identifiers")
        if (
            self.verdict is AcoustIDEvidenceVerdict.NO_MATCH
            and self.reason is not AcoustIDEvidenceReason.NO_RESULT_ABOVE_MINIMUM
        ):
            raise ValueError("no_match evidence requires no_result_above_minimum")
        if self.verdict is AcoustIDEvidenceVerdict.NO_MATCH and (
            self.top_score is not None
            or self.eligible_result_count != 0
            or self.eligible_recording_count != 0
        ):
            raise ValueError("no_match evidence prohibits eligible score information")
        if self.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS and self.reason not in {
            AcoustIDEvidenceReason.COMPETING_RECORDINGS,
            AcoustIDEvidenceReason.INSUFFICIENT_MARGIN,
        }:
            raise ValueError("ambiguous evidence requires an ambiguity reason")
        if self.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS and (
            self.top_score is None
            or self.runner_up_score is None
            or self.eligible_result_count < 1
            or self.eligible_recording_count < 2
        ):
            raise ValueError("ambiguous evidence requires competing score information")
        if (
            self.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS
            and self.reason is AcoustIDEvidenceReason.COMPETING_RECORDINGS
            and self.runner_up_score != self.top_score
        ):
            raise ValueError("competing_recordings requires tied top scores")
        if (
            self.verdict is AcoustIDEvidenceVerdict.AMBIGUOUS
            and self.reason is AcoustIDEvidenceReason.INSUFFICIENT_MARGIN
            and self.runner_up_score == self.top_score
        ):
            raise ValueError("insufficient_margin requires a unique top score")
        if self.verdict is AcoustIDEvidenceVerdict.UNAVAILABLE and self.reason not in (
            _UNAVAILABLE_REASONS
        ):
            raise ValueError("unavailable evidence requires an unavailable reason")
        if self.verdict is AcoustIDEvidenceVerdict.UNAVAILABLE and (
            self.top_score is not None
            or self.eligible_result_count != 0
            or self.eligible_recording_count != 0
        ):
            raise ValueError("unavailable evidence prohibits eligible score information")


def normalize_result_groups(
    groups: Iterable[AcoustIDResultGroup], policy: AcoustIDEvidencePolicy
) -> tuple[AcoustIDResultGroup, ...]:
    values = tuple(groups)
    if any(not isinstance(group, AcoustIDResultGroup) for group in values):
        raise ValueError("groups must contain AcoustIDResultGroup values")
    unique_by_acoustid_id: dict[str, AcoustIDResultGroup] = {}
    for group in values:
        existing = unique_by_acoustid_id.get(group.acoustid_id)
        if existing is not None and existing != group:
            raise ValueError("conflicting duplicate AcoustID result groups")
        unique_by_acoustid_id[group.acoustid_id] = group
    ordered = sorted(
        unique_by_acoustid_id.values(),
        key=lambda group: (-group.score, group.acoustid_id, group.recording_mbids),
    )
    return tuple(
        AcoustIDResultGroup(
            group.acoustid_id,
            group.score,
            group.recording_mbids[: policy.max_recordings_per_result],
        )
        for group in ordered[: policy.max_results]
    )
