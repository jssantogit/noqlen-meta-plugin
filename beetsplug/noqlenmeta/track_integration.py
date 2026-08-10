"""Read-only beets track integration helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.importer.actions import Action
from beets.library import Item

from beetsplug.noqlenmeta.domain import (
    ArtistEnrichmentContext,
    ExternalIdentifier,
    MetadataValue,
    TrackEnrichmentContext,
    canonical_isrc,
    canonical_uuid,
)

_MUSICBRAINZ_RECORDING_NAMESPACE = "musicbrainz.recording"
_MUSICBRAINZ_RELEASE_TRACK_NAMESPACE = "musicbrainz.release_track"
_ISRC_NAMESPACE = "isrc"
_ACOUSTID_TRACK_NAMESPACE = "acoustid.track"


@dataclass(frozen=True, slots=True)
class SelectedImportTrack:
    """One already-selected beets Item-to-TrackInfo import mapping."""

    item: Item
    track_info: TrackInfo
    album_info: AlbumInfo | None


def context_from_track_info(
    track_info: TrackInfo,
    *,
    album_info: AlbumInfo | None = None,
    item: Item | None = None,
) -> TrackEnrichmentContext | None:
    """Copy selected provider track identity without supplementing it from Item."""
    title = _optional_text(track_info.title)
    artist = _optional_text(track_info.artist)
    if artist is None and album_info is not None:
        artist = _optional_text(album_info.artist)
    if artist is None or title is None:
        return None

    album_title = _optional_text(track_info.album)
    if album_title is None and album_info is not None:
        album_title = _optional_text(album_info.album)

    medium_index = _positive_int(track_info.medium_index)
    track_number = medium_index or _positive_int(track_info.index)
    item_ids = _item_identifier_values(item)
    data_source = _optional_text(track_info.data_source)
    is_musicbrainz = data_source is not None and data_source.casefold() == "musicbrainz"
    return TrackEnrichmentContext(
        artist=artist,
        title=title,
        album_title=album_title,
        duration=_positive_duration(track_info.length),
        track_number=track_number,
        disc_number=_positive_int(track_info.medium),
        external_ids=_external_ids(
            recording_values=(
                track_info.get("mb_trackid"),
                track_info.track_id if is_musicbrainz else None,
                item_ids[0],
            ),
            release_track_values=(
                track_info.get("mb_releasetrackid"),
                track_info.release_track_id if is_musicbrainz else None,
                item_ids[1],
            ),
            isrc_values=(track_info.get("isrc"), item_ids[2]),
            acoustid_values=(track_info.get("acoustid_id"), item_ids[3]),
        ),
        artists=_artist_contexts(
            artist,
            (
                track_info.get("mb_artistid"),
                getattr(track_info, "artist_id", None) if is_musicbrainz else None,
                _item_get(item, "mb_artistid") if item is not None else None,
            ),
        ),
    )


def context_from_library_item(item: Item) -> TrackEnrichmentContext | None:
    """Copy persistent Item-local identity without consulting its Album relation."""
    artist = _optional_text(_item_get(item, "artist"))
    title = _optional_text(_item_get(item, "title"))
    if artist is None or title is None:
        return None

    item_ids = _item_identifier_values(item)
    return TrackEnrichmentContext(
        artist=artist,
        title=title,
        album_title=_optional_text(_item_get(item, "album")),
        duration=_positive_duration(_item_get(item, "length")),
        track_number=_positive_int(_item_get(item, "track")),
        disc_number=_positive_int(_item_get(item, "disc")),
        external_ids=_external_ids(
            recording_values=(item_ids[0],),
            release_track_values=(item_ids[1],),
            isrc_values=(item_ids[2],),
            acoustid_values=(item_ids[3],),
        ),
        artists=_artist_contexts(artist, (_item_get(item, "mb_artistid"),)),
    )


def current_values_from_track_info(track_info: TrackInfo) -> dict[str, MetadataValue]:
    """Return explicitly carried canonical track values from TrackInfo."""
    return _current_track_values(track_info.get)


def current_values_from_library_item(item: Item) -> dict[str, MetadataValue]:
    """Return canonical track values from the Item itself without Album fallback."""
    return _current_track_values(lambda field: _item_get(item, field))


def selected_import_tracks(task: object) -> tuple[SelectedImportTrack, ...]:
    """Expose an APPLY task's existing selected track mapping without rematching."""
    if getattr(task, "choice_flag", None) is not Action.APPLY:
        return ()
    match = getattr(task, "match", None)
    if isinstance(match, AlbumMatch):
        return tuple(
            SelectedImportTrack(item, track_info, match.info)
            for item, track_info in match.mapping.items()
        )
    if isinstance(match, TrackMatch):
        return (SelectedImportTrack(match.item, match.info, None),)
    return ()


