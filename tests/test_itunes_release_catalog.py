import copy
import json
from pathlib import Path

from beetsplug.noqlenmeta.domain import ExternalIdentifier, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.evidence import AcquisitionMethod
from beetsplug.noqlenmeta.field_contracts import PartialDate
from beetsplug.noqlenmeta.providers.itunes import ITunesProvider

FIXTURE = Path(__file__).parent / "fixtures" / "itunes" / "lookup_collection.json"
COLLECTION_ID = 1097861387


class Requests:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data
        self.urls: list[str] = []

    def __call__(self, url: str) -> dict[str, object]:
        self.urls.append(url)
        return copy.deepcopy(self.data)


def payload() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def context() -> ReleaseEnrichmentContext:
    return ReleaseEnrichmentContext(
        "Radiohead",
        "OK Computer",
        external_ids=(ExternalIdentifier("itunes.collection", str(COLLECTION_ID)),),
    )


def test_itunes_release_date_uses_existing_lookup_response() -> None:
    requests = Requests(payload())
    provider = ITunesProvider(request_json=requests)

    evidence = provider.get_release_catalog_evidence(context(), {"date"})

    assert [(item.field, item.value) for item in evidence] == [("date", PartialDate(1997, 5, 21))]
    assert len(requests.urls) == 1
    assert "/lookup?" in requests.urls[0]
    assert evidence[0].provenance.method is AcquisitionMethod.EXACT_LOOKUP


def test_itunes_invalid_or_missing_release_date_emits_no_evidence() -> None:
    for value in (None, "", "not-a-date", "1997-02-30T00:00:00Z"):
        data = payload()
        data["results"][0]["releaseDate"] = value  # type: ignore[index]
        provider = ITunesProvider(request_json=Requests(data))

        assert provider.get_release_catalog_evidence(context(), {"date"}) == ()


def test_v2_and_v3_paths_each_use_the_same_single_endpoint_shape() -> None:
    v2_requests = Requests(payload())
    v3_requests = Requests(payload())

    assert ITunesProvider(request_json=v2_requests).get_candidates(context())
    assert ITunesProvider(request_json=v3_requests).get_release_catalog_evidence(
        context(), {"date"}
    )
    assert len(v2_requests.urls) == len(v3_requests.urls) == 1
    assert v2_requests.urls[0].split("?", 1)[0] == v3_requests.urls[0].split("?", 1)[0]


def test_shared_enrichment_uses_one_collection_acquisition() -> None:
    requests = Requests(payload())

    enrichment = ITunesProvider(request_json=requests).get_enrichment(context(), {"date"})

    assert enrichment.candidates
    assert enrichment.evidence
    assert len(requests.urls) == 1
