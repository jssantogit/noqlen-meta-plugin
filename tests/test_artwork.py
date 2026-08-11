import pytest

from beetsplug.noqlenmeta.artwork import (
    ArtworkCandidate,
    ArtworkSettings,
    ArtworkSize,
    artwork_settings_from_config,
)
from beetsplug.noqlenmeta.configuration import default_config


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
