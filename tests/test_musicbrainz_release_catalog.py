import copy
from collections.abc import Mapping

import pytest

from beetsplug.noqlenmeta.domain import ExternalIdentifier, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.field_contracts import EntityKind, PartialDate
from beetsplug.noqlenmeta.provider_cache import CommandEntityCache
from beetsplug.noqlenmeta.providers import ProviderError
from beetsplug.noqlenmeta.providers.musicbrainz import MusicBrainzProvider
from beetsplug.noqlenmeta.release_catalog import (
    ReleaseSecondaryType,
    ReleaseStatus,
    ReleaseType,
)

RELEASE_ID = "6ea45c08-3cfa-461a-aa4d-4cc404fcfa86"
RELEASE_GROUP_ID = "11111111-2222-3333-4444-555555555555"


def context(*, release_group_id: str | None = None) -> ReleaseEnrichmentContext:
    identifiers = [ExternalIdentifier("musicbrainz.release", RELEASE_ID)]
    if release_group_id is not None:
        identifiers.append(ExternalIdentifier("musicbrainz.release_group", release_group_id))
    return ReleaseEnrichmentContext(
        "Synthetic Artist",
        "Synthetic Album",
        external_ids=tuple(identifiers),
    )


def release_payload(*, nested: bool = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": RELEASE_ID,
        "date": "2020-05-17",
        "status": "Official",
    }
    if nested:
        payload["release_group"] = {
            "id": RELEASE_GROUP_ID,
            "first_release_date": "2019-??-??",
            "primary_type": "Album",
            "secondary_types": ["Live", "Compilation"],
        }
    return payload


def release_group_payload() -> dict[str, object]:
    return {
        "id": RELEASE_GROUP_ID,
        "first_release_date": "2019-04-??",
        "primary_type": "Album",
        "secondary_types": ["Live", "Compilation", "Live"],
    }


class Fetcher:
    def __init__(self, payload: Mapping[str, object] | None) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, entity_id: str) -> Mapping[str, object] | None:
        self.calls.append(entity_id)
        return copy.deepcopy(self.payload)


def values(evidence: tuple) -> dict[str, object]:
    return {item.field: item.value for item in evidence}


def test_release_fields_use_exact_release_payload() -> None:
    release = Fetcher(release_payload())
    release_group = Fetcher(release_group_payload())
    provider = MusicBrainzProvider(fetch_release=release, fetch_release_group=release_group)

    evidence = provider.get_release_catalog_evidence(context(), {"date", "release_status"})

    assert values(evidence) == {
        "date": PartialDate(2020, 5, 17),
        "release_status": ReleaseStatus.OFFICIAL,
    }
    assert all(item.subject.entity is EntityKind.RELEASE for item in evidence)
    assert release.calls == [RELEASE_ID]
    assert release_group.calls == []


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        ("Bootleg", ReleaseStatus.BOOTLEG),
        ("Cancelled", ReleaseStatus.CANCELLED),
        ("Expunged", ReleaseStatus.EXPUNGED),
        ("Official", ReleaseStatus.OFFICIAL),
        ("Promotion", ReleaseStatus.PROMOTION),
        ("Pseudo-Release", ReleaseStatus.PSEUDO_RELEASE),
        ("Withdrawn", ReleaseStatus.WITHDRAWN),
    ],
)
def test_release_status_evidence_covers_musicbrainz_contract(
    raw_status: str, expected: ReleaseStatus
) -> None:
    payload = release_payload()
    payload["status"] = raw_status
    provider = MusicBrainzProvider(fetch_release=Fetcher(payload))

    evidence = provider.get_release_catalog_evidence(context(), {"release_status"})

    assert values(evidence) == {"release_status": expected}


def test_nested_release_group_is_reused_for_all_requested_fields() -> None:
    release = Fetcher(release_payload())
    release_group = Fetcher(release_group_payload())
    provider = MusicBrainzProvider(fetch_release=release, fetch_release_group=release_group)

    evidence = provider.get_release_catalog_evidence(
        context(),
        {"original_date", "release_type", "release_secondary_types"},
    )

    assert values(evidence) == {
        "original_date": PartialDate(2019),
        "release_type": ReleaseType.ALBUM,
        "release_secondary_types": (
            ReleaseSecondaryType.LIVE,
            ReleaseSecondaryType.COMPILATION,
        ),
    }
    assert all(item.subject.entity is EntityKind.RELEASE_GROUP for item in evidence)
    assert release.calls == [RELEASE_ID]
    assert release_group.calls == []


