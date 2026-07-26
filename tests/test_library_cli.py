import copy
import logging
from types import SimpleNamespace

import pytest
from beets import config, ui
from beets.autotag.hooks import AlbumInfo
from beets.importer.actions import Action
from beets.importer.tasks import ImportTask
from beets.library import Album, Item, Library
from beets.ui import Subcommand

import beetsplug.noqlenmeta as plugin_module
from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.changeplan import ChangePlan
from beetsplug.noqlenmeta.domain import MetadataCandidate, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.library_integration import (
    context_from_library_album,
    current_values_from_library_album,
)
from beetsplug.noqlenmeta.library_mapping import LibraryMappingError
from beetsplug.noqlenmeta.providers import ProviderError
from beetsplug.noqlenmeta.providers.base import ProviderContractError

TOKEN = "test-personal-token"


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    # Materialize beets' lazy defaults before snapshotting its source list.
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


@pytest.fixture
def library() -> Library:
    return Library(":memory:", set_music_dir=False)


def configure_enabled(
    plugin: NoqlenMetaPlugin,
    *,
    preview: bool = True,
    apply: bool = False,
    apply_mode: str = "strict",
    discogs: bool = True,
    itunes: bool = False,
) -> None:
    plugin.config.set(
        {
            "preview": preview,
            "apply": apply,
            "apply_mode": apply_mode,
            "providers": {
                "discogs": {"enabled": discogs, "user_token": TOKEN},
                "itunes": {"enabled": itunes, "storefront": "us"},
            },
        }
    )


def candidate(
    field: str = "genres",
    value: object = ("Progressive Metal", "Groove Metal"),
    *,
    confidence: float = 0.94,
    provider: str = "discogs",
) -> MetadataCandidate:
    return MetadataCandidate(
        field,
        value,  # type: ignore[arg-type]
        provider,
        confidence,
        "123456" if provider == "discogs" else "1097861387",
    )


def add_album(lib: Library, **overrides: object) -> Album:
    values: dict[str, object] = {
        "albumartist": "Gojira",
        "album": "From Mars to Sirius",
        "title": "Ocean Planet",
        "artist": "Gojira",
        "path": b"01 Ocean Planet.flac",
    }
    values.update(overrides)
    return lib.add_album([Item(**values)])


def invoke(plugin: NoqlenMetaPlugin, lib: object, args: list[str]) -> None:
    opts, query = plugin.commands()[0].parse_args(args)
    plugin.commands()[0].func(lib, opts, query)


def test_commands_register_one_real_subcommand_with_alias() -> None:
    plugin = NoqlenMetaPlugin()

    commands = plugin.commands()

    assert len(commands) == 1
    assert isinstance(commands[0], Subcommand)
    assert commands[0].name == "noqlenmeta"
    assert "nm" in commands[0].aliases
    assert commands[0].func == plugin._command_noqlenmeta
    opts, query = commands[0].parse_args(["--apply"])
    assert opts.apply is True
    assert query == []


def test_no_query_fails_before_provider_or_library_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: pytest.fail("provider called without a query"),
    )
    lib = SimpleNamespace(albums=lambda query: pytest.fail("library queried without consent"))

    with pytest.raises(ui.UserError, match="provide an album query or use --all"):
        invoke(plugin, lib, [])

    with pytest.raises(ui.UserError, match="provide an album query or use --all"):
        invoke(plugin, lib, ["   "])

    with pytest.raises(ui.UserError, match="provide an album query or use --all"):
        invoke(plugin, lib, ["--apply"])


def test_all_is_allowed_and_query_plus_all_is_rejected(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", lambda *args: ())

    invoke(plugin, library, ["--all"])

    assert album.id is not None
    with pytest.raises(ui.UserError, match="not both"):
        invoke(plugin, library, ["--all", "artist:Gojira"])


def test_no_useful_provider_avoids_library_query(monkeypatch: pytest.MonkeyPatch) -> None:
    output: list[str] = []
    plugin = NoqlenMetaPlugin()
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)
    lib = SimpleNamespace(albums=lambda query: pytest.fail("library must not be queried"))

    invoke(plugin, lib, ["artist:Gojira"])

    assert output == [
        "Noqlen Meta: no enabled provider can contribute to the configured fields"
    ]


def test_no_match_reports_without_provider_call(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: pytest.fail("provider called without a matched album"),
    )

    invoke(plugin, library, ["album:Missing"])

    assert output == ["Noqlen Meta: no albums matched"]


