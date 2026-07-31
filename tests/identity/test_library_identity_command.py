from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from beets import config, ui
from beets.dbcore.db import Transaction
from beets.library import Album, Item, Library

import beetsplug.noqlenmeta as plugin_module
from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.identity import (
    IdentityAlbumContext,
    IdentitySourceError,
    MusicBrainzReleaseIdentity,
    MusicBrainzTrackIdentity,
)
from beetsplug.noqlenmeta.identity.library_application import (
    LibraryIdentityApplicationError,
)

from .helpers import mbid

PRIVATE_PATH = b"/private/library/identity-track.flac"
PRIVATE_QUERY = "id:999999999"
PRIVATE_ERROR = "private source failure at /private/library"
PRIVATE_MALFORMED_ID = "private-malformed-identity-value"


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


@pytest.fixture
def library(tmp_path: Path) -> object:
    yield Library(str(tmp_path / "synthetic-library.db"), set_music_dir=False)


class FakeIdentitySource:
    def __init__(
        self,
        route: Callable[
            [IdentityAlbumContext], Sequence[MusicBrainzReleaseIdentity]
        ],
    ) -> None:
        self.route = route
        self.contexts: list[IdentityAlbumContext] = []

    def candidates_for(
        self, context: IdentityAlbumContext
    ) -> tuple[MusicBrainzReleaseIdentity, ...]:
        self.contexts.append(context)
        return tuple(self.route(context))


def configure(
    plugin: NoqlenMetaPlugin,
    *,
    identity_enabled: object = True,
    identity_apply: object = False,
    ordinary_apply: bool = False,
    discogs: bool = False,
) -> None:
    plugin.config.set(
        {
            "preview": True,
            "apply": ordinary_apply,
            "identity": {
                "enabled": identity_enabled,
                "preview": True,
                "apply": identity_apply,
            },
            "fields": {
                "genres": True,
                "styles": False,
                "labels": False,
                "catalog_numbers": False,
                "barcodes": False,
                "country": False,
                "year": False,
                "media": False,
                "format_descriptions": False,
                "mood": False,
                "lyrics": False,
                "synced_lyrics": False,
                "cover": False,
            },
            "providers": {
                "discogs": {"enabled": discogs, "user_token": "synthetic-token"},
                "musicbrainz": {"enabled": False},
                "lastfm": {"enabled": False},
                "itunes": {"enabled": False, "storefront": "us"},
                "lrclib": {"enabled": False},
            },
        }
    )


def add_album(
    library: Library,
    name: str,
    *,
    count: int = 1,
    seed: int | None = None,
) -> Album:
    items = []
    for index in range(1, count + 1):
        values: dict[str, object] = {
            "path": f"/synthetic/{name}/{index}.flac".encode(),
            "albumartist": "Example Artist",
            "album": name,
            "artist": "Example Artist",
            "title": f"Track {index}",
            "length": 180.0 + index,
            "disc": 1,
            "track": index,
        }
        if seed is not None:
            values.update(
                {
                    "mb_albumid": mbid(seed),
                    "mb_releasegroupid": mbid(seed + 1),
                    "mb_trackid": mbid(seed + 100 + index),
                    "mb_releasetrackid": mbid(seed + 200 + index),
                }
            )
        items.append(Item(**values))
    album = library.add_album(items)
    if seed is not None:
        album.mb_albumid = mbid(seed)
        album.mb_releasegroupid = mbid(seed + 1)
        album.store(inherit=False)
    return album


def add_singleton(library: Library, title: str = "Solo") -> Item:
    item = Item(
        path=PRIVATE_PATH,
        artist="Example Artist",
        album=title,
        title=title,
        length=181.0,
        disc=1,
        track=1,
    )
    library.add(item)
    return item


def remote_for(
    context: IdentityAlbumContext,
    seed: int,
) -> MusicBrainzReleaseIdentity:
    tracks = tuple(
        MusicBrainzTrackIdentity(
            recording_mbid=mbid(seed + 100 + index),
            release_track_mbid=mbid(seed + 200 + index),
            artist=track.artist,
            title=track.title,
            length=track.length,
            medium=track.medium,
            medium_index=track.medium_index,
            index=track.index,
        )
        for index, track in enumerate(context.tracks, start=1)
    )
    return MusicBrainzReleaseIdentity(
        release_mbid=mbid(seed),
        release_group_mbid=mbid(seed + 1),
        album_artist=context.album_artist,
        album=context.album,
        tracks=tracks,
        year=context.year,
        country=context.country,
        label=context.label,
    )


