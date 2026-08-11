import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from beets import config
from beets.library import Item, Library
from mediafile import MediaFile

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.artwork import ArtworkCandidate, ArtworkLookupResult, ArtworkSize
from beetsplug.noqlenmeta.artwork_application import apply_artwork_plan
from beetsplug.noqlenmeta.tempo import LocalBpmSettings, TempoObservation

FIXTURE = Path(__file__).parent / "fixtures" / "identity_tags" / "silence.flac"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"x" * 20 + b"\xff\xd9"


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


def invoke(plugin: NoqlenMetaPlugin, library: Library, arguments: list[str]) -> None:
    command = plugin.commands()[0]
    opts, query = command.parse_args(arguments)
    command.func(library, opts, query)


def configure_bpm(
    plugin: NoqlenMetaPlugin, *, round_bpm: bool = False, local_enabled: bool = True
) -> None:
    for field in plugin.config["fields"].keys():
        plugin.config["fields"][field].set(field == "bpm")
    for provider in plugin.config["providers"].keys():
        plugin.config["providers"][provider]["enabled"].set(False)
    plugin.config["bpm"].set(
        {
            "round": round_bpm,
            "recalculate_existing": False,
            "octave_normalization": False,
            "octave_range": {"min": 70, "max": 180},
        }
    )
    plugin.config["local_analysis"].set(
        {
            "bpm": {
                "enabled": local_enabled,
                "analysis_mode": "full",
                "window_seconds": 90,
            },
            "mood": {"enabled": False},
        }
    )


class TempoAnalyzer:
    def __init__(self, bpm: float = 127.63) -> None:
        self.bpm = bpm
        self.calls: list[bytes] = []

    def analyze(self, path: bytes, settings: LocalBpmSettings) -> TempoObservation:
        self.calls.append(path)
        return TempoObservation(self.bpm, "synthetic")


class ConfigValue:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self, expected: type[bool]) -> bool:
        return self.value


class ArtworkResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int) -> object:
        return iter((JPEG,))


class ArtworkSession:
    def get(self, url: str, *, stream: bool, timeout: object) -> ArtworkResponse:
        return ArtworkResponse()


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
        invoke(plugin, library, arguments)

    assert calls == 2
    assert plans[0].candidate == plans[1].candidate
    assert plans[0].embed_item_ids == ()
    assert plans[1].embed_item_ids == (album.items().get().id,)


