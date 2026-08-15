"""Read-only beets track integration helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.importer.actions import Action
from beets.library import Item

from beetsplug.noqlenmeta.credit_state import read_credit_state
from beetsplug.noqlenmeta.credits import (
    CreditParty,
    CreditReference,
    CreditRole,
    canonical_credit_references,
)
from beetsplug.noqlenmeta.domain import (
    ArtistEnrichmentContext,
    ExternalIdentifier,
    ReleaseEnrichmentContext,
    TrackEnrichmentContext,
    canonical_isrc,
    canonical_uuid,
)
from beetsplug.noqlenmeta.evidence import CanonicalValue
from beetsplug.noqlenmeta.field_contracts import EntityKind, IdentifierCollection
from beetsplug.noqlenmeta.release_catalog import parse_partial_date
from beetsplug.noqlenmeta.work_identity import WorkReference, canonical_work_references

_MUSICBRAINZ_RECORDING_NAMESPACE = "musicbrainz.recording"
_MUSICBRAINZ_RELEASE_TRACK_NAMESPACE = "musicbrainz.release_track"
_MUSICBRAINZ_RELEASE_NAMESPACE = "musicbrainz.release"
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
    album_data_source = (
        _optional_text(album_info.data_source) if album_info is not None else None
    )
    release = _release_context(
        artist,
        album_title,
        (
            getattr(album_info, "mb_albumid", None) if album_info is not None else None,
            album_info.album_id
            if album_info is not None
            and album_data_source is not None
            and album_data_source.casefold() == "musicbrainz"
            else None,
            track_info.get("mb_albumid"),
            _item_get(item, "mb_albumid") if item is not None else None,
        ),
    )
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
        release=release,
        artists=_artist_contexts(
            artist,
            (
                (
                    track_info.get("artists"),
                    track_info.get("artists_credit"),
                    track_info.get("artists_sort"),
                    track_info.get("artists_ids"),
                ),
                (
                    (artist,),
                    (track_info.get("artist_credit"),),
                    (track_info.get("artist_sort"),),
                    (
                        track_info.get("mb_artistid")
                        or (
                            getattr(track_info, "artist_id", None)
                            if is_musicbrainz
                            else None
                        ),
                    ),
                ),
                (
                    _item_get(item, "artists") if item is not None else None,
                    _item_get(item, "artists_credit") if item is not None else None,
                    _item_get(item, "artists_sort") if item is not None else None,
                    _item_get(item, "mb_artistids") if item is not None else None,
                ),
                (
                    (artist,),
                    (_item_get(item, "artist_credit") if item is not None else None,),
                    (_item_get(item, "artist_sort") if item is not None else None,),
                    (_item_get(item, "mb_artistid") if item is not None else None,),
                ),
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
    album_title = _optional_text(_item_get(item, "album"))
    return TrackEnrichmentContext(
        artist=artist,
        title=title,
        album_title=album_title,
        duration=_positive_duration(_item_get(item, "length")),
        track_number=_positive_int(_item_get(item, "track")),
        disc_number=_positive_int(_item_get(item, "disc")),
        external_ids=_external_ids(
            recording_values=(item_ids[0],),
            release_track_values=(item_ids[1],),
            isrc_values=(item_ids[2],),
            acoustid_values=(item_ids[3],),
        ),
        release=_release_context(
            artist, album_title, (_item_get(item, "mb_albumid"),)
        ),
        artists=_artist_contexts(
            artist,
            (
                (
                    _item_get(item, "artists"),
                    _item_get(item, "artists_credit"),
                    _item_get(item, "artists_sort"),
                    _item_get(item, "mb_artistids"),
                ),
                (
                    (artist,),
                    (_item_get(item, "artist_credit"),),
                    (_item_get(item, "artist_sort"),),
                    (_item_get(item, "mb_artistid"),),
                ),
            ),
        ),
    )


def current_values_from_track_info(track_info: TrackInfo) -> dict[str, CanonicalValue]:
    """Return explicitly carried canonical track values from TrackInfo."""
    return _current_track_values(track_info.get)


def current_values_from_library_item(item: Item) -> dict[str, CanonicalValue]:
    """Return canonical track values from the Item itself without Album fallback."""
    values = _current_track_values(lambda field: _item_get(item, field))
    if isinstance(item.id, int):
        values.update(read_credit_state(item._db, "item", item.id))
    return values


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


def _release_context(
    artist: str, album_title: str | None, release_id_values: tuple[object, ...]
) -> ReleaseEnrichmentContext | None:
    if album_title is None:
        return None
    for value in release_id_values:
        release_id = canonical_uuid(value)
        if release_id is not None:
            return ReleaseEnrichmentContext(
                artist,
                album_title,
                external_ids=(ExternalIdentifier(_MUSICBRAINZ_RELEASE_NAMESPACE, release_id),),
            )
    return None


def _artist_contexts(
    artist_name: str,
    sources: tuple[tuple[object, object, object, object], ...],
) -> tuple[ArtistEnrichmentContext, ...]:
    for names_value, credits_value, sorts_value, ids_value in sources:
        ids = _object_tuple(ids_value)
        if not ids:
            continue
        names = _object_tuple(names_value)
        credits = _object_tuple(credits_value)
        sorts = _object_tuple(sorts_value)
        contexts: list[ArtistEnrichmentContext] = []
        seen: set[str] = set()
        for index, value in enumerate(ids, 1):
            artist_id = canonical_uuid(value)
            if artist_id is None or artist_id in seen:
                continue
            seen.add(artist_id)
            contexts.append(
                ArtistEnrichmentContext(
                    _optional_text(_at(names, index - 1)) or artist_name,
                    sort_name=_optional_text(_at(sorts, index - 1)),
                    credit_name=_optional_text(_at(credits, index - 1)),
                    credit_index=index,
                    external_ids=(
                        ExternalIdentifier("musicbrainz.artist", artist_id),
                    ),
                )
            )
        if contexts:
            return tuple(contexts)
    return ()


def _object_tuple(value: object) -> tuple[object, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return ()


def _at(values: tuple[object, ...], index: int) -> object:
    return values[index] if index < len(values) else None


def _item_identifier_values(item: Item | None) -> tuple[object, object, object, object]:
    if item is None:
        return None, None, None, None
    return (
        _item_get(item, "mb_trackid"),
        _item_get(item, "mb_releasetrackid"),
        _item_get(item, "isrc"),
        _item_get(item, "acoustid_id"),
    )


def _current_track_values(getter: Callable[[str], object]) -> dict[str, CanonicalValue]:
    values: dict[str, CanonicalValue] = {}
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
    isrcs = _canonical_identifiers(getter("isrcs"), "isrc", canonical_isrc)
    if not isrcs:
        isrcs = _canonical_identifiers(getter("isrc"), "isrc", canonical_isrc)
    if isrcs:
        values["isrcs"] = IdentifierCollection(isrcs)
    iswcs = _canonical_identifiers(getter("iswcs"), "iswc", _canonical_iswc)
    if iswcs:
        values["iswcs"] = IdentifierCollection(iswcs)
    work_ids = _canonical_identifiers(
        getter("mb_workids"), "musicbrainz.work", canonical_uuid
    )
    if not work_ids:
        work_ids = _canonical_identifiers(
            getter("mb_workid"), "musicbrainz.work", canonical_uuid
        )
    if work_ids:
        work_title = _optional_text(getter("work")) if len(work_ids) == 1 else None
        values["works"] = canonical_work_references(
            WorkReference(identifier.value, work_title, "stored identity", None)
            for identifier in work_ids
        )
    if recording_date := parse_partial_date(getter("recording_date")):
        values["recording_date"] = recording_date
    work_source = work_ids[0].value if len(work_ids) == 1 else None
    recording_source = canonical_uuid(getter("mb_trackid"))
    for field, role in (
        ("composers", CreditRole.COMPOSER),
        ("lyricists", CreditRole.LYRICIST),
        ("arrangers", CreditRole.ARRANGER),
    ):
        names = _text_tuple(getter(field))
        ids = _text_tuple(getter(f"{field}_ids"))
        if names:
            references = []
            for position, name in enumerate(names):
                mbid = canonical_uuid(ids[position]) if len(ids) == len(names) else None
                references.append(
                    CreditReference(
                        CreditParty(name, mbid),
                        role,
                        EntityKind.WORK,
                        source_entity_id=work_source,
                    )
                )
            values[field] = canonical_credit_references(references)
    for field, role in (
        ("producers", CreditRole.PRODUCER),
        ("conductors", CreditRole.CONDUCTOR),
        ("performers", CreditRole.PERFORMER),
        ("featured_artists", CreditRole.FEATURED_ARTIST),
    ):
        names = _text_tuple(getter(field))
        if names:
            values[field] = canonical_credit_references(
                CreditReference(
                    CreditParty(name),
                    role,
                    EntityKind.RECORDING,
                    source_entity_id=recording_source,
                )
                for name in names
            )
    return values


def _canonical_identifiers(
    raw: object, namespace: str, normalizer: Callable[[object], str | None]
) -> tuple[ExternalIdentifier, ...]:
    candidates = raw if isinstance(raw, (tuple, list)) else str(raw).split(";") if raw else ()
    values = {value for candidate in candidates if (value := normalizer(candidate)) is not None}
    return tuple(ExternalIdentifier(namespace, value) for value in sorted(values))


def _canonical_iswc(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().upper()
    return text if text.startswith("T-") and len(text) == 15 else None


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
