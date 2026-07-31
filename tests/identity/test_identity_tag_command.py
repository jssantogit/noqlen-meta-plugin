from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from beets import config, ui
from beets.library import Item, Library
from mediafile import MediaFile

import beetsplug.noqlenmeta as plugin_module
from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.identity import IDENTITY_TAG_FIELDS, IdentityTagApplicationError

from .helpers import mbid

FIXTURE = Path(__file__).parents[1] / "fixtures" / "identity_tags" / "silence.flac"


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return Library(str(tmp_path / "library.db"), set_music_dir=False)


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


def _copy(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    shutil.copy2(FIXTURE, path)
    return path


def _album(library: Library, tmp_path: Path, name: str = "Album", count: int = 2):
    items = [
        Item(
            path=str(_copy(tmp_path, f"{name}-{index}.flac")).encode(),
            albumartist="Example Artist",
            album=name,
            artist="Example Artist",
            title=f"Track {index}",
            disc=1,
            track=index,
            mtime=10.0,
            mb_albumid=mbid(1),
            mb_releasegroupid=mbid(2),
            mb_trackid=mbid(10 + index),
            mb_releasetrackid=mbid(20 + index),
        )
        for index in range(1, count + 1)
    ]
    album = library.add_album(items)
    album.mb_albumid = mbid(1)
    album.mb_releasegroupid = mbid(2)
    album.store(inherit=False)
    return album


def _singleton(
    library: Library, tmp_path: Path, name: str = "Single", *, coherent: bool = True
) -> Item:
    values: dict[str, object] = {}
    if coherent:
        values.update(
            mb_albumid=mbid(101),
            mb_releasegroupid=mbid(102),
            mb_trackid=mbid(103),
            mb_releasetrackid=mbid(104),
        )
    item = Item(
        path=str(_copy(tmp_path, f"{name}.flac")).encode(),
        artist="Example Artist",
        title=name,
        mtime=10.0,
        **values,
    )
    library.add(item)
    return item


def _invoke(plugin: NoqlenMetaPlugin, library: Library, args: list[str]) -> None:
    command = plugin.commands()[0]
    opts, query = command.parse_args(args)
    command.func(library, opts, query)


def _output(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    output: list[str] = []
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)
    return output


def test_option_parsing_and_all_invalid_combinations(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    plugin = NoqlenMetaPlugin()
    command = plugin.commands()[0]
    opts, query = command.parse_args(["--identity-tags", "--write", "title:Track"])
    assert opts.identity_tags is True
    assert opts.write is True
    assert query == ["title:Track"]
    monkeypatch.setattr(
        plugin_module,
        "select_library_identity_targets",
        lambda *args: pytest.fail("invalid CLI queried the library"),
    )
    cases = [
        ["--identity", "--identity-tags", "--all"],
        ["--write", "--all"],
        ["--identity-tags", "--apply", "--all"],
        ["--identity-tags", "--partial", "--all"],
        ["--identity-tags"],
        ["--identity-tags", "--all", "title:Track"],
    ]
    for args in cases:
        with pytest.raises(ui.UserError):
            _invoke(plugin, library, args)


def test_item_query_expands_complete_album_singletons_and_all(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    _album(library, tmp_path)
    singleton = _singleton(library, tmp_path)
    plugin = NoqlenMetaPlugin()
    output = _output(monkeypatch)

    _invoke(plugin, library, ["--identity-tags", "title:Track 2"])
    assert len(output) == 2
    assert all("target: album" in entry for entry in output)
    output.clear()
    _invoke(plugin, library, ["--identity-tags", f"id:{singleton.id}"])
    assert len(output) == 1 and "target: singleton" in output[0]
    output.clear()
    _invoke(plugin, library, ["--identity-tags", "--all"])
    assert len(output) == 3


def test_empty_selection_and_preview_create_no_artifacts_or_database_write(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    album = _album(library, tmp_path)
    before = tuple(item.mtime for item in album.items())
    plugin = NoqlenMetaPlugin()
    output = _output(monkeypatch)
    monkeypatch.setattr(
        plugin_module,
        "apply_identity_tag_file_plan",
        lambda *args: pytest.fail("preview attempted application"),
    )

    _invoke(plugin, library, ["--identity-tags", "title:missing"])
    assert output == ["Noqlen MusicBrainz identity tags: no Items matched"]
    output.clear()
    _invoke(plugin, library, ["--identity-tags", "--all"])

    assert all("application: disabled" in entry for entry in output)
    assert tuple(item.get_fresh_from_db().mtime for item in album.items()) == before
    assert list(tmp_path.glob(".noqlen-identity-*")) == []


def test_identity_tag_mode_never_calls_sources_audits_or_providers(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    _singleton(library, tmp_path)
    plugin = NoqlenMetaPlugin()
    _output(monkeypatch)
    for name in (
        "_identity_source",
        "_discogs_candidates",
        "_musicbrainz_candidates",
        "_itunes_candidates",
        "_lastfm_candidates",
        "_lrclib_candidates",
    ):
        monkeypatch.setattr(
            NoqlenMetaPlugin,
            name,
            lambda *args, name=name: pytest.fail(f"called {name}"),
        )
    for name in ("resolve_metadata", "audit_musicbrainz_identity", "audit_with_musicbrainz_source"):
        monkeypatch.setattr(
            plugin_module,
            name,
            lambda *args, name=name: pytest.fail(f"called {name}"),
            raising=False,
        )

    _invoke(plugin, library, ["--identity-tags", "--all"])


def test_all_planning_and_preflight_precede_first_candidate(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    _album(library, tmp_path)
    plugin = NoqlenMetaPlugin()
    _output(monkeypatch)
    sequence: list[str] = []
    original_plan = plugin_module.plan_identity_tag_targets
    original_verify = plugin_module.verify_identity_tag_file_plan
    original_apply = plugin_module.apply_identity_tag_file_plan

    def plan_all(targets: object):
        result = original_plan(targets)  # type: ignore[arg-type]
        sequence.extend(
            f"plan:{plan.database.selected.item_id}"
            for target in result
            for plan in target.files
        )
        return result

    def verify(*args: object) -> None:
        sequence.append(f"verify:{args[2].database.selected.item_id}")  # type: ignore[attr-defined]
        original_verify(*args)  # type: ignore[arg-type]

    def apply(*args: object):
        assert sequence[:4] == ["plan:1", "plan:2", "verify:1", "verify:2"]
        sequence.append("apply")
        return original_apply(*args)  # type: ignore[arg-type]

    monkeypatch.setattr(plugin_module, "plan_identity_tag_targets", plan_all)
    monkeypatch.setattr(plugin_module, "verify_identity_tag_file_plan", verify)
    monkeypatch.setattr(plugin_module, "apply_identity_tag_file_plan", apply)

    _invoke(plugin, library, ["--identity-tags", "--write", "--all"])


def test_command_wide_stale_preflight_aborts_before_first_candidate(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    _album(library, tmp_path)
    plugin = NoqlenMetaPlugin()
    _output(monkeypatch)
    calls = 0
    original_verify = plugin_module.verify_identity_tag_file_plan

    def fail_second(*args: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise IdentityTagApplicationError("identity tag source changed")
        original_verify(*args)  # type: ignore[arg-type]

    monkeypatch.setattr(plugin_module, "verify_identity_tag_file_plan", fail_second)
    monkeypatch.setattr(
        plugin_module,
        "apply_identity_tag_file_plan",
        lambda *args: pytest.fail("application began before preflight completed"),
    )

    with pytest.raises(IdentityTagApplicationError):
        _invoke(plugin, library, ["--identity-tags", "--write", "--all"])

    assert list(tmp_path.glob(".noqlen-identity-*")) == []


def test_stale_noop_aborts_before_another_file_candidate(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    album = _album(library, tmp_path)
    first, second = tuple(album.items())
    first_media = MediaFile(Path(first.path.decode()))
    for field in IDENTITY_TAG_FIELDS:
        setattr(first_media, field, first.get(field, with_album=False))
    first_media.save()
    plugin = NoqlenMetaPlugin()
    _output(monkeypatch)
    original_plan = plugin_module.plan_identity_tag_targets

    def plan_then_stale(targets: object):
        result = original_plan(targets)  # type: ignore[arg-type]
        Path(first.path.decode()).touch()
        return result

    monkeypatch.setattr(plugin_module, "plan_identity_tag_targets", plan_then_stale)
    monkeypatch.setattr(
        plugin_module,
        "apply_identity_tag_file_plan",
        lambda *args: pytest.fail("candidate created after stale no-op"),
    )

    with pytest.raises(IdentityTagApplicationError, match="changed"):
        _invoke(plugin, library, ["--identity-tags", "--write", f"id:{second.id}"])


def test_mixed_preview_and_write_integration(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    album_a = _album(library, tmp_path, "Album A", 1)
    album_b = _album(library, tmp_path, "Album B", 1)
    singleton = _singleton(library, tmp_path, coherent=False)
    item_a = next(iter(album_a.items()))
    media_a = MediaFile(Path(item_a.path.decode()))
    for field in IDENTITY_TAG_FIELDS:
        setattr(media_a, field, item_a.get(field, with_album=False))
    media_a.save()
    before_mtimes = {
        item.id: item.get_fresh_from_db().mtime
        for item in (*tuple(album_a.items()), *tuple(album_b.items()), singleton)
    }
    plugin = NoqlenMetaPlugin()
    output = _output(monkeypatch)

    _invoke(plugin, library, ["--identity-tags", "--all"])
    assert len(output) == 3
    assert "file status: synchronized" in output[0]
    assert "file status: changes planned" in output[1]
    assert "database identity: blocked" in output[2]
    assert all(
        library.get_item(item_id).mtime == mtime  # type: ignore[union-attr]
        for item_id, mtime in before_mtimes.items()
    )

    output.clear()
    _invoke(plugin, library, ["--identity-tags", "--write", "--all"])

    item_b = next(iter(album_b.items())).get_fresh_from_db()
    assert MediaFile(Path(item_b.path.decode())).mb_albumid == mbid(1)
    assert item_b.mtime != before_mtimes[item_b.id]
    assert next(iter(album_a.items())).get_fresh_from_db().mtime == before_mtimes[item_a.id]
    assert singleton.get_fresh_from_db().mtime == before_mtimes[singleton.id]
    assert "application: synchronized/no changes" in output[0]
    assert "application: replaced and verified" in output[1]
    assert "application: blocked" in output[2]


def test_apply_and_importer_identity_config_cannot_authorize_file_writes(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    _singleton(library, tmp_path)
    plugin = NoqlenMetaPlugin()
    plugin.config["apply"].set(True)
    plugin.config["identity"]["apply"].set(True)
    _output(monkeypatch)
    monkeypatch.setattr(
        plugin_module,
        "apply_identity_tag_file_plan",
        lambda *args: pytest.fail("configuration authorized a tag write"),
    )

    _invoke(plugin, library, ["--identity-tags", "--all"])


def test_output_hides_paths_local_keys_and_raw_errors(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    item = _singleton(library, tmp_path)
    private_path = item.path.decode()
    MediaFile(Path(private_path)).mb_albumid = "private-malformed-value"
    media = MediaFile(Path(private_path))
    media.mb_albumid = "private-malformed-value"
    media.save()
    plugin = NoqlenMetaPlugin()
    output = _output(monkeypatch)

    _invoke(plugin, library, ["--identity-tags", f"id:{item.id}"])

    rendered = "\n".join(output)
    assert "status: malformed" in rendered
    assert private_path not in rendered
    assert Path(private_path).name not in rendered
    assert "identity-tag-item:" not in rendered
    assert "private-malformed-value" not in rendered
