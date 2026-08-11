import builtins
import copy
import logging
from types import SimpleNamespace

import pytest
from beets import config, ui
from beets.autotag import AlbumMatch
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.importer.actions import Action
from beets.importer.tasks import ImportTask
from beets.library import Item

import beetsplug.noqlenmeta as plugin_module
from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.beets_application import BeetsApplicationError
from beetsplug.noqlenmeta.beets_mapping import BeetsMappingError
from beetsplug.noqlenmeta.changeplan import ChangePlanError
from beetsplug.noqlenmeta.domain import (
    ArtistEnrichmentContext,
    MetadataCandidate,
    ReleaseEnrichmentContext,
    SemanticEvidenceBundle,
)
from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.integration import (
    context_from_album_info,
    current_values_from_album_info,
    resolution_policy_from_settings,
    resolve_discogs_token,
)
from beetsplug.noqlenmeta.providers import ProviderError
from beetsplug.noqlenmeta.providers.base import ProviderContractError
from beetsplug.noqlenmeta.providers.specs import (
    BUILTIN_RELEASE_PROVIDER_SPECS,
    ProviderScope,
)
from beetsplug.noqlenmeta.resolver import default_resolution_policy

TOKEN = "test-personal-token"
RELEASE_MBID = "6ea45c08-3cfa-461a-aa4d-4cc404fcfa86"
DISCOGS_FIELDS = (
    "genres",
    "styles",
    "labels",
    "catalog_numbers",
    "barcodes",
    "country",
    "year",
    "media",
    "format_descriptions",
)
DISABLED_V2_FIELDS = ("artist_areas", "lyrics", "synced_lyrics")


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    # Materialize beets' lazy defaults before snapshotting its source list.
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


def album_info(**overrides: object) -> AlbumInfo:
    values: dict[str, object] = {
        "artist": "Selected Artist",
        "album": "Selected Album",
    }
    values.update(overrides)
    tracks = values.pop("tracks", [])
    return AlbumInfo(tracks, **values)  # type: ignore[arg-type]


def import_task(info: AlbumInfo, choice: Action = Action.APPLY) -> ImportTask:
    task = ImportTask(None, [], [])
    task.choice_flag = choice
    task.match = SimpleNamespace(info=info) if choice is Action.APPLY else None
    return task


def candidate(
    field: str = "genres",
    value: object = ("Electronic", "Rock"),
    confidence: float = 0.98,
    provider: str = "discogs",
) -> MetadataCandidate:
    return MetadataCandidate(
        field=field,
        value=value,  # type: ignore[arg-type]
        provider=provider,
        confidence=confidence,
        source_id={
            "discogs": "123456",
            "musicbrainz": RELEASE_MBID,
            "lastfm": "Selected Artist / Selected Album",
            "itunes": "1097861387",
        }[provider],
    )


def lastfm_genre_bundle(*genres: str) -> SemanticEvidenceBundle:
    return SemanticEvidenceBundle(
        genres=tuple(
            GenreEvidence(
                genre,
                "lastfm",
                ProviderScope.RELEASE,
                GenreEvidenceKind.COMMUNITY_TAG,
                0.85,
                "Selected Artist / Selected Album",
            )
            for genre in genres
        )
    )


def configure_enabled(
    plugin: NoqlenMetaPlugin,
    *,
    preview: bool = True,
    apply: bool = False,
    apply_mode: str | None = None,
    fields: dict[str, bool] | None = None,
    discogs: bool = True,
    musicbrainz: bool = False,
    lastfm: bool = False,
    itunes: bool = False,
    lrclib: bool = False,
    storefront: str = "us",
    resolution: dict[str, object] | None = None,
) -> None:
    settings: dict[str, object] = {
        "preview": preview,
        "apply": apply,
        "genres": {"num_genres": 2, "promote_styles": True},
        "fields": fields or {},
        "providers": {
            "discogs": {"enabled": discogs, "user_token": TOKEN},
            "musicbrainz": {"enabled": musicbrainz},
            "lastfm": {"enabled": lastfm},
            "itunes": {"enabled": itunes, "storefront": storefront},
            "lrclib": {"enabled": lrclib},
        },
    }
    if apply_mode is not None:
        settings["apply_mode"] = apply_mode
    if resolution is not None:
        settings["resolution"] = resolution
    plugin.config.set(settings)


def test_configuration_defaults_and_redacts_user_token() -> None:
    plugin = NoqlenMetaPlugin()

    assert plugin.config["preview"].get(bool) is True
    assert plugin.config["apply"].get(bool) is False
    assert plugin.config["apply_mode"].as_str() == "strict"
    assert all(plugin.config["fields"][field].get(bool) for field in DISCOGS_FIELDS)
    assert all(
        not plugin.config["fields"][field].get(bool) for field in DISABLED_V2_FIELDS
    )
    assert plugin.config["fields"]["moods"].get(bool) is True
    assert plugin.config["fields"]["bpm"].get(bool) is True
    assert plugin.config["fields"]["cover"].get(bool) is True
    assert plugin.config["providers"]["discogs"]["enabled"].get(bool) is False
    assert plugin.config["providers"]["discogs"]["user_token"].redact is True
    assert plugin.config["providers"]["musicbrainz"]["enabled"].get(bool) is True
    assert plugin.config["providers"]["lastfm"]["enabled"].get(bool) is False
    assert plugin.config["providers"]["itunes"]["enabled"].get(bool) is False
    assert plugin.config["providers"]["itunes"]["storefront"].as_str() == "us"
    assert plugin.config["providers"]["lrclib"]["enabled"].get(bool) is False
    assert plugin.config["resolution"]["authority"].get(dict) == {}
    assert plugin.config["resolution"]["min_confidence"].get(dict) == {}
    assert plugin.config["resolution"]["preserve_existing"].get(dict) == {}
    assert "discogs" not in plugin.config.keys()
    assert plugin._import_task_choice in plugin._raw_listeners["import_task_choice"]
    assert not hasattr(plugin_module, "_ITUNES_FIELDS")


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
    context = context_from_album_info(album_info(data_source="Discogs", album_id=RELEASE_MBID))

    assert context is not None
    assert context.external_ids == ()


