from dataclasses import FrozenInstanceError, replace
from typing import Any, cast

import pytest

from beetsplug.noqlenmeta.identity import (
    IdentityFieldStatus,
    IdentityImportMappingError,
    IdentityImportMatchKind,
    IdentityImportTargetKind,
    IdentityVerdict,
    audit_musicbrainz_identity,
    map_identity_audit_to_import_targets,
)

from .helpers import candidate, context, local_track, mbid


def _audit(*, current: str = "missing", count: int = 2):
    recordings = () if current == "missing" else tuple(mbid(1000 + i) for i in range(1, count + 1))
    release_tracks = (
        () if current == "missing" else tuple(mbid(2000 + i) for i in range(1, count + 1))
    )
    local = context(
        count,
        tracks=tuple(
            local_track(
                i,
                recording=recordings[i - 1] if recordings else None,
                release_track=release_tracks[i - 1] if release_tracks else None,
            )
            for i in range(1, count + 1)
        ),
        release_ids=(mbid(100),) if current == "confirmed" else (),
        release_group_ids=(mbid(200),) if current == "confirmed" else (),
    )
    return audit_musicbrainz_identity(local, (candidate(count),))


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (
            IdentityImportMatchKind.ALBUM,
            [
                ("mb_albumid", None, "album_info_attribute", "album_id"),
                ("mb_releasegroupid", None, "album_info_attribute", "releasegroup_id"),
                ("mb_trackid", "local-1", "track_info_attribute", "track_id"),
                (
                    "mb_releasetrackid",
                    "local-1",
                    "track_info_attribute",
                    "release_track_id",
                ),
                ("mb_trackid", "local-2", "track_info_attribute", "track_id"),
                (
                    "mb_releasetrackid",
                    "local-2",
                    "track_info_attribute",
                    "release_track_id",
                ),
            ],
        ),
        (
            IdentityImportMatchKind.TRACK,
            [
                ("mb_albumid", None, "track_info_item_field", "mb_albumid"),
                ("mb_releasegroupid", None, "track_info_item_field", "mb_releasegroupid"),
                ("mb_trackid", "local-1", "track_info_attribute", "track_id"),
                (
                    "mb_releasetrackid",
                    "local-1",
                    "track_info_attribute",
                    "release_track_id",
                ),
            ],
        ),
    ],
)
def test_maps_all_four_identity_targets_in_audit_order(kind, expected) -> None:
    audit = _audit(count=2 if kind is IdentityImportMatchKind.ALBUM else 1)

    plan = map_identity_audit_to_import_targets(audit, match_kind=kind)

    assert [
        (change.canonical_field, change.scope_key, change.target_kind.value, change.target_field)
        for change in plan.changes
    ] == expected
    assert all(change.before_status is IdentityFieldStatus.MISSING for change in plan.changes)
    assert [change.target_value for change in plan.changes] == [
        finding.expected_value
        for finding in audit.field_findings
        if finding.status is not IdentityFieldStatus.CONFIRMED
    ]


def test_plan_and_changes_are_immutable_tuples() -> None:
    plan = map_identity_audit_to_import_targets(
        _audit(count=1), match_kind=IdentityImportMatchKind.TRACK
    )

    assert isinstance(plan.changes, tuple)
    with pytest.raises(FrozenInstanceError):
        plan.match_kind = IdentityImportMatchKind.ALBUM  # type: ignore[reportAttributeAccessIssue]
    with pytest.raises(FrozenInstanceError):
        plan.changes[0].target_field = "album_id"  # type: ignore[reportAttributeAccessIssue]


def test_confirmed_and_ambiguous_audits_map_to_empty_plans() -> None:
    confirmed = _audit(current="confirmed")
    ambiguous = audit_musicbrainz_identity(context(), ())

    confirmed_plan = map_identity_audit_to_import_targets(
        confirmed, match_kind=IdentityImportMatchKind.ALBUM
    )
    ambiguous_plan = map_identity_audit_to_import_targets(
        ambiguous, match_kind=IdentityImportMatchKind.ALBUM
    )

    assert confirmed.verdict is IdentityVerdict.CONFIRMED
    assert ambiguous.verdict is IdentityVerdict.AMBIGUOUS
    assert confirmed_plan.changes == ambiguous_plan.changes == ()


def test_non_ready_missing_audit_maps_to_an_empty_plan() -> None:
    audit = replace(_audit(), repair_ready=False)

    plan = map_identity_audit_to_import_targets(
        audit, match_kind=IdentityImportMatchKind.ALBUM
    )

    assert audit.verdict is IdentityVerdict.MISSING
    assert plan.changes == ()


@pytest.mark.parametrize(
    ("field", "scope", "message"),
    [
        ("unsupported", None, "unsupported"),
        ("mb_albumid", "local-1", "invalid scope"),
        ("mb_releasegroupid", "local-1", "invalid scope"),
        ("mb_trackid", None, "does not resolve"),
        ("mb_releasetrackid", "absent", "does not resolve"),
    ],
)
def test_rejects_bad_canonical_fields_and_scopes(field, scope, message) -> None:
    audit = _audit(count=1)
    malformed = replace(
        audit,
        field_findings=(replace(audit.field_findings[0], field=field, scope_key=scope),),
    )

    with pytest.raises(IdentityImportMappingError, match=message):
        map_identity_audit_to_import_targets(
            malformed, match_kind=IdentityImportMatchKind.TRACK
        )


def test_rejects_noncanonical_uuid_and_bad_finding_status() -> None:
    audit = _audit(count=1)
    uppercase = replace(
        audit,
        field_findings=(
            replace(audit.field_findings[0], expected_value=mbid(0xABCDEF).upper()),
        ),
    )
    bad_status = replace(
        audit,
        field_findings=(replace(audit.field_findings[0], status="missing"),),
    )

    with pytest.raises(IdentityImportMappingError, match="not canonical"):
        map_identity_audit_to_import_targets(
            uppercase, match_kind=IdentityImportMatchKind.TRACK
        )
    with pytest.raises(IdentityImportMappingError, match="status is unsupported"):
        map_identity_audit_to_import_targets(
            bad_status, match_kind=IdentityImportMatchKind.TRACK
        )


def test_rejects_invalid_source_match_kind_and_inconsistent_noop_policy() -> None:
    confirmed = _audit(current="confirmed")
    invalid = cast(Any, object())

    with pytest.raises(IdentityImportMappingError, match="source is invalid"):
        map_identity_audit_to_import_targets(
            invalid, match_kind=IdentityImportMatchKind.ALBUM
        )
    with pytest.raises(IdentityImportMappingError, match="match kind is invalid"):
        map_identity_audit_to_import_targets(confirmed, match_kind=invalid)
    with pytest.raises(IdentityImportMappingError, match="inconsistent repair policy"):
        map_identity_audit_to_import_targets(
            replace(confirmed, repair_ready=True),
            match_kind=IdentityImportMatchKind.ALBUM,
        )


def test_target_kind_enum_covers_only_the_three_production_surfaces() -> None:
    assert set(IdentityImportTargetKind) == {
        IdentityImportTargetKind.ALBUM_INFO_ATTRIBUTE,
        IdentityImportTargetKind.TRACK_INFO_ATTRIBUTE,
        IdentityImportTargetKind.TRACK_INFO_ITEM_FIELD,
    }
