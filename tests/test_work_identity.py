from itertools import permutations

import pytest

from beetsplug.noqlenmeta.work_identity import (
    WorkReference,
    canonical_work_references,
)

WORK_1 = "12345678-1234-5678-9234-567812345678"
WORK_2 = "22345678-1234-5678-9234-567812345678"


def work(mbid: str = WORK_1, **changes: object) -> WorkReference:
    values = {
        "mbid": mbid,
        "title": "Synthetic Work",
        "relation_type": "performance",
        "relation_type_id": "a3005666-a872-32c3-ad06-98af558e99b0",
        "attributes": ("live",),
        "ordering_key": None,
    }
    values.update(changes)
    return WorkReference(**values)  # type: ignore[arg-type]


def test_work_reference_canonicalizes_uuid_and_preserves_relation_data() -> None:
    reference = work(mbid=WORK_1.upper(), title="  Synthetic Work  ")

    assert reference == work()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mbid", "not-a-uuid"),
        ("title", " "),
        ("relation_type", " "),
        ("relation_type_id", "not-a-uuid"),
        ("attributes", ("",)),
        ("ordering_key", -1),
    ],
)
def test_work_reference_rejects_malformed_values(field: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        work(**{field: value})


def test_work_reference_deduplication_and_order_are_deterministic() -> None:
    first = work(WORK_1)
    ordered = work(WORK_2, ordering_key=1)
    duplicates = [first, ordered, first]

    results = {canonical_work_references(order) for order in permutations(duplicates)}

    assert results == {(ordered, first)}


def test_distinct_relations_to_same_work_are_preserved() -> None:
    performance = work()
    medley = work(relation_type="medley", attributes=())

    assert canonical_work_references((performance, medley)) == (medley, performance)