def test_context_maps_musicbrainz_source_album_id_without_duplicate() -> None:
    info = album_info(
        data_source="musicbrainz",
        album_id=f" {RELEASE_MBID.upper()} ",
        mb_albumid=RELEASE_MBID,
    )

    context = context_from_album_info(info)

    assert context is not None
    assert [(item.namespace, item.value) for item in context.external_ids] == [
        ("musicbrainz.release", RELEASE_MBID)
    ]


def test_context_maps_explicit_musicbrainz_mbid_for_other_source() -> None:
    context = context_from_album_info(
        album_info(data_source="Discogs", mb_albumid=RELEASE_MBID)
    )

    assert context is not None
    assert [(item.namespace, item.value) for item in context.external_ids] == [
        ("musicbrainz.release", RELEASE_MBID)
    ]


@pytest.mark.parametrize("value", [None, "", "invalid", 123])
def test_context_omits_malformed_explicit_musicbrainz_mbid(value: object) -> None:
    context = context_from_album_info(album_info(mb_albumid=value))

    assert context is not None
    assert context.external_ids == ()


def test_current_values_map_album_info_to_canonical_shapes() -> None:
    info = album_info(
        genres=["Progressive Metal", "", "  Rock  "],
        style="Progressive Metal, Heavy Metal",
        label=" Roadrunner Records ",
        catalognum=" RR-001 ",
        barcode=" 012345678901 ",
        country=" NL ",
        year=2024,
        media=" CD ",
        artist_countries=["Brazil", " Japan "],
        artist_areas=["Salvador", " Tokyo "],
        artist_languages=["por", " jpn "],
    )

    assert current_values_from_album_info(info) == {
        "genres": ("Progressive Metal", "Rock"),
        "styles": ("Progressive Metal, Heavy Metal",),
        "labels": ("Roadrunner Records",),
        "catalog_numbers": ("RR-001",),
        "barcodes": ("012345678901",),
        "country": "NL",
        "year": 2024,
        "media": ("CD",),
        "artist_countries": ("Brazil", "Japan"),
        "artist_areas": ("Salvador", "Tokyo"),
        "artist_languages": ("por", "jpn"),
    }


def test_current_values_omit_empty_invalid_and_unmapped_values() -> None:
    info = album_info(
        genres=["", "  "],
        style=None,
        label=" ",
        catalognum=None,
        barcode="",
        country=None,
        year=0,
        media=" ",
    )

    assert current_values_from_album_info(info) == {}
    assert "format_descriptions" not in current_values_from_album_info(info)


def test_current_values_prefer_plural_styles_over_legacy_style() -> None:
    info = album_info(style="Legacy")
    info["styles"] = ["Modern A", "Modern B"]

    assert current_values_from_album_info(info)["styles"] == ("Modern A", "Modern B")


def test_current_values_fall_back_to_legacy_style() -> None:
    assert current_values_from_album_info(album_info(style="Legacy"))["styles"] == (
        "Legacy",
    )


def test_settings_only_override_known_policy_enablement() -> None:
    baseline = default_resolution_policy()
    policy = resolution_policy_from_settings(
        {"genres": False, "styles": True, "unknown": True},
        {"discogs": False, "unknown": True},
    )

    assert not policy.is_field_enabled("genres")
    assert policy.is_field_enabled("styles")
    assert not policy.is_field_enabled("unknown")
    assert not policy.is_provider_enabled("discogs")
    assert not policy.is_provider_enabled("unknown")
    assert policy.field_rules["genres"].authority == baseline.field_rules["genres"].authority
    assert (
        policy.field_rules["genres"].min_confidence
        == baseline.field_rules["genres"].min_confidence
    )
    assert (
        policy.field_rules["genres"].preserve_existing
        == baseline.field_rules["genres"].preserve_existing
    )


def test_settings_can_enable_provider_and_future_field_without_granting_authority() -> None:
    policy = resolution_policy_from_settings({"moods": True}, {"discogs": True})

    assert policy.is_provider_enabled("discogs")
    assert policy.is_field_enabled("moods")
    assert policy.authority_rank("moods", "discogs") is None


def test_policy_provider_map_includes_all_production_providers_disabled_by_default() -> None:
    policy = default_resolution_policy()

    assert dict(policy.providers) == {
        "discogs": False,
        "musicbrainz": False,
        "lastfm": False,
        "itunes": False,
        "lrclib": False,
    }


def test_release_orchestration_registry_contains_only_current_album_providers() -> None:
    assert tuple(BUILTIN_RELEASE_PROVIDER_SPECS) == (
        "discogs",
        "musicbrainz",
        "lastfm",
        "itunes",
    )


def test_actual_plugin_policy_accepts_enabled_lrclib_and_custom_authority() -> None:
    plugin = NoqlenMetaPlugin()
    plugin.config.set(
        {
            "providers": {
                "lrclib": {"enabled": True},
                "musicbrainz": {"enabled": False},
            },
            "fields": {"lyrics": True, "synced_lyrics": True},
            "resolution": {"authority": {"lyrics": ["lrclib"]}},
        }
    )

    policy = plugin._resolution_policy()

    assert policy.is_provider_enabled("lrclib")
    assert policy.is_field_enabled("lyrics")
    assert policy.is_field_enabled("synced_lyrics")
    assert policy.field_rules["lyrics"].authority == ("lrclib",)
    assert not plugin._has_contributing_release_provider(policy)


