import copy
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from beetsplug.noqlenmeta.domain import ExternalIdentifier, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.providers import MetadataProvider, ProviderError
from beetsplug.noqlenmeta.providers.itunes import ITunesProvider

FIXTURES = Path(__file__).parent / "fixtures" / "itunes"
COLLECTION_ID = 1097861387


def fixture(name: str = "lookup_collection.json") -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def context(**overrides: object) -> ReleaseEnrichmentContext:
    values: dict[str, object] = {
        "album_artist": "Radiohead",
        "album_title": "OK Computer",
        "year": 1997,
    }
    values.update(overrides)
    return ReleaseEnrichmentContext(**values)  # type: ignore[arg-type]


class Requests:
    def __init__(self, *responses: dict[str, Any]) -> None:
        self.responses = list(responses) or [fixture()]
        self.urls: list[str] = []

    def __call__(self, url: str) -> dict[str, Any]:
        self.urls.append(url)
        return copy.deepcopy(self.responses.pop(0))


def direct_context(value: str = str(COLLECTION_ID)) -> ReleaseEnrichmentContext:
    return context(external_ids=(ExternalIdentifier("itunes.collection", value),))


def query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query)


def test_direct_collection_identifier_fetches_without_search() -> None:
    requests = Requests()
    candidates = ITunesProvider(request_json=requests).get_candidates(direct_context())

    assert candidates
    assert len(requests.urls) == 1
    assert urlsplit(requests.urls[0]).path == "/lookup"
    assert query(requests.urls[0]) == {
        "id": [str(COLLECTION_ID)],
        "entity": ["album"],
        "country": ["US"],
    }
    assert all(candidate.confidence == 0.98 for candidate in candidates)


@pytest.mark.parametrize("value", ["abc", "0", "-1", "12.5", "１２３", "9" * 5000])
def test_invalid_direct_collection_identifier_returns_no_candidates(value: str) -> None:
    requests = Requests()

    assert ITunesProvider(request_json=requests).get_candidates(direct_context(value)) == ()
    assert requests.urls == []


def test_multiple_explicit_collection_identifiers_are_ambiguous() -> None:
    requests = Requests()
    release_context = context(
        external_ids=(
            ExternalIdentifier("itunes.collection", str(COLLECTION_ID)),
            ExternalIdentifier("itunes.collection", str(COLLECTION_ID + 1)),
        )
    )

    assert ITunesProvider(request_json=requests).get_candidates(release_context) == ()
    assert requests.urls == []


def test_direct_lookup_requires_returned_collection_id_to_match() -> None:
    payload = fixture()
    payload["results"][0]["collectionId"] = COLLECTION_ID + 1

    assert ITunesProvider(request_json=Requests(payload)).get_candidates(direct_context()) == ()


def test_barcode_uses_upc_lookup_and_selects_unique_validated_collection() -> None:
    requests = Requests()
    candidates = ITunesProvider(storefront="br", request_json=requests).get_candidates(
        context(barcode="634904078164")
    )

    assert candidates
    assert len(requests.urls) == 1
    assert urlsplit(requests.urls[0]).path == "/lookup"
    assert query(requests.urls[0]) == {
        "upc": ["634904078164"],
        "entity": ["album"],
        "country": ["BR"],
    }
    assert all(candidate.confidence == 0.94 for candidate in candidates)
    assert "barcodes" not in {candidate.field for candidate in candidates}


def test_empty_upc_result_permits_one_bounded_text_search() -> None:
    requests = Requests({"resultCount": 0, "results": []}, fixture())

    candidates = ITunesProvider(request_json=requests).get_candidates(
        context(barcode="634904078164")
    )

    assert candidates
    assert [urlsplit(url).path for url in requests.urls] == ["/lookup", "/search"]
    assert query(requests.urls[1])["limit"] == ["10"]


def test_ambiguous_validated_upc_results_do_not_fall_back_or_select() -> None:
    payload = fixture()
    second = copy.deepcopy(payload["results"][0])
    second["collectionId"] = COLLECTION_ID + 1
    payload["results"].append(second)
    requests = Requests(payload)

    assert ITunesProvider(request_json=requests).get_candidates(
        context(barcode="634904078164")
    ) == ()
    assert [urlsplit(url).path for url in requests.urls] == ["/lookup"]


def test_search_is_structured_bounded_and_uses_configured_storefront() -> None:
    requests = Requests()

    ITunesProvider(storefront=" JP ", request_json=requests).get_candidates(context())

    assert urlsplit(requests.urls[0]).path == "/search"
    assert query(requests.urls[0]) == {
        "term": ["Radiohead OK Computer"],
        "media": ["music"],
        "entity": ["album"],
        "limit": ["10"],
        "country": ["JP"],
    }
    assert "offset" not in query(requests.urls[0])


