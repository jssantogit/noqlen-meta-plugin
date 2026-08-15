from beetsplug.noqlenmeta.configuration import default_config
from beetsplug.noqlenmeta.field_contracts import FIELD_CONTRACTS, field_contract
from beetsplug.noqlenmeta.identity.tag_sync import IDENTITY_TAG_FIELDS
from beetsplug.noqlenmeta.providers.specs import BUILTIN_PROVIDER_CAPABILITIES
from beetsplug.noqlenmeta.resolver import default_resolution_policy
from beetsplug.noqlenmeta.semantic_media import SEMANTIC_MEDIA_FIELDS

V2_FIELDS = {
    "genres",
    "styles",
    "labels",
    "catalog_numbers",
    "barcodes",
    "country",
    "year",
    "media",
    "format_descriptions",
    "moods",
    "bpm",
    "lyrics_languages",
    "artist_countries",
    "artist_areas",
    "artist_languages",
    "lyrics",
    "synced_lyrics",
    "cover",
}
WAVE_ONE_FIELDS = {
    "date",
    "original_date",
    "release_type",
    "release_secondary_types",
    "release_status",
    "edition",
    "isrcs",
    "iswcs",
    "works",
    "recording_date",
}
WAVE_TWO_A_FIELDS = {
    "composers",
    "lyricists",
    "producers",
    "arrangers",
    "conductors",
    "performers",
    "featured_artists",
    "structured_artist_credits",
}


def test_v2_public_fields_are_preserved_when_v3_fields_are_added() -> None:
    config = default_config()

    assert set(config["fields"]) == V2_FIELDS | WAVE_ONE_FIELDS | WAVE_TWO_A_FIELDS
    assert config["fields"]["cover"] is True
    assert "vocal_languages" not in config["fields"]
    assert all(config["fields"][field] is True for field in WAVE_ONE_FIELDS)
    assert all(config["fields"][field] is True for field in WAVE_TWO_A_FIELDS)


def test_v2_semantics_are_not_reassigned_by_aliases() -> None:
    assert field_contract("lyrics_languages") is FIELD_CONTRACTS["lyrics_languages"]
    assert field_contract("lyrics_languages") is not FIELD_CONTRACTS["vocal_languages"]
    assert field_contract("year") is FIELD_CONTRACTS["year"]
    assert field_contract("year") is not FIELD_CONTRACTS["date"]
    assert field_contract("cover") is FIELD_CONTRACTS["front_artwork"]


def test_identity_and_acoustid_configuration_remain_frozen() -> None:
    config = default_config()

    assert IDENTITY_TAG_FIELDS == (
        "mb_albumid",
        "mb_releasegroupid",
        "mb_trackid",
        "mb_releasetrackid",
    )
    assert set(config["acoustid"]) == {
        "enabled",
        "reuse_existing",
        "compute_missing",
        "lookup",
        "use_for_identity",
        "min_score",
        "min_margin",
        "max_results",
        "max_recordings_per_result",
        "timeout_seconds",
        "requests_per_second",
        "cache_entries",
        "fpcalc",
    }


def test_v2_authority_configuration_and_defaults_remain_ordinal() -> None:
    config = default_config()
    policy = default_resolution_policy()

    assert set(config["resolution"]) == {
        "authority",
        "min_confidence",
        "preserve_existing",
    }
    assert policy.field_rules["year"].authority == (
        "musicbrainz",
        "discogs",
        "itunes",
    )


def test_existing_private_tags_are_preserved_without_new_v3_tags() -> None:
    assert set(SEMANTIC_MEDIA_FIELDS) == {
        "styles",
        "moods",
        "lyrics_languages",
        "artist_languages",
        "artist_countries",
        "artist_areas",
    }
    assert (
        not {
            "vocal_languages",
            "isrcs",
            "iswcs",
            "recording_date",
            "energy",
            "danceability",
        }
        & SEMANTIC_MEDIA_FIELDS.keys()
    )


def test_wave_two_and_later_concepts_do_not_expand_provider_behavior() -> None:
    future_fields = {
        "vocal_languages",
        "explicitness",
        "back_artwork",
        "key",
        "energy",
        "danceability",
    }

    assert not future_fields & {capability.field for capability in BUILTIN_PROVIDER_CAPABILITIES}
    assert {"isrcs", "iswcs", "works", "recording_date"} <= {
        capability.field for capability in BUILTIN_PROVIDER_CAPABILITIES
    }
    assert "deezer" not in {capability.provider for capability in BUILTIN_PROVIDER_CAPABILITIES}