def test_release_importer_does_not_execute_lrclib_when_it_is_only_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.providers.lrclib.urlopen",
        lambda *args, **kwargs: pytest.fail("release importer must not call LRCLIB"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        fields={field: False for field in DISCOGS_FIELDS} | {"lyrics": True},
        discogs=False,
        lrclib=True,
    )

    plugin._import_task_choice(None, import_task(album_info()))


@pytest.mark.parametrize(
    (
        "provider_settings",
        "discogs_enabled",
        "musicbrainz_enabled",
        "lastfm_enabled",
        "itunes_enabled",
    ),
    [
        ({"discogs": True}, True, False, False, False),
        ({"musicbrainz": True}, False, True, False, False),
        ({"lastfm": True}, False, False, True, False),
        ({"itunes": True}, False, False, False, True),
        (
            {"discogs": True, "musicbrainz": True, "lastfm": True, "itunes": True},
            True,
            True,
            True,
            True,
        ),
    ],
)
def test_providers_can_be_enabled_independently(
    provider_settings: dict[str, bool],
    discogs_enabled: bool,
    musicbrainz_enabled: bool,
    lastfm_enabled: bool,
    itunes_enabled: bool,
) -> None:
    policy = resolution_policy_from_settings({}, provider_settings)

    assert policy.is_provider_enabled("discogs") is discogs_enabled
    assert policy.is_provider_enabled("musicbrainz") is musicbrainz_enabled
    assert policy.is_provider_enabled("lastfm") is lastfm_enabled
    assert policy.is_provider_enabled("itunes") is itunes_enabled


def test_plugin_config_extracts_all_resolution_sections_as_plain_values() -> None:
    plugin = NoqlenMetaPlugin()
    plugin.config.set(
        {
            "resolution": {
                "authority": {"year": [" Discogs ", "MusicBrainz"]},
                "min_confidence": {"year": 0.9},
                "preserve_existing": {"year": False},
            }
        }
    )

    policy = plugin._resolution_policy()

    assert policy.field_rules["year"].authority == ("discogs", "musicbrainz")
    assert policy.field_rules["year"].min_confidence == 0.9
    assert policy.field_rules["year"].preserve_existing is False


def test_unknown_resolution_section_is_a_user_configuration_error() -> None:
    plugin = NoqlenMetaPlugin()
    plugin.config.set({"resolution": {"confidence": {"year": 0.9}}})

    with pytest.raises(
        ui.UserError,
        match="invalid resolution configuration: unknown resolution section 'confidence'",
    ):
        plugin._resolution_policy()


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
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lastfm_candidates",
        lambda self, context: pytest.fail("provider must remain disabled"),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda self, context, storefront: pytest.fail("provider must remain disabled"),
    )

    NoqlenMetaPlugin()._import_task_choice(None, import_task(album_info()))


def test_enabled_provider_is_not_invoked_when_no_authoritative_field_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: pytest.fail("provider has no useful enabled field"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, fields={field: False for field in DISCOGS_FIELDS})
    plugin.config["fields"]["moods"].set(True)

    plugin._import_task_choice(None, import_task(album_info()))


def test_itunes_is_not_invoked_when_only_styles_can_be_enriched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda self, context, storefront: pytest.fail("iTunes has no styles authority"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        fields={field: field == "styles" for field in DISCOGS_FIELDS},
        discogs=False,
        itunes=True,
    )

    plugin._import_task_choice(None, import_task(album_info()))


