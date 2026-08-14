"""Plugin-owned structured credit state inside the active beets library."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from beets.library import Library

from beetsplug.noqlenmeta.changeplan import PlannedChange
from beetsplug.noqlenmeta.credits import (
    ArtistCredit,
    ArtistCreditNode,
    CreditParty,
    CreditReference,
    CreditRole,
    canonical_credit_references,
)
from beetsplug.noqlenmeta.evidence import MetadataEvidence
from beetsplug.noqlenmeta.field_contracts import EntityKind

_SCHEMA_VERSION = 1
_OWNER_KINDS = frozenset({"item", "album"})
_CREDIT_FIELDS = frozenset(
    {
        "composers",
        "lyricists",
        "producers",
        "arrangers",
        "conductors",
        "performers",
        "featured_artists",
    }
)

_CREATE_SQL = (
    "CREATE TABLE IF NOT EXISTS noqlenmeta_credit_schema (version INTEGER NOT NULL)",
    """CREATE TABLE IF NOT EXISTS noqlenmeta_credit (
        owner_kind TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        field TEXT NOT NULL,
        relation_key TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        role TEXT NOT NULL,
        scope TEXT NOT NULL,
        party_name TEXT NOT NULL,
        party_mbid TEXT,
        credited_as TEXT,
        instrument TEXT,
        relation_type TEXT,
        relation_type_id TEXT,
        source_entity_id TEXT,
        direction TEXT,
        ordering_key INTEGER,
        PRIMARY KEY (owner_kind, owner_id, field, relation_key)
    )""",
    """CREATE TABLE IF NOT EXISTS noqlenmeta_credit_attribute (
        owner_kind TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        field TEXT NOT NULL,
        relation_key TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY (owner_kind, owner_id, field, relation_key, value)
    )""",
    """CREATE TABLE IF NOT EXISTS noqlenmeta_credit_name_variant (
        owner_kind TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        field TEXT NOT NULL,
        relation_key TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY (owner_kind, owner_id, field, relation_key, value)
    )""",
    """CREATE TABLE IF NOT EXISTS noqlenmeta_artist_credit (
        owner_kind TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        field TEXT NOT NULL,
        credit_key TEXT NOT NULL,
        scope TEXT NOT NULL,
        source_entity_id TEXT,
        PRIMARY KEY (owner_kind, owner_id, field, credit_key)
    )""",
    """CREATE TABLE IF NOT EXISTS noqlenmeta_artist_credit_node (
        owner_kind TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        field TEXT NOT NULL,
        credit_key TEXT NOT NULL,
        position INTEGER NOT NULL,
        artist_mbid TEXT NOT NULL,
        canonical_name TEXT NOT NULL,
        credited_name TEXT NOT NULL,
        join_phrase TEXT NOT NULL,
        PRIMARY KEY (owner_kind, owner_id, field, credit_key, position)
    )""",
    """CREATE TABLE IF NOT EXISTS noqlenmeta_credit_provenance (
        owner_kind TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        field TEXT NOT NULL,
        provider TEXT NOT NULL,
        source_id TEXT NOT NULL,
        method TEXT NOT NULL,
        subject_entity TEXT NOT NULL,
        confidence REAL,
        PRIMARY KEY (owner_kind, owner_id, field, provider, source_id, method)
    )""",
)


def read_credit_state(
    library: Library, owner_kind: str, owner_id: int
) -> dict[str, object]:
    """Read accepted structured credits without creating optional tables."""
    _validate_owner(owner_kind, owner_id)
    with library.transaction() as tx:
        if not _tables_exist(tx):
            return {}
        _require_schema_version(tx)
        credit_rows = tx.query(
            """SELECT * FROM noqlenmeta_credit
            WHERE owner_kind=? AND owner_id=? ORDER BY field, ordinal, relation_key""",
            (owner_kind, owner_id),
        )
        attribute_rows = tx.query(
            """SELECT * FROM noqlenmeta_credit_attribute
            WHERE owner_kind=? AND owner_id=? ORDER BY ordinal""",
            (owner_kind, owner_id),
        )
        variant_rows = tx.query(
            """SELECT * FROM noqlenmeta_credit_name_variant
            WHERE owner_kind=? AND owner_id=? ORDER BY ordinal""",
            (owner_kind, owner_id),
        )
        artist_rows = tx.query(
            """SELECT * FROM noqlenmeta_artist_credit
            WHERE owner_kind=? AND owner_id=? ORDER BY field, credit_key""",
            (owner_kind, owner_id),
        )
        node_rows = tx.query(
            """SELECT * FROM noqlenmeta_artist_credit_node
            WHERE owner_kind=? AND owner_id=? ORDER BY field, credit_key, position""",
            (owner_kind, owner_id),
        )
    attributes = _child_values(attribute_rows)
    variants = _child_values(variant_rows)
    grouped: dict[str, list[CreditReference]] = {}
    for row in credit_rows:
        key = (row["field"], row["relation_key"])
        try:
            reference = CreditReference(
                CreditParty(
                    row["party_name"],
                    row["party_mbid"],
                    row["credited_as"],
                    variants.get(key, ()),
                ),
                CreditRole(row["role"]),
                EntityKind(row["scope"]),
                instrument=row["instrument"],
                relation_type=row["relation_type"],
                relation_type_id=row["relation_type_id"],
                source_entity_id=row["source_entity_id"],
                attributes=attributes.get(key, ()),
                direction=row["direction"],
                ordering_key=row["ordering_key"],
            )
        except (TypeError, ValueError):
            continue
        grouped.setdefault(row["field"], []).append(reference)
    result: dict[str, object] = {
        field: canonical_credit_references(references)
        for field, references in grouped.items()
    }
    nodes_by_key: dict[tuple[str, str], list[ArtistCreditNode]] = {}
    for row in node_rows:
        key = (row["field"], row["credit_key"])
        nodes_by_key.setdefault(key, []).append(
            ArtistCreditNode(
                row["artist_mbid"],
                row["canonical_name"],
                row["credited_name"],
                row["join_phrase"],
                row["position"],
            )
        )
    for row in artist_rows:
        key = (row["field"], row["credit_key"])
        nodes = tuple(nodes_by_key.get(key, ()))
        if nodes and row["field"] not in result:
            result[row["field"]] = ArtistCredit(
                EntityKind(row["scope"]), nodes, row["source_entity_id"]
            )
    return result


def apply_credit_state(
    library: Library,
    owner_kind: str,
    owner_id: int,
    changes: Sequence[PlannedChange],
) -> int:
    """Append accepted structured state and provenance; never delete by omission."""
    _validate_owner(owner_kind, owner_id)
    relevant = tuple(
        change
        for change in changes
        if change.field in _CREDIT_FIELDS or change.field == "structured_artist_credits"
    )
    if not relevant:
        return 0
    inserted = 0
    with library.transaction() as tx:
        _ensure_schema(tx)
        for change in relevant:
            if isinstance(change.after, ArtistCredit):
                inserted += _insert_artist_credit(
                    tx, owner_kind, owner_id, change.field, change.after
                )
            elif isinstance(change.after, tuple) and all(
                isinstance(value, CreditReference) for value in change.after
            ):
                for ordinal, reference in enumerate(change.after):
                    inserted += _insert_reference(
                        tx,
                        owner_kind,
                        owner_id,
                        change.field,
                        ordinal,
                        reference,
                    )
            else:
                raise ValueError("credit state change has an unsupported canonical value")
            for item in change.evidence:
                _insert_provenance(tx, owner_kind, owner_id, change.field, item)
    return inserted


def _ensure_schema(tx: object) -> None:
    for statement in _CREATE_SQL:
        tx.mutate(statement)
    rows = tx.query("SELECT version FROM noqlenmeta_credit_schema")
    if not rows:
        tx.mutate("INSERT INTO noqlenmeta_credit_schema (version) VALUES (?)", (_SCHEMA_VERSION,))
    _require_schema_version(tx)


def _tables_exist(tx: object) -> bool:
    rows = tx.query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='noqlenmeta_credit_schema'"
    )
    return bool(rows)


def _require_schema_version(tx: object) -> None:
    rows = tx.query("SELECT version FROM noqlenmeta_credit_schema")
    if len(rows) != 1 or rows[0]["version"] != _SCHEMA_VERSION:
        raise RuntimeError("unsupported Noqlen Meta credit schema version")


def _insert_reference(
    tx: object,
    owner_kind: str,
    owner_id: int,
    field: str,
    ordinal: int,
    reference: CreditReference,
) -> int:
    relation_key = _relation_key(reference)
    before = tx.query(
        """SELECT 1 FROM noqlenmeta_credit
        WHERE owner_kind=? AND owner_id=? AND field=? AND relation_key=?""",
        (owner_kind, owner_id, field, relation_key),
    )
    tx.mutate(
        """INSERT OR IGNORE INTO noqlenmeta_credit VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            owner_kind,
            owner_id,
            field,
            relation_key,
            ordinal,
            reference.role.value,
            reference.scope.value,
            reference.party.name,
            reference.party.mbid,
            reference.party.credited_as,
            reference.instrument,
            reference.relation_type,
            reference.relation_type_id,
            reference.source_entity_id,
            reference.direction,
            reference.ordering_key,
        ),
    )
    for position, value in enumerate(reference.attributes):
        tx.mutate(
            "INSERT OR IGNORE INTO noqlenmeta_credit_attribute VALUES (?, ?, ?, ?, ?, ?)",
            (owner_kind, owner_id, field, relation_key, position, value),
        )
    for position, value in enumerate(reference.party.credited_as_variants):
        tx.mutate(
            "INSERT OR IGNORE INTO noqlenmeta_credit_name_variant VALUES (?, ?, ?, ?, ?, ?)",
            (owner_kind, owner_id, field, relation_key, position, value),
        )
    return 0 if before else 1


