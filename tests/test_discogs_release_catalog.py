import copy
import json
from pathlib import Path

from beetsplug.noqlenmeta.credits import CreditRole
from beetsplug.noqlenmeta.domain import ExternalIdentifier, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.evidence import AcquisitionMethod
from beetsplug.noqlenmeta.field_contracts import PartialDate
from beetsplug.noqlenmeta.providers.discogs import DiscogsProvider
from beetsplug.noqlenmeta.release_catalog_resolution import resolve_release_catalog
from beetsplug.noqlenmeta.resolver import ResolutionAction

FIXTURE = Path(__file__).parent / "fixtures" / "discogs" / "release.json"


class Release:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data

    def refresh(self) -> None:
        pass


class Client:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data
        self.release_ids: list[int] = []

    def set_timeout(self, connect: float, read: float) -> None:
        pass

    def release(self, release_id: int) -> Release:
        self.release_ids.append(release_id)
        return Release(copy.deepcopy(self.data))


def payload() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def context() -> ReleaseEnrichmentContext:
    return ReleaseEnrichmentContext(
        "Synthetic Artist",
        "Synthetic Album",
        external_ids=(ExternalIdentifier("discogs.release", "123456"),),
    )


def values(provider: DiscogsProvider) -> dict[str, list[object]]:
    result: dict[str, list[object]] = {}
    for evidence in provider.get_release_catalog_evidence(context(), {"date", "edition"}):
        result.setdefault(evidence.field, []).append(evidence.value)
    return result


def test_discogs_structural_date_and_controlled_edition_use_one_release_request() -> None:
    data = payload()
    data["released"] = "2024-03-17"
    client = Client(data)

    assert values(DiscogsProvider(client=client)) == {
        "date": [PartialDate(2024, 3, 17)],
        "edition": ["Limited Edition"],
    }
    assert client.release_ids == [123456]
    evidence = DiscogsProvider(client=Client(data)).get_release_catalog_evidence(
        context(), {"date"}
    )
    assert evidence[0].provenance.method is AcquisitionMethod.EXACT_LOOKUP


def test_discogs_ignores_formatted_date_and_unsupported_edition_text() -> None:
    data = payload()
    data.pop("released", None)
    data["released_formatted"] = "17 Mar 2024"
    data["formats"] = [{"name": "Vinyl", "descriptions": ["Remastered", "Reissue", "180g"]}]

    assert values(DiscogsProvider(client=Client(data))) == {}


def test_discogs_conflicting_controlled_editions_are_separate_evidence() -> None:
    data = payload()
    data["formats"] = [
        {
            "name": "Vinyl",
            "descriptions": ["Limited Edition", "Deluxe Edition"],
        }
    ]

    assert values(DiscogsProvider(client=Client(data))) == {
        "edition": ["Limited Edition", "Deluxe Edition"]
    }
    evidence = DiscogsProvider(client=Client(data)).get_release_catalog_evidence(
        context(), {"edition"}
    )
    assert resolve_release_catalog({}, evidence)[0].action is ResolutionAction.REVIEW


def test_discogs_does_not_extract_edition_from_title_or_notes() -> None:
    data = payload()
    data["formats"] = [{"name": "Vinyl", "descriptions": ["Album"]}]
    data["title"] = "Synthetic Album (Deluxe Edition)"
    data["notes"] = "Limited Edition"

    assert values(DiscogsProvider(client=Client(data))) == {}


def test_shared_enrichment_uses_one_concrete_discogs_release() -> None:
    data = payload()
    client = Client(data)

    enrichment = DiscogsProvider(client=client).get_enrichment(context(), {"date", "edition"})

    assert enrichment.candidates
    assert enrichment.evidence
    assert client.release_ids == [123456]


def test_discogs_release_credits_reuse_one_concrete_release() -> None:
    data = payload()
    data["extraartists"] = [
        {"name": "Producer", "anv": "Credited Producer", "role": "Producer", "tracks": ""},
        {"name": "Conductor", "role": "Conductor", "tracks": ""},
        {"name": "Guitarist", "role": "Electric Guitar", "tracks": ""},
        {"name": "Featured", "role": "Featuring", "tracks": ""},
        {"name": "Guest", "role": "Guest", "tracks": ""},
    ]
    client = Client(data)

    enrichment = DiscogsProvider(client=client).get_enrichment(
        context(), {"producers", "conductors", "performers", "featured_artists"}
    )

    by_field = {item.field: item.value for item in enrichment.evidence}
    assert by_field["producers"][0].party.credited_as == "Credited Producer"
    assert by_field["conductors"][0].role is CreditRole.CONDUCTOR
    assert by_field["performers"][0].instrument == "electric guitar"
    assert [credit.role for credit in by_field["featured_artists"]] == [
        CreditRole.FEATURED_ARTIST,
        CreditRole.GUEST_ARTIST,
    ]
    assert all(credit.scope.value == "release" for values in by_field.values() for credit in values)
    assert client.release_ids == [123456]


def test_discogs_ambiguous_roles_and_nonblank_track_scopes_are_not_promoted() -> None:
    data = payload()
    data["extraartists"] = [
        {"name": "Writer", "role": "Written-By", "tracks": ""},
        {"name": "Vague", "role": "Co-Producer-ish", "tracks": ""},
        {"name": "Scoped", "role": "Producer", "tracks": "1-1"},
        {"name": "Compound", "role": "Producer, Artwork", "tracks": ""},
        {"name": "Malformed", "role": None, "tracks": ""},
    ]
    data["tracklist"] = [
        {
            "position": "1-1",
            "title": "Synthetic Track",
            "extraartists": [{"name": "Track Producer", "role": "Producer"}],
        }
    ]

    enrichment = DiscogsProvider(client=Client(data)).get_enrichment(
        context(), {"producers", "performers", "featured_artists"}
    )

    assert enrichment.evidence == ()
