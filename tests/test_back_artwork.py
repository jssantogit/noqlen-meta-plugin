"""V3 exact-release back artwork with typed no-clobber associated asset."""

import base64
import shutil
from pathlib import Path

import pytest
from beets import config
from beets.library import Item, Library

from beetsplug.noqlenmeta.artwork import ArtworkSettings, artwork_context_from_album
from beetsplug.noqlenmeta.back_artwork import (
    apply_back_artwork_plan,
    back_artwork_requires_lookup,
    plan_back_artwork,
    resolve_caa_back_artwork,
)

JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////"
    "////////////////////////////////////////////////////////2wBDAf//"
    "//////////////////////////////////////////////////////////////"
    "////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAA"
    "AAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAA"
    "AAEf/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAA"
    "AAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAA"
    "AP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ/"
    "/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAA"
    "ABD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/EH//xAAUEQEAAAAAA"
    "AAAAAAAAAAAAAAA/9oACAECAQE/EH//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/"
    "9oACAEBAAE/EH//2Q=="
) + b"\xff\xd9"

RELEASE = "11111111-1111-4111-8111-111111111111"


@pytest.fixture(autouse=True)
def restore_beets_global_configuration() -> object:
    # beets shares the global config source stack across plugin instances.
    # Restore its *sources*, not just field values, after this module's tests.
    config["timeout"].get()
    sources = list(config.sources)
    yield
    config.sources[:] = sources


def payload(*, back: bool = True, approved: bool = True) -> dict[str, object]:
    return {
        "release": f"https://musicbrainz.org/release/{RELEASE}",
        "images": [
            {
                "id": "123",
                "front": False,
                "back": back,
                "approved": approved,
                "image": "https://coverartarchive.org/release/test/123.jpg",
                "thumbnails": {},
            }
        ],
    }


class Client:
    def __init__(self, data: object) -> None:
        self.data = data
        self.calls: list[str] = []

    def get_release(self, mbid: str):
        self.calls.append(mbid)
        return self.data


@pytest.fixture
def album(tmp_path: Path):
    lib = Library(str(tmp_path / "library.db"), set_music_dir=False)
    audio = tmp_path / "track.flac"
    fixture = Path(__file__).parent / "fixtures" / "identity_tags" / "silence.flac"
    shutil.copyfile(fixture, audio)
    item = Item(
        path=str(audio).encode(), album="Synthetic Album",
        albumartist="Synthetic Artist", artist="Synthetic Artist",
        title="Title", mb_albumid=RELEASE,
    )
    selected = lib.add_album([item])
    return lib, selected, artwork_context_from_album(selected, tuple(selected.items()))


def test_exact_back_is_identified_without_replacing_front() -> None:
    client = Client(payload())
    lookup = resolve_caa_back_artwork(client, RELEASE, ArtworkSettings())
    assert lookup.outcome == "RESOLVED"
    assert lookup.candidate is not None
    assert lookup.candidate.image_id == "123"
    assert client.calls == [RELEASE]


@pytest.mark.parametrize("invalid", [
    {"images": [], "release": f"https://musicbrainz.org/release/{RELEASE}"},
    payload(back=False),
    payload(approved=False),
    {"images": payload()["images"], "release": "https://musicbrainz.org/release/other"},
])
def test_missing_unapproved_or_wrong_release_back_is_never_selected(
    invalid: dict[str, object],
) -> None:
    lookup = resolve_caa_back_artwork(Client(invalid), RELEASE, ArtworkSettings())
    assert lookup.outcome != "RESOLVED"


def test_multiple_approved_back_images_need_review() -> None:
    result = payload()
    result["images"] = [*result["images"], dict(result["images"][0], id="different")]
    lookup = resolve_caa_back_artwork(Client(result), RELEASE, ArtworkSettings())
    assert lookup.outcome == "REVIEW"


def test_back_preview_is_noop_then_apply_creates_asset(album) -> None:
    lib, selected, ctx = album
    lookup = resolve_caa_back_artwork(Client(payload()), RELEASE, ArtworkSettings())
    plan = plan_back_artwork(ctx, lookup)
    sidecar = Path(ctx.disc_directories[0].decode()) / "back.jpg"
    assert plan.status == "PROPOSE"
    assert not sidecar.exists()

    class Session:
        def get(self, *_args, **_kwargs):
            class Response:
                def raise_for_status(self):
                    pass
                def iter_content(self, chunk_size):
                    yield JPEG
            return Response()

    result = apply_back_artwork_plan(lib, selected, plan, session=Session())
    assert result.status == "COMMITTED"
    assert sidecar.read_bytes() == JPEG
    assert selected.artpath != bytes(sidecar)


def test_existing_back_is_preserved_without_network(album) -> None:
    lib, selected, ctx = album
    sidecar = Path(ctx.disc_directories[0].decode()) / "back.jpg"
    sidecar.write_bytes(JPEG)
    assert not back_artwork_requires_lookup(ctx)
    plan = plan_back_artwork(ctx, None)
    assert plan.status == "PRESERVED"
    assert not apply_back_artwork_plan(lib, selected, plan).created


def test_existing_back_symlink_is_preserved(album, tmp_path: Path) -> None:
    lib, selected, ctx = album
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    (tmp_path / "back.jpg").symlink_to(secret)
    plan = plan_back_artwork(ctx, None)
    assert plan.status == "PRESERVED"
    assert not apply_back_artwork_plan(lib, selected, plan).created
    assert secret.read_text(encoding="utf-8") == "secret"


def test_back_path_created_after_preview_blocks_apply(album, tmp_path: Path) -> None:
    lib, selected, ctx = album
    plan = plan_back_artwork(
        ctx, resolve_caa_back_artwork(Client(payload()), RELEASE, ArtworkSettings())
    )
    (tmp_path / "back.jpg").write_text("local", encoding="utf-8")
    result = apply_back_artwork_plan(lib, selected, plan)
    assert result.status == "BLOCKED"
    assert (tmp_path / "back.jpg").read_text(encoding="utf-8") == "local"


def test_back_artwork_full_cli_preview_and_apply_is_opt_in(
    album, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import beetsplug.noqlenmeta.back_artwork as back_module
    from beetsplug.noqlenmeta import NoqlenMetaPlugin

    lib, selected, _ = album
    plugin = NoqlenMetaPlugin()
    plugin.config["fields"].set({
        **{field: False for field in plugin.config["fields"].keys()},
        "back_artwork": True,
    })
    plugin._coverartarchive_client = Client(payload())
    monkeypatch.setattr(back_module, "download_artwork", lambda *_: JPEG)
    command = plugin.commands()[0]
    preview, args = command.parse_args(["--all"])
    command.func(lib, preview, args)
    destination = tmp_path / "back.jpg"
    assert not destination.exists()

    apply, args = command.parse_args(["--apply", "--all"])
    command.func(lib, apply, args)
    assert destination.read_bytes() == JPEG
    assert selected.artpath != bytes(destination)
