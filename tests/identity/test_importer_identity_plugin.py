import copy
import logging
from collections.abc import Sequence

import pytest
from beets import config
from beets.autotag import AlbumMatch, TrackMatch
from beets.autotag.distance import Distance
from beets.autotag.hooks import AlbumInfo, TrackInfo
from beets.importer.actions import Action
from beets.importer.tasks import ImportTask, SingletonImportTask
from beets.library import Album, Item

from beetsplug.noqlenmeta import IdentityImporterSettingsError, NoqlenMetaPlugin
from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.identity import (
    BeetsMusicBrainzIdentitySource,
    IdentityAlbumContext,
    IdentityImportApplicationError,
    IdentitySourceError,
    MusicBrainzReleaseIdentity,
)

from .helpers import candidate, mbid

PRIVATE_PATH = b"/private/music/identity.flac"
PRIVATE_ERROR = "private raw source failure at /private/music"
PRIVATE_LYRIC = "private ordinary-provider value"


@pytest.fixture(autouse=True)
def restore_beets_config(monkeypatch: pytest.MonkeyPatch) -> object:
    config.add(
        {
            "artist_credit": False,
            "original_date": False,
            "overwrite_null": {"album": [], "track": []},
            "per_disc_numbering": False,
        }
    )
    sources = list(config.sources)
    monkeypatch.setattr(AlbumMatch, "from_scratch", lambda self, value: False)
    monkeypatch.setattr(TrackMatch, "from_scratch", lambda self, value: False)
    yield
    config.sources[:] = sources


class FakeIdentitySource:
    def __init__(
        self,
        candidates: Sequence[MusicBrainzReleaseIdentity] = (),
        error: Exception | None = None,
    ) -> None:
        self.candidates = tuple(candidates)
        self.error = error
        self.contexts: list[IdentityAlbumContext] = []

    def candidates_for(
        self, context: IdentityAlbumContext
    ) -> tuple[MusicBrainzReleaseIdentity, ...]:
        self.contexts.append(context)
        if self.error is not None:
            raise self.error
        return self.candidates


def _track(title: str = "Track 1", **overrides: object) -> TrackInfo:
    values: dict[str, object] = {
        "artist": "Example Artist",
        "title": title,
        "album": "Example Album",
        "length": 181.0,
        "index": 1,
        "medium": 1,
        "medium_index": 1,
    }
    values.update(overrides)
    return TrackInfo(**values)  # type: ignore[arg-type]


def _singleton_task(track: TrackInfo | None = None, item: Item | None = None):
    selected_item = item or Item(path=PRIVATE_PATH)
    selected_track = track or _track()
    task = SingletonImportTask(None, selected_item)
    task.choice_flag = Action.APPLY
    task.match = TrackMatch(Distance(), selected_track, selected_item)
    return task, selected_item, selected_track


def _album_task(count: int = 2):
    pairs = [
        (
            Item(path=f"/synthetic/{index}.flac".encode()),
            _track(
                f"Track {index}",
                length=180.0 + index,
                index=index,
                medium_index=index,
            ),
        )
        for index in range(1, count + 1)
    ]
    info = AlbumInfo(
        [track for _, track in pairs],
        artist="Example Artist",
        album="Example Album",
    )
    match = AlbumMatch(Distance(), info, dict(pairs), [], [])
    task = ImportTask(None, [], [item for item, _ in pairs])
    task.choice_flag = Action.APPLY
    task.match = match
    return task, pairs, info


def _configure(
    plugin: NoqlenMetaPlugin,
    *,
    enabled: object = True,
    preview: object = True,
    apply: object = False,
    ordinary_apply: bool = False,
    genres: bool = False,
    lyrics: bool = False,
    synced_lyrics: bool = False,
    discogs: bool = False,
    lrclib: bool = False,
) -> None:
    plugin.config.set(
        {
            "preview": True,
            "apply": ordinary_apply,
            "identity": {"enabled": enabled, "preview": preview, "apply": apply},
            "fields": {
                "genres": genres,
                "lyrics": lyrics,
                "synced_lyrics": synced_lyrics,
            },
            "providers": {
                "discogs": {"enabled": discogs, "user_token": ""},
                "musicbrainz": {"enabled": False},
                "lastfm": {"enabled": False},
                "itunes": {"enabled": False, "storefront": "us"},
                "lrclib": {"enabled": lrclib},
            },
        }
    )


