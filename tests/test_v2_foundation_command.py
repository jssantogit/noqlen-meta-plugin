import shutil
from pathlib import Path

import pytest
from beets import ui
from beets.library import Item, Library
from mediafile import MediaFile

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.domain import MetadataCandidate

FIXTURE = Path(__file__).parent / "fixtures" / "identity_tags" / "silence.flac"


def invoke(plugin: NoqlenMetaPlugin, library: Library, args: list[str]) -> None:
    command = plugin.commands()[0]
    opts, query = command.parse_args(args)
    command.func(library, opts, query)


def test_ordinary_write_requires_apply() -> None:
    plugin = NoqlenMetaPlugin()
    library = Library(":memory:", set_music_dir=False)

    with pytest.raises(ui.UserError, match="--write requires --apply"):
        invoke(plugin, library, ["--write", "--all"])


def test_legacy_identity_tag_write_remains_valid() -> None:
    invoke(
        NoqlenMetaPlugin(),
        Library(":memory:", set_music_dir=False),
        ["--identity-tags", "--write", "--all"],
    )


def test_ordinary_apply_write_is_accepted() -> None:
    invoke(
        NoqlenMetaPlugin(),
        Library(":memory:", set_music_dir=False),
        ["--apply", "--write", "--all"],
    )


def test_ordinary_apply_write_updates_database_and_real_media_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    album = library.add_album(
        [
            Item(
                path=str(path).encode(),
                albumartist="Synthetic Artist",
                album="Synthetic Album",
                artist="Synthetic Artist",
                title="Synthetic Track",
            )
        ]
    )
    plugin = NoqlenMetaPlugin()
    plugin.config.set(
        {
            "providers": {
                "discogs": {"enabled": True, "user_token": "synthetic-token"},
                "musicbrainz": {"enabled": False},
                "lastfm": {"enabled": False},
                "itunes": {"enabled": False, "storefront": "us"},
                "lrclib": {"enabled": False},
            }
        }
    )
    monkeypatch.setattr(
        plugin,
        "_discogs_candidates",
        lambda *args: (
            MetadataCandidate("genres", ("Ambient", "Electronic"), "discogs", 0.95, "1"),
        ),
    )

    invoke(plugin, library, ["--apply", "--write", "--all"])

    assert library.get_album(album.id).genres == ["Ambient", "Electronic"]
    assert MediaFile(path).genres == ["Ambient", "Electronic"]
