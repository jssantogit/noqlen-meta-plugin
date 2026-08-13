import pytest

from beetsplug.noqlenmeta.field_contracts import PartialDate
from beetsplug.noqlenmeta.release_catalog import (
    ReleaseSecondaryType,
    ReleaseStatus,
    ReleaseType,
    compatible_partial_dates,
    normalize_edition,
    normalize_release_secondary_types,
    normalize_release_status,
    normalize_release_type,
    parse_partial_date,
    prefer_precise_date,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2020", PartialDate(2020)),
        ("2020-05", PartialDate(2020, 5)),
        ("2020-05-17", PartialDate(2020, 5, 17)),
        ("2020-??-??", PartialDate(2020)),
        ("2020-05-??", PartialDate(2020, 5)),
    ],
)
def test_parse_partial_date_preserves_real_precision(value: str, expected: PartialDate) -> None:
    assert parse_partial_date(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "2020-??",
        "2020-??-17",
        "2020-02-30",
        "2020-13-01",
        "0000",
        "2020-1-01",
        "2020-01-1",
        "2020-01-01T00:00:00Z",
        2020,
    ],
)
def test_parse_partial_date_rejects_malformed_or_impossible_values(value: object) -> None:
    assert parse_partial_date(value) is None


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (PartialDate(2020), PartialDate(2020, 5)),
        (PartialDate(2020, 5), PartialDate(2020, 5, 17)),
        (PartialDate(2020), PartialDate(2020, 5, 17)),
    ],
)
def test_partial_dates_with_agreeing_known_components_are_compatible(
    left: PartialDate, right: PartialDate
) -> None:
    assert compatible_partial_dates(left, right)
    assert prefer_precise_date(left, right) == right
    assert prefer_precise_date(right, left) == right


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (PartialDate(2020), PartialDate(2021)),
        (PartialDate(2020, 4), PartialDate(2020, 5)),
        (PartialDate(2020, 5, 16), PartialDate(2020, 5, 17)),
    ],
)
def test_partial_dates_with_conflicting_known_components_are_incompatible(
    left: PartialDate, right: PartialDate
) -> None:
    assert not compatible_partial_dates(left, right)
    assert prefer_precise_date(left, right) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Album", ReleaseType.ALBUM),
        ("EP", ReleaseType.EP),
        ("Single", ReleaseType.SINGLE),
        ("Broadcast", ReleaseType.BROADCAST),
        ("Other", ReleaseType.OTHER),
    ],
)
def test_musicbrainz_primary_release_types_are_controlled(
    value: str, expected: ReleaseType
) -> None:
    assert normalize_release_type(value) is expected


def test_unknown_primary_release_type_is_not_invented() -> None:
    assert normalize_release_type("Mixtape") is None
    assert normalize_release_type(1) is None


def test_secondary_release_types_are_ordered_and_deduplicated() -> None:
    assert normalize_release_secondary_types(
        ["Live", "Compilation", "Live", "Unknown", "Remix"]
    ) == (
        ReleaseSecondaryType.LIVE,
        ReleaseSecondaryType.COMPILATION,
        ReleaseSecondaryType.REMIX,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Official", ReleaseStatus.OFFICIAL),
        ("Promotion", ReleaseStatus.PROMOTION),
        ("Bootleg", ReleaseStatus.BOOTLEG),
        ("Pseudo-Release", ReleaseStatus.PSEUDO_RELEASE),
        ("Cancelled", ReleaseStatus.CANCELLED),
        ("Expunged", ReleaseStatus.EXPUNGED),
        ("Withdrawn", ReleaseStatus.WITHDRAWN),
        ("official", ReleaseStatus.OFFICIAL),
        ("PSEUDO-RELEASE", ReleaseStatus.PSEUDO_RELEASE),
    ],
)
def test_musicbrainz_release_status_is_controlled(value: str, expected: ReleaseStatus) -> None:
    assert normalize_release_status(value) is expected


def test_musicbrainz_release_status_contract_is_exact() -> None:
    assert {status.value for status in ReleaseStatus} == {
        "Bootleg",
        "Cancelled",
        "Expunged",
        "Official",
        "Promotion",
        "Pseudo-Release",
        "Withdrawn",
    }


@pytest.mark.parametrize(
    "value",
    [None, 1, "", "Unknown", "Pseudo Release", "Pseudo--Release"],
)
def test_unknown_or_malformed_release_status_is_rejected(value: object) -> None:
    assert normalize_release_status(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Deluxe Edition", "Deluxe Edition"),
        (" limited edition ", "Limited Edition"),
        ("Collector's Edition", "Collector's Edition"),
        ("Anniversary Edition", "Anniversary Edition"),
        ("Expanded Edition", "Expanded Edition"),
    ],
)
def test_controlled_edition_whole_values_normalize(value: str, expected: str) -> None:
    assert normalize_edition(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "Remastered",
        "Reissue",
        "180g",
        "Gatefold",
        "Mono",
        "Deluxe Edition Remastered",
        "Album (Deluxe Edition)",
        "Special",
        "",
    ],
)
def test_edition_does_not_infer_from_unsupported_or_composite_text(value: str) -> None:
    assert normalize_edition(value) is None