def _capture_ui(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    output: list[str] = []
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.identity.importer_preview.ui.print_", output.append
    )
    monkeypatch.setattr("beetsplug.noqlenmeta.integration.ui.print_", output.append)
    monkeypatch.setattr("beetsplug.noqlenmeta.track_preview.ui.print_", output.append)
    return output


def _inject(plugin: NoqlenMetaPlugin, candidates=()) -> FakeIdentitySource:
    source = FakeIdentitySource(candidates)
    plugin._musicbrainz_identity_source = source
    return source


def _snapshot(*targets: object) -> tuple[dict[str, object], ...]:
    return tuple(copy.deepcopy(dict(target)) for target in targets)  # type: ignore[arg-type]


def test_identity_config_defaults_are_safe() -> None:
    plugin = NoqlenMetaPlugin()

    assert plugin._identity_settings() == (False, True, False)


def test_disabled_identity_does_not_construct_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.BeetsMusicBrainzIdentitySource",
        lambda: pytest.fail("disabled identity constructed a source"),
    )
    plugin = NoqlenMetaPlugin()
    _configure(plugin, enabled=False)

    plugin._import_task_choice(None, _singleton_task()[0])

    assert plugin._musicbrainz_identity_source is None


def test_preview_only_calls_source_once_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _capture_ui(monkeypatch)
    task, item, track = _singleton_task()
    before = _snapshot(item, track)
    plugin = NoqlenMetaPlugin()
    _configure(plugin)
    source = _inject(plugin, (candidate(1),))

    plugin._import_task_choice(None, task)

    assert len(source.contexts) == 1
    assert _snapshot(item, track) == before
    assert len(output) == 1
    assert "verdict: missing" in output[0]
    assert "application: disabled" in output[0]


@pytest.mark.parametrize("preview", [False, True])
def test_identity_apply_mutates_selected_metadata_with_or_without_preview(
    monkeypatch: pytest.MonkeyPatch, preview: bool
) -> None:
    output = _capture_ui(monkeypatch)
    task, item, track = _singleton_task()
    item_before = copy.deepcopy(dict(item))
    plugin = NoqlenMetaPlugin()
    _configure(plugin, preview=preview, apply=True)
    source = _inject(plugin, (candidate(1),))

    plugin._import_task_choice(None, task)

    assert len(source.contexts) == 1
    assert dict(item) == item_before
    assert track.track_id == mbid(1001)
    assert track.release_track_id == mbid(2001)
    assert track["mb_albumid"] == mbid(100)
    assert track["mb_releasegroupid"] == mbid(200)
    assert bool(output) is preview
    if preview:
        assert "application: applied 4 changes" in output[0]


@pytest.mark.parametrize(
    "identity",
    [
        {"enabled": False, "preview": True, "apply": True},
        {"enabled": "yes", "preview": True, "apply": False},
    ],
)
def test_invalid_identity_settings_fail_before_ordinary_provider_work(
    monkeypatch: pytest.MonkeyPatch, identity: dict[str, object]
) -> None:
    ordinary_calls: list[object] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: ordinary_calls.append(context) or (),
    )
    plugin = NoqlenMetaPlugin()
    _configure(plugin, lyrics=True, lrclib=True)
    plugin.config["identity"].set(identity)

    with pytest.raises(IdentityImporterSettingsError):
        plugin._import_task_choice(None, _singleton_task()[0])

    assert ordinary_calls == []


def test_enabled_identity_with_preview_and_apply_off_has_no_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.BeetsMusicBrainzIdentitySource",
        lambda: pytest.fail("non-executing identity constructed a source"),
    )
    plugin = NoqlenMetaPlugin()
    _configure(plugin, preview=False, apply=False)

    plugin._import_task_choice(None, _singleton_task()[0])

    assert plugin._musicbrainz_identity_source is None


