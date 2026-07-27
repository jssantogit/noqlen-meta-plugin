import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest
from requests.exceptions import HTTPError, Timeout

from beetsplug.noqlenmeta.domain import ExternalIdentifier, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.providers import MetadataProvider, ProviderError
from beetsplug.noqlenmeta.providers.musicbrainz import MusicBrainzProvider
from beetsplug.noqlenmeta.providers.specs import MUSICBRAINZ_SPEC

FIXTURES = Path(__file__).parent / "fixtures" / "musicbrainz"
RELEASE_MBID = "6ea45c08-3cfa-461a-aa4d-4cc404fcfa86"
DEFAULT_PAYLOAD = object()


def fixture() -> dict[str, Any]:
    return json.loads((FIXTURES / "release.json").read_text(encoding="utf-8"))


def context(*identifiers: str) -> ReleaseEnrichmentContext:
    return ReleaseEnrichmentContext(
        "Gojira",
        "From Mars to Sirius",
        external_ids=tuple(
            ExternalIdentifier("musicbrainz.release", value) for value in identifiers
        ),
    )


class FetchRelease:
    def __init__(self, payload: object = DEFAULT_PAYLOAD) -> None:
        self.payload = fixture() if payload is DEFAULT_PAYLOAD else payload
        self.calls: list[str] = []

    def __call__(self, release_mbid: str) -> dict[str, Any]:
        self.calls.append(release_mbid)
        return copy.deepcopy(self.payload)  # type: ignore[return-value]


def fields_for(payload: dict[str, Any]) -> dict[str, object]:
    candidates = MusicBrainzProvider(fetch_release=FetchRelease(payload)).get_candidates(
        context(RELEASE_MBID)
    )
    return {candidate.field: candidate.value for candidate in candidates}


def test_exact_release_normalization_emits_supported_fields_and_provenance() -> None:
    candidates = MusicBrainzProvider(fetch_release=FetchRelease()).get_candidates(
        context(RELEASE_MBID)
    )

    assert {candidate.field: candidate.value for candidate in candidates} == {
        "labels": ("Listenable Records",),
        "catalog_numbers": ("POSH 074",),
        "barcodes": ("3760053840745",),
        "country": "FR",
        "year": 2005,
        "media": ("CD",),
    }
    assert all(candidate.provider == "musicbrainz" for candidate in candidates)
    assert all(candidate.source_id == RELEASE_MBID for candidate in candidates)
    assert all(candidate.confidence == 0.99 for candidate in candidates)
    assert all(
        candidate.source_url == f"https://musicbrainz.org/release/{RELEASE_MBID}"
        for candidate in candidates
    )


def test_normalized_beets_release_shape_emits_labels_and_catalog_numbers() -> None:
    fields = fields_for(fixture())

    assert fields["labels"] == ("Listenable Records",)
    assert fields["catalog_numbers"] == ("POSH 074",)


@pytest.mark.parametrize("identifiers", [(), ("invalid",)])
def test_missing_or_malformed_mbid_performs_no_fetch(identifiers: tuple[str, ...]) -> None:
    fetch = FetchRelease()

    assert MusicBrainzProvider(fetch_release=fetch).get_candidates(context(*identifiers)) == ()
    assert fetch.calls == []


def test_ambiguous_distinct_mbids_perform_no_fetch() -> None:
    fetch = FetchRelease()

    assert MusicBrainzProvider(fetch_release=fetch).get_candidates(
        context(RELEASE_MBID, "11111111-2222-3333-4444-555555555555")
    ) == ()
    assert fetch.calls == []


def test_duplicate_equivalent_mbids_normalize_to_one_lookup() -> None:
    fetch = FetchRelease()

    candidates = MusicBrainzProvider(fetch_release=fetch).get_candidates(
        context(RELEASE_MBID, f" {RELEASE_MBID.upper()} ")
    )

    assert candidates
    assert fetch.calls == [RELEASE_MBID]


@pytest.mark.parametrize("payload", [None, [], "invalid", {}])
def test_malformed_top_level_response_raises_provider_error(payload: object) -> None:
    fetch = FetchRelease(payload)

    with pytest.raises(ProviderError, match=r"^MusicBrainz release response is invalid$"):
        MusicBrainzProvider(fetch_release=fetch).get_candidates(context(RELEASE_MBID))


def test_response_id_mismatch_raises_provider_error_without_candidates() -> None:
    payload = fixture()
    payload["id"] = "11111111-2222-3333-4444-555555555555"

    with pytest.raises(ProviderError, match=r"^MusicBrainz release response is invalid$"):
        MusicBrainzProvider(fetch_release=FetchRelease(payload)).get_candidates(
            context(RELEASE_MBID)
        )


