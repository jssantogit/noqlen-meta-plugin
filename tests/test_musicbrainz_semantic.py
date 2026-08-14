from collections.abc import Mapping

import pytest
from beetsplug._utils.musicbrainz import MusicBrainzAPI
from requests import RequestException

from beetsplug.noqlenmeta.domain import (
    ArtistEnrichmentContext,
    ExternalIdentifier,
    ReleaseEnrichmentContext,
    SemanticCategory,
    TrackEnrichmentContext,
)
from beetsplug.noqlenmeta.field_contracts import PartialDate
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
from beetsplug.noqlenmeta.work_identity import WorkReference

RELEASE_MBID = "6ea45c08-3cfa-461a-aa4d-4cc404fcfa86"
RECORDING_MBID = "11111111-1111-4111-8111-111111111111"
WORK_ONE = "22222222-2222-4222-8222-222222222222"
WORK_TWO = "33333333-3333-4333-8333-333333333333"
PERFORMANCE_TYPE_ID = "a3005666-a872-32c3-ad06-98af558e99b0"
RECORDED_AT_TYPE_ID = "ad462279-14b0-4180-9b58-571d0eef7c51"
ARTIST_MBID = "44444444-4444-4444-8444-444444444444"
SALVADOR_MBID = "55555555-5555-4555-8555-555555555555"
BRAZIL_MBID = "66666666-6666-4666-8666-666666666666"
FAILED_AREA_MBID = "77777777-7777-4777-8777-777777777777"


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
    works: Mapping[str, Mapping[str, object] | Exception | None] | None = None,
    artist: Mapping[str, object] | None = None,
    areas: Mapping[str, Mapping[str, object] | Exception | None] | None = None,
) -> tuple[MusicBrainzSemanticClient, dict[str, list[str]]]:
    calls: dict[str, list[str]] = {
        "recording": [],
        "work": [],
        "artist": [],
        "area": [],
    }

    def fetch(
        entity: str,
        values: Mapping[str, Mapping[str, object] | Exception | None],
    ):
        def inner(entity_id: str, *_args: object) -> Mapping[str, object] | None:
            calls[entity].append(entity_id)
            value = values.get(entity_id)
            if isinstance(value, Exception):
                raise value
            return value

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


def test_failed_work_retains_recording_semantics_and_successful_language() -> None:
    semantic_client, calls = client(
        recording={
            "id": RECORDING_MBID,
            "genres": [{"name": "k-pop", "count": 9}],
            "tags": [{"name": "dreamy", "count": 8}],
            "relations": [
                {"target-type": "work", "work": {"id": WORK_ONE}},
                {"target-type": "work", "work": {"id": WORK_TWO}},
            ],
        },
        works={
            WORK_ONE: {"id": WORK_ONE, "languages": ["kor"]},
            WORK_TWO: RequestException("temporary"),
        },
    )

    bundle = MusicBrainzTrackProvider(semantic_client).get_semantic_evidence(
        track_context()
    )

    assert [item.genre for item in bundle.genres] == ["K-pop"]
    assert [item.canonical_term for item in bundle.tags] == ["Dreamy"]
    assert {item.field: item.value for item in bundle.metadata} == {
        "lyrics_languages": ("kor",)
    }
    assert bundle.unavailable_fields == frozenset(
        {"lyrics_languages", "artist_languages"}
    )
    assert calls["work"] == [WORK_ONE, WORK_TWO]


def test_genre_only_collection_does_not_fetch_works() -> None:
    semantic_client, calls = client(
        recording={
            "id": RECORDING_MBID,
            "genres": [{"name": "k-pop", "count": 9}],
            "relations": [{"target-type": "work", "work": {"id": WORK_ONE}}],
        },
        works={WORK_ONE: {"id": WORK_ONE, "languages": ["kor"]}},
    )
    bundle = MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"genres"}
    ).get_semantic_evidence(track_context())
    assert bundle.genres
    assert calls["work"] == []


