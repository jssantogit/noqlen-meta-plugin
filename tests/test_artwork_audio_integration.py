import shutil
from pathlib import Path

import pytest
from beets import config
from beets.library import Item, Library

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.artwork import ArtworkCandidate, ArtworkLookupResult, ArtworkSize

FIXTURE = Path(__file__).parent / "fixtures" / "identity_tags" / "silence.flac"


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


def test_write_changes_only_prepared_embed_targets_not_artwork_lookup(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    album = library.add_album(
        [
            Item(
                path=bytes(path),
                albumartist="Artist",
                album="Album",
                artist="Artist",
                title="Track",
                mb_albumid="release-id",
            )
        ]
    )
    plugin = NoqlenMetaPlugin()
    for field in plugin.config["fields"].keys():
        plugin.config["fields"][field].set(field == "cover")
    plugin.config["providers"]["musicbrainz"]["enabled"].set(False)
    candidate = ArtworkCandidate(
        "release",
        "release-id",
        None,
        None,
        "123",
        "https://archive.test/123.jpg",
        {},
        ArtworkSize.ORIGINAL,
        "original",
        "https://archive.test/123.jpg",
    )
    calls = 0
    plans = []

    def resolve(*args, **kwargs) -> ArtworkLookupResult:
        nonlocal calls
        calls += 1
        return ArtworkLookupResult("RESOLVED", candidate)

    monkeypatch.setattr(plugin, "_resolve_album_artwork", resolve)
    monkeypatch.setattr(plugin, "_apply_artwork_plan", lambda *args: None)
    monkeypatch.setattr(plugin, "_render_artwork_plan", plans.append)
    monkeypatch.setattr(plugin, "_render_artwork_application_result", lambda *args: None)

    for arguments in (["--all"], ["--apply", "--write", "--all"]):
        command = plugin.commands()[0]
        opts, query = command.parse_args(arguments)
        command.func(library, opts, query)

    assert calls == 2
    assert plans[0].candidate == plans[1].candidate
    assert plans[0].embed_item_ids == ()
    assert plans[1].embed_item_ids == (album.items().get().id,)
