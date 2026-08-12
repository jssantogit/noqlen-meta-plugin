from requests import RequestException

from beetsplug.noqlenmeta.provider_cache import CommandEntityCache, EntityCacheKey


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
