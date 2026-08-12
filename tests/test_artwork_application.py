import base64
import shutil
from pathlib import Path

import pytest
from beets.library import Item, Library
from mediafile import Image, ImageType, MediaFile

from beetsplug.noqlenmeta.artwork import (
    ArtworkCandidate,
    ArtworkLookupResult,
    ArtworkSettings,
    ArtworkSize,
    plan_album_artwork,
)
from beetsplug.noqlenmeta.artwork_application import (
    ArtworkApplicationError,
    apply_artwork_plan,
    download_artwork,
    validate_jpeg_bytes,
)

FIXTURE = Path(__file__).parent / "fixtures" / "identity_tags" / "silence.flac"
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


def candidate(
    *,
    selected_url: str = "https://archive.test/original.jpg",
    effective_size: str = "original",
) -> ArtworkCandidate:
    return ArtworkCandidate(
        source_scope="release",
        release_mbid="release-id",
        release_group_mbid="group-id",
        source_release_mbid=None,
        image_id="123",
        original_url="https://archive.test/original.jpg",
        thumbnail_urls={
            1200: "https://archive.test/1200.jpg",
            500: "https://archive.test/500.jpg",
            250: "https://archive.test/250.jpg",
        },
        requested_size=ArtworkSize.ORIGINAL,
        effective_size=effective_size,
        selected_url=selected_url,
    )


def album_fixture(tmp_path: Path, *, multidisc: bool = False) -> tuple[Library, object, list[Item]]:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    items = []
    directories = [tmp_path / "CD1", tmp_path / "CD2"] if multidisc else [tmp_path]
    for index, directory in enumerate(directories, 1):
        directory.mkdir(exist_ok=True)
        path = directory / f"track-{index}.flac"
        shutil.copy2(FIXTURE, path)
        items.append(
            Item(
                path=str(path).encode(),
                albumartist="Synthetic Artist",
                album="Synthetic Album",
                artist="Synthetic Artist",
                title=f"Track {index}",
                mb_albumid="release-id",
                mb_releasegroupid="group-id",
            )
        )
    album = library.add_album(items)
    return library, album, list(album.items())


def resolved() -> ArtworkLookupResult:
    return ArtworkLookupResult("RESOLVED", candidate=candidate())


def test_existing_sidecar_is_authoritative_and_may_be_embedded(tmp_path: Path) -> None:
    _, album, items = album_fixture(tmp_path)
    sidecar = tmp_path / "cover.jpg"
    sidecar.write_bytes(JPEG)

    plan = plan_album_artwork(
        album, items, None, ArtworkSettings(), write_enabled=True
    )

    assert plan.outcome == "RESOLVED"
    assert plan.candidate is None
    assert plan.local_source == bytes(sidecar)
    assert plan.sidecar_destinations == ()
    assert plan.canonical_artpath == bytes(sidecar)
    assert plan.embed_item_ids == tuple(item.id for item in items)


def test_any_embedded_art_preserves_whole_album_without_gap_filling(tmp_path: Path) -> None:
    _, album, items = album_fixture(tmp_path, multidisc=True)
    media = MediaFile(Path(items[0].path.decode()))
    media.images = [Image(JPEG, type=ImageType.front)]
    media.save()

    plan = plan_album_artwork(
        album, items, resolved(), ArtworkSettings(), write_enabled=True
    )

    assert plan.outcome == "PRESERVED"
    assert plan.candidate is None
    assert plan.sidecar_destinations == ()
    assert plan.embed_item_ids == ()


def test_candidate_plans_one_sidecar_per_real_disc_directory(tmp_path: Path) -> None:
    _, album, items = album_fixture(tmp_path, multidisc=True)

    plan = plan_album_artwork(
        album, items, resolved(), ArtworkSettings(), write_enabled=False
    )

    destinations = (bytes(tmp_path / "CD1" / "cover.jpg"), bytes(tmp_path / "CD2" / "cover.jpg"))
    assert plan.outcome == "RESOLVED"
    assert plan.candidate == resolved().candidate
    assert plan.sidecar_destinations == destinations
    assert plan.canonical_artpath == destinations[0]
    assert plan.embed_item_ids == ()


