import shutil
from pathlib import Path

import pytest
from beets import config, plugins, ui
from beets.library import Album, Item, Library
from beets.util import cached_classproperty
from mediafile import MediaFile

import beetsplug.noqlenmeta as plugin_module
from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.changeplan import PlannedChange
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.file_sync import (
    FileSyncApplicationError,
    FileSyncPlan,
    FileSyncResult,
    plan_file_sync,
)
from beetsplug.noqlenmeta.library_application import LibraryApplicationError
from beetsplug.noqlenmeta.library_track_application import (
    LibraryTrackApplicationError,
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


def planned_change(field: str, value: object) -> PlannedChange:
    candidate = MetadataCandidate(field, value, "catalog", 0.95, "42")  # type: ignore[arg-type]
    return PlannedChange(field, None, candidate.value, candidate, f"resolved {field}")


@pytest.fixture
def file_error_plan(tmp_path: Path) -> FileSyncPlan:
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(path=str(path).encode(), artist="Synthetic Artist", title="Track")
    library.add(item)
    return plan_file_sync(item, (planned_change("bpm", 126.0),))


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
            "genres": {"num_genres": 2, "promote_styles": True},
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


def test_existing_library_release_uses_specific_promoted_style(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = NoqlenMetaPlugin()
    monkeypatch.setattr(plugins, "_instances", [plugin])
    monkeypatch.delitem(cached_classproperty.cache, (Album, "_types"), raising=False)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    album = library.add_album(
        [
            Item(
                path=str(tmp_path / "track.flac").encode(),
                albumartist="Synthetic Artist",
                album="Synthetic Album",
                artist="Synthetic Artist",
                title="Synthetic Track",
            )
        ]
    )
    plugin.config.set(
        {
            "genres": {"num_genres": 1, "promote_styles": True},
            "providers": {
                "discogs": {"enabled": True, "user_token": "synthetic-token"},
                "musicbrainz": {"enabled": False},
                "lastfm": {"enabled": False},
                "itunes": {"enabled": False, "storefront": "us"},
                "lrclib": {"enabled": False},
            },
        }
    )
    monkeypatch.setattr(
        plugin,
        "_discogs_candidates",
        lambda *args: (
            MetadataCandidate("genres", ("Rock",), "discogs", 0.95, "1"),
            MetadataCandidate(
                "styles", ("Technical Death Metal",), "discogs", 0.95, "1"
            ),
        ),
    )

    invoke(plugin, library, ["--apply", "--all"])

    fresh = library.get_album(album.id)
    assert fresh.genres == ["Technical Death Metal"]
    assert fresh["styles"] == ["Technical Death Metal"]


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


def test_album_database_failure_reports_earlier_committed_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    albums = [
        library.add_album(
            [
                Item(
                    path=str(tmp_path / f"album-{index}.flac").encode(),
                    albumartist="Synthetic Artist",
                    album=f"Synthetic Album {index}",
                    artist="Synthetic Artist",
                    title=f"Synthetic Track {index}",
                )
            ]
        )
        for index in (1, 2)
    ]
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
    original_apply = plugin_module.apply_library_target_plan
    calls = 0

    def apply_in_order(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise LibraryApplicationError("synthetic second Album failure")
        return original_apply(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(plugin_module, "apply_library_target_plan", apply_in_order)

    with pytest.raises(
        LibraryApplicationError, match="earlier target changes were committed"
    ) as captured:
        invoke(plugin, library, ["--apply", "--all"])

    assert isinstance(captured.value.__cause__, LibraryApplicationError)
    assert str(captured.value.__cause__) == "synthetic second Album failure"
    assert library.get_album(albums[0].id).genres == ["Ambient"]
    assert library.get_album(albums[1].id).genres == []


def test_item_database_failure_reports_earlier_committed_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    items = [
        Item(
            path=str(tmp_path / f"item-{index}.flac").encode(),
            artist="Synthetic Artist",
            title=f"Synthetic Track {index}",
        )
        for index in (1, 2)
    ]
    for item in items:
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
        lambda *args: (
            MetadataCandidate("lyrics", "Synthetic line", "lrclib", 0.95, "42"),
        ),
    )
    original_apply = plugin_module.apply_library_track_plan
    calls = 0

    def apply_in_order(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise LibraryTrackApplicationError("synthetic second Item failure")
        return original_apply(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(plugin_module, "apply_library_track_plan", apply_in_order)

    with pytest.raises(
        LibraryTrackApplicationError, match="earlier target changes were committed"
    ) as captured:
        invoke(plugin, library, ["--apply", "--all"])

    assert isinstance(captured.value.__cause__, LibraryTrackApplicationError)
    assert str(captured.value.__cause__) == "synthetic second Item failure"
    assert library.get_item(items[0].id).lyrics == "Synthetic line"
    assert library.get_item(items[1].id).lyrics == ""


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


def test_file_notification_failure_reports_committed_fields(
    file_error_plan: FileSyncPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    output: list[str] = []
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)

    plugin_module._render_file_sync_error(
        file_error_plan,
        FileSyncApplicationError("notification failed", committed=True),
    )

    assert "status=committed-error; fields=1" in output[0]
    assert "recovery_artifact_retained" not in output[0]


def test_file_cleanup_failure_reports_retained_recovery_artifact(
    file_error_plan: FileSyncPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    output: list[str] = []
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)

    plugin_module._render_file_sync_error(
        file_error_plan,
        FileSyncApplicationError(
            "artifact cleanup failed",
            committed=True,
            recovery_artifact_retained=True,
        ),
    )

    assert "status=committed-error; fields=1" in output[0]
    assert "recovery_artifact_retained=true" in output[0]


def test_file_precommit_failure_reports_zero_fields(
    file_error_plan: FileSyncPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    output: list[str] = []
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)

    plugin_module._render_file_sync_error(
        file_error_plan,
        FileSyncApplicationError("pre-commit failure"),
    )

    assert "status=failed; fields=0" in output[0]