def _insert_artist_credit(
    tx: object,
    owner_kind: str,
    owner_id: int,
    field: str,
    credit: ArtistCredit,
) -> int:
    credit_key = _artist_credit_key(credit)
    before = tx.query(
        """SELECT 1 FROM noqlenmeta_artist_credit
        WHERE owner_kind=? AND owner_id=? AND field=? AND credit_key=?""",
        (owner_kind, owner_id, field, credit_key),
    )
    tx.mutate(
        "INSERT OR IGNORE INTO noqlenmeta_artist_credit VALUES (?, ?, ?, ?, ?, ?)",
        (owner_kind, owner_id, field, credit_key, credit.scope.value, credit.source_entity_id),
    )
    for node in credit.nodes:
        tx.mutate(
            """INSERT OR IGNORE INTO noqlenmeta_artist_credit_node
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                owner_kind,
                owner_id,
                field,
                credit_key,
                node.position,
                node.artist_mbid,
                node.canonical_name,
                node.credited_name,
                node.join_phrase,
            ),
        )
    return 0 if before else 1


def _insert_provenance(
    tx: object,
    owner_kind: str,
    owner_id: int,
    field: str,
    item: MetadataEvidence,
) -> None:
    tx.mutate(
        """INSERT OR IGNORE INTO noqlenmeta_credit_provenance
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            owner_kind,
            owner_id,
            field,
            item.provider,
            item.source_id,
            item.provenance.method.value,
            item.subject.entity.value,
            item.confidence,
        ),
    )