def test_replace_and_write_targets_every_persisted_album_item(tmp_path: Path) -> None:
    _, album, items = album_fixture(tmp_path, multidisc=True)
    for directory in (tmp_path / "CD1", tmp_path / "CD2"):
        (directory / "cover.jpg").write_bytes(JPEG)

    plan = plan_album_artwork(
        album,
        items,
        resolved(),
        ArtworkSettings(replace_existing=True),
        write_enabled=True,
    )

    assert plan.replace_existing is True
    assert plan.sidecar_destinations == (
        bytes(tmp_path / "CD1" / "cover.jpg"),
        bytes(tmp_path / "CD2" / "cover.jpg"),
    )
    assert plan.embed_item_ids == tuple(item.id for item in items)


def test_unpersisted_album_has_no_artwork_plan(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    shutil.copy2(FIXTURE, path)
    item = Item(path=bytes(path), artist="Artist", title="Track")

    with pytest.raises(ValueError, match="persisted Album"):
        plan_album_artwork(object(), [item], resolved(), ArtworkSettings(), write_enabled=True)  # type: ignore[arg-type]


class Response:
    def __init__(self, payload: bytes, *, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("HTTP failure")

    def iter_content(self, chunk_size: int) -> object:
        midpoint = len(self.payload) // 2
        return iter((self.payload[:midpoint], self.payload[midpoint:]))


class Session:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.calls: list[str] = []

    def get(self, url: str, *, stream: bool, timeout: object) -> Response:
        self.calls.append(url)
        return Response(self.payloads[url])


def test_download_rejects_empty_and_oversized_payloads() -> None:
    with pytest.raises(ArtworkApplicationError):
        download_artwork(candidate(), Session({candidate().selected_url: b""}))
    with pytest.raises(ArtworkApplicationError):
        download_artwork(
            candidate(),
            Session({candidate().selected_url: JPEG + b"x" * 10}),
            max_bytes=len(JPEG),
        )


def test_non_jpeg_original_uses_preplanned_thumbnail_fallbacks() -> None:
    artwork = candidate(selected_url="original", effective_size="original")
    session = Session(
        {
            "original": b"not jpeg",
            artwork.thumbnail_urls[1200]: b"not jpeg either",
            artwork.thumbnail_urls[500]: JPEG,
        }
    )

    assert download_artwork(artwork, session) == JPEG
    assert session.calls == ["original", artwork.thumbnail_urls[1200], artwork.thumbnail_urls[500]]


@pytest.mark.parametrize("payload", [b"", b"\xff\xd8missing-end", b"missing-start\xff\xd9"])
def test_jpeg_validation_rejects_invalid_payload(payload: bytes) -> None:
    with pytest.raises(ArtworkApplicationError):
        validate_jpeg_bytes(payload)


def test_apply_writes_identical_multidisc_sidecars_artpath_and_embeds(tmp_path: Path) -> None:
    library, album, items = album_fixture(tmp_path, multidisc=True)
    plan = plan_album_artwork(
        album, items, resolved(), ArtworkSettings(), write_enabled=True
    )

    result = apply_artwork_plan(library, album, plan, Session({candidate().selected_url: JPEG}))

    assert result.committed_sidecars == plan.sidecar_destinations
    assert all(Path(path.decode()).read_bytes() == JPEG for path in plan.sidecar_destinations)
    assert result.artpath_committed is True
    assert library.get_album(album.id).artpath == plan.canonical_artpath
    assert result.embedded_item_ids == tuple(item.id for item in items)
    for item in items:
        images = MediaFile(Path(item.path.decode())).images
        assert len(images) == 1
        assert images[0].data == JPEG


def test_apply_local_source_does_not_download(tmp_path: Path) -> None:
    library, album, items = album_fixture(tmp_path)
    sidecar = tmp_path / "cover.jpg"
    sidecar.write_bytes(JPEG)
    plan = plan_album_artwork(album, items, None, ArtworkSettings(), write_enabled=True)
    session = Session({})

    result = apply_artwork_plan(library, album, plan, session)

    assert session.calls == []
    assert result.embedded_item_ids == (items[0].id,)


def test_invalid_download_mutates_neither_sidecar_nor_artpath(tmp_path: Path) -> None:
    library, album, items = album_fixture(tmp_path)
    plan = plan_album_artwork(album, items, resolved(), ArtworkSettings(), write_enabled=False)

    result = apply_artwork_plan(
        library, album, plan, Session({candidate().selected_url: b"invalid"})
    )

    assert result.committed_sidecars == ()
    assert result.blocked_reason is not None
    assert not (tmp_path / "cover.jpg").exists()
    assert not library.get_album(album.id).artpath