@pytest.mark.parametrize("field", ["styles", "moods"])
def test_lastfm_is_not_invoked_for_future_classification_fields(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lastfm_candidates",
        lambda self, context: pytest.fail(f"Last.fm cannot emit {field}"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        fields={known: known == field for known in (*DISCOGS_FIELDS, "moods")},
        discogs=False,
        lastfm=True,
    )

    plugin._import_task_choice(None, import_task(album_info()))


def test_lastfm_genres_join_shared_importer_plan_without_preview_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    contexts: list[ReleaseEnrichmentContext] = []

    def lastfm_semantics(context: ReleaseEnrichmentContext) -> SemanticEvidenceBundle:
        contexts.append(context)
        return lastfm_genre_bundle("Progressive Metal", "Death Metal")

    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    monkeypatch.setattr(plugin, "_lastfm_release_semantics", lastfm_semantics)
    configure_enabled(plugin, discogs=False, lastfm=True)
    info = album_info()
    snapshot = copy.deepcopy(dict(info))

    plugin._import_task_choice(None, import_task(info))

    assert contexts == [ReleaseEnrichmentContext("Selected Artist", "Selected Album")]
    assert "genres\n    PROPOSE" in output[0]
    assert "source: Noqlen" in output[0]
    assert "Death Metal: lastfm community tag" in output[0]
    assert "proposed: Death Metal, Progressive Metal" in output[0]
    assert "application: disabled (preview only)" in output[0]
    assert dict(info) == snapshot


def test_lastfm_provider_instance_is_retained_across_album_plans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instances: list[object] = []

    class FakeLastFmProvider:
        def __init__(self) -> None:
            instances.append(self)

        def get_candidates(self, context: ReleaseEnrichmentContext) -> tuple[()]:
            return ()

    monkeypatch.setattr(
        "beetsplug.noqlenmeta.providers.lastfm.LastFmProvider", FakeLastFmProvider
    )
    plugin = NoqlenMetaPlugin()

    plugin._lastfm_candidates(ReleaseEnrichmentContext("Artist", "Album One"))
    plugin._lastfm_candidates(ReleaseEnrichmentContext("Artist", "Album Two"))

    assert len(instances) == 1


def test_custom_styles_authority_is_accepted_but_itunes_capability_still_gates_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda self, context, storefront: pytest.fail("iTunes cannot emit styles"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        fields={field: field == "styles" for field in DISCOGS_FIELDS},
        discogs=False,
        itunes=True,
        resolution={"authority": {"styles": ["itunes"]}},
    )

    assert plugin._resolution_policy().field_rules["styles"].authority == ("itunes",)
    plugin._import_task_choice(None, import_task(album_info()))


def test_custom_authority_excludes_enabled_provider_before_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", lambda output: None)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: calls.append("discogs") or (),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_musicbrainz_candidates",
        lambda self, context: pytest.fail("MusicBrainz has no configured year authority"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        fields={field: field == "year" for field in DISCOGS_FIELDS},
        discogs=True,
        musicbrainz=True,
        resolution={"authority": {"year": ["discogs"]}},
    )

    plugin._import_task_choice(None, import_task(album_info()))

    assert calls == ["discogs"]


@pytest.mark.parametrize("field", ["labels", "catalog_numbers", "country", "media"])
def test_itunes_is_not_invoked_for_authoritative_fields_it_does_not_emit(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda self, context, storefront: pytest.fail("iTunes cannot emit this field"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        fields={known: known == field for known in DISCOGS_FIELDS},
        discogs=False,
        itunes=True,
    )

    plugin._import_task_choice(None, import_task(album_info()))


def test_musicbrainz_is_not_invoked_when_only_styles_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_musicbrainz_candidates",
        lambda self, context: pytest.fail("MusicBrainz cannot emit styles"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        fields={field: field == "styles" for field in DISCOGS_FIELDS},
        discogs=False,
        musicbrainz=True,
    )

    plugin._import_task_choice(None, import_task(album_info()))


def test_selected_musicbrainz_release_joins_shared_importer_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    contexts: list[ReleaseEnrichmentContext] = []

    def musicbrainz_candidates(
        self: NoqlenMetaPlugin, context: ReleaseEnrichmentContext
    ) -> tuple[MetadataCandidate, ...]:
        contexts.append(context)
        return (candidate("year", 2005, provider="musicbrainz"),)

    monkeypatch.setattr(NoqlenMetaPlugin, "_musicbrainz_candidates", musicbrainz_candidates)
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=False, musicbrainz=True)

    plugin._import_task_choice(
        None,
        import_task(album_info(data_source="MusicBrainz", album_id=RELEASE_MBID)),
    )

    assert contexts[0].external_ids[0].value == RELEASE_MBID
    assert "source: MusicBrainz" in output[0]
    assert "year\n    PROPOSE" in output[0]


def test_enabled_musicbrainz_without_mbid_performs_no_release_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "beetsplug._utils.musicbrainz.MusicBrainzAPI.get_release",
        lambda *args, **kwargs: pytest.fail("release lookup without MBID"),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", lambda output: None)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=False, musicbrainz=True)

    plugin._import_task_choice(None, import_task(album_info()))


def test_discogs_is_not_loaded_or_invoked_for_cover_only_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def reject_discogs_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "beetsplug.noqlenmeta.providers.discogs":
            pytest.fail("Discogs dependency boundary must remain unloaded")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_discogs_import)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: pytest.fail("Discogs cannot emit cover"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        fields={field: False for field in DISCOGS_FIELDS},
        discogs=True,
    )
    plugin.config["fields"]["cover"].set(True)

    plugin._import_task_choice(None, import_task(album_info()))


def test_genres_bypass_generic_resolver_and_rejoin_one_change_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from beetsplug.noqlenmeta.beets_mapping import (
        map_change_plan_to_beets as real_map_change_plan_to_beets,
    )
    from beetsplug.noqlenmeta.changeplan import build_change_plan as real_build_change_plan
    from beetsplug.noqlenmeta.resolver import resolve_metadata as real_resolve_metadata

    provider_calls: list[tuple[str, str | None]] = []
    resolution_calls: list[tuple[MetadataCandidate, ...]] = []
    plan_calls: list[object] = []
    mapping_calls: list[object] = []
    rendered: list[object] = []

    def discogs_candidates(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        token: str | None,
    ) -> tuple[MetadataCandidate, ...]:
        provider_calls.append(("discogs", token))
        return (candidate(value=("Rock", "Electronic"), confidence=0.88),)

    def itunes_candidates(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        storefront: str,
    ) -> tuple[MetadataCandidate, ...]:
        provider_calls.append(("itunes", storefront))
        return (candidate(value=("Electronic",), confidence=0.99, provider="itunes"),)

    def record_resolution(
        current_values: object, candidates: object, policy: object
    ) -> object:
        resolution_calls.append(tuple(candidates))  # type: ignore[arg-type]
        return real_resolve_metadata(current_values, candidates, policy)  # type: ignore[arg-type]

    def record_plan(decisions: object) -> object:
        plan_calls.append(decisions)
        return real_build_change_plan(decisions)  # type: ignore[arg-type]

    def record_mapping(plan: object) -> object:
        mapping_calls.append(plan)
        return real_map_change_plan_to_beets(plan)  # type: ignore[arg-type]

    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", discogs_candidates)
    monkeypatch.setattr(NoqlenMetaPlugin, "_itunes_candidates", itunes_candidates)
    monkeypatch.setattr("beetsplug.noqlenmeta.resolve_metadata", record_resolution)
    monkeypatch.setattr("beetsplug.noqlenmeta.build_change_plan", record_plan)
    monkeypatch.setattr("beetsplug.noqlenmeta.map_change_plan_to_beets", record_mapping)
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.render_beets_target_plan",
        lambda plan, application_result, semantic_outcomes: rendered.append(plan),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=True, itunes=True, storefront="gb")
    info = album_info()
    info_snapshot = copy.deepcopy(dict(info))
    task = import_task(info)
    choice_snapshot = task.choice_flag
    match_snapshot = task.match
    items_snapshot = list(task.items)

    plugin._import_task_choice(None, task)

    assert provider_calls == [("discogs", TOKEN), ("itunes", "gb")]
    assert len(resolution_calls) == 1
    assert resolution_calls[0] == ()
    assert len(plan_calls) == 1
    decisions = plan_calls[0]
    decision = decisions[0]  # type: ignore[index]
    assert decision.selected.provider == "noqlen"
    assert decision.selected.value == ("Electronic", "Rock")
    assert decision.alternatives == ()
    assert len(mapping_calls) == 1
    assert mapping_calls[0].changes[0].source is decision.selected  # type: ignore[attr-defined]
    target_plan = rendered[0]
    assert target_plan.source is mapping_calls[0]  # type: ignore[attr-defined]
    assert target_plan.mapped_changes[0].source.source is decision.selected  # type: ignore[attr-defined]
    assert target_plan.mapped_changes[0].target_field == "genres"  # type: ignore[attr-defined]
    assert dict(info) == info_snapshot
    assert task.choice_flag is choice_snapshot
    assert task.match is match_snapshot
    assert task.items == items_snapshot