def test_wave_one_enrichment_reuses_recording_and_work_payloads() -> None:
    semantic_client, calls = client(
        recording={
            "id": RECORDING_MBID,
            "genres": [{"name": "k-pop", "count": 9}],
            "isrcs": ["US-AAA-01-00001", "USAAA0100001", "GBBBB0200002"],
            "relations": [
                {
                    "target-type": "work",
                    "type": "performance",
                    "type-id": PERFORMANCE_TYPE_ID,
                    "attributes": ["live"],
                    "ordering-key": 1,
                    "work": {"id": WORK_ONE, "title": "Synthetic Work"},
                }
            ],
        },
        works={
            WORK_ONE: {
                "id": WORK_ONE,
                "iswcs": ["T-123.456.789-0", "T-123.456.789-0"],
                "languages": ["eng"],
            }
        },
    )
    provider = MusicBrainzTrackProvider(
        semantic_client,
        enabled_fields={"genres", "lyrics_languages", "isrcs", "works", "iswcs"},
    )

    enrichment = provider.get_enrichment(track_context())

    assert enrichment.semantic.genres
    assert {item.field for item in enrichment.evidence} == {"isrcs", "works", "iswcs"}
    isrcs = next(item.value for item in enrichment.evidence if item.field == "isrcs")
    assert [identifier.value for identifier in isrcs.values] == [
        "GBBBB0200002",
        "USAAA0100001",
    ]
    works = next(item.value for item in enrichment.evidence if item.field == "works")
    assert works == (
        WorkReference(
            WORK_ONE,
            "Synthetic Work",
            "performance",
            PERFORMANCE_TYPE_ID,
            ("live",),
            1,
        ),
    )
    iswc = next(item for item in enrichment.evidence if item.field == "iswcs")
    assert iswc.subject.entity.value == "work"
    assert calls["recording"] == [RECORDING_MBID]
    assert calls["work"] == [WORK_ONE]


def test_isrc_only_enrichment_never_fetches_work() -> None:
    semantic_client, calls = client(
        recording={
            "id": RECORDING_MBID,
            "isrcs": ["USAAA0100001"],
            "relations": [{"target-type": "work", "work": {"id": WORK_ONE}}],
        },
        works={WORK_ONE: {"id": WORK_ONE, "iswcs": ["T-123.456.789-0"]}},
    )

    enrichment = MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"isrcs"}
    ).get_enrichment(track_context())

    assert [item.field for item in enrichment.evidence] == ["isrcs"]
    assert calls["work"] == []


def test_isrc_only_without_recording_mbid_makes_no_request() -> None:
    semantic_client, calls = client(recording={"id": RECORDING_MBID})
    context = TrackEnrichmentContext("Synthetic Artist", "Synthetic Track")

    enrichment = MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"isrcs"}
    ).get_enrichment(context)

    assert enrichment.evidence == ()
    assert calls["recording"] == []


def test_explicit_empty_enabled_fields_produce_no_evidence_or_work_lookup() -> None:
    semantic_client, calls = client(
        recording={
            "id": RECORDING_MBID,
            "isrcs": ["USAAA0100001"],
            "work_relations": [
                {
                    "type": "performance",
                    "type_id": PERFORMANCE_TYPE_ID,
                    "work": {"id": WORK_ONE},
                }
            ],
        },
        works={WORK_ONE: {"id": WORK_ONE, "iswcs": ["T-123.456.789-0"]}},
    )

    enrichment = MusicBrainzTrackProvider(
        semantic_client, enabled_fields=()
    ).get_enrichment(track_context())

    assert enrichment == type(enrichment)()
    assert calls["recording"] == []
    assert calls["work"] == []


