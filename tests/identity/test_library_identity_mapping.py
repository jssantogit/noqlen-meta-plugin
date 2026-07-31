from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, field, replace
from typing import Any, cast

import pytest
from beets.library import Album, Item, Library

from beetsplug.noqlenmeta.identity import (
    IdentityAlbumContext,
    IdentityFieldStatus,
    IdentityVerdict,
    LibraryIdentityMappingError,
    LibraryIdentityTargetPlan,
    LibraryIdentityWriteKind,
    MusicBrainzReleaseIdentity,
    all_library_identity_targets,
    audit_library_identity_target,
    map_library_identity_targets,
)

from .helpers import candidate, candidate_track, mbid


@pytest.fixture
def library() -> Library:
    return Library(":memory:", set_music_dir=False)


def _add_album(library: Library, *, count: int = 2) -> Album:
    album = library.add_album(
        [
            Item(
                albumartist="Example Artist",
                album="Example Album",
                artist="Example Artist",
                title=f"Track {index}",
                length=180.0 + index,
                disc=1,
                track=index,
                path=f"private/{index:02}.flac".encode(),
            )
            for index in range(1, count + 1)
        ]
    )
    assert album.id is not None
    fresh = library.get_album(album.id)
    assert fresh is not None
    return fresh


def _add_singleton(library: Library) -> Item:
    item = Item(
        album="Example Album",
        artist="Example Artist",
        title="Track 1",
        length=181.0,
        disc=1,
        track=1,
        path=b"private/single.flac",
    )
    library.add(item)
    assert item.id is not None
    return item


@dataclass
class _Source:
    candidates: tuple[MusicBrainzReleaseIdentity, ...]
    contexts: list[IdentityAlbumContext] = field(default_factory=list)

    def candidates_for(
        self, context: IdentityAlbumContext
    ) -> tuple[MusicBrainzReleaseIdentity, ...]:
        self.contexts.append(context)
        return self.candidates


def _audit(library: Library, release: MusicBrainzReleaseIdentity | None = None):
    selected = all_library_identity_targets(library)[0]
    result = audit_library_identity_target(selected, _Source((release or candidate(2),)))
    assert result is not None
    return result


def test_album_mapping_targets_album_and_every_item_in_canonical_order(
    library: Library,
) -> None:
    album = _add_album(library)
    audit = _audit(library)

    plan = map_library_identity_targets(audit)

    item_ids = [item.item_id for item in audit.selected.items]
    assert [
        (
            change.canonical_field,
            change.scope_key,
            change.write_kind,
            change.row_id,
            change.target_field,
        )
        for change in plan.changes
    ] == [
        ("mb_albumid", None, LibraryIdentityWriteKind.ALBUM_FIELD, album.id, "mb_albumid"),
        (
            "mb_releasegroupid",
            None,
            LibraryIdentityWriteKind.ALBUM_FIELD,
            album.id,
            "mb_releasegroupid",
        ),
        ("mb_albumid", None, LibraryIdentityWriteKind.ITEM_FIELD, item_ids[0], "mb_albumid"),
        (
            "mb_releasegroupid",
            None,
            LibraryIdentityWriteKind.ITEM_FIELD,
            item_ids[0],
            "mb_releasegroupid",
        ),
        (
            "mb_trackid",
            f"library-item:{item_ids[0]}",
            LibraryIdentityWriteKind.ITEM_FIELD,
            item_ids[0],
            "mb_trackid",
        ),
        (
            "mb_releasetrackid",
            f"library-item:{item_ids[0]}",
            LibraryIdentityWriteKind.ITEM_FIELD,
            item_ids[0],
            "mb_releasetrackid",
        ),
        ("mb_albumid", None, LibraryIdentityWriteKind.ITEM_FIELD, item_ids[1], "mb_albumid"),
        (
            "mb_releasegroupid",
            None,
            LibraryIdentityWriteKind.ITEM_FIELD,
            item_ids[1],
            "mb_releasegroupid",
        ),
        (
            "mb_trackid",
            f"library-item:{item_ids[1]}",
            LibraryIdentityWriteKind.ITEM_FIELD,
            item_ids[1],
            "mb_trackid",
        ),
        (
            "mb_releasetrackid",
            f"library-item:{item_ids[1]}",
            LibraryIdentityWriteKind.ITEM_FIELD,
            item_ids[1],
            "mb_releasetrackid",
        ),
    ]
    assert [change.target_value for change in plan.changes] == [
        mbid(100),
        mbid(200),
        mbid(100),
        mbid(200),
        mbid(1001),
        mbid(2001),
        mbid(100),
        mbid(200),
        mbid(1002),
        mbid(2002),
    ]


