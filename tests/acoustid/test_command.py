from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest
from beets import config, ui
from beets.library import Item, Library

import beetsplug.noqlenmeta as plugin_module
from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.acoustid import (
    AcoustIDEvidencePolicy,
    AcoustIDEvidenceReason,
    AcoustIDEvidenceVerdict,
    AcoustIDFingerprintOrigin,
    AcoustIDResultGroup,
    AcoustIDTrackEvidence,
    FingerprintBackendResult,
    classify_acoustid_evidence,
    default_acoustid_settings,
)
from beetsplug.noqlenmeta.identity import (
    IdentityAlbumContext,
    MusicBrainzReleaseIdentity,
    MusicBrainzTrackIdentity,
)
from tests.identity.helpers import mbid


@pytest.fixture(autouse=True)
def restore_beets_config() -> object:
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return Library(str(tmp_path / "library.db"), set_music_dir=False)


def configure(plugin: NoqlenMetaPlugin, **changes: object) -> None:
    plugin.config.set({"acoustid": {**asdict(default_acoustid_settings()), **changes}})


def invoke(plugin: NoqlenMetaPlugin, library: Library, args: list[str]) -> None:
    command = plugin.commands()[0]
    opts, query = command.parse_args(args)
    command.func(library, opts, query)


def add_singleton(
    library: Library,
    path: Path,
    *,
    fingerprint: object = None,
) -> Item:
    path.write_bytes(b"synthetic audio bytes")
    item = Item(
        path=str(path),
        artist="Example Artist",
        album="Solo",
        title="Solo",
        length=181.0,
        disc=1,
        track=1,
        acoustid_fingerprint=fingerprint,
    )
    library.add(item)
    return item


def remote(
    context: IdentityAlbumContext, seed: int, *, recording: str
) -> MusicBrainzReleaseIdentity:
    track = context.tracks[0]
    return MusicBrainzReleaseIdentity(
        mbid(seed),
        mbid(seed + 1),
        context.album_artist,
        context.album,
        (
            MusicBrainzTrackIdentity(
                recording,
                mbid(seed + 200),
                track.artist,
                track.title,
                track.length,
                1,
                1,
                1,
            ),
        ),
    )


class Source:
    def __init__(self, route) -> None:
        self.route = route

    def candidates_for(self, context: IdentityAlbumContext):
        return self.route(context)


def decisive(local_key: str, recording: str) -> AcoustIDTrackEvidence:
    return classify_acoustid_evidence(
        local_key,
        AcoustIDFingerprintOrigin.EXISTING,
        (
            AcoustIDResultGroup(
                "00000001-0000-4000-8000-000000000001", 0.99, (recording,)
            ),
        ),
        AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
    )


def unavailable(local_key: str, reason: AcoustIDEvidenceReason) -> AcoustIDTrackEvidence:
    return AcoustIDTrackEvidence(
        local_key,
        AcoustIDFingerprintOrigin.EXISTING,
        (),
        AcoustIDEvidenceVerdict.UNAVAILABLE,
        None,
        None,
        reason,
        None,
        None,
        None,
        0,
        0,
    )


def no_match(local_key: str) -> AcoustIDTrackEvidence:
    return classify_acoustid_evidence(
        local_key,
        AcoustIDFingerprintOrigin.EXISTING,
        (
            AcoustIDResultGroup(
                "00000001-0000-4000-8000-000000000001", 0.5, (mbid(1001),)
            ),
        ),
        AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
    )


def ambiguous(local_key: str) -> AcoustIDTrackEvidence:
    return classify_acoustid_evidence(
        local_key,
        AcoustIDFingerprintOrigin.EXISTING,
        (
            AcoustIDResultGroup(
                "00000001-0000-4000-8000-000000000001", 0.99, (mbid(1001),)
            ),
            AcoustIDResultGroup(
                "00000002-0000-4000-8000-000000000002", 0.99, (mbid(1002),)
            ),
        ),
        AcoustIDEvidencePolicy(0.9, 0.05, 5, 10),
    )


