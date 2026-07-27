import copy
import logging

import pytest
from beets import config
from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.distance import Distance
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.importer.actions import Action
from beets.importer.tasks import ImportTask, SingletonImportTask
from beets.library import Item

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.domain import MetadataCandidate, TrackEnrichmentContext
from beetsplug.noqlenmeta.providers import ProviderError
from beetsplug.noqlenmeta.providers.base import ProviderContractError

PRIVATE_LYRIC = "PRIVATE-SYNTHETIC-LYRIC-CONTENT-DO-NOT-DISPLAY"


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    sources = list(config.sources)
    yield
    config.sources[:] = sources


def _track(title: str, index: int, **overrides: object) -> TrackInfo:
    values: dict[str, object] = {
        "artist": "Synthetic Artist",
        "title": title,
        "album": "Synthetic Album",
        "length": 180.0 + index,
        "index": index,
        "medium": 1,
        "medium_index": index,
    }
    values.update(overrides)
    return TrackInfo(**values)  # type: ignore[arg-type]


def _album_task(
    pairs: list[tuple[Item, TrackInfo]],
    *,
    extra_items: list[Item] | None = None,
    extra_tracks: list[TrackInfo] | None = None,
    action: Action = Action.APPLY,
) -> tuple[ImportTask, AlbumInfo]:
    extras = extra_tracks or []
    info = AlbumInfo(
        [track for _, track in pairs] + extras,
        artist="Synthetic Artist",
        album="Synthetic Album",
    )
    match = AlbumMatch(
        Distance(),
        info,
        dict(pairs),
        extra_items or [],
        extras,
    )
    task = ImportTask(None, [], [item for item, _ in pairs] + (extra_items or []))
    task.choice_flag = action
    task.match = match
    return task, info


def _singleton_task(item: Item, track: TrackInfo) -> SingletonImportTask:
    task = SingletonImportTask(None, item)
    task.choice_flag = Action.APPLY
    task.match = TrackMatch(Distance(), track, item)
    return task


def _configure(
    plugin: NoqlenMetaPlugin,
    *,
    preview: bool = True,
    apply: bool = False,
    lyrics: bool = True,
    synced_lyrics: bool = False,
    lrclib: bool = True,
    discogs: bool = False,
) -> None:
    plugin.config.set(
        {
            "preview": preview,
            "apply": apply,
            "fields": {"lyrics": lyrics, "synced_lyrics": synced_lyrics},
            "providers": {
                "discogs": {"enabled": discogs, "user_token": ""},
                "musicbrainz": {"enabled": False},
                "lastfm": {"enabled": False},
                "itunes": {"enabled": False, "storefront": "us"},
                "lrclib": {"enabled": lrclib},
            },
        }
    )


def _candidate(field: str = "lyrics", value: str = PRIVATE_LYRIC) -> MetadataCandidate:
    return MetadataCandidate(field, value, "lrclib", 0.95, "42")


def _silence_preview(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    output: list[str] = []
    monkeypatch.setattr("beetsplug.noqlenmeta.track_preview.ui.print_", output.append)
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    return output


def test_album_plans_selected_mapping_in_order_and_excludes_extras(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _silence_preview(monkeypatch)
    first = (Item(title="Local One"), _track("Selected One", 1))
    second = (Item(title="Local Two"), _track("Selected Two", 2))
    extra_item = Item(title="Extra Item")
    extra_track = _track("Extra Track", 3)
    task, _ = _album_task(
        [first, second], extra_items=[extra_item], extra_tracks=[extra_track]
    )
    contexts: list[TrackEnrichmentContext] = []

    def candidates(
        self: NoqlenMetaPlugin, context: TrackEnrichmentContext
    ) -> tuple[MetadataCandidate, ...]:
        contexts.append(context)
        return (_candidate(),)

    monkeypatch.setattr(NoqlenMetaPlugin, "_lrclib_candidates", candidates)
    plugin = NoqlenMetaPlugin()
    _configure(plugin)

    plugin._import_task_choice(None, task)

    assert [context.title for context in contexts] == ["Selected One", "Selected Two"]
    assert len([text for text in output if "Noqlen Meta / track plan:" in text]) == 2


def test_singleton_track_match_produces_one_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    output = _silence_preview(monkeypatch)
    calls: list[TrackEnrichmentContext] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: calls.append(context) or (_candidate(),),
    )
    plugin = NoqlenMetaPlugin()
    _configure(plugin)

    plugin._import_task_choice(None, _singleton_task(Item(), _track("Singleton", 1)))

    assert len(calls) == 1
    assert len(output) == 1
    assert "track: 1.1 Synthetic Artist - Singleton" in output[0]


@pytest.mark.parametrize(
    ("action", "preview", "lrclib", "lyrics"),
    [
        (Action.SKIP, True, True, True),
        (Action.APPLY, False, True, True),
        (Action.APPLY, True, False, True),
        (Action.APPLY, True, True, False),
    ],
)
def test_track_provider_gates_prevent_calls(
    monkeypatch: pytest.MonkeyPatch,
    action: Action,
    preview: bool,
    lrclib: bool,
    lyrics: bool,
) -> None:
    _silence_preview(monkeypatch)
    calls: list[TrackEnrichmentContext] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: calls.append(context) or (),
    )
    task, _ = _album_task([(Item(), _track("Selected", 1))], action=action)
    plugin = NoqlenMetaPlugin()
    _configure(plugin, preview=preview, lrclib=lrclib, lyrics=lyrics)

    plugin._import_task_choice(None, task)

    assert calls == []


