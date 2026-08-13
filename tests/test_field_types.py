import pytest
from beets import plugins
from beets.dbcore import types
from beets.library import Album, Item, Library
from beets.util import cached_classproperty

from beetsplug.noqlenmeta import NoqlenMetaPlugin


@pytest.fixture
def loaded_plugin(monkeypatch: pytest.MonkeyPatch) -> NoqlenMetaPlugin:
    plugin = NoqlenMetaPlugin()
    monkeypatch.setattr(plugins, "_instances", [plugin])
    monkeypatch.delitem(cached_classproperty.cache, (Album, "_types"), raising=False)
    return plugin


def test_plugin_declares_v2_multivalue_types(loaded_plugin: NoqlenMetaPlugin) -> None:
    plugin = loaded_plugin

    assert plugin.album_types["styles"] is types.MULTI_VALUE_DSV
    assert plugin.item_types["moods"] is types.MULTI_VALUE_DSV
    assert "bpm" not in plugin.item_types
    assert Item._fields["bpm"].normalize(126.4) == 126.4
    assert Item._fields["bpm"].sql == types.INTEGER.sql


def test_styles_round_trip_as_multiple_album_values(tmp_path, loaded_plugin) -> None:
    library = Library(str(tmp_path / "library.db"))
    album = Album(album="Synthetic", albumartist="Artist")
    album["styles"] = ["Progressive Metal", "Technical Death Metal"]
    album.add(library)

    fresh = library.get_album(album.id)

    assert fresh is not None
    assert fresh["styles"] == ["Progressive Metal", "Technical Death Metal"]


def test_release_catalog_fields_round_trip_on_album(tmp_path, loaded_plugin) -> None:
    library = Library(str(tmp_path / "catalog.db"))
    album = Album(album="Synthetic", albumartist="Artist")
    album["edition"] = "Limited Edition"
    album["release_secondary_types"] = ["Live", "Compilation"]
    album.add(library)

    fresh = library.get_album(album.id)

    assert fresh is not None
    assert fresh["edition"] == "Limited Edition"
    assert fresh["release_secondary_types"] == ["Live", "Compilation"]


def test_recording_work_fields_round_trip_on_item(tmp_path, loaded_plugin) -> None:
    library = Library(str(tmp_path / "recording.db"))
    item = Item(path=b"synthetic.flac", title="Synthetic", artist="Artist")
    item["isrcs"] = ["USAAA0100001", "GBBBB0200002"]
    item["iswcs"] = ["T-123.456.789-0"]
    item["mb_workids"] = ["11111111-2222-3333-4444-555555555555"]
    item["recording_date"] = "2020-05"
    item.add(library)

    fresh = library.get_item(item.id)

    assert fresh is not None
    assert fresh["isrcs"] == ["USAAA0100001", "GBBBB0200002"]
    assert fresh["iswcs"] == ["T-123.456.789-0"]
    assert fresh["mb_workids"] == ["11111111-2222-3333-4444-555555555555"]
    assert fresh["recording_date"] == "2020-05"