def test_normalized_production_shape_emits_complete_wave_one_evidence() -> None:
    raw = {
        "id": RECORDING_MBID,
        "first-release-date": "1999-01-02",
        "isrcs": ["USAAA0100001"],
        "relations": [
            {
                "target-type": "work",
                "type": "performance",
                "type-id": PERFORMANCE_TYPE_ID,
                "ordering-key": 2,
                "attributes": ["live"],
                "work": {"id": WORK_ONE, "title": "Synthetic Work"},
            },
            {
                "target-type": "place",
                "type": "recorded at",
                "type-id": RECORDED_AT_TYPE_ID,
                "begin": "2020-05-17",
                "end": "2020-05-17",
                "place": {"id": SALVADOR_MBID, "name": "Synthetic Studio"},
            },
        ],
    }
    normalized = MusicBrainzAPI._normalize_data(raw)
    assert "relations" not in normalized
    assert "work_relations" in normalized
    assert "place_relations" in normalized
    semantic_client, calls = client(
        recording=normalized,
        works={WORK_ONE: {"id": WORK_ONE, "iswcs": ["T-123.456.789-0"]}},
    )

    enrichment = MusicBrainzTrackProvider(
        semantic_client,
        enabled_fields={"isrcs", "works", "iswcs", "recording_date"},
    ).get_enrichment(track_context())

    assert {item.field for item in enrichment.evidence} == {
        "isrcs",
        "works",
        "iswcs",
        "recording_date",
    }
    works = next(item.value for item in enrichment.evidence if item.field == "works")
    assert works == (
        WorkReference(
            WORK_ONE,
            "Synthetic Work",
            "performance",
            PERFORMANCE_TYPE_ID,
            ("live",),
            2,
        ),
    )
    assert calls["recording"] == [RECORDING_MBID]
    assert calls["work"] == [WORK_ONE]


def test_production_recording_fetch_uses_one_deterministic_include_union(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []

    def get_recording(
        _api: object, recording_id: str, *, includes: list[str]
    ) -> Mapping[str, object]:
        calls.append((recording_id, tuple(includes)))
        return {"id": recording_id, "isrcs": ["USAAA0100001"]}

    monkeypatch.setattr(MusicBrainzAPI, "get_recording", get_recording)
    provider = MusicBrainzTrackProvider(
        MusicBrainzSemanticClient(),
        enabled_fields={"genres", "isrcs", "works", "iswcs", "recording_date"},
    )

    provider.get_enrichment(track_context())

    assert calls == [
        (
            RECORDING_MBID,
            ("genres", "isrcs", "place-rels", "tags", "work-rels"),
        )
    ]


def test_recording_cache_does_not_reuse_insufficient_include_profile() -> None:
    calls: list[tuple[str, ...]] = []

    def fetch_recording(
        recording_id: str, profile: object
    ) -> Mapping[str, object]:
        includes = profile.includes
        calls.append(includes)
        return {"id": recording_id}

    semantic_client = MusicBrainzSemanticClient(fetch_recording=fetch_recording)
    MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"genres"}
    ).get_enrichment(track_context())
    MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"isrcs"}
    ).get_enrichment(track_context())

    assert calls == [("genres", "tags"), ("isrcs",)]


def test_only_performance_work_relationship_is_accepted() -> None:
    semantic_client, _ = client(
        recording={
            "id": RECORDING_MBID,
            "work_relations": [
                {
                    "type": "performance",
                    "type_id": PERFORMANCE_TYPE_ID,
                    "work": {"id": WORK_ONE},
                },
                {
                    "type": "other",
                    "type_id": "11111111-2222-4333-8444-555555555555",
                    "work": {"id": WORK_TWO},
                },
            ],
        }
    )

    enrichment = MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"works"}
    ).get_enrichment(track_context())

    works = next(item.value for item in enrichment.evidence if item.field == "works")
    assert tuple(reference.mbid for reference in works) == (WORK_ONE,)


@pytest.mark.parametrize(
    ("relation", "accepted"),
    [
        ({"type": "performance"}, True),
        ({"type": "performance", "type_id": "not-a-uuid"}, False),
        ({"type": "performance", "type_id": PERFORMANCE_TYPE_ID}, True),
        (
            {
                "type": "performance",
                "type_id": "11111111-2222-4333-8444-555555555555",
            },
            False,
        ),
    ],
)
def test_performance_relation_type_id_fails_closed(
    relation: Mapping[str, object], accepted: bool
) -> None:
    semantic_client, _ = client(
        recording={
            "id": RECORDING_MBID,
            "work_relations": [
                {**relation, "work": {"id": WORK_ONE, "title": "Synthetic Work"}}
            ],
        }
    )

    enrichment = MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"works"}
    ).get_enrichment(track_context())

    works = [item for item in enrichment.evidence if item.field == "works"]
    assert bool(works) is accepted