def test_incomplete_context_skips_provider_and_renders_safe_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _silence_preview(monkeypatch)
    calls: list[object] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: calls.append(context) or (),
    )
    task, _ = _album_task([(Item(path=b"private/path"), _track(" ", 1))])
    plugin = NoqlenMetaPlugin()
    _configure(plugin)

    plugin._import_task_choice(None, task)

    assert calls == []
    assert output == [
        "Noqlen Meta / track plan:\n\n  track skipped: incomplete selected identity"
    ]
    assert "private/path" not in output[0]


def test_provider_error_is_sanitized_and_later_tracks_continue(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output = _silence_preview(monkeypatch)

    def candidates(
        self: NoqlenMetaPlugin, context: TrackEnrichmentContext
    ) -> tuple[MetadataCandidate, ...]:
        if context.track_number == 1:
            raise ProviderError(f"unsafe {PRIVATE_LYRIC}")
        return (_candidate(),)

    monkeypatch.setattr(NoqlenMetaPlugin, "_lrclib_candidates", candidates)
    task, _ = _album_task(
        [(Item(), _track("First", 1)), (Item(), _track("Second", 2))]
    )
    plugin = NoqlenMetaPlugin()
    _configure(plugin)

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, task)

    rendered = "\n".join(output)
    assert "LRCLIB enrichment unavailable; processing will continue" in caplog.text
    assert "provider candidates: 0" in rendered
    assert "provider candidates: 1" in rendered
    assert "lyrics" in rendered
    assert "PROPOSE" in rendered
    assert "source: LRCLIB" in rendered
    assert PRIVATE_LYRIC not in rendered
    assert PRIVATE_LYRIC not in caplog.text


def test_provider_contract_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    _silence_preview(monkeypatch)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: (
            MetadataCandidate("lyrics", "synthetic", "discogs", 0.95, "42"),
        ),
    )
    task, _ = _album_task([(Item(), _track("Selected", 1))])
    plugin = NoqlenMetaPlugin()
    _configure(plugin)

    with pytest.raises(ProviderContractError):
        plugin._import_task_choice(None, task)


def test_track_planning_is_read_only_even_when_apply_is_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _silence_preview(monkeypatch)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: (_candidate(),),
    )
    item = Item(lyrics="local plain", synced_lyrics="local synced")
    track = _track("Selected", 1)
    task, album = _album_task([(item, track)])
    snapshots = (copy.deepcopy(dict(item)), copy.deepcopy(dict(track)), copy.deepcopy(dict(album)))
    plugin = NoqlenMetaPlugin()
    _configure(plugin, apply=True)

    plugin._import_task_choice(None, task)

    assert (dict(item), dict(track), dict(album)) == snapshots


@pytest.mark.parametrize("apply", [False, True])
def test_release_and_track_plans_coexist_without_track_mutation(
    monkeypatch: pytest.MonkeyPatch,
    apply: bool,
) -> None:
    output = _silence_preview(monkeypatch)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            MetadataCandidate("genres", ("Metal",), "discogs", 0.95, "7"),
        ),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: (_candidate(),),
    )
    item = Item()
    track = _track("Selected", 1)
    task, album = _album_task([(item, track)])
    item_snapshot = copy.deepcopy(dict(item))
    track_snapshot = copy.deepcopy(dict(track))
    plugin = NoqlenMetaPlugin()
    _configure(plugin, apply=apply, discogs=True)

    plugin._import_task_choice(None, task)

    rendered = "\n".join(output)
    assert "Noqlen Meta / beets target plan:" in rendered
    assert "Noqlen Meta / track plan:" in rendered
    assert dict(item) == item_snapshot
    assert dict(track) == track_snapshot
    assert album.genres == (["Metal"] if apply else None)


def test_preview_false_keeps_release_application_but_never_calls_lrclib(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            MetadataCandidate("genres", ("Metal",), "discogs", 0.95, "7"),
        ),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: calls.append(context) or (),
    )
    task, album = _album_task([(Item(), _track("Selected", 1))])
    plugin = NoqlenMetaPlugin()
    _configure(plugin, preview=False, apply=True, discogs=True)

    plugin._import_task_choice(None, task)

    assert calls == []
    assert album.genres == ["Metal"]


def test_one_lrclib_provider_instance_is_retained_for_multiple_tracks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _silence_preview(monkeypatch)
    instances: list[object] = []
    contexts: list[TrackEnrichmentContext] = []
    from_scratch_calls: list[object] = []

    class FakeProvider:
        def __init__(self) -> None:
            instances.append(self)

        def get_candidates(
            self, context: TrackEnrichmentContext
        ) -> tuple[MetadataCandidate, ...]:
            contexts.append(context)
            return ()

    monkeypatch.setattr("beetsplug.noqlenmeta.providers.lrclib.LRCLIBProvider", FakeProvider)
    monkeypatch.setattr(
        AlbumMatch,
        "from_scratch",
        lambda self, override: from_scratch_calls.append(override) or False,
    )
    task, _ = _album_task(
        [(Item(), _track("First", 1)), (Item(), _track("Second", 2))]
    )
    plugin = NoqlenMetaPlugin()
    _configure(plugin)

    plugin._import_task_choice(None, task)

    assert len(instances) == 1
    assert len(contexts) == 2
    assert from_scratch_calls == [None]
    assert plugin._lrclib_provider is instances[0]