@pytest.mark.parametrize("kind", ["album", "singleton"])
def test_each_selected_import_calls_identity_source_once(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    _capture_ui(monkeypatch)
    if kind == "album":
        task = _album_task()[0]
        remote = candidate(2)
    else:
        task = _singleton_task()[0]
        remote = candidate(1)
    plugin = NoqlenMetaPlugin()
    _configure(plugin)
    source = _inject(plugin, (remote,))

    plugin._import_task_choice(None, task)

    assert len(source.contexts) == 1
    assert len(source.contexts[0].tracks) == (2 if kind == "album" else 1)


def test_incomplete_identity_does_not_construct_or_call_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _capture_ui(monkeypatch)
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.BeetsMusicBrainzIdentitySource",
        lambda: pytest.fail("incomplete identity constructed a source"),
    )
    plugin = NoqlenMetaPlugin()
    _configure(plugin)
    task = _singleton_task(_track(title=" "))[0]

    plugin._import_task_choice(None, task)

    assert output == [
        "Noqlen Meta: selected import has insufficient identity structure for "
        "MusicBrainz audit"
    ]


def test_source_error_is_sanitized_and_fails_open(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    output = _capture_ui(monkeypatch)
    task, item, track = _singleton_task()
    before = _snapshot(item, track)
    plugin = NoqlenMetaPlugin()
    _configure(plugin, apply=True)
    source = FakeIdentitySource(error=IdentitySourceError(PRIVATE_ERROR))
    plugin._musicbrainz_identity_source = source

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, task)

    assert len(source.contexts) == 1
    assert _snapshot(item, track) == before
    assert output == []
    assert "MusicBrainz identity audit unavailable" in caplog.text
    assert PRIVATE_ERROR not in caplog.text
    assert PRIVATE_PATH.decode() not in caplog.text


def test_internal_identity_application_errors_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _capture_ui(monkeypatch)
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.apply_import_identity_plan",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            IdentityImportApplicationError("synthetic internal failure")
        ),
    )
    plugin = NoqlenMetaPlugin()
    _configure(plugin, apply=True)
    _inject(plugin, (candidate(1),))

    with pytest.raises(IdentityImportApplicationError, match="synthetic internal failure"):
        plugin._import_task_choice(None, _singleton_task()[0])


@pytest.mark.parametrize(
    ("case", "remotes", "expected_verdict", "mutated"),
    [
        ("missing", (candidate(1),), "missing", True),
        (
            "conflict",
            (candidate(1),),
            "conflict",
            True,
        ),
        (
            "confirmed",
            (candidate(1),),
            "confirmed",
            False,
        ),
        (
            "ambiguous",
            (candidate(1, release=mbid(100)), candidate(1, release=mbid(101))),
            "ambiguous",
            False,
        ),
    ],
)
def test_identity_verdicts_have_conservative_application_behavior(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    remotes: tuple[MusicBrainzReleaseIdentity, ...],
    expected_verdict: str,
    mutated: bool,
) -> None:
    output = _capture_ui(monkeypatch)
    ids: dict[str, str] = {}
    if case == "conflict":
        ids = {
            "mb_albumid": mbid(900),
            "mb_releasegroupid": mbid(901),
            "track_id": mbid(902),
            "release_track_id": mbid(903),
        }
    elif case == "confirmed":
        ids = {
            "mb_albumid": mbid(100),
            "mb_releasegroupid": mbid(200),
            "track_id": mbid(1001),
            "release_track_id": mbid(2001),
        }
    task, _, track = _singleton_task(_track(**ids))
    before = copy.deepcopy(dict(track))
    plugin = NoqlenMetaPlugin()
    _configure(plugin, apply=True)
    _inject(plugin, remotes)

    plugin._import_task_choice(None, task)

    assert f"verdict: {expected_verdict}" in output[0]
    assert (dict(track) != before) is mutated
    if case == "ambiguous":
        assert "application: blocked" in output[0]
    if case == "confirmed":
        assert "application: confirmed/no changes" in output[0]