def test_release_group_lookup_occurs_once_only_when_requested_data_is_missing() -> None:
    payload = release_payload()
    payload["release_group"] = {"id": RELEASE_GROUP_ID}
    release = Fetcher(payload)
    release_group = Fetcher(release_group_payload())
    provider = MusicBrainzProvider(
        fetch_release=release,
        fetch_release_group=release_group,
        cache=CommandEntityCache(),
    )

    evidence = provider.get_release_catalog_evidence(
        context(),
        {"original_date", "release_type", "release_secondary_types"},
    )

    assert set(values(evidence)) == {
        "original_date",
        "release_type",
        "release_secondary_types",
    }
    assert release_group.calls == [RELEASE_GROUP_ID]


def test_explicit_context_release_group_id_enables_exact_lookup_when_not_nested() -> None:
    release = Fetcher(release_payload(nested=False))
    release_group = Fetcher(release_group_payload())
    provider = MusicBrainzProvider(fetch_release=release, fetch_release_group=release_group)

    evidence = provider.get_release_catalog_evidence(
        context(release_group_id=RELEASE_GROUP_ID), {"original_date"}
    )

    assert values(evidence) == {"original_date": PartialDate(2019, 4)}
    assert release_group.calls == [RELEASE_GROUP_ID]


def test_missing_release_group_identity_never_triggers_speculative_lookup() -> None:
    release_group = Fetcher(release_group_payload())
    provider = MusicBrainzProvider(
        fetch_release=Fetcher(release_payload(nested=False)),
        fetch_release_group=release_group,
    )

    assert provider.get_release_catalog_evidence(context(), {"original_date"}) == ()
    assert release_group.calls == []


def test_supporting_release_group_failure_does_not_discard_release_fields() -> None:
    payload = release_payload()
    payload["release_group"] = {"id": RELEASE_GROUP_ID}

    def fail(_: str) -> Mapping[str, object]:
        raise ProviderError("supporting failure")

    provider = MusicBrainzProvider(fetch_release=Fetcher(payload), fetch_release_group=fail)

    evidence = provider.get_release_catalog_evidence(
        context(), {"date", "release_status", "original_date"}
    )

    assert values(evidence) == {
        "date": PartialDate(2020, 5, 17),
        "release_status": ReleaseStatus.OFFICIAL,
    }


@pytest.mark.parametrize(
    "group_payload",
    [
        {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        {"id": RELEASE_GROUP_ID, "first_release_date": "invalid"},
    ],
)
def test_malformed_or_mismatched_release_group_emits_no_group_evidence(
    group_payload: Mapping[str, object],
) -> None:
    payload = release_payload()
    payload["release_group"] = {"id": RELEASE_GROUP_ID}
    provider = MusicBrainzProvider(
        fetch_release=Fetcher(payload), fetch_release_group=Fetcher(group_payload)
    )

    evidence = provider.get_release_catalog_evidence(context(), {"original_date"})

    assert evidence == ()


def test_v2_candidates_do_not_trigger_release_group_lookup() -> None:
    release = Fetcher(release_payload())
    release_group = Fetcher(release_group_payload())
    provider = MusicBrainzProvider(fetch_release=release, fetch_release_group=release_group)

    assert provider.get_candidates(context())
    assert release_group.calls == []


def test_shared_enrichment_reuses_one_release_for_v2_and_v3() -> None:
    release = Fetcher(release_payload())
    provider = MusicBrainzProvider(fetch_release=release)

    enrichment = provider.get_enrichment(context(), {"date", "release_status"})

    assert enrichment.candidates
    assert values(enrichment.evidence) == {
        "date": PartialDate(2020, 5, 17),
        "release_status": ReleaseStatus.OFFICIAL,
    }
    assert release.calls == [RELEASE_ID]


def test_production_release_group_boundary_uses_exact_normalized_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []

    def get_json(self: object, url: str, **kwargs: object) -> dict[str, object]:
        calls.append((url, kwargs.get("params")))
        return release_group_payload()

    monkeypatch.setattr(
        "beetsplug._utils.musicbrainz.MusicBrainzAPI.get_json",
        get_json,
    )
    payload = release_payload()
    payload["release_group"] = {"id": RELEASE_GROUP_ID}
    provider = MusicBrainzProvider(fetch_release=Fetcher(payload))

    evidence = provider.get_release_catalog_evidence(context(), {"original_date"})

    assert values(evidence) == {"original_date": PartialDate(2019, 4)}
    assert len(calls) == 1
    assert calls[0][0].endswith(f"/release-group/{RELEASE_GROUP_ID}")
    assert calls[0][1] == {"inc": "", "fmt": "json"}