def context_from_selected_import_track(
    selected: SelectedImportTrack,
) -> TrackEnrichmentContext | None:
    """Build context from one selected mapping with Item used only for identifiers."""
    return context_from_track_info(
        selected.track_info,
        album_info=selected.album_info,
        item=selected.item,
    )


def _external_ids(
    *,
    recording_values: tuple[object, ...],
    release_track_values: tuple[object, ...],
    isrc_values: tuple[object, ...],
    acoustid_values: tuple[object, ...],
) -> tuple[ExternalIdentifier, ...]:
    identifiers: list[ExternalIdentifier] = []
    seen: set[tuple[str, str]] = set()

    def add(namespace: str, value: str | None) -> None:
        if value is None or (namespace, value) in seen:
            return
        seen.add((namespace, value))
        identifiers.append(ExternalIdentifier(namespace, value))

    for value in recording_values:
        add(_MUSICBRAINZ_RECORDING_NAMESPACE, canonical_uuid(value))
    for value in release_track_values:
        add(_MUSICBRAINZ_RELEASE_TRACK_NAMESPACE, canonical_uuid(value))
    for value in isrc_values:
        if not isinstance(value, str):
            continue
        for component in value.split(";"):
            add(_ISRC_NAMESPACE, canonical_isrc(component))
    for value in acoustid_values:
        add(_ACOUSTID_TRACK_NAMESPACE, canonical_uuid(value))
    return tuple(identifiers)


def _artist_contexts(
    artist_name: str, artist_id_values: tuple[object, ...]
) -> tuple[ArtistEnrichmentContext, ...]:
    artist_ids: list[ExternalIdentifier] = []
    for value in artist_id_values:
        artist_id = canonical_uuid(value)
        identifier = (
            ExternalIdentifier("musicbrainz.artist", artist_id) if artist_id else None
        )
        if identifier is not None and identifier not in artist_ids:
            artist_ids.append(identifier)
    if not artist_ids:
        return ()
    return (ArtistEnrichmentContext(artist_name, credit_index=1, external_ids=tuple(artist_ids)),)


def _item_identifier_values(item: Item | None) -> tuple[object, object, object, object]:
    if item is None:
        return None, None, None, None
    return (
        _item_get(item, "mb_trackid"),
        _item_get(item, "mb_releasetrackid"),
        _item_get(item, "isrc"),
        _item_get(item, "acoustid_id"),
    )


def _current_track_values(getter: Callable[[str], object]) -> dict[str, MetadataValue]:
    values: dict[str, MetadataValue] = {}
    for field in ("lyrics", "synced_lyrics"):
        value = getter(field)
        text = _optional_text(value)
        if text is not None:
            values[field] = text

    for field in (
        "genres",
        "moods",
        "lyrics_languages",
        "artist_countries",
        "artist_areas",
        "artist_languages",
    ):
        multi_value = _text_tuple(getter(field))
        if multi_value:
            values[field] = multi_value

    bpm = getter("bpm")
    if (
        not isinstance(bpm, bool)
        and isinstance(bpm, (int, float))
        and isfinite(bpm)
        and bpm > 0
    ):
        values["bpm"] = float(bpm)
    return values


def _item_get(item: Item, field: str) -> object:
    return item.get(field, None, with_album=False)


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _text_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(text for item in value if (text := _optional_text(item)) is not None)


def _positive_duration(value: object) -> float | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value <= 0
    ):
        return None
    return float(value)


def _positive_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None
