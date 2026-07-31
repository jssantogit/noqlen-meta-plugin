from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from beets import config, ui
from beets.autotag.hooks import AlbumInfo
from beets.importer.actions import Action
from beets.library import Item, Library
from mediafile import MediaFile

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.identity import (
    IdentityAlbumContext,
    MusicBrainzReleaseIdentity,
    MusicBrainzTrackIdentity,
)
from beetsplug.noqlenmeta.identity.library import select_library_identity_targets
from beetsplug.noqlenmeta.integration import eligible_album_info

FIXTURE = Path(__file__).parents[1] / "fixtures" / "identity_tags" / "silence.flac"


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


def _invoke(plugin: NoqlenMetaPlugin, library: Library, args: list[str]) -> None:
    command = plugin.commands()[0]
    opts, query = command.parse_args(args)
    command.func(library, opts, query)


def _configured_plugin(*, importer_apply: bool = False) -> NoqlenMetaPlugin:
    plugin = NoqlenMetaPlugin()
    plugin.config.set(
        {
            "preview": True,
            "apply": importer_apply,
            "apply_mode": "strict",
            "providers": {
                "discogs": {"enabled": True, "user_token": ""},
                "musicbrainz": {"enabled": False},
                "lastfm": {"enabled": False},
                "itunes": {"enabled": False, "storefront": "us"},
                "lrclib": {"enabled": False},
            },
        }
    )
    return plugin


def _album(library: Library, path: Path, *, name: str = "Release"):
    item = Item(
        path=str(path).encode(),
        albumartist="Example Artist",
        album=name,
        artist="Example Artist",
        title="Example Track",
        disc=1,
        track=1,
    )
    return library.add_album([item])


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _IdentitySource:
    def __init__(self, release: MusicBrainzReleaseIdentity) -> None:
        self.release = release

    def candidates_for(
        self, context: IdentityAlbumContext
    ) -> tuple[MusicBrainzReleaseIdentity, ...]:
        return (self.release,)


def test_importer_runs_only_for_selected_apply_tasks() -> None:
    info = AlbumInfo([], artist="Example Artist", album="Example Album")
    apply_task = SimpleNamespace(
        is_album=True,
        choice_flag=Action.APPLY,
        match=SimpleNamespace(info=info),
    )

    assert eligible_album_info(apply_task) is info
    for choice in (Action.SKIP, Action.ASIS):
        task = SimpleNamespace(is_album=True, choice_flag=choice, match=apply_task.match)
        assert eligible_album_info(task) is None