def test_work_failure_preserves_isrc_and_work_reference() -> None:
    semantic_client, _ = client(
        recording={
            "id": RECORDING_MBID,
            "isrcs": ["USAAA0100001"],
            "relations": [
                {
                    "target-type": "work",
                    "type": "performance",
                    "work": {"id": WORK_ONE, "title": "Synthetic Work"},
                }
            ],
        },
        works={WORK_ONE: RequestException("temporary")},
    )

    enrichment = MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"isrcs", "works", "iswcs"}
    ).get_enrichment(track_context())

    assert {item.field for item in enrichment.evidence} == {"isrcs", "works"}
    assert "iswcs" in enrichment.unavailable_fields


@pytest.mark.parametrize(
    "recording",
    [
        {"id": RECORDING_MBID, "first-release-date": "1999-01-02"},
        {
            "id": RECORDING_MBID,
            "relations": [
                {"target-type": "place", "type": "recorded at", "begin": "2020-01-02"}
            ],
        },
        {
            "id": RECORDING_MBID,
            "relations": [
                {
                    "target-type": "place",
                    "type": "recorded at",
                    "begin": "2020-01-02",
                    "end": "2020-01-03",
                }
            ],
        },
    ],
)
def test_unsafe_recording_dates_emit_no_evidence(recording: Mapping[str, object]) -> None:
    semantic_client, _ = client(recording=recording)

    enrichment = MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"recording_date"}
    ).get_enrichment(track_context())

    assert enrichment.evidence == ()


def test_same_explicit_recorded_at_begin_end_emits_recording_date() -> None:
    semantic_client, _ = client(
        recording={
            "id": RECORDING_MBID,
            "relations": [
                {
                    "target-type": "place",
                    "type": "recorded at",
                    "type-id": RECORDED_AT_TYPE_ID,
                    "begin": "2020-01-02",
                    "end": "2020-01-02",
                }
            ],
        }
    )

    enrichment = MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"recording_date"}
    ).get_enrichment(track_context())

    assert [(item.field, item.value) for item in enrichment.evidence] == [
        ("recording_date", PartialDate(2020, 1, 2))
    ]


@pytest.mark.parametrize(
    ("relation", "accepted"),
    [
        ({"type": "recorded at"}, True),
        ({"type": "recorded at", "type_id": "not-a-uuid"}, False),
        ({"type": "recorded at", "type_id": RECORDED_AT_TYPE_ID}, True),
        (
            {
                "type": "recorded at",
                "type_id": "11111111-2222-4333-8444-555555555555",
            },
            False,
        ),
    ],
)
def test_recorded_at_relation_type_id_fails_closed(
    relation: Mapping[str, object], accepted: bool
) -> None:
    semantic_client, _ = client(
        recording={
            "id": RECORDING_MBID,
            "place_relations": [
                {**relation, "begin": "2020-01-02", "end": "2020-01-02"}
            ],
        }
    )

    enrichment = MusicBrainzTrackProvider(
        semantic_client, enabled_fields={"recording_date"}
    ).get_enrichment(track_context())

    dates = [item for item in enrichment.evidence if item.field == "recording_date"]
    assert bool(dates) is accepted


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


