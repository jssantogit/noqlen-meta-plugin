import copy
from types import SimpleNamespace

import pytest
from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.distance import Distance
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.importer.actions import Action
from beets.library import Item

from beetsplug.noqlenmeta.domain import ExternalIdentifier, TrackEnrichmentContext
from beetsplug.noqlenmeta.track_integration import (
    SelectedImportTrack,
    context_from_library_item,
    context_from_selected_import_track,
    context_from_track_info,
    current_values_from_library_item,
    current_values_from_track_info,
    selected_import_tracks,
)

RECORDING_MBID = "6ea45c08-3cfa-461a-aa4d-4cc404fcfa86"
RELEASE_TRACK_MBID = "15ad0189-3921-42d5-a5b5-21b92133e4f0"
SECOND_RECORDING_MBID = "680be1b3-3326-4fd0-8f10-55e2b4514439"
ACOUSTID_ID = "e365ad13-c3e2-44d7-a781-79666b70a233"
RELEASE_MBID = "11111111-1111-4111-8111-111111111111"
ARTIST_ONE_MBID = "22222222-2222-4222-8222-222222222222"
ARTIST_TWO_MBID = "33333333-3333-4333-8333-333333333333"


def track_info(**overrides: object) -> TrackInfo:
    values: dict[str, object] = {
        "artist": "Gojira",
        "title": "Flying Whales",
        "length": 442.0,
        "medium": 1,
        "medium_index": 6,
        "index": 6,
    }
    values.update(overrides)
    return TrackInfo(**values)  # type: ignore[arg-type]


def id_pairs(context: TrackEnrichmentContext) -> list[tuple[str, str]]:
    return [(identifier.namespace, identifier.value) for identifier in context.external_ids]


def test_track_info_context_maps_selected_identity_and_position() -> None:
    context = context_from_track_info(track_info(album=" From Mars to Sirius "))

    assert context == TrackEnrichmentContext(
        artist="Gojira",
        title="Flying Whales",
        album_title="From Mars to Sirius",
        duration=442.0,
        track_number=6,
        disc_number=1,
    )


def test_track_info_uses_explicit_parent_album_fallbacks_only_when_needed() -> None:
    album = AlbumInfo([], artist="Album Artist", album="From Mars to Sirius")

    assert context_from_track_info(track_info(artist=None, album=None), album_info=album) == (
        TrackEnrichmentContext(
            "Album Artist",
            "Flying Whales",
            album_title="From Mars to Sirius",
            duration=442.0,
            track_number=6,
            disc_number=1,
        )
    )
    assert context_from_track_info(track_info(artist="Track Artist"), album_info=album).artist == (
        "Track Artist"
    )


def test_track_info_missing_required_selected_identity_returns_none() -> None:
    assert context_from_track_info(track_info(title=" ")) is None
    assert context_from_track_info(track_info(artist=None)) is None


def test_track_info_omits_malformed_optional_numeric_values_and_falls_back_to_index() -> None:
    context = context_from_track_info(
        track_info(length="bad", medium=True, medium_index=0, index=8)
    )

    assert context is not None
    assert context.duration is None
    assert context.track_number == 8
    assert context.disc_number is None


def test_musicbrainz_track_info_maps_generic_recording_and_release_track_ids() -> None:
    context = context_from_track_info(
        track_info(
            data_source="MusicBrainz",
            track_id=RECORDING_MBID.upper(),
            release_track_id=RELEASE_TRACK_MBID,
        )
    )

    assert context is not None
    assert id_pairs(context) == [
        ("musicbrainz.recording", RECORDING_MBID),
        ("musicbrainz.release_track", RELEASE_TRACK_MBID),
    ]


def test_selected_exact_release_mbid_is_carried_into_track_context() -> None:
    info = track_info()
    album = AlbumInfo(
        [info],
        artist="Gojira",
        album="From Mars to Sirius",
        data_source="MusicBrainz",
        album_id=RELEASE_MBID,
    )

    context = context_from_track_info(info, album_info=album)

    assert context is not None
    assert context.release is not None
    assert context.release.external_ids == (
        ExternalIdentifier("musicbrainz.release", RELEASE_MBID),
    )


def test_collaboration_creates_one_context_per_artist_in_stable_credit_order() -> None:
    context = context_from_track_info(
        track_info(
            artists=["First Artist", "Second Artist", "First Artist"],
            artists_credit=["First", "Second", "First"],
            artists_ids=[ARTIST_ONE_MBID, ARTIST_TWO_MBID, ARTIST_ONE_MBID],
        )
    )

    assert context is not None
    credits = [
        (artist.name, artist.credit_name, artist.credit_index)
        for artist in context.artists
    ]
    assert credits == [
        ("First Artist", "First", 1),
        ("Second Artist", "Second", 2),
    ]
    assert [artist.external_ids[0].value for artist in context.artists] == [
        ARTIST_ONE_MBID,
        ARTIST_TWO_MBID,
    ]


