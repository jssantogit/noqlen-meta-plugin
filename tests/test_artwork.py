import pytest

from beetsplug.noqlenmeta.artwork import (
    ArtworkCandidate,
    ArtworkLookupResult,
    ArtworkSettings,
    ArtworkSize,
    artwork_settings_from_config,
    resolve_caa_artwork,
)
from beetsplug.noqlenmeta.configuration import default_config
from beetsplug.noqlenmeta.providers.coverartarchive import (
    CoverArtArchiveUnavailable,
)

EXACT_MBID = "11111111-1111-1111-1111-111111111111"
GROUP_MBID = "22222222-2222-2222-2222-222222222222"
SOURCE_MBID = "33333333-3333-3333-3333-333333333333"


def caa_payload(
    release_mbid: str = EXACT_MBID,
    *,
    front: bool = True,
    approved: bool = True,
    image: str = "https://coverartarchive.org/release/x/123.jpg",
    thumbnails: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "images": [
            {
                "id": "123",
                "front": front,
                "approved": approved,
                "image": image,
                "thumbnails": thumbnails
                if thumbnails is not None
                else {
                    "250": "https://coverartarchive.org/release/x/123-250.jpg",
                    "500": "https://coverartarchive.org/release/x/123-500.jpg",
                    "1200": "https://coverartarchive.org/release/x/123-1200.jpg",
                },
                "votes": 999,
            }
        ],
        "release": f"https://musicbrainz.org/release/{release_mbid}",
    }


class CaaClient:
    def __init__(self, exact: object, group: object = None) -> None:
        self.exact = exact
        self.group = group
        self.release_calls = 0
        self.group_calls = 0

    def get_release(self, release_mbid: str) -> dict[str, object] | None:
        self.release_calls += 1
        if isinstance(self.exact, Exception):
            raise self.exact
        return self.exact  # type: ignore[return-value]

    def get_release_group(self, release_group_mbid: str) -> dict[str, object] | None:
        self.group_calls += 1
        if isinstance(self.group, Exception):
            raise self.group
        return self.group  # type: ignore[return-value]


def test_artwork_public_defaults_are_exact() -> None:
    config = default_config()

    assert config["providers"]["coverartarchive"] == {"enabled": True}
    assert config["artwork"] == {"size": "original", "replace_existing": False}
    assert artwork_settings_from_config(config["artwork"]) == ArtworkSettings()


@pytest.mark.parametrize(
    "value",
    [
        {"size": "1000", "replace_existing": False},
        {"size": "original", "replace_existing": 0},
        {"size": "original", "replace_existing": False, "extra": True},
        {"size": "original"},
        None,
    ],
)
def test_artwork_settings_reject_invalid_values(value: object) -> None:
    with pytest.raises(ValueError):
        artwork_settings_from_config(value)


def test_artwork_candidate_copies_thumbnail_mapping() -> None:
    thumbnails = {500: "https://example.test/500.jpg"}
    candidate = ArtworkCandidate(
        source_scope="release",
        release_mbid="release-id",
        release_group_mbid=None,
        source_release_mbid=None,
        image_id="123",
        original_url="https://example.test/original.jpg",
        thumbnail_urls=thumbnails,
        requested_size=ArtworkSize.ORIGINAL,
        effective_size="original",
        selected_url="https://example.test/original.jpg",
    )

    thumbnails[250] = "https://example.test/250.jpg"

    assert dict(candidate.thumbnail_urls) == {500: "https://example.test/500.jpg"}


def test_exact_approved_main_front_is_selected_without_group_lookup() -> None:
    client = CaaClient(caa_payload(), caa_payload(SOURCE_MBID))

    result = resolve_caa_artwork(
        client,
        release_mbid=EXACT_MBID,
        release_group_mbid=GROUP_MBID,
        settings=ArtworkSettings(),
    )

    assert result.outcome == "RESOLVED"
    assert result.candidate is not None
    assert result.candidate.source_scope == "release"
    assert result.candidate.release_mbid == EXACT_MBID
    assert result.candidate.image_id == "123"
    assert result.candidate.effective_size == "original"
    assert client.release_calls == 1
    assert client.group_calls == 0


