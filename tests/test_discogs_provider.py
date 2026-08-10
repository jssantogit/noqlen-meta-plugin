import json
from pathlib import Path
from typing import Any

import pytest
from discogs_client.exceptions import DiscogsAPIError
from requests.exceptions import Timeout

from beetsplug.noqlenmeta.domain import ExternalIdentifier, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.providers import ProviderError, ReleaseMetadataProvider
from beetsplug.noqlenmeta.providers.discogs import DiscogsProvider
from beetsplug.noqlenmeta.providers.specs import DISCOGS_SPEC
from beetsplug.noqlenmeta.semantic_resolution import resolve_styles

FIXTURES = Path(__file__).parent / "fixtures" / "discogs"
DEFAULT_RELEASE = object()


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Result:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data


class SearchResults:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = [Result(result) for result in results]
        self.per_page = 50
        self.pages_requested: list[int] = []

    def page(self, index: int) -> list[Result]:
        self.pages_requested.append(index)
        return self.results


class Release:
    def __init__(self, data: object, error: Exception | None = None) -> None:
        self.data = data
        self.error = error
        self.refreshed = False

    def refresh(self) -> None:
        self.refreshed = True
        if self.error:
            raise self.error


class Client:
    def __init__(
        self,
        release_data: object = DEFAULT_RELEASE,
        search_data: dict[str, Any] | None = None,
    ) -> None:
        self.release_data = (
            fixture("release.json") if release_data is DEFAULT_RELEASE else release_data
        )
        self.search_data = search_data or {"results": []}
        self.release_ids: list[int] = []
        self.searches: list[dict[str, object]] = []
        self.timeout: tuple[float, float] | None = None
        self.release_error: Exception | None = None
        self.search_error: Exception | None = None
        self.results: SearchResults | None = None
        self.release_objects: list[Release] = []

    def set_timeout(self, connect: float, read: float) -> None:
        self.timeout = connect, read

    def release(self, release_id: int) -> Release:
        self.release_ids.append(release_id)
        release = Release(self.release_data, self.release_error)
        self.release_objects.append(release)
        return release

    def search(self, **fields: object) -> SearchResults:
        self.searches.append(fields)
        if self.search_error:
            raise self.search_error
        self.results = SearchResults(self.search_data["results"])
        return self.results


def context(**overrides: object) -> ReleaseEnrichmentContext:
    values: dict[str, object] = {
        "album_artist": "Synthetic Artist",
        "album_title": "Synthetic Album",
    }
    values.update(overrides)
    return ReleaseEnrichmentContext(**values)  # type: ignore[arg-type]


def candidates_by_field(
    provider: DiscogsProvider, release_context: ReleaseEnrichmentContext
) -> dict[str, object]:
    return {
        candidate.field: candidate.value
        for candidate in provider.get_candidates(release_context)
    }


def test_direct_release_identifier_fetches_without_search_or_token() -> None:
    client = Client()
    provider = DiscogsProvider(client=client)

    candidates = provider.get_candidates(
        context(external_ids=(ExternalIdentifier("discogs.release", "123456"),))
    )

    assert candidates
    assert client.release_ids == [123456]
    assert client.release_objects[0].refreshed
    assert client.searches == []
    assert client.timeout == (5, 10)
    assert all(candidate.confidence == 0.98 for candidate in candidates)


@pytest.mark.parametrize(
    "value",
    ["abc", "0", "-1", "12.5", "１２３", "9" * 5000],
)
def test_invalid_direct_release_identifier_returns_no_candidates(value: str) -> None:
    client = Client()
    provider = DiscogsProvider(token="token", client=client)

    assert provider.get_candidates(
        context(external_ids=(ExternalIdentifier("discogs.release", value),))
    ) == ()
    assert client.release_ids == []
    assert client.searches == []


def test_multiple_direct_release_identifiers_are_ambiguous() -> None:
    client = Client()
    provider = DiscogsProvider(token="token", client=client)
    release_context = context(
        external_ids=(
            ExternalIdentifier("discogs.release", "123456"),
            ExternalIdentifier("discogs.release", "123457"),
        )
    )

    assert provider.get_candidates(release_context) == ()
    assert client.searches == []


def test_search_uses_structured_required_and_optional_filters() -> None:
    client = Client(search_data=fixture("search_unique.json"))
    provider = DiscogsProvider(token="token", client=client)

    provider.get_candidates(
        context(year=2024, barcode="012345678901", catalog_number="SYN-001")
    )

    assert client.searches == [
        {
            "type": "release",
            "artist": "Synthetic Artist",
            "release_title": "Synthetic Album",
            "year": 2024,
            "barcode": "012345678901",
            "catno": "SYN-001",
        }
    ]
    assert client.results is not None
    assert client.results.per_page == 10
    assert client.results.pages_requested == [1]


def test_search_omits_missing_optional_filters() -> None:
    client = Client(search_data=fixture("search_unique.json"))
    provider = DiscogsProvider(token="token", client=client)

    provider.get_candidates(context())

    assert client.searches == [
        {
            "type": "release",
            "artist": "Synthetic Artist",
            "release_title": "Synthetic Album",
        }
    ]


def test_unique_defensible_search_result_fetches_concrete_release() -> None:
    client = Client(search_data=fixture("search_unique.json"))
    provider = DiscogsProvider(token="token", client=client)

    candidates = provider.get_candidates(context(year=2024))

    assert candidates
    assert client.release_ids == [123456]
    assert all(candidate.confidence == 0.82 for candidate in candidates)