def test_selected_scalar_artist_id_wins_over_stale_item_credit_ids() -> None:
    context = context_from_track_info(
        track_info(mb_artistid=ARTIST_ONE_MBID),
        item=Item(
            artist="Stale Artist",
            mb_artistids=[ARTIST_TWO_MBID],
            artists=["Stale Artist"],
        ),
    )

    assert context is not None
    assert [artist.external_ids[0].value for artist in context.artists] == [
        ARTIST_ONE_MBID
    ]


@pytest.mark.parametrize("track_id", ["123456", RECORDING_MBID])
def test_non_musicbrainz_generic_track_id_is_never_misclassified(track_id: str) -> None:
    context = context_from_track_info(track_info(data_source="Deezer", track_id=track_id))

    assert context is not None
    assert not any(
        identifier.namespace == "musicbrainz.recording"
        for identifier in context.external_ids
    )


def test_explicit_musicbrainz_ids_are_validated_for_other_sources() -> None:
    context = context_from_track_info(
        track_info(
            data_source="Deezer",
            mb_trackid=RECORDING_MBID.upper(),
            mb_releasetrackid=RELEASE_TRACK_MBID,
        )
    )

    assert context is not None
    assert id_pairs(context) == [
        ("musicbrainz.recording", RECORDING_MBID),
        ("musicbrainz.release_track", RELEASE_TRACK_MBID),
    ]
    malformed = context_from_track_info(
        track_info(mb_trackid="invalid", mb_releasetrackid="invalid")
    )
    assert malformed is not None
    assert malformed.external_ids == ()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("USABC1201234", ["USABC1201234"]),
        (
            "US-ABC-12-01234; GBAYE6800011; USABC1201234",
            ["USABC1201234", "GBAYE6800011"],
        ),
        ("invalid; USABC1201234", ["USABC1201234"]),
        ("USABC1201234,GBAYE6800011", []),
        ("USABC1201234/GBAYE6800011", []),
    ],
)
def test_track_info_isrc_parsing_is_semicolon_only(value: str, expected: list[str]) -> None:
    context = context_from_track_info(track_info(isrc=value))

    assert context is not None
    assert [identifier.value for identifier in context.external_ids] == expected


def test_acoustid_id_is_carried_but_fingerprint_is_excluded() -> None:
    context = context_from_track_info(
        track_info(acoustid_id=ACOUSTID_ID.upper(), acoustid_fingerprint="SECRET-FINGERPRINT")
    )

    assert context is not None
    assert id_pairs(context) == [("acoustid.track", ACOUSTID_ID)]
    assert all("fingerprint" not in identifier.namespace for identifier in context.external_ids)
    malformed = context_from_track_info(track_info(acoustid_id="invalid"))
    assert malformed is not None
    assert malformed.external_ids == ()


def test_matched_item_supplements_ids_without_replacing_selected_identity() -> None:
    info = track_info(
        artist="Selected Artist",
        title="Selected Title",
        album="Selected Album",
        mb_trackid=RECORDING_MBID,
        isrc="USABC1201234",
    )
    item = Item(
        artist="Local Artist",
        title="Local Title",
        album="Local Album",
        length=1.0,
        track=1,
        disc=2,
        mb_trackid=RECORDING_MBID,
        mb_releasetrackid=RELEASE_TRACK_MBID,
        isrc="USABC1201234;GBAYE6800011",
        acoustid_id=ACOUSTID_ID,
    )

    context = context_from_track_info(info, item=item)

    assert context is not None
    assert (context.artist, context.title, context.album_title) == (
        "Selected Artist",
        "Selected Title",
        "Selected Album",
    )
    assert context.duration == 442.0
    assert context.track_number == 6
    assert context.disc_number == 1
    assert id_pairs(context) == [
        ("musicbrainz.recording", RECORDING_MBID),
        ("musicbrainz.release_track", RELEASE_TRACK_MBID),
        ("isrc", "USABC1201234"),
        ("isrc", "GBAYE6800011"),
        ("acoustid.track", ACOUSTID_ID),
    ]


def test_library_item_context_maps_item_local_fields_and_ids() -> None:
    item = Item(
        artist=" Gojira ",
        title=" Flying Whales ",
        album=" From Mars to Sirius ",
        length=442,
        track=6,
        disc=1,
        mb_trackid=RECORDING_MBID.upper(),
        mb_releasetrackid=RELEASE_TRACK_MBID,
        isrc="US-ABC-12-01234;GBAYE6800011",
        acoustid_id=ACOUSTID_ID.upper(),
        acoustid_fingerprint="SECRET-FINGERPRINT",
    )

    context = context_from_library_item(item)

    assert context is not None
    assert context == TrackEnrichmentContext(
        artist="Gojira",
        title="Flying Whales",
        album_title="From Mars to Sirius",
        duration=442.0,
        track_number=6,
        disc_number=1,
        external_ids=context.external_ids,
    )
    assert id_pairs(context) == [
        ("musicbrainz.recording", RECORDING_MBID),
        ("musicbrainz.release_track", RELEASE_TRACK_MBID),
        ("isrc", "USABC1201234"),
        ("isrc", "GBAYE6800011"),
        ("acoustid.track", ACOUSTID_ID),
    ]