def test_standalone_query_and_all_preview_without_backend_or_network(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    item = add_singleton(library, tmp_path / "preview.flac")
    plugin = NoqlenMetaPlugin()
    configure(plugin)
    output = []
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)
    monkeypatch.setattr(
        plugin_module.FpcalcFingerprintBackend,
        "from_settings",
        lambda settings: (_ for _ in ()).throw(AssertionError("backend construction")),
    )

    invoke(plugin, library, ["--acoustid", f"id:{item.id}"])
    invoke(plugin, library, ["--acoustid", "--all"])

    assert len(output) == 2
    assert all("Fingerprint MISSING" in value for value in output)
    with pytest.raises(ui.UserError, match="query or --all"):
        invoke(plugin, library, ["--acoustid"])
    with pytest.raises(ui.UserError, match="not both"):
        invoke(plugin, library, ["--acoustid", "--all", f"id:{item.id}"])


@pytest.mark.parametrize(
    "arguments",
    [
        ["--acoustid", "--identity", "--all"],
        ["--acoustid", "--identity-tags", "--all"],
        ["--acoustid", "--write", "--all"],
        ["--acoustid", "--partial", "--all"],
        ["--fingerprint-missing", "--all"],
    ],
)
def test_invalid_combinations_fail_before_config_selection_or_local_work(
    monkeypatch: pytest.MonkeyPatch, library: Library, arguments: list[str]
) -> None:
    plugin = NoqlenMetaPlugin()
    monkeypatch.setattr(
        plugin,
        "_acoustid_settings",
        lambda: (_ for _ in ()).throw(AssertionError("configuration work")),
    )
    monkeypatch.setattr(
        plugin_module,
        "select_acoustid_targets",
        lambda *args: (_ for _ in ()).throw(AssertionError("selection work")),
    )
    monkeypatch.setattr(
        plugin_module,
        "select_library_identity_targets",
        lambda *args: (_ for _ in ()).throw(AssertionError("selection work")),
    )

    with pytest.raises(ui.UserError):
        invoke(plugin, library, arguments)