def test_library_album_adapters_preserve_canonical_shapes_without_splitting() -> None:
    album = Album(
        albumartist="  Gojira  ",
        album=" From Mars to Sirius ",
        year=2005,
        barcode=" 0123456789012 ",
        catalognum=" RR-123 ",
        discogs_albumid=123456,
        genres=["Progressive Metal", "", " Groove Metal "],
        style="Progressive Metal / Groove Metal",
        label="Label A / Label B",
        country=" FR ",
    )

    context = context_from_library_album(album)

    assert context == ReleaseEnrichmentContext(
        album_artist="Gojira",
        album_title="From Mars to Sirius",
        year=2005,
        barcode="0123456789012",
        catalog_number="RR-123",
        external_ids=context.external_ids,
    )
    assert [(item.namespace, item.value) for item in context.external_ids] == [
        ("discogs.release", "123456")
    ]
    assert current_values_from_library_album(album) == {
        "genres": ("Progressive Metal", "Groove Metal"),
        "styles": ("Progressive Metal / Groove Metal",),
        "labels": ("Label A / Label B",),
        "catalog_numbers": ("RR-123",),
        "barcodes": ("0123456789012",),
        "country": "FR",
        "year": 2005,
    }
    assert "media" not in current_values_from_library_album(album)


@pytest.mark.parametrize("year", [0, 10000, True, "2005"])
def test_library_adapter_omits_invalid_year(year: object) -> None:
    album = Album(albumartist="Artist", album="Album")
    album._values_fixed["year"] = year

    assert context_from_library_album(album).year is None
    assert "year" not in current_values_from_library_album(album)


@pytest.mark.parametrize("field", ["albumartist", "album"])
def test_library_adapter_requires_artist_and_title(field: str) -> None:
    album = Album(albumartist="Artist", album="Album")
    setattr(album, field, " ")

    assert context_from_library_album(album) is None