def test_identity_runs_with_all_ordinary_providers_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _capture_ui(monkeypatch)
    plugin = NoqlenMetaPlugin()
    _configure(plugin)
    source = _inject(plugin, (candidate(1),))

    plugin._import_task_choice(None, _singleton_task()[0])

    assert len(source.contexts) == 1
    assert len(output) == 1


@pytest.mark.parametrize(
    ("ordinary_apply", "identity_apply", "identity_mutates"),
    [(False, True, True), (True, False, False)],
)
def test_identity_application_is_independent_of_ordinary_application(
    monkeypatch: pytest.MonkeyPatch,
    ordinary_apply: bool,
    identity_apply: bool,
    identity_mutates: bool,
) -> None:
    _capture_ui(monkeypatch)
    task, _, track = _singleton_task()
    before = copy.deepcopy(dict(track))
    plugin = NoqlenMetaPlugin()
    _configure(plugin, apply=identity_apply, ordinary_apply=ordinary_apply)
    _inject(plugin, (candidate(1),))

    plugin._import_task_choice(None, task)

    assert (dict(track) != before) is identity_mutates


def test_identity_and_ordinary_track_provider_coexist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _capture_ui(monkeypatch)
    ordinary_calls: list[object] = []
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: ordinary_calls.append(context)
        or (MetadataCandidate("lyrics", PRIVATE_LYRIC, "lrclib", 0.95, "42"),),
    )
    plugin = NoqlenMetaPlugin()
    _configure(plugin, lyrics=True, lrclib=True)
    source = _inject(plugin, (candidate(1),))

    plugin._import_task_choice(None, _singleton_task()[0])

    assert len(ordinary_calls) == 1
    assert len(source.contexts) == 1
    rendered = "\n".join(output)
    assert "Noqlen Meta / track plan:" in rendered
    assert "MusicBrainz identity audit" in rendered
    assert PRIVATE_LYRIC not in rendered


def test_ordinary_and_identity_application_can_both_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _capture_ui(monkeypatch)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: (
            MetadataCandidate("lyrics", PRIVATE_LYRIC, "lrclib", 0.95, "42"),
        ),
    )
    task, item, track = _singleton_task()
    item_before = copy.deepcopy(dict(item))
    plugin = NoqlenMetaPlugin()
    _configure(
        plugin,
        apply=True,
        ordinary_apply=True,
        lyrics=True,
        lrclib=True,
    )
    source = _inject(plugin, (candidate(1),))

    plugin._import_task_choice(None, task)

    assert len(source.contexts) == 1
    assert dict(item) == item_before
    assert track.lyrics == PRIVATE_LYRIC
    assert track.track_id == mbid(1001)
    assert track.release_track_id == mbid(2001)
    assert track["mb_albumid"] == mbid(100)
    assert track["mb_releasegroupid"] == mbid(200)
    rendered = "\n".join(output)
    assert "application status: applied" in rendered
    assert "application: applied 4 changes" in rendered
    assert PRIVATE_LYRIC not in rendered


def test_ordinary_release_application_coexists_with_identity_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _capture_ui(monkeypatch)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            MetadataCandidate("genres", ("Synthetic Genre",), "discogs", 0.95, "7"),
        ),
    )
    task, pairs, album_info = _album_task()
    plugin = NoqlenMetaPlugin()
    _configure(
        plugin,
        apply=True,
        ordinary_apply=True,
        genres=True,
        discogs=True,
    )
    source = _inject(plugin, (candidate(2),))

    plugin._import_task_choice(None, task)

    assert len(source.contexts) == 1
    assert album_info.genres == ["Synthetic Genre"]
    assert album_info.album_id == mbid(100)
    assert album_info.releasegroup_id == mbid(200)
    assert [track.track_id for _, track in pairs] == [mbid(1001), mbid(1002)]
    assert [track.release_track_id for _, track in pairs] == [mbid(2001), mbid(2002)]
    rendered = "\n".join(output)
    assert "Noqlen Meta / beets target plan:" in rendered
    assert "application: applied 6 changes" in rendered