def test_bpm_preview_apply_and_write_use_prepared_policy(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(path=bytes(path), artist="Artist", title="Track")
    library.add(item)
    plugin = NoqlenMetaPlugin()
    configure_bpm(plugin)
    analyzer = TempoAnalyzer()
    plugin._tempo_analyzer = analyzer

    invoke(plugin, library, ["--all"])

    assert len(analyzer.calls) == 1
    assert library.get_item(item.id).bpm == 0.0
    assert MediaFile(path).bpm is None

    invoke(plugin, library, ["--apply", "--all"])

    assert len(analyzer.calls) == 2
    assert library.get_item(item.id).bpm == 127.63
    assert MediaFile(path).bpm is None


def test_round_bpm_is_identical_in_database_and_reopened_media(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(path=bytes(path), artist="Artist", title="Track")
    library.add(item)
    plugin = NoqlenMetaPlugin()
    configure_bpm(plugin, round_bpm=True)
    analyzer = TempoAnalyzer()
    plugin._tempo_analyzer = analyzer

    invoke(plugin, library, ["--apply", "--write", "--all"])

    assert len(analyzer.calls) == 1
    assert library.get_item(item.id).bpm == 128.0
    assert MediaFile(path).bpm == 128.0


def test_existing_database_bpm_syncs_without_analysis(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(path=bytes(path), artist="Artist", title="Track", bpm=128.0)
    library.add(item)
    plugin = NoqlenMetaPlugin()
    configure_bpm(plugin, local_enabled=False)
    analyzer = TempoAnalyzer()
    plugin._tempo_analyzer = analyzer

    invoke(plugin, library, ["--apply", "--write", "--all"])

    assert analyzer.calls == []
    assert library.get_item(item.id).bpm == 128.0
    assert MediaFile(path).bpm == 128.0


def test_one_bpm_failure_does_not_block_sibling(tmp_path: Path) -> None:
    paths = [tmp_path / "bad.flac", tmp_path / "good.flac"]
    for path in paths:
        shutil.copy2(FIXTURE, path)
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    items = [
        Item(path=bytes(path), artist="Artist", title=path.stem) for path in paths
    ]
    for item in items:
        library.add(item)
    plugin = NoqlenMetaPlugin()
    configure_bpm(plugin, round_bpm=True)

    class FailingAnalyzer(TempoAnalyzer):
        def analyze(self, path: bytes, settings: LocalBpmSettings) -> TempoObservation:
            self.calls.append(path)
            if path == bytes(paths[0]):
                raise RuntimeError("decoder failed")
            return TempoObservation(self.bpm, "synthetic")

    analyzer = FailingAnalyzer()
    plugin._tempo_analyzer = analyzer

    invoke(plugin, library, ["--apply", "--all"])

    assert len(analyzer.calls) == 2
    assert library.get_item(items[0].id).bpm == 0.0
    assert library.get_item(items[1].id).bpm == 128.0


@pytest.mark.parametrize("write_enabled", [False, True])
def test_import_artwork_reuses_prepared_candidate_at_final_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, write_enabled: bool
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_paths = [source / "one.flac", source / "two.flac"]
    for path in source_paths:
        shutil.copy2(FIXTURE, path)
    source_items = [
        Item(path=bytes(path), artist="Artist", title=path.stem) for path in source_paths
    ]
    plugin = NoqlenMetaPlugin()
    for field in plugin.config["fields"].keys():
        plugin.config["fields"][field].set(field == "cover")
    artwork = ArtworkCandidate(
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
    lookup_calls = 0

    def resolve(*args: object) -> ArtworkLookupResult:
        nonlocal lookup_calls
        lookup_calls += 1
        return ArtworkLookupResult("RESOLVED", artwork)

    monkeypatch.setattr(plugin, "_resolve_album_artwork", resolve)
    monkeypatch.setattr(
        plugin,
        "_apply_artwork_plan",
        lambda library, album, plan: apply_artwork_plan(
            library, album, plan, ArtworkSession()
        ),
    )
    info = SimpleNamespace(
        mb_albumid="release-id",
        mb_releasegroupid=None,
        artist="Artist",
        album="Album",
    )
    task = SimpleNamespace(items=source_items)
    session = SimpleNamespace(config={"write": ConfigValue(write_enabled)})

    prepared = plugin._prepare_import_artwork(session, task, info)

    assert prepared is not None
    assert prepared.lookup is not None
    assert prepared.lookup.candidate is artwork
    assert lookup_calls == 1
    plugin._pending_import_artwork.setdefault(prepared.key, []).append(prepared)

    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    final_items = []
    for index, source_path in enumerate(source_paths, 1):
        directory = tmp_path / f"CD{index}"
        directory.mkdir()
        final_path = directory / source_path.name
        shutil.copy2(source_path, final_path)
        final_items.append(
            Item(
                path=bytes(final_path),
                albumartist="Artist",
                album="Album",
                artist="Artist",
                title=source_path.stem,
                mb_albumid="release-id",
            )
        )
    album = library.add_album(final_items)

    plugin._album_imported(library, album)

    assert lookup_calls == 1
    sidecars = [tmp_path / "CD1" / "cover.jpg", tmp_path / "CD2" / "cover.jpg"]
    assert [path.read_bytes() for path in sidecars] == [JPEG, JPEG]
    assert library.get_album(album.id).artpath == bytes(sidecars[0])
    for item in album.items():
        images = MediaFile(Path(item.path.decode())).images
        assert bool(images) is write_enabled


def test_import_existing_cover_is_authoritative_without_caa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_path = source / "track.flac"
    shutil.copy2(FIXTURE, source_path)
    (source / "cover.jpg").write_bytes(JPEG)
    plugin = NoqlenMetaPlugin()
    monkeypatch.setattr(
        plugin,
        "_resolve_album_artwork",
        lambda *args: pytest.fail("CAA lookup replaced authoritative local artwork"),
    )
    prepared = plugin._prepare_import_artwork(
        SimpleNamespace(config={"write": ConfigValue(False)}),
        SimpleNamespace(items=[Item(path=bytes(source_path))]),
        SimpleNamespace(
            mb_albumid="release-id",
            mb_releasegroupid=None,
            artist="Artist",
            album="Album",
        ),
    )

    assert prepared is not None
    assert prepared.local_source == bytes(source / "cover.jpg")
