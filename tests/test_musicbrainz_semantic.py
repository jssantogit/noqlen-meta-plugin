from collections.abc import Mapping

import pytest
from requests import RequestException

from beetsplug.noqlenmeta.domain import (
    ArtistEnrichmentContext,
    ExternalIdentifier,
    ReleaseEnrichmentContext,
    SemanticCategory,
    TrackEnrichmentContext,
)
from beetsplug.noqlenmeta.genre_evidence import GenreEvidenceKind
from beetsplug.noqlenmeta.provider_cache import CommandEntityCache
from beetsplug.noqlenmeta.providers import ProviderError
from beetsplug.noqlenmeta.providers.musicbrainz import MusicBrainzProvider
from beetsplug.noqlenmeta.providers.musicbrainz_semantic import (
    MusicBrainzArtistProvider,
    MusicBrainzSemanticClient,
    MusicBrainzTrackProvider,
)
from beetsplug.noqlenmeta.providers.specs import ProviderScope

RELEASE_MBID = "6ea45c08-3cfa-461a-aa4d-4cc404fcfa86"
RECORDING_MBID = "11111111-1111-4111-8111-111111111111"
WORK_ONE = "22222222-2222-4222-8222-222222222222"
WORK_TWO = "33333333-3333-4333-8333-333333333333"
ARTIST_MBID = "44444444-4444-4444-8444-444444444444"
SALVADOR_MBID = "55555555-5555-4555-8555-555555555555"
BRAZIL_MBID = "66666666-6666-4666-8666-666666666666"


def track_context() -> TrackEnrichmentContext:
    return TrackEnrichmentContext(
        "Synthetic Artist",
        "Synthetic Track",
        external_ids=(ExternalIdentifier("musicbrainz.recording", RECORDING_MBID),),
    )


def artist_context() -> ArtistEnrichmentContext:
    return ArtistEnrichmentContext(
        "Synthetic Artist",
        external_ids=(ExternalIdentifier("musicbrainz.artist", ARTIST_MBID),),
    )


def client(
    *,
    recording: Mapping[str, object] | None = None,
    works: Mapping[str, Mapping[str, object] | None] | None = None,
    artist: Mapping[str, object] | None = None,
    areas: Mapping[str, Mapping[str, object] | None] | None = None,
) -> tuple[MusicBrainzSemanticClient, dict[str, list[str]]]:
    calls: dict[str, list[str]] = {
        "recording": [],
        "work": [],
        "artist": [],
        "area": [],
    }

    def fetch(entity: str, values: Mapping[str, Mapping[str, object] | None]):
        def inner(entity_id: str) -> Mapping[str, object] | None:
            calls[entity].append(entity_id)
            return values.get(entity_id)

        return inner

    result = MusicBrainzSemanticClient(
        cache=CommandEntityCache(),
        fetch_recording=fetch(
            "recording", {RECORDING_MBID: recording} if recording is not None else {}
        ),
        fetch_work=fetch("work", works or {}),
        fetch_artist=fetch("artist", {ARTIST_MBID: artist} if artist is not None else {}),
        fetch_area=fetch("area", areas or {}),
    )
    return result, calls


def test_recording_work_languages_are_ordered_deduplicated_and_cached() -> None:
    recording = {
        "id": RECORDING_MBID,
        "relations": [{"target-type": "work", "work": {"id": WORK_ONE}},
                      {"target-type": "work", "work": {"id": WORK_TWO}}],
    }
    semantic_client, calls = client(
        recording=recording,
        works={
            WORK_ONE: {"id": WORK_ONE, "languages": ["kor", "eng", "kor"]},
            WORK_TWO: {"id": WORK_TWO, "languages": ["eng"]},
        },
    )
    provider = MusicBrainzTrackProvider(semantic_client)

    first = provider.get_semantic_evidence(track_context())
    second = provider.get_semantic_evidence(track_context())

    assert {item.field: item.value for item in first.metadata} == {
        "lyrics_languages": ("kor", "eng")
    }
    assert second == first
    assert calls["recording"] == [RECORDING_MBID]
    assert calls["work"] == [WORK_ONE, WORK_TWO]


@pytest.mark.parametrize(
    "work_payload",
    [
        {"id": WORK_ONE},
        {"id": WORK_ONE, "languages": ["zxx"], "attributes": ["instrumental"]},
        {"id": WORK_ONE, "languages": ["English", "en", "12x", "mul", "und"]},
    ],
)
def test_unusable_work_languages_never_fabricate_metadata(
    work_payload: Mapping[str, object],
) -> None:
    semantic_client, _ = client(
        recording={
            "id": RECORDING_MBID,
            "relations": [{"target-type": "work", "work": {"id": WORK_ONE}}],
        },
        works={WORK_ONE: work_payload},
    )
    bundle = MusicBrainzTrackProvider(semantic_client).get_semantic_evidence(
        track_context()
    )
    assert bundle.metadata == ()