def test_library_singleton_with_blank_album_remains_usable() -> None:
    context = context_from_library_item(Item(artist="Gojira", title="Oroborus", album=" "))

    assert context == TrackEnrichmentContext("Gojira", "Oroborus")


def test_library_item_adapter_always_disables_album_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []
    original_get = Item.get

    def local_only_get(
        self: Item, key: str, default: object = None, with_album: bool = True
    ) -> object:
        calls.append((key, with_album))
        if with_album:
            pytest.fail("Item adapter attempted Album fallback")
        return original_get(self, key, default, with_album=with_album)

    monkeypatch.setattr(Item, "get", local_only_get)
    item = Item(artist="Gojira", title="Flying Whales", album="From Mars to Sirius")

    assert context_from_library_item(item) is not None
    assert calls
    assert all(not with_album for _, with_album in calls)


def test_current_values_from_track_info_are_explicit_trimmed_strings() -> None:
    info = track_info(
        lyrics="  line one\nline two  ",
        synced_lyrics="  [00:01.00]line one\n[00:02.00]line two  ",
        bpm=126.4,
        moods=[" Dark ", "Energetic"],
        lyrics_languages=["English", " Korean "],
    )

    assert current_values_from_track_info(info) == {
        "lyrics": "line one\nline two",
        "synced_lyrics": "[00:01.00]line one\n[00:02.00]line two",
        "bpm": 126.4,
        "moods": ("Dark", "Energetic"),
        "lyrics_languages": ("English", "Korean"),
    }
    assert current_values_from_track_info(track_info(lyrics=" ", synced_lyrics=None)) == {}


def test_current_values_from_item_are_local_and_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = Item(
        artist="Gojira",
        title="Flying Whales",
        lyrics=" line one\nline two ",
        synced_lyrics=" [00:01.00]line one ",
        bpm=126.4,
        moods=["Dark", "Energetic"],
    )
    snapshot = copy.deepcopy(dict(item))
    original_get = Item.get

    def local_only_get(
        self: Item, key: str, default: object = None, with_album: bool = True
    ) -> object:
        assert with_album is False
        return original_get(self, key, default, with_album=with_album)

    monkeypatch.setattr(Item, "get", local_only_get)

    assert current_values_from_library_item(item) == {
        "lyrics": "line one\nline two",
        "synced_lyrics": "[00:01.00]line one",
        "bpm": 126.4,
        "moods": ("Dark", "Energetic"),
    }
    assert dict(item) == snapshot


def test_selected_album_match_exposes_only_mapping_pairs_in_order() -> None:
    first_item = Item(artist="Gojira", title="Ocean Planet")
    second_item = Item(artist="Gojira", title="Backbone")
    extra_item = Item(artist="Gojira", title="Extra Item")
    first_info = track_info(title="Ocean Planet", index=1, medium_index=1)
    second_info = track_info(title="Backbone", index=2, medium_index=2)
    extra_info = track_info(title="Extra Track")
    album_info = AlbumInfo([first_info, second_info, extra_info], artist="Gojira", album="Album")
    match = AlbumMatch(
        Distance(),
        album_info,
        {first_item: first_info, second_item: second_info},
        [extra_item],
        [extra_info],
    )
    task = SimpleNamespace(choice_flag=Action.APPLY, match=match)

    selected = selected_import_tracks(task)

    assert selected == (
        SelectedImportTrack(first_item, first_info, album_info),
        SelectedImportTrack(second_item, second_info, album_info),
    )
    task.choice_flag = Action.SKIP
    assert selected_import_tracks(task) == ()


def test_selected_singleton_track_match_exposes_one_pair() -> None:
    item = Item(artist="Gojira", title="Flying Whales")
    info = track_info()
    match = TrackMatch(Distance(), info, item)

    assert selected_import_tracks(SimpleNamespace(choice_flag=Action.APPLY, match=match)) == (
        SelectedImportTrack(item, info, None),
    )


def test_selected_tracks_ignore_unknown_or_missing_matches() -> None:
    assert selected_import_tracks(SimpleNamespace(choice_flag=Action.APPLY, match=None)) == ()
    assert selected_import_tracks(SimpleNamespace(choice_flag=Action.APPLY, match=object())) == ()
    assert selected_import_tracks(object()) == ()


def test_selected_context_convenience_is_read_only() -> None:
    item = Item(artist="Local", title="Local", acoustid_id=ACOUSTID_ID)
    info = track_info(artist="Selected", title="Selected")
    album = AlbumInfo([info], artist="Album Artist", album="Album")
    selected = SelectedImportTrack(item, info, album)
    snapshots = (copy.deepcopy(dict(item)), copy.deepcopy(dict(info)), copy.deepcopy(dict(album)))

    context = context_from_selected_import_track(selected)

    assert context is not None
    assert context.artist == "Selected"
    assert ExternalIdentifier("acoustid.track", ACOUSTID_ID) in context.external_ids
    assert (dict(item), dict(info), dict(album)) == snapshots