def test_mapping_omits_only_database_copies_already_equal_to_canonical_values(
    library: Library,
) -> None:
    album = _add_album(library)
    album.mb_albumid = mbid(100)
    album.store()
    items = tuple(album.items())
    items[0].mb_albumid = mbid(100)
    items[0].mb_releasegroupid = mbid(200)
    items[0].mb_trackid = mbid(1001)
    items[0].mb_releasetrackid = mbid(2001)
    items[0].store()
    items[1].mb_trackid = mbid(1002)
    items[1].store()

    plan = map_library_identity_targets(_audit(library))

    assert [(change.row_id, change.target_field) for change in plan.changes] == [
        (album.id, "mb_releasegroupid"),
        (items[1].id, "mb_releasegroupid"),
        (items[1].id, "mb_releasetrackid"),
    ]


def test_singleton_mapping_writes_all_four_item_fields(library: Library) -> None:
    item = _add_singleton(library)
    audit = _audit(library, candidate(1))

    plan = map_library_identity_targets(audit)

    assert [(change.write_kind, change.row_id, change.target_field) for change in plan.changes] == [
        (LibraryIdentityWriteKind.ITEM_FIELD, item.id, "mb_albumid"),
        (LibraryIdentityWriteKind.ITEM_FIELD, item.id, "mb_releasegroupid"),
        (LibraryIdentityWriteKind.ITEM_FIELD, item.id, "mb_trackid"),
        (LibraryIdentityWriteKind.ITEM_FIELD, item.id, "mb_releasetrackid"),
    ]
    assert [change.target_value for change in plan.changes] == [
        mbid(100),
        mbid(200),
        mbid(1001),
        mbid(2001),
    ]


def test_confirmed_ambiguous_and_non_ready_audits_are_noops(library: Library) -> None:
    album = _add_album(library)
    album.mb_albumid = mbid(100)
    album.mb_releasegroupid = mbid(200)
    album.store()
    for index, item in enumerate(album.items(), start=1):
        item.mb_albumid = mbid(100)
        item.mb_releasegroupid = mbid(200)
        item.mb_trackid = mbid(1000 + index)
        item.mb_releasetrackid = mbid(2000 + index)
        item.store()
    confirmed = _audit(library)
    ambiguous = replace(
        confirmed, audit=replace(confirmed.audit, verdict=IdentityVerdict.AMBIGUOUS)
    )
    non_ready = replace(
        confirmed,
        audit=replace(
            confirmed.audit,
            verdict=IdentityVerdict.CONFLICT,
            repair_ready=False,
        ),
    )

    assert confirmed.audit.verdict is IdentityVerdict.CONFIRMED
    assert map_library_identity_targets(confirmed).changes == ()
    assert map_library_identity_targets(ambiguous).changes == ()
    assert map_library_identity_targets(non_ready).changes == ()


