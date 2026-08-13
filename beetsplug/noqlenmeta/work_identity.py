"""Canonical Recording-to-Work relationship identity."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from beetsplug.noqlenmeta.domain import canonical_uuid


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class WorkReference:
    """One exact structured Recording-to-Work relationship."""

    mbid: str
    title: str | None
    relation_type: str
    relation_type_id: str | None
    attributes: tuple[str, ...] = ()
    ordering_key: int | None = None

    def __post_init__(self) -> None:
        mbid = canonical_uuid(self.mbid)
        if mbid is None:
            raise ValueError("Work MBID must be a UUID")
        object.__setattr__(self, "mbid", mbid)
        if self.title is not None:
            object.__setattr__(self, "title", _text(self.title, "Work title"))
        object.__setattr__(
            self,
            "relation_type",
            _text(self.relation_type, "Work relation type"),
        )
        if self.relation_type_id is not None:
            relation_type_id = canonical_uuid(self.relation_type_id)
            if relation_type_id is None:
                raise ValueError("Work relation type ID must be a UUID")
            object.__setattr__(self, "relation_type_id", relation_type_id)
        attributes = tuple(_text(value, "Work relation attribute") for value in self.attributes)
        object.__setattr__(self, "attributes", attributes)
        if self.ordering_key is not None and (
            isinstance(self.ordering_key, bool)
            or not isinstance(self.ordering_key, int)
            or self.ordering_key < 0
        ):
            raise ValueError("Work ordering key must be a non-negative integer")


def canonical_work_references(values: Iterable[WorkReference]) -> tuple[WorkReference, ...]:
    """Deduplicate relation/Work pairs and return a provider-order-independent tuple."""
    references = tuple(values)
    if not all(isinstance(value, WorkReference) for value in references):
        raise TypeError("Work references must contain WorkReference values")
    unique: dict[tuple[str, str, str | None], WorkReference] = {}
    for reference in sorted(references, key=_work_key):
        key = (reference.mbid, reference.relation_type, reference.relation_type_id)
        unique.setdefault(key, reference)
    return tuple(sorted(unique.values(), key=_work_key))


def _work_key(reference: WorkReference) -> tuple[object, ...]:
    return (
        reference.ordering_key is None,
        reference.ordering_key if reference.ordering_key is not None else 0,
        reference.mbid,
        reference.relation_type_id or "",
        reference.relation_type,
        reference.title or "",
        reference.attributes,
    )