def test_cli_preview_maps_supported_fields_and_blocks_media(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    album = add_album(library)
    snapshot = copy.deepcopy(dict(album))
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (
            candidate(),
            candidate("labels", ("Roadrunner",)),
            candidate("media", ("CD",)),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.library_integration.ui.print_", output.append)

    invoke(plugin, library, ["album:From Mars to Sirius"])

    assert len(output) == 1
    assert "Noqlen Meta / library target preview:" in output[0]
    assert "genres\n    PROPOSE\n    target: genres" in output[0]
    assert "labels\n    PROPOSE\n    target: label" in output[0]
    assert "media\n    BLOCKED" in output[0]
    assert "persistent Album has no supported album-level media target" in output[0]
    assert "application: disabled (preview only)" in output[0]
    assert "file tags: unchanged" in output[0]
    assert dict(album) == snapshot


def test_cli_is_preview_only_regardless_of_import_application_config(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    album = add_album(library)
    items = list(album.items())
    album_snapshot = [copy.deepcopy(dict(item)) for item in library.albums()]
    item_snapshots = [copy.deepcopy(dict(item)) for item in items]
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, preview=False, apply=True, apply_mode="partial")
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (candidate(),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.library_integration.ui.print_", output.append)
    monkeypatch.setattr(
        Album,
        "__setitem__",
        lambda *args, **kwargs: pytest.fail("assigned persistent Album metadata"),
    )
    monkeypatch.setattr(
        Album,
        "items",
        lambda *args, **kwargs: pytest.fail("queried Album Items"),
    )
    for model, method in (
        (Album, "store"),
        (Album, "try_sync"),
        (Album, "move"),
        (Item, "store"),
        (Item, "write"),
        (Item, "try_sync"),
        (Item, "move"),
    ):
        monkeypatch.setattr(
            model,
            method,
            lambda *args, method=method, **kwargs: pytest.fail(f"called {method}"),
        )

    invoke(plugin, library, ["artist:Gojira"])

    assert "library target preview" in output[0]
    assert [dict(item) for item in library.albums()] == album_snapshot
    assert [dict(item) for item in library.items()] == item_snapshots


def test_cli_preserves_authority_and_provider_failure_fallback(
    monkeypatch: pytest.MonkeyPatch,
    library: Library,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output: list[str] = []
    add_album(library)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=True, itunes=True)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (candidate(confidence=0.88),),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda *args: (candidate(value=("Metal",), confidence=0.99, provider="itunes"),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.library_integration.ui.print_", output.append)

    invoke(plugin, library, ["artist:Gojira"])

    assert "source: Discogs" in output[0]
    assert "proposed: Progressive Metal, Groove Metal" in output[0]

    output.clear()
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (_ for _ in ()).throw(ProviderError(f"unsafe {TOKEN}")),
    )
    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        invoke(plugin, library, ["artist:Gojira"])

    assert "source: iTunes" in output[0]
    assert TOKEN not in caplog.text
    assert TOKEN not in output[0]


def test_cli_internal_contract_and_mapping_errors_propagate(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    add_album(library)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=False, itunes=True)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda *args: (candidate("labels", ("Invalid",), provider="itunes"),),
    )

    with pytest.raises(ProviderContractError, match="unsupported field 'labels'"):
        invoke(plugin, library, ["artist:Gojira"])

    configure_enabled(plugin, discogs=True, itunes=False)
    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", lambda *args: ())
    monkeypatch.setattr(
        plugin_module,
        "map_change_plan_to_library_album",
        lambda plan: (_ for _ in ()).throw(LibraryMappingError("broken library mapping")),
    )

    with pytest.raises(LibraryMappingError, match="broken library mapping"):
        invoke(plugin, library, ["artist:Gojira"])


def test_cli_skips_missing_identity_before_provider_work(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    add_album(library, albumartist="")
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: pytest.fail("provider called without release identity"),
    )
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)

    invoke(plugin, library, ["--all"])

    assert output == [
        "Noqlen Meta: [1/1] album has no usable artist/title identity; skipped"
    ]


def test_cli_preview_sanitizes_album_and_provider_text(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    add_album(library, albumartist="Go\njira", album="\x1b[31mMars")
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (candidate("labels", ("Safe\nForged",)),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.library_integration.ui.print_", output.append)

    invoke(plugin, library, ["--all"])

    assert "Go jira - [31mMars" in output[0]
    assert "proposed: Safe Forged" in output[0]
    assert "\x1b" not in output[0]


def test_multiple_albums_are_planned_independently(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    add_album(library, album="Album A")
    add_album(library, album="Album B", title="Track B")
    contexts: list[ReleaseEnrichmentContext] = []
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    def candidates(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        token: str | None,
    ) -> tuple[MetadataCandidate, ...]:
        contexts.append(context)
        return (candidate(value=(context.album_title,)),)

    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", candidates)
    monkeypatch.setattr("beetsplug.noqlenmeta.library_integration.ui.print_", output.append)

    invoke(plugin, library, ["artist:Gojira"])

    assert {context.album_title for context in contexts} == {"Album A", "Album B"}
    assert len(output) == 2
    assert "[1/2]" in output[0]
    assert "[2/2]" in output[1]


def test_importer_and_cli_invoke_the_same_planning_helper(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    add_album(library)
    calls: list[tuple[ReleaseEnrichmentContext, object, object]] = []

    def record_plan(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        current_values: object,
        policy: object,
    ) -> ChangePlan:
        calls.append((context, current_values, policy))
        return ChangePlan()

    monkeypatch.setattr(NoqlenMetaPlugin, "_build_change_plan_for_release", record_plan)
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.library_integration.ui.print_", lambda output: None
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", lambda output: None)
    importer_plugin = NoqlenMetaPlugin()
    configure_enabled(importer_plugin)
    cli_plugin = NoqlenMetaPlugin()
    configure_enabled(cli_plugin)
    info = AlbumInfo([], artist="Gojira", album="From Mars to Sirius")
    task = ImportTask(None, [], [])
    task.choice_flag = Action.APPLY
    task.match = SimpleNamespace(info=info)

    importer_plugin._import_task_choice(None, task)
    invoke(cli_plugin, library, ["artist:Gojira"])

    assert len(calls) == 2
    assert calls[0][0] == calls[1][0]
    assert calls[0][1] == calls[1][1]
    assert calls[0][2] == calls[1][2]


def test_cli_apply_persists_even_when_importer_apply_is_false(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    album = add_album(library)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=False)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (candidate(value=("Rock", "Metal")),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.library_integration.ui.print_", output.append)

    invoke(plugin, library, ["artist:Gojira", "--apply"])

    reloaded = library.get_album(album.id)
    assert reloaded.genres == ["Rock", "Metal"]
    assert [item.genres for item in reloaded.items()] == [["Rock", "Metal"]]
    assert "application: stored in library database (1 fields)" in output[0]
    assert "file tags: unchanged" in output[0]


def test_importer_config_does_not_authorize_cli_database_writes(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    album = add_album(library)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, preview=False, apply=True, apply_mode="partial")
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (candidate(value=("Rock", "Metal")),),
    )
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.library_integration.ui.print_", lambda output: None
    )

    invoke(plugin, library, ["artist:Gojira"])

    reloaded = library.get_album(album.id)
    assert reloaded.genres == []
    assert [item.genres for item in reloaded.items()] == [[]]


def test_cli_strict_mapping_blocker_prevents_mapped_database_change(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    album = add_album(library)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (candidate(value=("Rock",)), candidate("media", ("CD",))),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.library_integration.ui.print_", output.append)

    invoke(plugin, library, ["artist:Gojira", "--apply"])

    reloaded = library.get_album(album.id)
    assert reloaded.genres == []
    assert [item.genres for item in reloaded.items()] == [[]]
    assert "application: blocked" in output[0]
    assert "mapping blockers: 1" in output[0]


def test_cli_strict_review_prevents_mapped_database_change(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    album = add_album(library, label="Existing")
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (
            candidate(value=("Rock",)),
            candidate("labels", ("Replacement",)),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.library_integration.ui.print_", output.append)

    invoke(plugin, library, ["artist:Gojira", "--apply"])

    reloaded = library.get_album(album.id)
    assert reloaded.genres == []
    assert reloaded.label == "Existing"
    assert [item.genres for item in reloaded.items()] == [[]]
    assert "application: blocked" in output[0]
    assert "resolution review: 1" in output[0]


def test_all_apply_is_strict_per_album(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    output: list[str] = []
    albums = [
        add_album(library, album="Album A"),
        add_album(library, album="Album B", title="Track B"),
        add_album(library, album="Album C", title="Track C"),
    ]
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    def candidates(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        token: str | None,
    ) -> tuple[MetadataCandidate, ...]:
        values = [candidate(value=(context.album_title,))]
        if context.album_title == "Album B":
            values.append(candidate("media", ("CD",)))
        return tuple(values)

    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", candidates)
    monkeypatch.setattr("beetsplug.noqlenmeta.library_integration.ui.print_", output.append)

    invoke(plugin, library, ["--all", "--apply"])

    assert library.get_album(albums[0].id).genres == ["Album A"]
    assert library.get_album(albums[1].id).genres == []
    assert library.get_album(albums[2].id).genres == ["Album C"]
    assert ["application: blocked" in entry for entry in output] == [False, True, False]


def test_all_planning_completes_before_first_store(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    add_album(library, album="Album A")
    add_album(library, album="Album B", title="Track B")
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (candidate(value=("Rock",)),),
    )
    calls = 0
    original_map = plugin_module.map_change_plan_to_library_album

    def fail_second_mapping(plan: ChangePlan) -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise LibraryMappingError("broken second plan")
        return original_map(plan)

    monkeypatch.setattr(plugin_module, "map_change_plan_to_library_album", fail_second_mapping)
    store_calls: list[Album] = []
    monkeypatch.setattr(Album, "store", lambda album, *args, **kwargs: store_calls.append(album))

    with pytest.raises(LibraryMappingError, match="broken second plan"):
        invoke(plugin, library, ["--all", "--apply"])

    assert calls == 2
    assert store_calls == []


def test_store_failure_aborts_later_albums_without_global_rollback(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    albums = [
        add_album(library, album="Album A"),
        add_album(library, album="Album B", title="Track B"),
        add_album(library, album="Album C", title="Track C"),
    ]
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    def candidates(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        token: str | None,
    ) -> tuple[MetadataCandidate, ...]:
        return (candidate(value=(context.album_title,)),)

    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", candidates)
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.library_integration.ui.print_", lambda output: None
    )
    original_store = Album.store
    store_attempts: list[str] = []

    def fail_album_b(self: Album, fields: object = None, inherit: bool = True) -> None:
        store_attempts.append(self.album)
        if self.album == "Album B":
            raise RuntimeError("database failure")
        original_store(self, fields=fields, inherit=inherit)

    monkeypatch.setattr(Album, "store", fail_album_b)

    with pytest.raises(RuntimeError, match="database failure"):
        invoke(plugin, library, ["--all", "--apply"])

    assert store_attempts == ["Album A", "Album B"]
    assert library.get_album(albums[0].id).genres == ["Album A"]
    assert library.get_album(albums[1].id).genres == []
    assert library.get_album(albums[2].id).genres == []
