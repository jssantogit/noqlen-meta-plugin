from requests import RequestException

from beetsplug.noqlenmeta.provider_cache import (
    CommandEntityCache,
    EntityCacheKey,
    EntityFetchProfile,
)


def test_successful_payload_is_fetched_once_per_key() -> None:
    cache = CommandEntityCache()
    key = EntityCacheKey(" MusicBrainz ", " Recording ", " recording-id ")
    calls = 0

    def fetch() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"id": "recording-id"}

    assert cache.get_or_fetch(key, fetch) == {"id": "recording-id"}
    assert cache.get_or_fetch(key, fetch) == {"id": "recording-id"}
    assert calls == 1
    assert key == EntityCacheKey("musicbrainz", "recording", "recording-id")


def test_different_schema_versions_do_not_collide() -> None:
    cache = CommandEntityCache()
    calls = 0

    def fetch() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"call": calls}

    assert cache.get_or_fetch(
        EntityCacheKey("musicbrainz", "recording", "recording-id", "v1"), fetch
    ) == {"call": 1}
    assert cache.get_or_fetch(
        EntityCacheKey("musicbrainz", "recording", "recording-id", "v2"), fetch
    ) == {"call": 2}
    assert calls == 2


def test_fetch_profiles_are_ordered_deduplicated_and_part_of_cache_key() -> None:
    cache = CommandEntityCache()
    narrow = EntityFetchProfile((" isrcs ", "isrcs"))
    equivalent = EntityFetchProfile(("isrcs",))
    rich = EntityFetchProfile(("work-rels", "isrcs"))
    calls = 0

    def fetch() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"call": calls}

    narrow_key = EntityCacheKey("musicbrainz", "recording", "recording-id", profile=narrow)
    equivalent_key = EntityCacheKey(
        "musicbrainz", "recording", "recording-id", profile=equivalent
    )
    rich_key = EntityCacheKey("musicbrainz", "recording", "recording-id", profile=rich)

    assert narrow.includes == ("isrcs",)
    assert cache.get_or_fetch(narrow_key, fetch) == {"call": 1}
    assert cache.get_or_fetch(equivalent_key, fetch) == {"call": 1}
    assert cache.get_or_fetch(rich_key, fetch) == {"call": 2}
    assert calls == 2


def test_broad_fetch_profile_satisfies_later_narrow_request() -> None:
    cache = CommandEntityCache()
    broad = EntityCacheKey(
        "musicbrainz",
        "recording",
        "recording-id",
        profile=EntityFetchProfile(
            ("genres", "tags", "isrcs", "work-rels", "place-rels")
        ),
    )
    narrow = EntityCacheKey(
        "musicbrainz",
        "recording",
        "recording-id",
        profile=EntityFetchProfile(("work-rels",)),
    )
    calls = 0

    def fetch() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"call": calls}

    assert cache.get_or_fetch(broad, fetch) == {"call": 1}
    assert cache.get_or_fetch(narrow, fetch) == {"call": 1}
    assert calls == 1


def test_narrow_fetch_profile_does_not_satisfy_later_broad_request() -> None:
    cache = CommandEntityCache()
    narrow = EntityCacheKey(
        "musicbrainz",
        "recording",
        "recording-id",
        profile=EntityFetchProfile(("work-rels",)),
    )
    broad = EntityCacheKey(
        "musicbrainz",
        "recording",
        "recording-id",
        profile=EntityFetchProfile(
            ("genres", "tags", "isrcs", "work-rels", "place-rels")
        ),
    )
    calls = 0

    def fetch() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"call": calls}

    assert cache.get_or_fetch(narrow, fetch) == {"call": 1}
    assert cache.get_or_fetch(broad, fetch) == {"call": 2}
    assert calls == 2


def test_equivalent_fetch_profiles_with_different_order_share_payload() -> None:
    cache = CommandEntityCache()
    first = EntityCacheKey(
        "musicbrainz",
        "recording",
        "recording-id",
        profile=EntityFetchProfile(("work-rels", "isrcs")),
    )
    reordered = EntityCacheKey(
        "musicbrainz",
        "recording",
        "recording-id",
        profile=EntityFetchProfile(("isrcs", "work-rels")),
    )
    calls = 0

    def fetch() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"call": calls}

    assert cache.get_or_fetch(first, fetch) == {"call": 1}
    assert cache.get_or_fetch(reordered, fetch) == {"call": 1}
    assert calls == 1


def test_narrow_negative_cache_does_not_satisfy_later_broad_request() -> None:
    cache = CommandEntityCache()
    narrow = EntityCacheKey(
        "musicbrainz",
        "recording",
        "recording-id",
        profile=EntityFetchProfile(("work-rels",)),
    )
    broad = EntityCacheKey(
        "musicbrainz",
        "recording",
        "recording-id",
        profile=EntityFetchProfile(("isrcs", "work-rels")),
    )
    calls = 0

    def fetch() -> None:
        nonlocal calls
        calls += 1
        return None

    assert cache.get_or_fetch(narrow, fetch) is None
    assert cache.get_or_fetch(broad, fetch) is None
    assert calls == 2


def test_schema_version_is_normalized_but_not_case_folded() -> None:
    assert EntityCacheKey("provider", "entity", "id", " Parser-V1 ").schema_version == (
        "Parser-V1"
    )


def test_definitive_missing_payload_is_negatively_cached() -> None:
    cache = CommandEntityCache()
    key = EntityCacheKey("musicbrainz", "work", "work-id")
    calls = 0

    def fetch() -> None:
        nonlocal calls
        calls += 1
        return None

    assert cache.get_or_fetch(key, fetch) is None
    assert cache.get_or_fetch(key, fetch) is None
    assert calls == 1


def test_transient_failure_is_not_cached() -> None:
    cache = CommandEntityCache()
    key = EntityCacheKey("musicbrainz", "artist", "artist-id")
    calls = 0

    def fetch() -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RequestException("temporary")
        return {"id": "artist-id"}

    try:
        cache.get_or_fetch(key, fetch)
    except RequestException:
        pass
    else:
        raise AssertionError("first transient failure was not raised")

    assert cache.get_or_fetch(key, fetch) == {"id": "artist-id"}
    assert calls == 2