def invoke(plugin: NoqlenMetaPlugin, library: Library, args: list[str]) -> None:
    command = plugin.commands()[0]
    opts, query = command.parse_args(args)
    command.func(library, opts, query)


def capture_output(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    output: list[str] = []
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)
    return output


def identity_values(library: Library, album: Album) -> tuple[object, ...]:
    fresh = library.get_album(album.id)
    assert fresh is not None
    items = list(fresh.items())
    return (
        fresh.mb_albumid,
        fresh.mb_releasegroupid,
        *(
            value
            for item in items
            for value in (
                item.mb_albumid,
                item.mb_releasegroupid,
                item.mb_trackid,
                item.mb_releasetrackid,
            )
        ),
    )


def test_identity_option_parsing_and_exclusive_validation(library: Library) -> None:
    plugin = NoqlenMetaPlugin()
    configure(plugin)
    command = plugin.commands()[0]

    opts, query = command.parse_args(["--identity", "--apply", "album:Example"])
    assert opts.identity is True
    assert opts.apply is True
    assert opts.partial is False
    assert query == ["album:Example"]

    with pytest.raises(ui.UserError, match="Item query or --all"):
        invoke(plugin, library, ["--identity"])
    with pytest.raises(ui.UserError, match="not both"):
        invoke(plugin, library, ["--identity", "--all", "album:Example"])
    with pytest.raises(ui.UserError, match="cannot be used with --partial"):
        invoke(plugin, library, ["--identity", "--apply", "--partial", "--all"])