def test_itunes_wins_when_discogs_has_no_eligible_genres_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda self, context, storefront: (
            candidate(value=("K-pop",), confidence=0.99, provider="itunes"),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=True, itunes=True)

    plugin._import_task_choice(None, import_task(album_info()))

    assert "source: Noqlen" in output[0]
    assert "source: Itunes" not in output[0]
    assert "K-pop: itunes genre" in output[0]


def test_discogs_failure_does_not_suppress_itunes(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output: list[str] = []

    def fail_discogs(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        token: str | None,
    ) -> tuple[()]:
        raise ProviderError("unsafe Discogs detail")

    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", fail_discogs)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda self, context, storefront: (candidate(provider="itunes"),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=True, itunes=True)

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(album_info()))

    assert "Discogs enrichment unavailable" in caplog.text
    assert "source: Noqlen" in output[0]
    assert "itunes genre" in output[0]


def test_lastfm_failure_hides_key_detail_and_itunes_continues(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output: list[str] = []
    fake_key = "fake-shared-key-in-underlying-error"
    plugin = NoqlenMetaPlugin()
    plugin._lastfm_provider = SimpleNamespace(
        get_semantic_evidence=lambda *args: (_ for _ in ()).throw(
            ProviderError(f"unsafe {fake_key}")
        )
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda *args: (candidate(provider="itunes"),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    configure_enabled(plugin, discogs=False, lastfm=True, itunes=True)

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(album_info()))

    assert "Last.fm enrichment unavailable" in caplog.text
    assert "source: Noqlen" in output[0]
    assert "itunes genre" in output[0]
    assert fake_key not in caplog.text
    assert fake_key not in output[0]


def test_lastfm_missing_album_is_quiet_and_itunes_continues(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output: list[str] = []
    plugin = NoqlenMetaPlugin()
    monkeypatch.setattr(
        plugin,
        "_lastfm_release_semantics",
        lambda *args: SemanticEvidenceBundle(),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda *args: (candidate(provider="itunes"),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    configure_enabled(plugin, discogs=False, lastfm=True, itunes=True)

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(album_info()))

    assert "Last.fm enrichment unavailable" not in caplog.text
    assert "source: Noqlen" in output[0]
    assert "itunes genre" in output[0]


def test_itunes_failure_does_not_suppress_discogs(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output: list[str] = []

    def fail_itunes(
        self: NoqlenMetaPlugin,
        context: ReleaseEnrichmentContext,
        storefront: str,
    ) -> tuple[()]:
        raise ProviderError("unsafe iTunes detail")

    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate(),),
    )
    monkeypatch.setattr(NoqlenMetaPlugin, "_itunes_candidates", fail_itunes)
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=True, itunes=True)

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(album_info()))

    assert "iTunes enrichment unavailable" in caplog.text
    assert "source: Noqlen" in output[0]
    assert "discogs genre" in output[0]


def test_musicbrainz_failure_warns_and_discogs_continues(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: (candidate("year", 2005),),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_musicbrainz_candidates",
        lambda *args: (_ for _ in ()).throw(ProviderError("raw failure")),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=True, musicbrainz=True)

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(album_info(mb_albumid=RELEASE_MBID)))

    assert "MusicBrainz enrichment unavailable" in caplog.text
    assert "source: Discogs" in output[0]


def test_musicbrainz_contract_error_is_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_musicbrainz_candidates",
        lambda *args: (candidate("styles", ("Invalid",), provider="musicbrainz"),),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=False, musicbrainz=True)

    with pytest.raises(ProviderContractError, match="unsupported field 'styles'"):
        plugin._import_task_choice(None, import_task(album_info(mb_albumid=RELEASE_MBID)))


def test_provider_contract_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda self, context, storefront: (candidate(field="labels", provider="itunes"),),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, discogs=False, itunes=True)

    with pytest.raises(ProviderContractError, match="unsupported field 'labels'"):
        plugin._import_task_choice(None, import_task(album_info()))


def test_change_plan_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate(),),
    )
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.build_change_plan",
        lambda decisions: (_ for _ in ()).throw(ChangePlanError("broken decision contract")),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    with pytest.raises(ChangePlanError, match="broken decision contract"):
        plugin._import_task_choice(None, import_task(album_info()))


def test_beets_mapping_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate(),),
    )
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.map_change_plan_to_beets",
        lambda plan: (_ for _ in ()).throw(BeetsMappingError("broken mapping contract")),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    with pytest.raises(BeetsMappingError, match="broken mapping contract"):
        plugin._import_task_choice(None, import_task(album_info()))