@pytest.mark.parametrize(
    ("field", "scope", "message"),
    [
        ("unsupported", None, "field is unknown"),
        ("mb_albumid", "library-item:1", "track scope"),
        ("mb_trackid", None, "scope is unresolved"),
        ("mb_releasetrackid", "absent", "scope is unresolved"),
    ],
)
def test_mapping_rejects_unknown_fields_and_invalid_scopes(
    library: Library, field: str, scope: str | None, message: str
) -> None:
    _add_album(library)
    audit = _audit(library)
    malformed_audit = replace(
        audit.audit,
        field_findings=(replace(audit.audit.field_findings[0], field=field, scope_key=scope),),
    )

    with pytest.raises(LibraryIdentityMappingError, match=message):
        map_library_identity_targets(replace(audit, audit=malformed_audit))


def test_mapping_rejects_noncanonical_values_statuses_and_sources(
    library: Library,
) -> None:
    _add_album(library)
    audit = _audit(library)
    uppercase = replace(
        audit.audit,
        field_findings=(
            replace(audit.audit.field_findings[0], expected_value=mbid(0xABCDEF).upper()),
        ),
    )
    bad_status = replace(
        audit.audit,
        field_findings=(replace(audit.audit.field_findings[0], status="missing"),),
    )

    with pytest.raises(LibraryIdentityMappingError, match="not a canonical UUID"):
        map_library_identity_targets(replace(audit, audit=uppercase))
    with pytest.raises(LibraryIdentityMappingError, match="status is invalid"):
        map_library_identity_targets(replace(audit, audit=bad_status))
    with pytest.raises(LibraryIdentityMappingError, match="source is invalid"):
        map_library_identity_targets(cast(Any, object()))


def test_mapping_rejects_duplicate_and_incomplete_repair_ready_findings(
    library: Library,
) -> None:
    _add_album(library)
    audit = _audit(library)
    duplicate = replace(
        audit.audit,
        field_findings=(audit.audit.field_findings[0],) * 2,
    )
    incomplete = replace(audit.audit, field_findings=audit.audit.field_findings[:-1])

    with pytest.raises(LibraryIdentityMappingError, match="finding is duplicated"):
        map_library_identity_targets(replace(audit, audit=duplicate))
    with pytest.raises(LibraryIdentityMappingError, match="track identity finding is missing"):
        map_library_identity_targets(replace(audit, audit=incomplete))


def test_mapping_rejects_repair_ready_plan_with_no_differing_rows(
    library: Library,
) -> None:
    album = _add_album(library)
    album.mb_albumid = mbid(100)
    album.mb_releasegroupid = mbid(200)
    album.store()
    for index, item in enumerate(album.items(), start=1):
        item.mb_albumid = mbid(100)
        item.mb_releasegroupid = mbid(200)
        item.mb_trackid = mbid(1000 + index)
        item.mb_releasetrackid = mbid(2000 + index)
        item.store()
    audit = _audit(library)
    forged = replace(
        audit,
        audit=replace(
            audit.audit,
            verdict=IdentityVerdict.CONFLICT,
            repair_ready=True,
            field_findings=tuple(
                replace(finding, status=IdentityFieldStatus.CONFLICT)
                for finding in audit.audit.field_findings
            ),
        ),
    )

    with pytest.raises(LibraryIdentityMappingError, match="no differing database row"):
        map_library_identity_targets(forged)


def test_plan_source_changes_and_candidate_inputs_are_immutable(library: Library) -> None:
    _add_album(library)
    candidate_tracks = (
        candidate_track(1, recording=mbid(5000)),
        candidate_track(2, recording=mbid(5000)),
    )
    audit = _audit(library, candidate(2, tracks=candidate_tracks))
    plan = map_library_identity_targets(audit)

    assert isinstance(plan, LibraryIdentityTargetPlan)
    assert isinstance(plan.changes, tuple)
    assert [
        change.target_value for change in plan.changes if change.target_field == "mb_trackid"
    ] == [mbid(5000), mbid(5000)]
    with pytest.raises(FrozenInstanceError):
        plan.changes = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        plan.changes[0].target_value = mbid(9999)  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        audit.audit.field_findings[0].expected_value = mbid(9999)  # type: ignore[misc]