def test_identity_ambiguity_does_not_block_ordinary_track_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _capture_ui(monkeypatch)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: (
            MetadataCandidate("lyrics", PRIVATE_LYRIC, "lrclib", 0.95, "42"),
        ),
    )
    task, _, track = _singleton_task()
    plugin = NoqlenMetaPlugin()
    _configure(
        plugin,
        apply=True,
        ordinary_apply=True,
        lyrics=True,
        lrclib=True,
    )
    _inject(
        plugin,
        (candidate(1, release=mbid(100)), candidate(1, release=mbid(101))),
    )

    plugin._import_task_choice(None, task)

    assert track.lyrics == PRIVATE_LYRIC
    assert track.track_id is None
    assert track.release_track_id is None
    rendered = "\n".join(output)
    assert "application status: applied" in rendered
    assert "verdict: ambiguous" in rendered
    assert "application: blocked" in rendered


def test_identity_ambiguity_does_not_block_ordinary_release_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _capture_ui(monkeypatch)
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            MetadataCandidate("genres", ("Synthetic Genre",), "discogs", 0.95, "7"),
        ),
    )
    task, pairs, album_info = _album_task()
    plugin = NoqlenMetaPlugin()
    _configure(
        plugin,
        apply=True,
        ordinary_apply=True,
        genres=True,
        discogs=True,
    )
    _inject(
        plugin,
        (candidate(2, release=mbid(100)), candidate(2, release=mbid(101))),
    )

    plugin._import_task_choice(None, task)

    assert album_info.genres == ["Synthetic Genre"]
    assert album_info.album_id is None
    assert album_info.releasegroup_id is None
    assert all(track.track_id is None for _, track in pairs)
    rendered = "\n".join(output)
    assert "application: applied to selected release (1 fields)" in rendered
    assert "verdict: ambiguous" in rendered
    assert "application: blocked" in rendered


@pytest.mark.parametrize("ordinary_outcome", ["review", "mapping_blocker"])
def test_ordinary_review_or_blocker_does_not_block_identity_repair(
    monkeypatch: pytest.MonkeyPatch, ordinary_outcome: str
) -> None:
    output = _capture_ui(monkeypatch)
    field = "lyrics" if ordinary_outcome == "review" else "synced_lyrics"
    value = PRIVATE_LYRIC if field == "lyrics" else "[00:01.00] synthetic line"
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: (MetadataCandidate(field, value, "lrclib", 0.95, "42"),),
    )
    item = Item(path=PRIVATE_PATH, lyrics="existing local lyrics")
    task, _, track = _singleton_task(item=item)
    plugin = NoqlenMetaPlugin()
    _configure(
        plugin,
        apply=True,
        ordinary_apply=True,
        lyrics=field == "lyrics",
        synced_lyrics=field == "synced_lyrics",
        lrclib=True,
    )
    _inject(plugin, (candidate(1),))

    plugin._import_task_choice(None, task)

    assert item.lyrics == "existing local lyrics"
    assert track.get(field) is None
    assert track.track_id == mbid(1001)
    assert track.release_track_id == mbid(2001)
    assert track["mb_albumid"] == mbid(100)
    assert track["mb_releasegroupid"] == mbid(200)
    rendered = "\n".join(output)
    if ordinary_outcome == "review":
        assert "resolution review: 1" in rendered
    else:
        assert "mapping blockers: 1" in rendered
    assert "application status: blocked" in rendered
    assert "application: applied 4 changes" in rendered
    assert PRIVATE_LYRIC not in rendered


def test_malformed_production_source_contract_is_identity_source_error_and_fails_open(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    output = _capture_ui(monkeypatch)
    malformed = AlbumInfo(
        [_track()],
        artist="Example Artist",
        album="Example Album",
        album_id=mbid(100),
        releasegroup_id=mbid(200),
    )
    source = BeetsMusicBrainzIdentitySource(
        fetch_release=lambda release_id: None,
        search_releases=lambda artist, album: (malformed,),
    )
    original_candidates_for = source.candidates_for
    errors: list[Exception] = []

    def recording_candidates_for(
        context: IdentityAlbumContext,
    ) -> tuple[MusicBrainzReleaseIdentity, ...]:
        try:
            return original_candidates_for(context)
        except Exception as error:
            errors.append(error)
            raise

    monkeypatch.setattr(source, "candidates_for", recording_candidates_for)
    task, item, track = _singleton_task()
    before = _snapshot(item, track)
    plugin = NoqlenMetaPlugin()
    _configure(plugin, apply=True)
    plugin._musicbrainz_identity_source = source

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, task)

    assert len(errors) == 1
    assert isinstance(errors[0], IdentitySourceError)
    assert _snapshot(item, track) == before
    assert output == []
    assert "MusicBrainz identity audit unavailable" in caplog.text
    assert "invalid data" not in caplog.text