@pytest.mark.parametrize("field", ["artistName", "collectionName"])
def test_search_requires_artist_and_title_agreement(field: str) -> None:
    payload = fixture()
    payload["results"][0][field] = "Different"

    assert ITunesProvider(request_json=Requests(payload)).get_candidates(context()) == ()


def test_matching_is_conservative_about_edition_suffixes() -> None:
    payload = fixture()
    payload["results"][0]["collectionName"] = "OK Computer (Deluxe Edition)"

    assert ITunesProvider(request_json=Requests(payload)).get_candidates(context()) == ()


def test_matching_normalizes_case_whitespace_unicode_and_punctuation() -> None:
    payload = fixture()
    payload["results"][0]["artistName"] = " RADIOHEAD "
    payload["results"][0]["collectionName"] = "OK—Computer"

    candidates = ITunesProvider(request_json=Requests(payload)).get_candidates(
        context(album_title="ok computer")
    )

    assert candidates


def test_search_rejects_clear_release_year_conflict() -> None:
    payload = fixture()
    payload["results"][0]["releaseDate"] = "1998-01-01T00:00:00Z"

    assert ITunesProvider(request_json=Requests(payload)).get_candidates(context()) == ()


def test_search_ambiguity_returns_no_candidates() -> None:
    payload = fixture()
    for index in range(1, 12):
        result = copy.deepcopy(payload["results"][0])
        result["collectionId"] = COLLECTION_ID + index
        payload["results"].append(result)

    assert ITunesProvider(request_json=Requests(payload)).get_candidates(context()) == ()


def test_normalization_emits_only_supported_fields_and_provenance() -> None:
    candidates = ITunesProvider(request_json=Requests()).get_candidates(direct_context())
    fields = {candidate.field: candidate.value for candidate in candidates}

    assert fields == {"genres": ("Alternative",), "year": 1997}
    assert "country" not in fields
    assert all(candidate.provider == "itunes" for candidate in candidates)
    assert all(candidate.source_id == str(COLLECTION_ID) for candidate in candidates)
    assert all(
        candidate.source_url
        == "https://music.apple.com/us/album/ok-computer/1097861387?uo=4"
        for candidate in candidates
    )


def test_empty_genre_and_malformed_release_date_are_omitted() -> None:
    payload = fixture()
    payload["results"][0]["primaryGenreName"] = " "
    payload["results"][0]["releaseDate"] = "not-a-date"

    assert ITunesProvider(request_json=Requests(payload)).get_candidates(direct_context()) == ()


@pytest.mark.parametrize(
    "error",
    [
        HTTPError("https://itunes.apple.com", 503, "unavailable", {}, None),
        URLError("unavailable"),
        TimeoutError("timed out"),
        json.JSONDecodeError("bad json", "", 0),
        UnicodeDecodeError("utf-8", b"x", 0, 1, "invalid"),
        ConnectionResetError("connection reset"),
        KeyError("malformed response"),
    ],
)
def test_expected_request_failures_become_fixed_provider_error(error: Exception) -> None:
    def fail_request(url: str) -> dict[str, Any]:
        raise error

    with pytest.raises(ProviderError, match=r"^iTunes API request failed$"):
        ITunesProvider(request_json=fail_request).get_candidates(direct_context())


@pytest.mark.parametrize("payload", [{}, {"results": None}, {"results": "invalid"}])
def test_malformed_response_structure_becomes_provider_error(payload: dict[str, Any]) -> None:
    with pytest.raises(ProviderError, match=r"^iTunes API request failed$"):
        ITunesProvider(request_json=Requests(payload)).get_candidates(direct_context())


@pytest.mark.parametrize("path", ["direct", "search"])
def test_track_wrappers_are_not_accepted_as_album_collections(path: str) -> None:
    payload = fixture()
    payload["results"][0]["wrapperType"] = "track"
    release_context = direct_context() if path == "direct" else context()

    assert ITunesProvider(request_json=Requests(payload)).get_candidates(release_context) == ()


def test_programming_error_is_not_disguised_as_provider_error() -> None:
    def fail_request(url: str) -> dict[str, Any]:
        raise AttributeError("programming defect")

    with pytest.raises(AttributeError, match="programming defect"):
        ITunesProvider(request_json=fail_request).get_candidates(direct_context())


@pytest.mark.parametrize("storefront", ["", "usa", "u1", "éé"])
def test_storefront_must_be_two_ascii_letters(storefront: str) -> None:
    with pytest.raises(ProviderError, match=r"^iTunes storefront configuration is invalid$"):
        ITunesProvider(storefront=storefront)


def test_itunes_provider_satisfies_metadata_provider_contract() -> None:
    assert isinstance(ITunesProvider(request_json=Requests()), MetadataProvider)