@pytest.mark.parametrize("front,approved", [(False, True), (True, False)])
def test_ineligible_exact_front_allows_release_group_fallback(
    front: bool, approved: bool
) -> None:
    client = CaaClient(
        caa_payload(front=front, approved=approved),
        caa_payload(SOURCE_MBID),
    )

    result = resolve_caa_artwork(
        client,
        release_mbid=EXACT_MBID,
        release_group_mbid=GROUP_MBID,
        settings=ArtworkSettings(),
    )

    assert result.outcome == "RESOLVED"
    assert result.candidate is not None
    assert result.candidate.source_scope == "release_group"
    assert result.candidate.release_group_mbid == GROUP_MBID
    assert result.candidate.source_release_mbid == SOURCE_MBID
    assert client.group_calls == 1


def test_exact_absence_then_group_absence_is_no_evidence() -> None:
    result = resolve_caa_artwork(
        CaaClient(None, None),
        release_mbid=EXACT_MBID,
        release_group_mbid=GROUP_MBID,
        settings=ArtworkSettings(),
    )

    assert result == ArtworkLookupResult("NO_EVIDENCE", reason="no eligible CAA front")


@pytest.mark.parametrize(
    "exact",
    [
        CoverArtArchiveUnavailable("timeout"),
        caa_payload("not-the-exact-release"),
        {"images": "invalid", "release": f"https://musicbrainz.org/release/{EXACT_MBID}"},
    ],
)
def test_invalid_or_transient_exact_result_is_unavailable_without_fallback(exact: object) -> None:
    client = CaaClient(exact, caa_payload(SOURCE_MBID))

    result = resolve_caa_artwork(
        client,
        release_mbid=EXACT_MBID,
        release_group_mbid=GROUP_MBID,
        settings=ArtworkSettings(),
    )

    assert result.outcome == "UNAVAILABLE"
    assert result.candidate is None
    assert client.group_calls == 0


def test_group_transient_failure_is_unavailable() -> None:
    result = resolve_caa_artwork(
        CaaClient(None, CoverArtArchiveUnavailable("timeout")),
        release_mbid=EXACT_MBID,
        release_group_mbid=GROUP_MBID,
        settings=ArtworkSettings(),
    )

    assert result.outcome == "UNAVAILABLE"


@pytest.mark.parametrize(
    "size,image,thumbnails,effective",
    [
        (ArtworkSize.ORIGINAL, "https://x.test/a.jpg", {1200: "1200", 500: "500"}, "original"),
        (ArtworkSize.ORIGINAL, "https://x.test/a.png", {1200: "1200", 500: "500"}, "1200"),
        (ArtworkSize.ORIGINAL, "https://x.test/a.webp", {500: "500", 250: "250"}, "500"),
        (ArtworkSize.PX_1200, "https://x.test/a.jpg", {500: "500", 250: "250"}, "500"),
        (ArtworkSize.PX_500, "https://x.test/a.jpg", {250: "250"}, "250"),
        (ArtworkSize.PX_250, "https://x.test/a.jpg", {250: "250"}, "250"),
    ],
)
def test_native_size_selection_never_escalates(
    size: ArtworkSize,
    image: str,
    thumbnails: dict[int, str],
    effective: str,
) -> None:
    payload = caa_payload(
        image=image,
        thumbnails={str(key): value for key, value in thumbnails.items()},
    )

    result = resolve_caa_artwork(
        CaaClient(payload),
        release_mbid=EXACT_MBID,
        release_group_mbid=None,
        settings=ArtworkSettings(size=size),
    )

    assert result.candidate is not None
    assert result.candidate.effective_size == effective


@pytest.mark.parametrize(
    "size,thumbnails",
    [
        (ArtworkSize.PX_500, {"1200": "1200"}),
        (ArtworkSize.PX_250, {"500": "500"}),
        (ArtworkSize.ORIGINAL, {}),
    ],
)
def test_missing_eligible_native_representation_is_no_evidence(
    size: ArtworkSize, thumbnails: dict[str, str]
) -> None:
    image = "https://x.test/a.png" if size is ArtworkSize.ORIGINAL else "https://x.test/a.jpg"
    result = resolve_caa_artwork(
        CaaClient(caa_payload(image=image, thumbnails=thumbnails)),
        release_mbid=EXACT_MBID,
        release_group_mbid=None,
        settings=ArtworkSettings(size=size),
    )

    assert result.outcome == "NO_EVIDENCE"


def test_unknown_original_format_is_selected_provisionally() -> None:
    result = resolve_caa_artwork(
        CaaClient(caa_payload(image="https://archive.test/download/123")),
        release_mbid=EXACT_MBID,
        release_group_mbid=None,
        settings=ArtworkSettings(),
    )

    assert result.candidate is not None
    assert result.candidate.effective_size == "original"
    assert result.candidate.original_mime_hint is None