def _child_values(rows: Sequence[Mapping[str, object]]) -> dict[tuple[str, str], tuple[str, ...]]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        value = row["value"]
        if isinstance(value, str):
            grouped.setdefault((row["field"], row["relation_key"]), []).append(value)
    return {key: tuple(values) for key, values in grouped.items()}


def _relation_key(reference: CreditReference) -> str:
    return _digest(
        reference.party.mbid or "",
        reference.party.name if reference.party.mbid is None else "",
        reference.role.value,
        reference.scope.value,
        reference.instrument or "",
        reference.source_entity_id or "",
    )


def _artist_credit_key(credit: ArtistCredit) -> str:
    values = [credit.scope.value, credit.source_entity_id or ""]
    for node in credit.nodes:
        values.extend(
            [
                str(node.position),
                node.artist_mbid,
                node.canonical_name,
                node.credited_name,
                node.join_phrase,
            ]
        )
    return _digest(*values)


def _digest(*values: str) -> str:
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _validate_owner(owner_kind: str, owner_id: int) -> None:
    if owner_kind not in _OWNER_KINDS:
        raise ValueError("credit state owner kind must be item or album")
    if isinstance(owner_id, bool) or not isinstance(owner_id, int) or owner_id <= 0:
        raise ValueError("credit state owner ID must be a positive integer")