def test_beets_application_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate(),),
    )
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.apply_beets_target_plan",
        lambda info, plan, mode: (_ for _ in ()).throw(
            BeetsApplicationError("unsafe plan")
        ),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True)

    with pytest.raises(BeetsApplicationError, match="unsafe plan"):
        plugin._import_task_choice(None, import_task(album_info()))


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
        return (candidate(), candidate("labels", ("Listenable Records",)))

    monkeypatch.setattr(NoqlenMetaPlugin, "_discogs_candidates", preview_candidates)
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    info = album_info(discogs_albumid="123456", label="Roadrunner Records")
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
    assert len(output) == 1
    assert "Noqlen Meta / beets target plan:" in output[0]
    assert "application: disabled (preview only)" in output[0]
    assert "planned changes: 1" in output[0]
    assert "losslessly mapped: 1" in output[0]
    assert "mapping blockers: 0" in output[0]
    assert "resolution review: 1" in output[0]
    assert "unchanged: 0" in output[0]
    assert "skipped: 0" in output[0]
    assert "mapping complete: yes" in output[0]
    assert "genres\n    PROPOSE" in output[0]
    assert "target: genres" in output[0]
    assert "target shape: string-list" in output[0]
    assert "proposed: Electronic, Rock" in output[0]
    assert "source: Noqlen" in output[0]
    assert "discogs genre" in output[0]
    assert "confidence: 0.98" in output[0]
    assert "labels\n    REVIEW" in output[0]
    assert "current: Roadrunner Records" in output[0]
    assert "candidate: Listenable Records" in output[0]
    assert "existing conflicting value is preserved" in output[0]
    assert TOKEN not in output[0]


def test_importer_preview_retains_semantic_no_evidence_and_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from beetsplug.noqlenmeta.providers.musicbrainz_semantic import (
        MusicBrainzArtistProvider,
        MusicBrainzTrackProvider,
    )

    artist_ids = (
        "22222222-2222-4222-8222-222222222222",
        "33333333-3333-4333-8333-333333333333",
    )
    output: list[str] = []

    monkeypatch.setattr(
        MusicBrainzTrackProvider,
        "get_semantic_evidence",
        lambda *args: SemanticEvidenceBundle(),
    )

    def artist_evidence(
        provider: MusicBrainzArtistProvider, context: ArtistEnrichmentContext
    ) -> SemanticEvidenceBundle:
        if context.external_ids[0].value == artist_ids[1]:
            raise ProviderError("network")
        return SemanticEvidenceBundle(
            metadata=(
                MetadataCandidate(
                    "artist_countries",
                    ("Brazil",),
                    "musicbrainz",
                    0.99,
                    artist_ids[0],
                ),
            )
        )

    monkeypatch.setattr(MusicBrainzArtistProvider, "get_semantic_evidence", artist_evidence)
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        fields={
            field: field in {"artist_countries", "artist_areas", "artist_languages"}
            for field in plugin.config["fields"]
        },
        discogs=False,
        musicbrainz=True,
    )
    track = TrackInfo(
        title="Selected Track",
        artist="Artist A feat. Artist B",
        artists=["Artist A", "Artist B"],
        artists_ids=list(artist_ids),
    )
    info = album_info(tracks=[track], artist_countries=["Existing"])
    item = Item(title="Local Track")
    task = ImportTask(None, [], [item])
    task.choice_flag = Action.APPLY
    task.match = AlbumMatch(None, info, {item: track})  # type: ignore[arg-type]

    plugin._import_task_choice(None, task)

    release_preview = output[0]
    assert "artist_languages: no-evidence" in release_preview
    assert "artist_areas: unavailable" in release_preview
    assert "artist_countries: unavailable" in release_preview
    assert "partial semantic evidence retained" in release_preview
    assert "raw_tag" not in release_preview


def test_importer_uses_preserve_override_but_preview_does_not_mutate_selected_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate("year", 2005),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        apply=False,
        resolution={"preserve_existing": {"year": False}},
    )
    info = album_info(year=2006)

    plugin._import_task_choice(None, import_task(info))

    assert info.year == 2006
    assert "year\n    PROPOSE" in output[0]
    assert "policy allows replacing the existing value" in output[0]


def test_invalid_importer_resolution_fails_before_provider_and_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda *args: pytest.fail("invalid resolution invoked provider"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        resolution={"min_confidence": {"yeer": 0.9}},
    )
    info = album_info(year=2006)
    snapshot = copy.deepcopy(dict(info))

    with pytest.raises(
        ui.UserError,
        match="invalid resolution configuration.*unknown field 'yeer'",
    ):
        plugin._import_task_choice(None, import_task(info))

    assert dict(info) == snapshot


def test_multi_label_proposal_is_previewed_as_mapping_blocker_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("labels", ("Roadrunner Records", "Listenable Records")),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)
    info = album_info()
    info_snapshot = copy.deepcopy(dict(info))
    task = import_task(info)
    choice_snapshot = task.choice_flag
    match_snapshot = task.match
    items_snapshot = list(task.items)

    plugin._import_task_choice(None, task)

    assert "planned changes: 1" in output[0]
    assert "losslessly mapped: 0" in output[0]
    assert "mapping blockers: 1" in output[0]
    assert "mapping complete: no" in output[0]
    assert "labels\n    BLOCKED" in output[0]
    assert "target: label" in output[0]
    assert "proposed: Roadrunner Records, Listenable Records" in output[0]
    assert "multiple canonical values cannot be represented losslessly" in output[0]
    assert dict(info) == info_snapshot
    assert task.choice_flag is choice_snapshot
    assert task.match is match_snapshot
    assert task.items == items_snapshot


def test_unsupported_target_is_clear_in_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("format_descriptions", ("CD", "Album")),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    plugin._import_task_choice(None, import_task(album_info()))

    assert "format_descriptions\n    BLOCKED" in output[0]
    assert "target: unsupported" in output[0]
    assert "no supported AlbumInfo target" in output[0]


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
    info = album_info()

    plugin._import_task_choice(None, import_task(info))

    assert output == []
    assert info.genres is None