@pytest.mark.parametrize("error", [Timeout("timed out secret"), HTTPError("raw response")])
def test_expected_request_failure_becomes_fixed_provider_error(error: Exception) -> None:
    def fail_fetch(release_mbid: str) -> dict[str, Any]:
        raise error

    with pytest.raises(ProviderError, match=r"^MusicBrainz API request failed$") as caught:
        MusicBrainzProvider(fetch_release=fail_fetch).get_candidates(context(RELEASE_MBID))

    assert "secret" not in str(caught.value)
    assert "raw response" not in str(caught.value)


def test_programming_error_is_not_disguised_as_provider_error() -> None:
    def fail_fetch(release_mbid: str) -> dict[str, Any]:
        raise AttributeError("programming defect")

    with pytest.raises(AttributeError, match="programming defect"):
        MusicBrainzProvider(fetch_release=fail_fetch).get_candidates(context(RELEASE_MBID))


@pytest.mark.parametrize("date", ["2005", "2005-09", "2005-09-27", "2008-??-02"])
def test_partial_release_dates_emit_leading_year(date: str) -> None:
    payload = fixture()
    payload["date"] = date

    assert fields_for(payload)["year"] == int(date[:4])


@pytest.mark.parametrize("date", [None, "", "unknown", "0000", "2005-13", 2005])
def test_malformed_release_date_omits_year(date: object) -> None:
    payload = fixture()
    payload["date"] = date

    assert "year" not in fields_for(payload)


def test_multi_values_are_preserved_and_stably_deduplicated() -> None:
    payload = fixture()
    payload["label_info"] = [
        {"label": {"name": "Label A"}, "catalog_number": "CAT A"},
        {"label": {"name": "Label B"}, "catalog_number": "CAT B"},
        {"label": {"name": "Label A"}, "catalog_number": "CAT A"},
        {"catalog_number": "CAT C"},
    ]
    payload["media"] = [
        {"format": "CD"},
        {"format": "DVD"},
        {"format": "CD"},
    ]

    fields = fields_for(payload)

    assert fields["labels"] == ("Label A", "Label B")
    assert fields["catalog_numbers"] == ("CAT A", "CAT B", "CAT C")
    assert fields["media"] == ("CD", "DVD")


def test_null_and_malformed_nested_values_are_skipped_individually() -> None:
    payload = fixture()
    payload["label_info"] = [
        None,
        "invalid",
        {"label": None, "catalog_number": " STANDALONE "},
        {"label": {"name": 123}, "catalog_number": []},
        {"label": {"name": " Valid Label "}},
    ]
    payload["media"] = [None, "CD", {"format": None}, {"format": " DVD "}]
    payload["barcode"] = 123
    payload["country"] = []

    fields = fields_for(payload)

    assert fields["labels"] == ("Valid Label",)
    assert fields["catalog_numbers"] == ("STANDALONE",)
    assert fields["media"] == ("DVD",)
    assert "barcodes" not in fields
    assert "country" not in fields


def test_production_boundary_uses_one_exact_lookup_with_narrow_includes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def get_release(self: object, release_mbid: str, **kwargs: object) -> dict[str, Any]:
        calls.append((release_mbid, kwargs["includes"]))  # type: ignore[arg-type]
        return fixture()

    monkeypatch.setattr(
        "beetsplug._utils.musicbrainz.MusicBrainzAPI.get_release",
        get_release,
    )

    candidates = MusicBrainzProvider().get_candidates(context(RELEASE_MBID))

    fields = {candidate.field: candidate.value for candidate in candidates}

    assert fields["labels"] == ("Listenable Records",)
    assert fields["catalog_numbers"] == ("POSH 074",)
    assert calls == [(RELEASE_MBID, ["labels", "media"])]


def test_musicbrainz_provider_satisfies_metadata_provider_contract() -> None:
    provider = MusicBrainzProvider(fetch_release=FetchRelease())

    assert isinstance(provider, MetadataProvider)
    assert provider.name == MUSICBRAINZ_SPEC.name
    assert provider.supported_fields is MUSICBRAINZ_SPEC.supported_fields


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("NOQLEN_LIVE_TESTS") != "1",
    reason="set NOQLEN_LIVE_TESTS=1 to contact MusicBrainz",
)
def test_live_exact_release_lookup() -> None:
    candidates = MusicBrainzProvider().get_candidates(context(RELEASE_MBID))

    assert candidates
    assert all(candidate.provider == "musicbrainz" for candidate in candidates)
    assert all(candidate.source_id == RELEASE_MBID for candidate in candidates)
    assert {candidate.field for candidate in candidates} & MUSICBRAINZ_SPEC.supported_fields
