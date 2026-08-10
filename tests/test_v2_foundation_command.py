import shutil
from pathlib import Path

import pytest
from beets import config, ui
from beets.library import Item, Library
from mediafile import MediaFile

import beetsplug.noqlenmeta as plugin_module
from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.file_sync import (
    FileSyncApplicationError,
    FileSyncResult,
)

FIXTURE = Path(__file__).parent / "fixtures" / "identity_tags" / "silence.flac"


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


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


def test_identity_apply_write_is_rejected() -> None:
    with pytest.raises(ui.UserError, match="--identity cannot be used with --write"):
        invoke(
            NoqlenMetaPlugin(),
            Library(":memory:", set_music_dir=False),
            ["--identity", "--apply", "--write", "--all"],
        )


def test_invalid_local_analysis_is_rejected_before_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = NoqlenMetaPlugin()
    plugin.config["local_analysis"]["bpm"]["mode"].set("eager")
    library = Library(":memory:", set_music_dir=False)
    monkeypatch.setattr(
        library,
        "albums",
        lambda *args: pytest.fail("invalid analysis config reached selection"),
    )

    with pytest.raises(ui.UserError, match="invalid local_analysis"):
        invoke(plugin, library, ["--all"])


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

    output: list[str] = []
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)

    invoke(plugin, library, ["--apply", "--write", "--all"])

    assert library.get_album(album.id).genres == ["Ambient", "Electronic"]
    assert MediaFile(path).genres == ["Ambient", "Electronic"]
    assert any("database PREVIEW" in line and "planned" in line for line in output)
    assert any("database application" in line and "status=stored" in line for line in output)
    assert any("status=committed-complete" in line for line in output)


def test_existing_library_item_reuses_track_candidate_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    library = Library(":memory:", set_music_dir=False)
    item = Item(
        path=b"synthetic.flac",
        artist="Synthetic Artist",
        title="Synthetic Track",
    )
    library.add(item)
    plugin = NoqlenMetaPlugin()
    plugin.config.set(
        {
            "fields": {"lyrics": True},
            "providers": {
                "discogs": {"enabled": False, "user_token": ""},
                "musicbrainz": {"enabled": False},
                "lastfm": {"enabled": False},
                "itunes": {"enabled": False, "storefront": "us"},
                "lrclib": {"enabled": True},
            },
        }
    )
    monkeypatch.setattr(
        plugin,
        "_lrclib_candidates",
        lambda context: (
            MetadataCandidate("lyrics", "Synthetic line", "lrclib", 0.95, "42"),
        ),
    )

    invoke(plugin, library, ["--apply", "--all"])

    assert library.get_item(item.id).lyrics == "Synthetic line"


def test_file_command_reports_earlier_commits_when_later_item_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = [tmp_path / "first.flac", tmp_path / "second.flac"]
    for path in paths:
        shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    library.add_album(
        [
            Item(
                path=str(path).encode(),
                albumartist="Synthetic Artist",
                album="Synthetic Album",
                artist="Synthetic Artist",
                title=f"Synthetic Track {index}",
            )
            for index, path in enumerate(paths, 1)
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
            MetadataCandidate("genres", ("Ambient",), "discogs", 0.95, "1"),
        ),
    )
    calls = 0

    def apply_in_order(lib: Library, plan: object) -> FileSyncResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return FileSyncResult(item_id=1, applied_fields=("genres",), committed=True)
        raise FileSyncApplicationError("synthetic second failure")

    monkeypatch.setattr(plugin_module, "apply_file_sync_plan", apply_in_order)

    with pytest.raises(FileSyncApplicationError, match="earlier file changes") as captured:
        invoke(plugin, library, ["--apply", "--write", "--all"])

    assert captured.value.committed


def test_file_reporting_distinguishes_partial_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)
    result = FileSyncResult(
        item_id=7,
        applied_fields=("lyrics",),
        blocked_reason="no supported lossless MediaFile target exists",
        blocker_count=1,
        committed=True,
    )

    plugin_module._render_file_sync_result(result)

    assert output == [
        "Noqlen Meta / file application: Item 7; status=committed-partial; "
        "fields=1; blockers=1; reason=no supported lossless MediaFile target exists"
    ]