def test_failed_area_ancestry_retains_artist_area_and_marks_only_country() -> None:
    semantic_client, calls = client(
        artist={
            "id": ARTIST_MBID,
            "genres": [{"name": "k-pop", "count": 4}],
            "tags": [{"name": "dreamy", "count": 3}],
            "area": {"id": SALVADOR_MBID, "name": "Salvador", "type": "City"},
        },
        areas={
            SALVADOR_MBID: {
                "id": SALVADOR_MBID,
                "name": "Salvador",
                "type": "City",
                "relations": [
                    {
                        "target-type": "area",
                        "type": "part of",
                        "area": {"id": BRAZIL_MBID},
                    }
                ],
            },
            BRAZIL_MBID: RequestException("temporary"),
        },
    )

    bundle = MusicBrainzArtistProvider(semantic_client).get_semantic_evidence(
        artist_context()
    )

    assert {item.field: item.value for item in bundle.metadata} == {
        "artist_areas": ("Salvador",)
    }
    assert [item.genre for item in bundle.genres] == ["K-pop"]
    assert [item.canonical_term for item in bundle.tags] == ["Dreamy"]
    assert bundle.unavailable_fields == frozenset({"artist_countries"})
    assert calls["area"] == [SALVADOR_MBID, BRAZIL_MBID]


def test_failed_area_branch_does_not_hide_country_from_independent_branch() -> None:
    semantic_client, calls = client(
        artist={
            "id": ARTIST_MBID,
            "area": {"id": SALVADOR_MBID, "name": "Salvador", "type": "City"},
        },
        areas={
            SALVADOR_MBID: {
                "id": SALVADOR_MBID,
                "name": "Salvador",
                "type": "City",
                "relations": [
                    {
                        "target-type": "area",
                        "type": "part of",
                        "area": {"id": FAILED_AREA_MBID},
                    },
                    {
                        "target-type": "area",
                        "type": "part of",
                        "area": {"id": BRAZIL_MBID},
                    },
                ],
            },
            FAILED_AREA_MBID: RequestException("temporary"),
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
    assert bundle.unavailable_fields == frozenset({"artist_countries"})
    assert calls["area"] == [SALVADOR_MBID, FAILED_AREA_MBID, BRAZIL_MBID]


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

    def fetch_recording(recording_id: str, *_args: object) -> Mapping[str, object]:
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


def test_failed_supporting_work_and_area_are_retried_not_negative_cached() -> None:
    attempts = {"work": 0, "area": 0}

    def fetch_work(work_id: str) -> Mapping[str, object]:
        attempts["work"] += 1
        if attempts["work"] == 1:
            raise RequestException("temporary")
        return {"id": work_id, "languages": ["kor"]}

    def fetch_area(area_id: str) -> Mapping[str, object]:
        attempts["area"] += 1
        if attempts["area"] == 1:
            raise RequestException("temporary")
        return {
            "id": area_id,
            "name": "Brazil",
            "type": "Country",
            "iso-3166-1-codes": ["BR"],
        }

    semantic_client = MusicBrainzSemanticClient(
        fetch_recording=lambda recording_id, *_args: {
            "id": recording_id,
            "relations": [{"target-type": "work", "work": {"id": WORK_ONE}}],
        },
        fetch_work=fetch_work,
        fetch_artist=lambda artist_id: {
            "id": artist_id,
            "area": {"id": SALVADOR_MBID, "name": "Salvador", "type": "City"},
        },
        fetch_area=fetch_area,
    )
    track_provider = MusicBrainzTrackProvider(semantic_client)
    artist_provider = MusicBrainzArtistProvider(semantic_client)

    first_track = track_provider.get_semantic_evidence(track_context())
    first_artist = artist_provider.get_semantic_evidence(artist_context())
    second_track = track_provider.get_semantic_evidence(track_context())
    second_artist = artist_provider.get_semantic_evidence(artist_context())

    assert first_track.unavailable_fields == frozenset(
        {"lyrics_languages", "artist_languages"}
    )
    assert first_artist.unavailable_fields == frozenset({"artist_countries"})
    assert {item.field: item.value for item in second_track.metadata} == {
        "lyrics_languages": ("kor",)
    }
    assert {item.field: item.value for item in second_artist.metadata} == {
        "artist_areas": ("Salvador",),
        "artist_countries": ("Brazil",),
    }
    assert not second_track.unavailable_fields
    assert not second_artist.unavailable_fields
    assert attempts == {"work": 2, "area": 2}
