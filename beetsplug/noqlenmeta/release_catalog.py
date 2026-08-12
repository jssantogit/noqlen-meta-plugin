"""Canonical release catalog values and provider-independent normalization."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from enum import Enum

from beetsplug.noqlenmeta.field_contracts import PartialDate


class ReleaseType(Enum):
    ALBUM = "Album"
    EP = "EP"
    SINGLE = "Single"
    BROADCAST = "Broadcast"
    OTHER = "Other"


class ReleaseSecondaryType(Enum):
    COMPILATION = "Compilation"
    SOUNDTRACK = "Soundtrack"
    SPOKENWORD = "Spokenword"
    INTERVIEW = "Interview"
    AUDIOBOOK = "Audiobook"
    AUDIO_DRAMA = "Audio drama"
    LIVE = "Live"
    REMIX = "Remix"
    DJ_MIX = "DJ-mix"
    MIXTAPE_STREET = "Mixtape/Street"
    DEMO = "Demo"
    FIELD_RECORDING = "Field recording"


class ReleaseStatus(Enum):
    OFFICIAL = "Official"
    PROMOTION = "Promotion"
    BOOTLEG = "Bootleg"
    PSEUDO_RELEASE = "Pseudo-Release"


_PRIMARY_TYPES = {value.value.casefold(): value for value in ReleaseType}
_SECONDARY_TYPES = {value.value.casefold(): value for value in ReleaseSecondaryType}
_RELEASE_STATUSES = {value.value.casefold(): value for value in ReleaseStatus}
_EDITIONS = {
    value.casefold(): value
    for value in (
        "Deluxe Edition",
        "Limited Edition",
        "Special Edition",
        "Collector's Edition",
        "Anniversary Edition",
        "Expanded Edition",
    )
}


def parse_partial_date(value: object) -> PartialDate | None:
    """Parse only ISO partial dates and MusicBrainz unknown components."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    match = re.fullmatch(
        r"([0-9]{4})(?:-([0-9]{2}|\?\?)(?:-([0-9]{2}|\?\?))?)?",
        text,
    )
    if match is None:
        return None
    year_text, month_text, day_text = match.groups()
    if month_text == "??" and day_text not in {None, "??"}:
        return None
    if month_text == "??" and day_text is None:
        return None
    month = None if month_text in {None, "??"} else int(month_text)
    day = None if day_text in {None, "??"} else int(day_text)
    try:
        return PartialDate(int(year_text), month, day)
    except ValueError:
        return None


def parse_iso_datetime_date(value: object) -> PartialDate | None:
    """Parse an ISO timestamp while retaining only its explicit calendar date."""
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return PartialDate(parsed.year, parsed.month, parsed.day)


def compatible_partial_dates(left: PartialDate, right: PartialDate) -> bool:
    """Return whether every date component known by both values agrees."""
    return (
        left.year == right.year
        and (left.month is None or right.month is None or left.month == right.month)
        and (left.day is None or right.day is None or left.day == right.day)
    )


def prefer_precise_date(left: PartialDate, right: PartialDate) -> PartialDate | None:
    """Return the more precise compatible date, retaining the left value on ties."""
    if not compatible_partial_dates(left, right):
        return None
    left_precision = 1 + (left.month is not None) + (left.day is not None)
    right_precision = 1 + (right.month is not None) + (right.day is not None)
    return right if right_precision > left_precision else left


def normalize_release_type(value: object) -> ReleaseType | None:
    text = _text(value)
    return _PRIMARY_TYPES.get(text.casefold())


def normalize_release_secondary_types(value: object) -> tuple[ReleaseSecondaryType, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    normalized: list[ReleaseSecondaryType] = []
    for item in value:
        release_type = _SECONDARY_TYPES.get(_text(item).casefold())
        if release_type is not None and release_type not in normalized:
            normalized.append(release_type)
    return tuple(normalized)


def normalize_release_status(value: object) -> ReleaseStatus | None:
    text = _text(value)
    return _RELEASE_STATUSES.get(text.casefold())


def normalize_edition(value: object) -> str | None:
    text = _text(value)
    return _EDITIONS.get(text.casefold())


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