def test_apply_true_mutates_only_selected_album_info_and_never_calls_task_apply_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate(),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True)
    tracks: list[object] = [object()]
    info = album_info(
        tracks=tracks,
        album_id="mb-release",
        releasegroup_id="mb-release-group",
        discogs_albumid="123456",
        data_source="MusicBrainz",
    )
    item = Item(
        title="Original Track",
        album="Original Album",
        albumartist="Original Artist",
        genres=["Existing"],
    )
    task = import_task(info)
    task.items.append(item)
    match_snapshot = task.match
    items_snapshot = task.items
    item_snapshot = copy.deepcopy(dict(item))
    identity_snapshot = {
        field: info[field]
        for field in (
            "album",
            "artist",
            "album_id",
            "releasegroup_id",
            "discogs_albumid",
            "data_source",
        )
    }

    def reject_direct_application() -> None:
        pytest.fail("Noqlen must not call task.apply_metadata()")

    monkeypatch.setattr(task, "apply_metadata", reject_direct_application)

    plugin._import_task_choice(None, task)

    assert info.genres == ["Electronic", "Rock"]
    assert dict(item) == item_snapshot
    assert task.choice_flag is Action.APPLY
    assert task.match is match_snapshot
    assert task.items is items_snapshot
    assert task.items == [item]
    assert info.tracks is tracks
    assert {field: info[field] for field in identity_snapshot} == identity_snapshot
    assert "application mode: strict" in output[0]
    assert "application: applied to selected release (1 fields)" in output[0]


def test_preview_false_does_not_disable_application(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate(),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, preview=False, apply=True)
    info = album_info()

    with caplog.at_level(logging.INFO, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(info))

    assert output == []
    assert info.genres == ["Electronic", "Rock"]
    assert "prepared 1 selected-release metadata field(s) for beets application" in caplog.text


def test_apply_true_with_nothing_to_change_reports_no_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate(value=("Rock",)),),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True)
    info = album_info(genres=["Rock"])

    plugin._import_task_choice(None, import_task(info))

    assert info.genres == ["Rock"]
    assert "application: no changes" in output[0]
    assert "unchanged: 1" in output[0]


def test_apply_true_with_mapping_blocker_applies_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("genres", ("Rock",)),
            candidate("labels", ("Label A", "Label B")),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True)
    info = album_info()

    plugin._import_task_choice(None, import_task(info))

    assert info.genres is None
    assert info.label is None
    assert "application mode: strict" in output[0]
    assert "application: blocked" in output[0]
    assert "mapping blockers: 1" in output[0]


def test_preview_false_logs_blocked_application(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("genres", ("Rock",)),
            candidate("labels", ("Label A", "Label B")),
        ),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, preview=False, apply=True)
    info = album_info()

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(info))

    assert info.genres is None
    assert info.label is None
    assert "application blocked by unresolved review or target mapping" in caplog.text


def test_apply_true_with_resolution_review_applies_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("genres", ("Rock",)),
            candidate("labels", ("New Label",)),
        ),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True)
    info = album_info(label="Existing Label")

    plugin._import_task_choice(None, import_task(info))

    assert info.genres is None
    assert info.label == "Existing Label"


def test_explicit_strict_mode_preserves_all_or_nothing_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("genres", ("Rock",)),
            candidate("labels", ("Label A", "Label B")),
        ),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True, apply_mode=" strict ")
    info = album_info()

    plugin._import_task_choice(None, import_task(info))

    assert info.genres is None
    assert info.label is None


def test_partial_mode_applies_genres_and_withholds_mapping_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("genres", ("Rock",)),
            candidate("labels", ("Label A", "Label B")),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True, apply_mode="PARTIAL")
    info = album_info()

    plugin._import_task_choice(None, import_task(info))

    assert info.genres == ["Rock"]
    assert info.label is None
    assert "application mode: partial" in output[0]
    assert "application: partially applied to selected release (1 fields)" in output[0]
    assert "mapping blockers: 1" in output[0]


def test_partial_mode_applies_genres_and_withholds_resolution_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("genres", ("Rock",)),
            candidate("labels", ("New Label",)),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True, apply_mode="partial")
    info = album_info(label="Existing Label")

    plugin._import_task_choice(None, import_task(info))

    assert info.genres == ["Rock"]
    assert info.label == "Existing Label"
    assert "application: partially applied to selected release (1 fields)" in output[0]
    assert "resolution review: 1" in output[0]
    assert "labels\n    REVIEW" in output[0]


def test_partial_mode_applies_mapped_subset_and_retains_both_withheld_kinds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("genres", ("Rock",)),
            candidate("year", 2005),
            candidate("labels", ("New Label",)),
            candidate("format_descriptions", ("CD", "Album")),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True, apply_mode="partial")
    tracks: list[object] = [object()]
    info = album_info(
        tracks=tracks,
        label="Existing Label",
        album_id="mb-release",
        discogs_albumid="123456",
        data_source="MusicBrainz",
    )
    task = import_task(info)
    match_snapshot = task.match
    items_snapshot = task.items
    identity_snapshot = {
        field: info[field]
        for field in ("album", "artist", "album_id", "discogs_albumid", "data_source")
    }

    plugin._import_task_choice(None, task)

    assert info.genres == ["Rock"]
    assert info.year == 2005
    assert info.label == "Existing Label"
    assert info.tracks is tracks
    assert task.choice_flag is Action.APPLY
    assert task.match is match_snapshot
    assert task.items is items_snapshot
    assert {field: info[field] for field in identity_snapshot} == identity_snapshot
    assert "application: partially applied to selected release (2 fields)" in output[0]
    assert "mapping blockers: 1" in output[0]
    assert "resolution review: 1" in output[0]
    assert "format_descriptions\n    BLOCKED" in output[0]
    assert "labels\n    REVIEW" in output[0]


