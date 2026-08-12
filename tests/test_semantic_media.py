import shutil
from pathlib import Path

import pytest
from mediafile import MediaFile

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.semantic_media import SEMANTIC_MEDIA_FIELDS

FIXTURES = Path(__file__).parent / "fixtures" / "identity_tags"
FORMATS = ("flac", "m4a", "mp3", "ogg", "opus")
VALUES = {
    "styles": ["Progressive Metal", "Technical Death Metal"],
    "moods": ["Melancholic", "Atmospheric"],
    "lyrics_languages": ["kor", "eng"],
    "artist_languages": ["kor", "jpn"],
    "artist_countries": ["South Korea", "United States"],
    "artist_areas": ["Seoul", "New York City"],
}


@pytest.mark.parametrize("extension", FORMATS)
@pytest.mark.parametrize(("field", "values"), VALUES.items())
def test_semantic_media_field_round_trips_ordered_values(
    tmp_path: Path, extension: str, field: str, values: list[str]
) -> None:
    NoqlenMetaPlugin()
    source = FIXTURES / f"silence.{extension}"
    path = tmp_path / source.name
    shutil.copy2(source, path)

    media = MediaFile(path)
    setattr(media, field, values)
    media.save()

    assert getattr(MediaFile(path), field) == values


def test_all_production_semantic_fields_have_descriptors() -> None:
    assert set(SEMANTIC_MEDIA_FIELDS) == set(VALUES)