def test_recording_genres_and_tags_keep_track_scope_and_filter_noise() -> None:
    semantic_client, _ = client(
        recording={
            "id": RECORDING_MBID,
            "genres": [{"name": "k-pop", "count": 9}],
            "tags": [
                {"name": "dreamy", "count": 8},
                {"name": "seen live", "count": 2},
            ],
            "relations": [],
        }
    )
    bundle = MusicBrainzTrackProvider(semantic_client).get_semantic_evidence(
        track_context()
    )
    assert [(item.genre, item.scope, item.kind, item.weight) for item in bundle.genres] == [
        ("K-pop", ProviderScope.TRACK, GenreEvidenceKind.GENRE, 9)
    ]
    assert [(item.canonical_term, item.category, item.scope) for item in bundle.tags] == [
        ("Dreamy", SemanticCategory.MOOD, ProviderScope.TRACK)
    ]


def test_release_semantics_reuse_the_existing_exact_release_payload() -> None:
    calls = 0
    payload = {
        "id": RELEASE_MBID,
        "genres": [{"name": "k-pop", "count": 9}],
        "tags": [{"name": "dreamy", "count": 8}],
    }

    def fetch_release(release_id: str) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return payload

    provider = MusicBrainzProvider(fetch_release=fetch_release)
    context = ReleaseEnrichmentContext(
        "Synthetic Artist",
        "Synthetic Release",
        external_ids=(ExternalIdentifier("musicbrainz.release", RELEASE_MBID),),
    )
    provider.get_candidates(context)
    bundle = provider.get_semantic_evidence(context)

    assert calls == 1
    assert bundle.genres[0].scope is ProviderScope.RELEASE
    assert bundle.tags[0].category is SemanticCategory.MOOD


def test_artist_semantics_and_structural_geography() -> None:
    semantic_client, calls = client(
        artist={
            "id": ARTIST_MBID,
            "genres": [{"name": "k-pop", "count": 4}],
            "tags": [{"name": "dreamy", "count": 3}],
            "area": {"id": SALVADOR_MBID, "name": "Salvador", "type": "City"},
            "begin-area": {"id": "77777777-7777-4777-8777-777777777777", "name": "Other"},
        },
        areas={
            SALVADOR_MBID: {
                "id": SALVADOR_MBID,
                "name": "Salvador",
                "type": "City",
                "relations": [
                    {"target-type": "area", "type": "part of", "area": {"id": BRAZIL_MBID}}
                ],
            },
            BRAZIL_MBID: {
                "id": BRAZIL_MBID,
                "name": "Brazil",
                "type": "Country",
                "iso-3166-1-codes": ["BR"],
            },
        },
    )
    bundle = MusicBrainzArtistProvider(semantic_client).get_semantic_evidence(
        artist_context()
    )
    assert {item.field: item.value for item in bundle.metadata} == {
        "artist_areas": ("Salvador",),
        "artist_countries": ("Brazil",),
    }
    assert bundle.genres[0].scope is ProviderScope.ARTIST
    assert bundle.tags[0].scope is ProviderScope.ARTIST
    assert calls["area"] == [SALVADOR_MBID, BRAZIL_MBID]


def test_specific_main_area_survives_when_country_is_unresolved() -> None:
    semantic_client, _ = client(
        artist={
            "id": ARTIST_MBID,
            "area": {"id": SALVADOR_MBID, "name": "Salvador, Brazil", "type": "City"},
        },
        areas={SALVADOR_MBID: {"id": SALVADOR_MBID, "name": "Salvador, Brazil"}},
    )
    bundle = MusicBrainzArtistProvider(semantic_client).get_semantic_evidence(
        artist_context()
    )
    assert {item.field: item.value for item in bundle.metadata} == {
        "artist_areas": ("Salvador, Brazil",)
    }


def test_begin_area_is_used_only_when_main_area_is_absent() -> None:
    semantic_client, _ = client(
        artist={
            "id": ARTIST_MBID,
            "begin-area": {"id": SALVADOR_MBID, "name": "Salvador", "type": "City"},
        },
        areas={SALVADOR_MBID: {"id": SALVADOR_MBID, "name": "Salvador"}},
    )
    bundle = MusicBrainzArtistProvider(semantic_client).get_semantic_evidence(
        artist_context()
    )
    assert bundle.metadata[0].value == ("Salvador",)


def test_response_mismatch_and_transient_failure_are_not_negative_cached() -> None:
    calls = 0

    def fetch_recording(recording_id: str) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RequestException("temporary")
        return {"id": WORK_ONE}

    semantic_client = MusicBrainzSemanticClient(fetch_recording=fetch_recording)
    with pytest.raises(ProviderError, match="request failed"):
        semantic_client.lookup_recording(RECORDING_MBID)
    with pytest.raises(ProviderError, match="response is invalid"):
        semantic_client.lookup_recording(RECORDING_MBID)
    assert calls == 2