def test_partial_mode_with_only_withheld_fields_reports_no_eligible_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("labels", ("Label A", "Label B")),
            candidate("format_descriptions", ("CD", "Album")),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True, apply_mode="partial")
    info = album_info()

    plugin._import_task_choice(None, import_task(info))

    assert info.label is None
    assert "application mode: partial" in output[0]
    assert "application: no eligible changes applied" in output[0]
    assert "mapping blockers: 2" in output[0]


def test_preview_false_partial_application_logs_withheld_counts(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("genres", ("Rock",)),
            candidate("labels", ("New Label",)),
            candidate("format_descriptions", ("CD", "Album")),
        ),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, preview=False, apply=True, apply_mode="partial")
    info = album_info(label="Existing Label")

    with caplog.at_level(logging.INFO, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(info))

    assert info.genres == ["Rock"]
    assert info.label == "Existing Label"
    assert (
        "prepared 1 selected-release metadata field(s) for beets application; "
        "1 review and 1 mapping blocker withheld"
    ) in caplog.text


def test_preview_false_partial_with_nothing_eligible_logs_withheld_count(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("labels", ("Label A", "Label B")),
            candidate("format_descriptions", ("CD", "Album")),
        ),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, preview=False, apply=True, apply_mode="partial")

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(album_info()))

    assert "no eligible selected-release metadata changes" in caplog.text
    assert "2 unresolved field(s) withheld" in caplog.text


def test_invalid_application_mode_fails_before_provider_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: pytest.fail("invalid mode invoked provider"),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True, apply_mode="best_effort")
    info = album_info()

    with pytest.raises(BeetsApplicationError, match="invalid application mode"):
        plugin._import_task_choice(None, import_task(info))

    assert info.genres is None


def test_invalid_application_mode_is_inert_when_application_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate("genres", ("Rock",)),),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=False, apply_mode="best_effort")
    info = album_info()

    plugin._import_task_choice(None, import_task(info))

    assert info.genres is None


def test_provider_failure_allows_strict_fallback_application(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (_ for _ in ()).throw(ProviderError("unavailable")),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda self, context, storefront: (
            candidate(value=("K-pop",), provider="itunes"),
        ),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True, discogs=True, itunes=True)
    info = album_info()

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(info))

    assert "Discogs enrichment unavailable" in caplog.text
    assert info.genres == ["K-pop"]


def test_provider_failure_allows_valid_partial_subset_application(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (_ for _ in ()).throw(ProviderError("unavailable")),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_itunes_candidates",
        lambda self, context, storefront: (
            candidate(value=("K-pop",), provider="itunes"),
            candidate("year", 2005, provider="itunes"),
        ),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(
        plugin,
        apply=True,
        apply_mode="partial",
        discogs=True,
        itunes=True,
    )
    info = album_info(year=1999)

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, import_task(info))

    assert "Discogs enrichment unavailable" in caplog.text
    assert info.genres == ["K-pop"]
    assert info.year == 1999


def test_normal_later_beets_application_consumes_enriched_selected_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (candidate(value=("Rock", "Metal")),),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True)
    item = Item(title="Original Track", genres=[])
    track = TrackInfo(title="Matched Track", index=1, artist="Track Artist")
    info = album_info(tracks=[track])
    match = AlbumMatch(None, info, {item: track})  # type: ignore[arg-type]
    task = ImportTask(None, [], [item])
    task.choice_flag = Action.APPLY
    task.match = match

    plugin._import_task_choice(None, task)

    assert info.genres == ["Metal", "Rock"]
    assert item.genres == []

    task.apply_metadata()

    assert item.genres == ["Metal", "Rock"]


def test_normal_later_beets_application_consumes_only_partial_mapped_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("genres", ("Rock", "Metal")),
            candidate("labels", ("Label A", "Label B")),
        ),
    )
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, apply=True, apply_mode="partial")
    item = Item(title="Original Track", genres=[])
    track = TrackInfo(title="Matched Track", index=1, artist="Track Artist")
    info = album_info(tracks=[track])
    match = AlbumMatch(None, info, {item: track})  # type: ignore[arg-type]
    task = ImportTask(None, [], [item])
    task.choice_flag = Action.APPLY
    task.match = match

    plugin._import_task_choice(None, task)

    assert info.genres == ["Metal", "Rock"]
    assert info.label is None
    assert item.genres == []

    task.apply_metadata()

    assert item.genres == ["Metal", "Rock"]
    assert item.label == ""
    assert item.label not in {"Label A", "Label B", "Label A, Label B"}


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

    assert len(output) == 1
    assert "proposed: Safe Forged, [31mLabel" in output[0]
    assert "\x1b" not in output[0]


def test_resolved_integration_produces_keep_and_skip_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
            lambda self, context, token: (
                candidate("genres", ("Electronic", "Rock")),
                candidate("styles", ("Unrecognized Style",)),
            ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin, fields={"styles": False})

    plugin._import_task_choice(
        None,
        import_task(
            album_info(
                genres=["Electronic", "Rock"], style="Unrecognized Style"
            )
        ),
    )

    assert "genres\n    KEEP" in output[0]
    assert "current: Electronic, Rock" in output[0]
    assert "styles\n    SKIP" in output[0]
    assert "field is disabled by policy" in output[0]
    assert "unchanged: 1" in output[0]
    assert "skipped: 1" in output[0]
    assert "mapping complete: yes" in output[0]


def test_ambiguous_review_preview_has_no_selected_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            candidate("country", "NL"),
            MetadataCandidate("country", "US", "discogs", 0.95, "654321"),
        ),
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    plugin = NoqlenMetaPlugin()
    configure_enabled(plugin)

    plugin._import_task_choice(None, import_task(album_info()))

    assert "country\n    REVIEW" in output[0]
    assert "contenders: 2 from Discogs" in output[0]
    assert "returned conflicting values" in output[0]
    assert "candidate:" not in output[0]