def test_no_search_results_returns_no_candidates() -> None:
    client = Client(search_data={"results": []})

    assert DiscogsProvider(token="token", client=client).get_candidates(context()) == ()
    assert client.release_ids == []


def test_oversized_search_result_id_returns_no_candidates() -> None:
    search_data = fixture("search_unique.json")
    search_data["results"][0]["id"] = "9" * 5000
    client = Client(search_data=search_data)

    assert DiscogsProvider(token="token", client=client).get_candidates(context()) == ()
    assert client.release_ids == []


def test_ambiguous_search_results_return_no_candidates() -> None:
    client = Client(search_data=fixture("search_ambiguous.json"))

    assert DiscogsProvider(token="token", client=client).get_candidates(
        context(year=2024)
    ) == ()
    assert client.release_ids == []


def test_explicitly_conflicting_identifier_rejects_search_result() -> None:
    client = Client(search_data=fixture("search_unique.json"))
    provider = DiscogsProvider(token="token", client=client)

    assert provider.get_candidates(context(catalog_number="OTHER-001")) == ()
    assert client.release_ids == []


def test_strong_catalog_number_resolves_one_edition() -> None:
    release_data = fixture("release.json")
    release_data["id"] = 123457
    client = Client(
        release_data=release_data,
        search_data=fixture("search_ambiguous.json"),
    )
    provider = DiscogsProvider(token="token", client=client)

    candidates = provider.get_candidates(context(year=2024, catalog_number="syn 002"))

    assert candidates
    assert client.release_ids == [123457]
    assert all(candidate.confidence == 0.92 for candidate in candidates)


def test_concrete_release_normalization_preserves_structured_metadata() -> None:
    provider = DiscogsProvider(client=Client())
    release_context = context(
        external_ids=(ExternalIdentifier("discogs.release", "123456"),)
    )

    fields = candidates_by_field(provider, release_context)

    assert fields == {
        "genres": ("Electronic", "Rock"),
        "styles": ("Ambient", "Experimental"),
        "labels": ("Synthetic Records", "Second Label"),
        "catalog_numbers": ("SYN-001", "ALT 002"),
        "barcodes": ("0123 4567 8901", "012345678902"),
        "country": "UK",
        "year": 2024,
        "media": ("Vinyl",),
        "format_descriptions": ("LP", "Album", "Limited Edition"),
    }
    assert resolve_styles(fields["styles"], ()) == ("Ambient", "Experimental")


def test_candidates_have_concrete_release_provenance() -> None:
    provider = DiscogsProvider(client=Client())
    release_context = context(
        external_ids=(ExternalIdentifier("discogs.release", "123456"),)
    )

    candidates = provider.get_candidates(release_context)

    assert all(candidate.provider == "discogs" for candidate in candidates)
    assert all(candidate.source_id == "123456" for candidate in candidates)
    assert all(
        candidate.source_url == "https://www.discogs.com/release/123456-Synthetic-Release"
        for candidate in candidates
    )


@pytest.mark.parametrize("release_data", [{}, {"id": "invalid"}, [], None])
def test_malformed_required_release_data_returns_no_candidates(release_data: object) -> None:
    client = Client(release_data=release_data)
    provider = DiscogsProvider(client=client)

    assert provider.get_candidates(
        context(external_ids=(ExternalIdentifier("discogs.release", "123456"),))
    ) == ()


def test_search_without_token_fails_at_provider_boundary() -> None:
    with pytest.raises(ProviderError, match="personal user token"):
        DiscogsProvider(client=Client()).get_candidates(context())


@pytest.mark.parametrize(
    "error",
    [
        DiscogsAPIError("service unavailable"),
        Timeout("timed out"),
        KeyError("malformed response"),
    ],
)
def test_release_client_failures_become_provider_error(error: Exception) -> None:
    client = Client()
    client.release_error = error
    provider = DiscogsProvider(token="secret-token", client=client)

    with pytest.raises(ProviderError, match="release lookup failed") as caught:
        provider.get_candidates(
            context(external_ids=(ExternalIdentifier("discogs.release", "123456"),))
        )

    assert "secret-token" not in str(caught.value)


@pytest.mark.parametrize(
    "error",
    [
        DiscogsAPIError("service unavailable"),
        Timeout("timed out"),
        KeyError("malformed response"),
    ],
)
def test_search_client_failures_become_provider_error(error: Exception) -> None:
    client = Client()
    client.search_error = error
    provider = DiscogsProvider(token="secret-token", client=client)

    with pytest.raises(ProviderError, match="release search failed") as caught:
        provider.get_candidates(context())

    assert "secret-token" not in str(caught.value)


@pytest.mark.parametrize("error", [AttributeError("programming defect"), TypeError("type defect")])
@pytest.mark.parametrize("operation", ["release", "search"])
def test_programming_errors_are_not_disguised_as_provider_errors(
    operation: str, error: Exception
) -> None:
    client = Client()
    if operation == "release":
        client.release_error = error
        release_context = context(
            external_ids=(ExternalIdentifier("discogs.release", "123456"),)
        )
    else:
        client.search_error = error
        release_context = context()

    with pytest.raises(type(error), match=str(error)):
        DiscogsProvider(token="token", client=client).get_candidates(release_context)


def test_discogs_provider_satisfies_metadata_provider_contract() -> None:
    provider = DiscogsProvider(client=Client())

    assert isinstance(provider, ReleaseMetadataProvider)
    assert provider.name == DISCOGS_SPEC.name
    assert provider.supported_fields is DISCOGS_SPEC.supported_fields
