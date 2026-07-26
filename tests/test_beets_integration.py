import builtins
import copy
import logging
from types import SimpleNamespace

import pytest
from beets import config
from beets.autotag.hooks import AlbumInfo
from beets.importer.actions import Action
from beets.importer.tasks import ImportTask

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.domain import MetadataCandidate, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.integration import (
    context_from_album_info,
    resolve_discogs_token,
)
from beetsplug.noqlenmeta.providers import ProviderError

TOKEN = "test-personal-token"


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    sources = list(config.sources)
    yield
    config.sources[:] = sources


def album_info(**overrides: object) -> AlbumInfo:
    values: dict[str, object] = {
        "artist": "Selected Artist",
        "album": "Selected Album",
    }
    values.update(overrides)
    return AlbumInfo([], **values)


def import_task(info: AlbumInfo, choice: Action = Action.APPLY) -> ImportTask:
    task = ImportTask(None, [], [])
    task.choice_flag = choice
    task.match = SimpleNamespace(info=info) if choice is Action.APPLY else None
    return task


def candidate(field: str = "genres") -> MetadataCandidate:
    return MetadataCandidate(
        field=field,
        value=("Electronic", "Rock"),
        provider="discogs",
        confidence=0.98,
        source_id="123456",
    )


def configure_enabled(plugin: NoqlenMetaPlugin, *, preview: bool = True) -> None:
    plugin.config.set(
        {
            "discogs": {"enabled": True, "user_token": TOKEN},
            "preview": preview,
        }
    )


def test_configuration_defaults_and_redacts_user_token() -> None:
    plugin = NoqlenMetaPlugin()

    assert plugin.config["discogs"]["enabled"].get(bool) is False
    assert plugin.config["preview"].get(bool) is True
    assert plugin.config["discogs"]["user_token"].redact is True
    assert plugin._import_task_choice in plugin._raw_listeners["import_task_choice"]


def test_environment_token_overrides_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOQLENMETA_DISCOGS_TOKEN", " environment-token ")

    assert resolve_discogs_token("configured-token") == "environment-token"


def test_empty_environment_token_does_not_erase_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOQLENMETA_DISCOGS_TOKEN", "   ")

    assert resolve_discogs_token(" configured-token ") == "configured-token"


def test_context_maps_selected_album_fields_and_discogs_identity() -> None:
    info = album_info(
        year=2024,
        barcode=" 012345678901 ",
        catalognum=" CAT-001 ",
        discogs_albumid="00123456",
    )

    context = context_from_album_info(info)

    assert context == ReleaseEnrichmentContext(
        album_artist="Selected Artist",
        album_title="Selected Album",
        year=2024,
        barcode="012345678901",
        catalog_number="CAT-001",
        external_ids=context.external_ids,
    )
    assert [(identifier.namespace, identifier.value) for identifier in context.external_ids] == [
        ("discogs.release", "123456")
    ]


def test_context_uses_discogs_source_album_id_without_duplicate() -> None:
    info = album_info(
        data_source="Discogs",
        album_id="123456",
        discogs_albumid="123456",
    )

    context = context_from_album_info(info)

    assert context is not None
    assert len(context.external_ids) == 1
    assert context.external_ids[0].value == "123456"


def test_context_does_not_invent_source_for_arbitrary_album_id() -> None:
    context = context_from_album_info(album_info(data_source="MusicBrainz", album_id="123456"))

    assert context is not None
    assert context.external_ids == ()


@pytest.mark.parametrize("missing", ["artist", "album"])
def test_missing_required_selected_identity_skips_context(missing: str) -> None:
    assert context_from_album_info(album_info(**{missing: " "})) is None


def test_selected_album_apply_invokes_provider_with_selected_context_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str | None, ReleaseEnrichmentContext]] = []

    def record_candidates(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        token: str | None,
    ) -> tuple[()]:
        calls.append((token, context))
        return ()

    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", record_candidates)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    info = album_info(discogs_albumid="123456")

    plugin._import_task_choice(None, import_task(info))

    assert calls == [
        (
            TOKEN,
            ReleaseEnrichmentContext(
                album_artist="Selected Artist",
                album_title="Selected Album",
                external_ids=context_from_album_info(info).external_ids,
            ),
        )
    ]


def test_disabled_integration_does_not_invoke_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: pytest.fail("provider must remain disabled"),
    )

    NoqlenMetaPlugin()._import_task_choice(None, import_task(album_info()))


@pytest.mark.parametrize(
    ("choice", "is_album"),
    [
        (Action.SKIP, True),
        (Action.ASIS, True),
        (Action.RETAG, True),
        (Action.TRACKS, True),
        (Action.ALBUMS, True),
        (Action.APPLY, False),
    ],
)
def test_non_apply_and_non_album_paths_do_not_invoke_provider(
    monkeypatch: pytest.MonkeyPatch,
    choice: Action,
    is_album: bool,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: pytest.fail("ineligible task invoked provider"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    task = import_task(album_info(), choice)
    task.is_album = is_album

    plugin._import_task_choice(None, task)


def test_provider_error_warns_safely_and_does_not_abort(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_candidates(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        token: str | None,
    ) -> tuple[()]:
        assert token == TOKEN
        raise ProviderError(f"unsafe service detail containing {TOKEN}")

    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", fail_candidates)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(album_info()))

    assert "Discogs enrichment unavailable" in caplog.text
    assert TOKEN not in caplog.text


def test_missing_optional_discogs_client_warns_and_does_not_abort(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    real_import = builtins.__import__

    def missing_discogs_client(name: str, *args: object, **kwargs: object) -> object:
        if name == "beetsplug.noqlenmeta.providers.discogs":
            raise ModuleNotFoundError(
                "No module named 'discogs_client'",
                name="discogs_client",
            )
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_discogs_client)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(album_info()))

    assert "Discogs enrichment unavailable" in caplog.text


def test_preview_is_visible_and_selected_info_remains_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []

    def preview_candidates(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        token: str | None,
    ) -> tuple[MetadataCandidate, ...]:
        assert token == TOKEN
        return (candidate(), candidate("styles"))

    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", preview_candidates)
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    info = album_info(discogs_albumid="123456")
    snapshot = copy.deepcopy(dict(info))

    task = import_task(info)
    choice_snapshot = task.choice_flag
    match_snapshot = task.match
    items_snapshot = list(task.items)

    plugin._import_task_choice(None, task)

    assert dict(info) == snapshot
    assert task.choice_flag is choice_snapshot
    assert task.match is match_snapshot
    assert task.items == items_snapshot
    assert output == [
        "Noqlen Meta / Discogs:\n"
        "  release: 123456\n"
        "  genres: Electronic, Rock\n"
        "  styles: Electronic, Rock"
    ]
    assert TOKEN not in output[0]


def test_preview_disabled_suppresses_candidate_output(monkeypatch: pytest.MonkeyPatch) -> None:
    output: list[str] = []

    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate(),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, preview=False)

    plugin._import_task_choice(None, import_task(album_info()))

    assert output == []


def test_preview_removes_provider_control_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    output: list[str] = []
    unsafe_candidate = MetadataCandidate(
        field="labels",
        value=("Safe\nForged", "\x1b[31mLabel"),
        provider="discogs",
        confidence=0.98,
        source_id="123456",
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (unsafe_candidate,),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    plugin._import_task_choice(None, import_task(album_info()))

    assert output == [
        "Noqlen Meta / Discogs:\n  release: 123456\n  labels: Safe Forged, [31mLabel"
    ]