def test_disabled_identity_preserves_ordinary_release_and_track_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _capture_ui(monkeypatch)
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.BeetsMusicBrainzIdentitySource",
        lambda: pytest.fail("disabled identity constructed a source"),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_discogs_candidates",
        lambda self, context, token: (
            MetadataCandidate("genres", ("Synthetic Genre",), "discogs", 0.95, "7"),
        ),
    )
    monkeypatch.setattr(
        NoqlenMetaPlugin,
        "_lrclib_candidates",
        lambda self, context: (
            MetadataCandidate("lyrics", PRIVATE_LYRIC, "lrclib", 0.95, "42"),
        ),
    )
    task, pairs, album_info = _album_task(1)
    plugin = NoqlenMetaPlugin()
    _configure(
        plugin,
        enabled=False,
        ordinary_apply=True,
        genres=True,
        lyrics=True,
        discogs=True,
        lrclib=True,
    )

    plugin._import_task_choice(None, task)

    track = pairs[0][1]
    assert plugin._musicbrainz_identity_source is None
    assert album_info.genres == ["Synthetic Genre"]
    assert track.lyrics == PRIVATE_LYRIC
    assert album_info.album_id is None
    assert track.track_id is None
    rendered = "\n".join(output)
    assert "Noqlen Meta / beets target plan:" in rendered
    assert "Noqlen Meta / track plan:" in rendered
    assert "MusicBrainz identity audit" not in rendered
    assert PRIVATE_LYRIC not in rendered


def test_one_identity_source_is_retained_across_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _capture_ui(monkeypatch)
    instances: list[FakeIdentitySource] = []

    def construct() -> FakeIdentitySource:
        source = FakeIdentitySource((candidate(1),))
        instances.append(source)
        return source

    monkeypatch.setattr("beetsplug.noqlenmeta.BeetsMusicBrainzIdentitySource", construct)
    plugin = NoqlenMetaPlugin()
    _configure(plugin)

    plugin._import_task_choice(None, _singleton_task()[0])
    plugin._import_task_choice(None, _singleton_task()[0])

    assert len(instances) == 1
    assert len(instances[0].contexts) == 2
    assert plugin._musicbrainz_identity_source is instances[0]


def test_identity_never_calls_persistence_or_match_application_apis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _capture_ui(monkeypatch)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("identity called a prohibited beets API")

    for owner, name in (
        (AlbumMatch, "apply_metadata"),
        (TrackMatch, "apply_metadata"),
        (Item, "store"),
        (Item, "write"),
        (Item, "try_write"),
        (Item, "try_sync"),
        (Album, "store"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    plugin = NoqlenMetaPlugin()
    _configure(plugin, apply=True)
    _inject(plugin, (candidate(1),))

    plugin._import_task_choice(None, _singleton_task()[0])


def test_plugin_output_omits_local_keys_paths_and_raw_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    output = _capture_ui(monkeypatch)
    plugin = NoqlenMetaPlugin()
    _configure(plugin)
    source = FakeIdentitySource(error=IdentitySourceError(PRIVATE_ERROR))
    plugin._musicbrainz_identity_source = source

    with caplog.at_level(logging.WARNING, logger="beets.noqlenmeta"):
        plugin._import_task_choice(None, _singleton_task()[0])

    rendered = "\n".join(output) + caplog.text
    assert "track:0001" not in rendered
    assert PRIVATE_PATH.decode() not in rendered
    assert PRIVATE_ERROR not in rendered