def test_identity_mode_does_not_inherit_importer_enabled_config(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    add_album(library, "Disabled")
    plugin = NoqlenMetaPlugin()
    configure(plugin, identity_enabled=False)
    source = FakeIdentitySource(
        lambda context: (remote_for(context, 17000),)
    )
    plugin._musicbrainz_identity_source = source
    output = capture_output(monkeypatch)

    invoke(plugin, library, ["--identity", "--all"])

    assert len(source.contexts) == 1
    assert "application: disabled" in output[0]


def test_item_queries_expand_complete_albums_and_singletons_and_all(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    add_album(library, "Expanded", count=2)
    singleton = add_singleton(library)
    plugin = NoqlenMetaPlugin()
    configure(plugin)
    source = FakeIdentitySource(lambda context: (remote_for(context, 1000),))
    plugin._musicbrainz_identity_source = source
    capture_output(monkeypatch)

    invoke(plugin, library, ["--identity", "title:Track 2"])
    invoke(plugin, library, ["--identity", f"id:{singleton.id}"])
    invoke(plugin, library, ["--identity", "--all"])

    assert [len(context.tracks) for context in source.contexts] == [2, 1, 2, 1]
    assert [context.album for context in source.contexts] == [
        "Expanded",
        "Solo",
        "Expanded",
        "Solo",
    ]


def test_preview_and_importer_apply_config_never_write_library_identity(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library, "Preview")
    before = identity_values(library, album)
    plugin = NoqlenMetaPlugin()
    configure(plugin, identity_apply=True, ordinary_apply=True)
    plugin._musicbrainz_identity_source = FakeIdentitySource(
        lambda context: (remote_for(context, 2000),)
    )
    output = capture_output(monkeypatch)
    monkeypatch.setattr(
        plugin_module,
        "apply_library_identity_plan",
        lambda *args: pytest.fail("preview attempted a library identity write"),
    )

    invoke(plugin, library, ["--identity", "--all"])

    assert identity_values(library, album) == before
    assert "application: disabled" in output[0]


def test_identity_apply_persists_complete_eligible_database_repair(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library, "Repair", count=2)
    plugin = NoqlenMetaPlugin()
    configure(plugin)
    plugin._musicbrainz_identity_source = FakeIdentitySource(
        lambda context: (remote_for(context, 3000),)
    )
    output = capture_output(monkeypatch)

    invoke(plugin, library, ["--identity", "--all", "--apply"])

    assert identity_values(library, album) == (
        mbid(3000),
        mbid(3001),
        mbid(3000),
        mbid(3001),
        mbid(3101),
        mbid(3201),
        mbid(3000),
        mbid(3001),
        mbid(3102),
        mbid(3202),
    )
    assert "verdict: missing" in output[0]
    assert "application: stored 10 database field(s)" in output[0]


def test_all_source_calls_and_command_mapping_finish_before_first_sql_mutation(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    add_album(library, "First")
    add_album(library, "Second")
    plugin = NoqlenMetaPlugin()
    configure(plugin)
    source = FakeIdentitySource(
        lambda context: (remote_for(context, 4000 + len(source.contexts) * 1000),)
    )
    plugin._musicbrainz_identity_source = source
    capture_output(monkeypatch)
    mapped: list[str] = []
    original_map = plugin_module.map_library_identity_targets
    original_mutate = Transaction.mutate

    def recording_map(result: object) -> object:
        assert len(source.contexts) == 2
        mapped.append(result.context.album)  # type: ignore[attr-defined]
        return original_map(result)  # type: ignore[arg-type]

    def guarded_mutate(
        transaction: Transaction, statement: str, subvals: object = ()
    ) -> object:
        assert len(source.contexts) == 2
        assert mapped == ["First", "Second"]
        return original_mutate(transaction, statement, subvals)

    monkeypatch.setattr(plugin_module, "map_library_identity_targets", recording_map)
    monkeypatch.setattr(Transaction, "mutate", guarded_mutate)

    invoke(plugin, library, ["--identity", "--all", "--apply"])


def test_command_wide_stale_preflight_aborts_every_identity_write(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    first = add_album(library, "Stale First")
    second = add_album(library, "Stale Second")

    def route(context: IdentityAlbumContext) -> tuple[MusicBrainzReleaseIdentity, ...]:
        if context.album == "Stale Second":
            stale = library.get_item(next(iter(first.items())).id)
            assert stale is not None
            stale.title = "Changed after planning"
            stale.store()
        return (remote_for(context, 6000 if context.album == "Stale First" else 7000),)

    plugin = NoqlenMetaPlugin()
    configure(plugin)
    plugin._musicbrainz_identity_source = FakeIdentitySource(route)
    capture_output(monkeypatch)

    with pytest.raises(LibraryIdentityApplicationError, match="stale"):
        invoke(plugin, library, ["--identity", "--all", "--apply"])

    assert not any(identity_values(library, first))
    assert not any(identity_values(library, second))


def test_source_failure_is_private_and_does_not_block_other_targets(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    first = add_album(library, "Available First")
    failed = add_album(library, "Unavailable")
    last = add_album(library, "Available Last")

    def route(context: IdentityAlbumContext) -> tuple[MusicBrainzReleaseIdentity, ...]:
        if context.album == "Unavailable":
            raise IdentitySourceError(PRIVATE_ERROR)
        seed = 8000 if context.album == "Available First" else 9000
        return (remote_for(context, seed),)

    plugin = NoqlenMetaPlugin()
    configure(plugin)
    source = FakeIdentitySource(route)
    plugin._musicbrainz_identity_source = source
    output = capture_output(monkeypatch)

    invoke(plugin, library, ["--identity", "--all", "--apply"])

    assert [context.album for context in source.contexts] == [
        "Available First",
        "Unavailable",
        "Available Last",
    ]
    assert identity_values(library, first)[0] == mbid(8000)
    assert not any(identity_values(library, failed))
    assert identity_values(library, last)[0] == mbid(9000)
    rendered = "\n".join(output)
    assert "MusicBrainz identity audit unavailable" in rendered
    assert PRIVATE_ERROR not in rendered
    assert PRIVATE_PATH.decode() not in rendered


def test_one_identity_source_is_retained_across_library_commands(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    add_album(library, "Retained")
    instances: list[FakeIdentitySource] = []

    def construct() -> FakeIdentitySource:
        source = FakeIdentitySource(lambda context: (remote_for(context, 10000),))
        instances.append(source)
        return source

    monkeypatch.setattr(plugin_module, "BeetsMusicBrainzIdentitySource", construct)
    plugin = NoqlenMetaPlugin()
    configure(plugin)
    capture_output(monkeypatch)

    invoke(plugin, library, ["--identity", "--all"])
    invoke(plugin, library, ["--identity", "--all"])

    assert len(instances) == 1
    assert len(instances[0].contexts) == 2
    assert plugin._musicbrainz_identity_source is instances[0]


def test_identity_mode_never_runs_ordinary_providers_or_application(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    add_album(library, "Identity Only")
    plugin = NoqlenMetaPlugin()
    configure(plugin, ordinary_apply=True, discogs=True)
    plugin._musicbrainz_identity_source = FakeIdentitySource(
        lambda context: (remote_for(context, 11000),)
    )
    capture_output(monkeypatch)
    for name in (
        "_discogs_candidates",
        "_musicbrainz_candidates",
        "_itunes_candidates",
        "_lastfm_candidates",
        "_lrclib_candidates",
    ):
        monkeypatch.setattr(
            NoqlenMetaPlugin,
            name,
            lambda *args, name=name: pytest.fail(f"identity mode called {name}"),
        )
    monkeypatch.setattr(
        plugin_module,
        "apply_library_target_plan",
        lambda *args: pytest.fail("identity mode called ordinary application"),
    )

    invoke(plugin, library, ["--identity", "--all"])


def test_bare_apply_keeps_existing_ordinary_enrichment_behavior(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library, "Ordinary")
    plugin = NoqlenMetaPlugin()
    configure(plugin, identity_enabled=False, discogs=True)
    monkeypatch.setattr(
        plugin_module,
        "select_library_identity_targets",
        lambda *args: pytest.fail("bare --apply entered identity mode"),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (
            MetadataCandidate("genres", ("Synthetic Genre",), "discogs", 0.95, "1"),
        ),
    )
    capture_output(monkeypatch)

    invoke(plugin, library, ["--apply", "album:Ordinary"])

    fresh = library.get_album(album.id)
    assert fresh is not None
    assert fresh.genres == ["Synthetic Genre"]


def test_identity_output_omits_paths_queries_local_keys_and_raw_malformed_values(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library, "Privacy")
    item = next(iter(album.items()))
    item.path = PRIVATE_PATH
    item.mb_trackid = PRIVATE_MALFORMED_ID
    item.store()
    plugin = NoqlenMetaPlugin()
    configure(plugin)
    plugin._musicbrainz_identity_source = FakeIdentitySource(
        lambda context: (remote_for(context, 12000),)
    )
    output = capture_output(monkeypatch)

    invoke(plugin, library, ["--identity", f"id:{item.id}"])

    rendered = "\n".join(output)
    assert "current: malformed" in rendered
    assert PRIVATE_PATH.decode() not in rendered
    assert f"id:{item.id}" not in rendered
    assert "library-item:" not in rendered
    assert PRIVATE_MALFORMED_ID not in rendered


def test_mixed_confirmed_repair_and_ambiguous_singleton_command(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    confirmed = add_album(library, "Album A", seed=13000)
    repair = add_album(library, "Album B")
    singleton = add_singleton(library, "Singleton")
    confirmed_before = copy.deepcopy(identity_values(library, confirmed))

    def route(context: IdentityAlbumContext) -> tuple[MusicBrainzReleaseIdentity, ...]:
        if context.album == "Album A":
            return (remote_for(context, 13000),)
        if context.album == "Album B":
            return (remote_for(context, 14000),)
        return (remote_for(context, 15000), remote_for(context, 16000))

    plugin = NoqlenMetaPlugin()
    configure(plugin)
    plugin._musicbrainz_identity_source = FakeIdentitySource(route)
    output = capture_output(monkeypatch)

    invoke(plugin, library, ["--identity", "--all", "--apply"])

    assert identity_values(library, confirmed) == confirmed_before
    assert identity_values(library, repair)[0:2] == (mbid(14000), mbid(14001))
    fresh_singleton = library.get_item(singleton.id)
    assert fresh_singleton is not None
    assert not fresh_singleton.mb_albumid
    assert not fresh_singleton.mb_releasegroupid
    assert not fresh_singleton.mb_trackid
    assert not fresh_singleton.mb_releasetrackid
    rendered = "\n".join(output)
    assert "library entry: Example Artist - Album A\n  verdict: confirmed" in rendered
    assert "library entry: Example Artist - Album B\n  verdict: missing" in rendered
    assert "library entry: Example Artist - Singleton\n  verdict: ambiguous" in rendered
    assert "application: confirmed/no changes" in rendered
    assert "application: blocked" in rendered