def test_existing_library_preview_strict_and_partial_are_database_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    media_path = tmp_path / "release.flac"
    shutil.copy2(FIXTURE, media_path)
    before_file = _digest(media_path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    album = _album(library, media_path)
    plugin = _configured_plugin(importer_apply=True)
    candidates = (
        MetadataCandidate("genres", ("Ambient",), "discogs", 0.95, "1"),
        MetadataCandidate("year", 2026, "discogs", 0.95, "1"),
    )
    monkeypatch.setattr(plugin, "_discogs_candidates", lambda *args: candidates)

    _invoke(plugin, library, ["album:Release"])
    assert not album.get_fresh_from_db().genres
    _invoke(plugin, library, ["--apply", "album:Release"])
    assert album.get_fresh_from_db().genres == ["Ambient"]
    assert _digest(media_path) == before_file

    album.year = 2020
    album.store(inherit=True)
    partial_candidates = (
        MetadataCandidate("styles", ("Downtempo",), "discogs", 0.95, "1"),
        MetadataCandidate("year", 2026, "discogs", 0.95, "1"),
    )
    monkeypatch.setattr(plugin, "_discogs_candidates", lambda *args: partial_candidates)
    _invoke(plugin, library, ["--apply", "album:Release"])
    assert album.get_fresh_from_db().style == ""
    _invoke(plugin, library, ["--apply", "--partial", "album:Release"])
    fresh = album.get_fresh_from_db()
    assert fresh.style == "Downtempo"
    assert fresh.year == 2020
    assert _digest(media_path) == before_file


def test_identity_tag_preview_and_write_sync_only_four_tags(tmp_path: Path) -> None:
    media_path = tmp_path / "identity.flac"
    shutil.copy2(FIXTURE, media_path)
    media = MediaFile(media_path)
    media.title = "Unrelated title"
    media.save()
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    album = _album(library, media_path)
    item = next(iter(album.items()))
    values = {
        "mb_albumid": "00000000-0000-0000-0000-000000000001",
        "mb_releasegroupid": "00000000-0000-0000-0000-000000000002",
        "mb_trackid": "00000000-0000-0000-0000-000000000003",
        "mb_releasetrackid": "00000000-0000-0000-0000-000000000004",
    }
    for field, value in values.items():
        setattr(item, field, value)
    item.store()
    album.mb_albumid = values["mb_albumid"]
    album.mb_releasegroupid = values["mb_releasegroupid"]
    album.store(inherit=False)
    plugin = NoqlenMetaPlugin()
    before = _digest(media_path)

    _invoke(plugin, library, ["--identity-tags", "--all"])
    assert _digest(media_path) == before
    _invoke(plugin, library, ["--identity-tags", "--write", "--all"])

    written = MediaFile(media_path)
    assert written.title == "Unrelated title"
    assert {field: getattr(written, field) for field in values} == values
    assert item.get_fresh_from_db().mtime != 0


def test_navidrome_oriented_database_identity_and_tag_sequence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    media_path = tmp_path / "sequence.flac"
    shutil.copy2(FIXTURE, media_path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    album = _album(library, media_path)
    item = next(iter(album.items()))
    item.length = 180.0
    item.store()
    before = _digest(media_path)

    ordinary = _configured_plugin()
    monkeypatch.setattr(
        ordinary,
        "_discogs_candidates",
        lambda *args: (MetadataCandidate("genres", ("Ambient",), "discogs", 0.95, "1"),),
    )
    _invoke(ordinary, library, ["--apply", "--all"])
    assert album.get_fresh_from_db().genres == ["Ambient"]
    assert _digest(media_path) == before

    values = {
        "mb_albumid": "00000000-0000-0000-0000-000000000011",
        "mb_releasegroupid": "00000000-0000-0000-0000-000000000012",
        "mb_trackid": "00000000-0000-0000-0000-000000000013",
        "mb_releasetrackid": "00000000-0000-0000-0000-000000000014",
    }
    release = MusicBrainzReleaseIdentity(
        release_mbid=values["mb_albumid"],
        release_group_mbid=values["mb_releasegroupid"],
        album_artist="Example Artist",
        album="Release",
        tracks=(
            MusicBrainzTrackIdentity(
                recording_mbid=values["mb_trackid"],
                release_track_mbid=values["mb_releasetrackid"],
                artist="Example Artist",
                title="Example Track",
                length=180.0,
                medium=1,
                medium_index=1,
                index=1,
            ),
        ),
    )
    identity = NoqlenMetaPlugin()
    identity.config.set(
        {"identity": {"enabled": True, "preview": True, "apply": True}}
    )
    identity._musicbrainz_identity_source = _IdentitySource(release)

    _invoke(identity, library, ["--identity", "--all"])
    assert not item.get_fresh_from_db().mb_trackid
    assert _digest(media_path) == before
    _invoke(identity, library, ["--identity", "--apply", "--all"])
    fresh = item.get_fresh_from_db()
    assert {field: fresh.get(field, with_album=True) for field in values} == values
    assert _digest(media_path) == before

    _invoke(identity, library, ["--identity-tags", "--write", "--all"])
    written = MediaFile(media_path)
    assert {field: getattr(written, field) for field in values} == values


def test_permission_isolation_and_invalid_modes_fail_before_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    plugin = _configured_plugin(importer_apply=True)
    monkeypatch.setattr(
        library,
        "albums",
        lambda *args: pytest.fail("invalid command reached ordinary selection"),
    )
    monkeypatch.setattr(
        library,
        "items",
        lambda *args: pytest.fail("invalid command reached Item selection"),
    )

    invalid = (
        ["--partial", "--all"],
        ["--write", "--all"],
        ["--identity", "--identity-tags", "--all"],
        ["--identity-tags", "--apply", "--all"],
        ["--identity-tags", "--partial", "--all"],
    )
    for args in invalid:
        with pytest.raises(ui.UserError):
            _invoke(plugin, library, args)


def test_moderate_identity_selection_is_unique_and_deterministic(tmp_path: Path) -> None:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    expected_ids = []
    for index in range(40):
        album = library.add_album(
            [
                Item(
                    path=f"synthetic-{index}.flac".encode(),
                    albumartist="Artist",
                    album=f"Album {index:02d}",
                    artist="Artist",
                    title="Track",
                    disc=1,
                    track=1,
                )
            ]
        )
        expected_ids.append(album.id)

    selected = select_library_identity_targets(library, None)

    assert len(selected) == 40
    assert [target.album_id for target in selected] == expected_ids
    assert len({target.album_id for target in selected}) == 40
