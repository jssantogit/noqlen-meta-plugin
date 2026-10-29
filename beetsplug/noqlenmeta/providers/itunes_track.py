"""Conservative V3 advisory evidence from a *single* verified iTunes song.

The release-level iTunes adapter remains unchanged. Only affirmative track
flags `explicit` and `cleaned` contribute; `notExplicit` is not evidence of
a distinct clean edit and never becomes an implicit false.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from http.client import HTTPException
from urllib.parse import urlencode

from beetsplug.noqlenmeta.domain import (
    ExternalIdentifier,
    TrackEnrichmentContext,
)
from beetsplug.noqlenmeta.evidence import (
    AcquisitionMethod,
    AcquisitionProvenance,
    MetadataEvidence,
    SubjectRef,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind
from beetsplug.noqlenmeta.providers.base import ProviderError
from beetsplug.noqlenmeta.providers.itunes import _public_url, _request_json
from beetsplug.noqlenmeta.providers.specs import ProviderScope

_SEARCH_ENDPOINT = "https://itunes.apple.com/search"
_MAX_RESULTS = 25
_MAX_DURATION_DELTA_SECONDS = 2.0
_VALID_FLAGS = {"explicit": "explicit", "cleaned": "clean"}
_ERROR = "iTunes track advisory lookup failed"


class ITunesTrackExplicitnessProvider:
    """Select a unique exact song, not a likely release or fuzzy album match."""

    name = "itunes"

    def __init__(
        self,
        storefront: str = "us",
        *,
        request_json: Callable[[str], Mapping[str, object]] | None = None,
    ) -> None:
        storefront = storefront.strip().lower()
        if re.fullmatch(r"[a-z]{2}", storefront) is None:
            raise ProviderError("iTunes storefront configuration is invalid")
        self._storefront = storefront
        self._request_json = request_json or _request_json
        self._cache: dict[
            tuple[str, str, str, float, int | None, int | None],
            tuple[MetadataEvidence, ...],
        ] = {}

    def get_evidence(
        self, context: TrackEnrichmentContext
    ) -> tuple[MetadataEvidence, ...]:
        if context.album_title is None or context.duration is None:
            return ()
        key = (
            context.artist,
            context.title,
            context.album_title,
            context.duration,
            context.track_number,
            context.disc_number,
        )
        if key in self._cache:
            return self._cache[key]

        url = f"{_SEARCH_ENDPOINT}?{urlencode({
            'term': f'{context.artist} {context.title} {context.album_title}',
            'media': 'music',
            'entity': 'song',
            'limit': _MAX_RESULTS,
            'country': self._storefront.upper(),
            'explicit': 'Yes',
        })}"
        try:
            payload = self._request_json(url)
            rows = payload["results"]
            if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
                raise ValueError("invalid iTunes results")
        except (OSError, HTTPException, KeyError, TypeError, ValueError, UnicodeError):
            raise ProviderError(_ERROR) from None

        matches = [
            row
            for row in rows[:_MAX_RESULTS]
            if isinstance(row, Mapping) and _exact_song(row, context)
        ]
        result: tuple[MetadataEvidence, ...] = ()
        if len(matches) == 1:
            row = matches[0]
            explicitness = _VALID_FLAGS.get(row.get("trackExplicitness"))
            if explicitness is not None:
                song_id = str(row["trackId"])
                result = (
                    MetadataEvidence(
                        field="explicitness",
                        value=explicitness,
                        subject=SubjectRef(
                            EntityKind.RECORDING,
                            (ExternalIdentifier("itunes.track", song_id),),
                        ),
                        provider=self.name,
                        acquisition_scope=ProviderScope.TRACK,
                        source_id=song_id,
                        provenance=AcquisitionProvenance(
                            AcquisitionMethod.STRUCTURALLY_VALIDATED
                        ),
                        source_url=_public_url(row.get("trackViewUrl")),
                        confidence=0.95,
                    ),
                )
        self._cache[key] = result
        return result


def _identity_key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def _exact_song(
    row: Mapping[str, object], context: TrackEnrichmentContext
) -> bool:
    if row.get("wrapperType") != "track" or row.get("kind") != "song":
        return False
    track_id = row.get("trackId")
    duration_ms = row.get("trackTimeMillis")
    if (
        type(track_id) is not int
        or track_id <= 0
        or type(duration_ms) is not int
        or duration_ms <= 0
        or context.duration is None
        or abs(duration_ms / 1000 - context.duration) > _MAX_DURATION_DELTA_SECONDS
    ):
        return False
    for field, requested in (
        ("artistName", context.artist),
        ("trackName", context.title),
        ("collectionName", context.album_title),
    ):
        assert requested is not None
        if not _identity_key(requested) or _identity_key(row.get(field)) != _identity_key(
            requested
        ):
            return False
    for field, expected in (
        ("trackNumber", context.track_number),
        ("discNumber", context.disc_number),
    ):
        if expected is not None and (
            type(row.get(field)) is not int or row.get(field) != expected
        ):
            return False
    return True