def test_invalid_configuration_fails_before_selection(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    plugin = NoqlenMetaPlugin()
    plugin.config["acoustid"].set({**asdict(default_acoustid_settings()), "secret": "value"})
    monkeypatch.setattr(
        plugin_module,
        "select_acoustid_targets",
        lambda *args: (_ for _ in ()).throw(AssertionError("selection work")),
    )

    with pytest.raises(ui.UserError, match="invalid AcoustID configuration"):
        invoke(plugin, library, ["--acoustid", "--all"])


def test_fingerprint_missing_apply_is_database_only(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    path = tmp_path / "apply.flac"
    item = add_singleton(library, path)
    before = path.read_bytes()
    plugin = NoqlenMetaPlugin()
    configure(plugin, lookup=False)

    class Backend:
        def fingerprint(self, media_path: bytes | str) -> FingerprintBackendResult:
            return FingerprintBackendResult(181.0, "generated-private-fingerprint")

    class Factory:
        @classmethod
        def from_settings(cls, settings):
            return Backend()

    monkeypatch.setattr(plugin_module, "FpcalcFingerprintBackend", Factory)
    monkeypatch.setattr(plugin_module.ui, "print_", lambda value: None)

    invoke(
        plugin,
        library,
        ["--acoustid", "--fingerprint-missing", "--apply", f"id:{item.id}"],
    )

    fresh = library.get_item(item.id)
    assert fresh is not None
    assert fresh.acoustid_fingerprint == "generated-private-fingerprint"
    assert not fresh.acoustid_id
    assert path.read_bytes() == before


def test_every_standalone_target_is_planned_before_one_application_call(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    plugin = NoqlenMetaPlugin()
    configure(plugin, lookup=False)
    events = []
    monkeypatch.setattr(plugin_module, "select_acoustid_targets", lambda *args: ("a", "b"))
    monkeypatch.setattr(plugin_module, "AcoustIDLookupService", lambda settings: object())

    def plan(target, *args):
        events.append(f"plan:{target}")
        return f"result:{target}"

    def apply(lib, results):
        events.append(f"apply:{','.join(results)}")
        return type(
            "Result",
            (),
            {
                "target_count": 2,
                "changed_target_count": 0,
                "changed_item_count": 0,
                "applied_field_count": 0,
            },
        )()

    def preview(result):
        events.append(f"preview:{result}")
        return result

    monkeypatch.setattr(plugin_module, "plan_acoustid_target", plan)
    monkeypatch.setattr(plugin_module, "apply_acoustid_results", apply)
    monkeypatch.setattr(plugin_module, "render_acoustid_preview", preview)
    monkeypatch.setattr(plugin_module.ui, "print_", lambda value: None)

    invoke(plugin, library, ["--acoustid", "--apply", "--all"])

    assert events == [
        "plan:a",
        "plan:b",
        "preview:result:a",
        "preview:result:b",
        "apply:result:a,result:b",
    ]


def test_standalone_previews_are_rendered_before_application_error(
    monkeypatch: pytest.MonkeyPatch, library: Library
) -> None:
    plugin = NoqlenMetaPlugin()
    configure(plugin, lookup=False)
    events = []
    monkeypatch.setattr(plugin_module, "select_acoustid_targets", lambda *args: ("a", "b"))
    monkeypatch.setattr(plugin_module, "AcoustIDLookupService", lambda settings: object())

    def plan(target, *args):
        events.append(f"plan:{target}")
        return f"result:{target}"

    def preview(result):
        events.append(f"preview:{result}")
        return result

    def apply(lib, results):
        events.append(f"apply:{','.join(results)}")
        raise RuntimeError("application blocked")

    monkeypatch.setattr(plugin_module, "plan_acoustid_target", plan)
    monkeypatch.setattr(plugin_module, "render_acoustid_preview", preview)
    monkeypatch.setattr(plugin_module, "apply_acoustid_results", apply)
    monkeypatch.setattr(plugin_module.ui, "print_", lambda value: None)

    with pytest.raises(RuntimeError, match="application blocked"):
        invoke(plugin, library, ["--acoustid", "--apply", "--all"])

    assert events == [
        "plan:a",
        "plan:b",
        "preview:result:a",
        "preview:result:b",
        "apply:result:a,result:b",
    ]


def test_identity_decisive_lookup_filters_runner_up_without_acoustid_writes(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    item = add_singleton(library, tmp_path / "identity.flac", fingerprint="stored-private")
    plugin = NoqlenMetaPlugin()
    configure(plugin, enabled=True, use_for_identity=True)
    expected_recording = mbid(1001)
    plugin._musicbrainz_identity_source = Source(
        lambda context: (
            remote(context, 100, recording=expected_recording),
            remote(context, 101, recording=mbid(9001)),
        )
    )

    class Lookup:
        def __init__(self, settings) -> None:
            pass

        def lookup(self, material):
            return decisive(material.local_key, expected_recording)

    output = []
    monkeypatch.setattr(plugin_module, "AcoustIDLookupService", Lookup)
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)

    invoke(plugin, library, ["--identity", f"id:{item.id}"])

    assert "reason: identity_missing" in output[0]
    fresh = library.get_item(item.id)
    assert fresh is not None
    assert fresh.acoustid_fingerprint == "stored-private"
    assert not fresh.acoustid_id


def test_identity_compute_missing_never_constructs_backend_or_looks_up(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    item = add_singleton(library, tmp_path / "missing.flac")
    plugin = NoqlenMetaPlugin()
    configure(plugin, enabled=True, compute_missing=True)
    plugin._musicbrainz_identity_source = Source(
        lambda context: (remote(context, 100, recording=mbid(1001)),)
    )
    lookups = []

    class Lookup:
        def __init__(self, settings) -> None:
            pass

        def lookup(self, material):
            lookups.append(material)
            raise AssertionError("lookup must not run")

    monkeypatch.setattr(plugin_module, "AcoustIDLookupService", Lookup)
    monkeypatch.setattr(
        plugin_module,
        "_identity_backend_forbidden",
        lambda: (_ for _ in ()).throw(AssertionError("backend must not run")),
    )
    monkeypatch.setattr(plugin_module.ui, "print_", lambda value: None)

    invoke(plugin, library, ["--identity", f"id:{item.id}"])

    assert lookups == []


def test_identity_without_structural_candidates_skips_acoustid_lookup(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    item = add_singleton(library, tmp_path / "no-candidates.flac", fingerprint="stored-private")
    plugin = NoqlenMetaPlugin()
    configure(plugin, enabled=True)
    plugin._musicbrainz_identity_source = Source(lambda context: ())

    class Lookup:
        def __init__(self, settings) -> None:
            pass

        def lookup(self, material):
            raise AssertionError("lookup must not run without structural candidates")

    output = []
    monkeypatch.setattr(plugin_module, "AcoustIDLookupService", Lookup)
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)

    invoke(plugin, library, ["--identity", f"id:{item.id}"])

    assert "reason: no_candidates" in output[0]


@pytest.mark.parametrize(
    "changes", [{"enabled": False}, {"enabled": True, "use_for_identity": False}]
)
def test_identity_disabled_settings_do_not_construct_acoustid_service(
    monkeypatch: pytest.MonkeyPatch,
    library: Library,
    tmp_path: Path,
    changes: dict[str, object],
) -> None:
    item = add_singleton(library, tmp_path / "disabled.flac", fingerprint="stored-private")
    plugin = NoqlenMetaPlugin()
    configure(plugin, **changes)
    plugin._musicbrainz_identity_source = Source(
        lambda context: (remote(context, 100, recording=mbid(1001)),)
    )
    monkeypatch.setattr(
        plugin_module,
        "AcoustIDLookupService",
        lambda settings: (_ for _ in ()).throw(AssertionError("service construction")),
    )
    monkeypatch.setattr(plugin_module.ui, "print_", lambda value: None)

    invoke(plugin, library, ["--identity", f"id:{item.id}"])


@pytest.mark.parametrize(
    "evidence",
    [
        lambda key: unavailable(key, AcoustIDEvidenceReason.LOOKUP_DISABLED),
        lambda key: unavailable(key, AcoustIDEvidenceReason.CLIENT_KEY_MISSING),
        lambda key: unavailable(key, AcoustIDEvidenceReason.LOOKUP_FAILED),
        no_match,
        ambiguous,
    ],
)
def test_identity_unavailable_lookup_is_neutral(
    monkeypatch: pytest.MonkeyPatch,
    library: Library,
    tmp_path: Path,
    evidence,
) -> None:
    item = add_singleton(library, tmp_path / "neutral.flac", fingerprint="stored-private")
    plugin = NoqlenMetaPlugin()
    configure(plugin, enabled=True)
    plugin._musicbrainz_identity_source = Source(
        lambda context: (remote(context, 100, recording=mbid(1001)),)
    )

    class Lookup:
        def __init__(self, settings) -> None:
            pass

        def lookup(self, material):
            return evidence(material.local_key)

    output = []
    monkeypatch.setattr(plugin_module, "AcoustIDLookupService", Lookup)
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)

    invoke(plugin, library, ["--identity", f"id:{item.id}"])

    assert "reason: identity_missing" in output[0]


def test_identity_decisive_conflict_blocks_repair(
    monkeypatch: pytest.MonkeyPatch, library: Library, tmp_path: Path
) -> None:
    item = add_singleton(library, tmp_path / "conflict.flac", fingerprint="stored-private")
    plugin = NoqlenMetaPlugin()
    configure(plugin, enabled=True)
    plugin._musicbrainz_identity_source = Source(
        lambda context: (remote(context, 100, recording=mbid(1001)),)
    )

    class Lookup:
        def __init__(self, settings) -> None:
            pass

        def lookup(self, material):
            return decisive(material.local_key, mbid(9999))

    output = []
    monkeypatch.setattr(plugin_module, "AcoustIDLookupService", Lookup)
    monkeypatch.setattr(plugin_module.ui, "print_", output.append)

    invoke(plugin, library, ["--identity", "--apply", f"id:{item.id}"])

    assert "reason: acoustid_recording_conflict" in output[0]
    assert "repair ready: no" in output[0]
    fresh = library.get_item(item.id)
    assert fresh is not None
    assert not fresh.mb_trackid
    assert fresh.acoustid_fingerprint == "stored-private"
    assert not fresh.acoustid_id
