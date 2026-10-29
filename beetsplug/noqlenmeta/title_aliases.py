"""V3 lossless structured Recording title aliases in plugin-owned SQLite state.

No native title changes, string flattening, file tags, or identity repair.
Only exact MusicBrainz Recording aliases may contribute. State is additive,
owner-scoped, and guarded by a snapshot of the library Item.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from beets.library import Item, Library

from beetsplug.noqlenmeta.database_transaction import atomic_credit_application
from beetsplug.noqlenmeta.domain import canonical_uuid

_LOCALE = re.compile(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
_CREATE = """CREATE TABLE IF NOT EXISTS noqlenmeta_title_alias (
    item_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    recording_mbid TEXT NOT NULL,
    provider TEXT NOT NULL,
    alias_text TEXT NOT NULL,
    locale TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    sort_name TEXT,
    is_primary INTEGER,
    script TEXT,
    PRIMARY KEY (item_id, recording_mbid, provider, alias_text, locale, alias_type)
)"""


@dataclass(frozen=True, slots=True)
class TitleAlias:
    text: str
    locale: str
    alias_type: str
    provider: str
    source_id: str
    sort_name: str | None = None
    primary: bool | None = None
    script: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("title alias requires non-empty text")
        if canonical_uuid(self.source_id) is None:
            raise ValueError("title alias must refer to an exact Recording MBID")
        if self.provider != "musicbrainz":
            raise ValueError("title alias source must be musicbrainz")
        if self.locale and _LOCALE.fullmatch(self.locale) is None:
            raise ValueError("title alias locale is invalid")
        if not isinstance(self.alias_type, str):
            raise ValueError("title alias type must be text")
        if self.sort_name is not None and not isinstance(self.sort_name, str):
            raise ValueError("title alias sort name is invalid")
        if self.primary is not None and type(self.primary) is not bool:
            raise ValueError("title alias primary flag is invalid")
        if self.script is not None and not isinstance(self.script, str):
            raise ValueError("title alias script is invalid")
        object.__setattr__(self, "text", self.text.strip())
        object.__setattr__(self, "source_id", canonical_uuid(self.source_id))
        object.__setattr__(self, "alias_type", self.alias_type.strip())


@dataclass(frozen=True, slots=True)
class TitleAliasPlan:
    item_id: int
    recording_mbid: str
    audio_path: bytes
    original_title: str
    before: tuple[TitleAlias, ...]
    additions: tuple[TitleAlias, ...]
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class TitleAliasResult:
    item_id: int
    status: str
    stored: int = 0
    reason: str = ""


def parse_recording_aliases(payload: object, recording_mbid: str) -> tuple[TitleAlias, ...]:
    """Keep explicit names/locale/type from a validated Recording response."""
    if not isinstance(payload, dict) or canonical_uuid(payload.get("id")) != canonical_uuid(
        recording_mbid
    ):
        return ()
    raw = payload.get("aliases")
    if not isinstance(raw, list):
        return ()
    native = payload.get("title")
    original = native.strip().casefold() if isinstance(native, str) else ""
    aliases: list[TitleAlias] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        if name.strip().casefold() == original:
            continue
        alias_type = row.get("type")
        if alias_type is not None and not isinstance(alias_type, str):
            continue
        kind = alias_type.strip() if isinstance(alias_type, str) else ""
        if kind.casefold() == "search hint":
            continue
        locale = row.get("locale")
        if locale is None:
            locale = ""
        if not isinstance(locale, str) or (locale and not _LOCALE.fullmatch(locale)):
            continue
        sort_name = row.get("sort-name")
        if sort_name is not None and not isinstance(sort_name, str):
            continue
        primary = row.get("primary")
        if primary is not None and type(primary) is not bool:
            continue
        script = next(
            (part for part in locale.split("-")[1:] if len(part) == 4 and part.isalpha()),
            None,
        )
        try:
            alias = TitleAlias(
                name, locale, kind, "musicbrainz", recording_mbid,
                sort_name, primary, script,
            )
        except ValueError:
            continue
        if alias not in aliases:
            aliases.append(alias)
    return tuple(aliases)


def read_title_aliases(library: Library, item_id: int) -> tuple[TitleAlias, ...]:
    """Read structured state without creating a table on preview."""
    if type(item_id) is not int or item_id <= 0:
        raise ValueError("title alias owner requires a persisted Item ID")
    with library.transaction() as tx:
        if not tx.query(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='noqlenmeta_title_alias'"
        ):
            return ()
        rows = tx.query(
            "SELECT * FROM noqlenmeta_title_alias "
            "WHERE item_id=? ORDER BY ordinal, alias_text",
            (item_id,),
        )
    return tuple(
        TitleAlias(
            row["alias_text"], row["locale"], row["alias_type"],
            row["provider"], row["recording_mbid"], row["sort_name"],
            bool(row["is_primary"]) if row["is_primary"] is not None else None,
            row["script"],
        )
        for row in rows
    )


def plan_title_aliases(
    library: Library, item: Item, candidates: tuple[TitleAlias, ...]
) -> TitleAliasPlan:
    if not isinstance(item.id, int) or not isinstance(item.path, bytes):
        raise ValueError("title aliases require a persisted library Item")
    recording_id = canonical_uuid(item.get("mb_trackid"))
    previous = read_title_aliases(library, item.id)
    wanted = tuple(dict.fromkeys(candidates))
    if recording_id is None:
        status, reason = "BLOCKED", "library Item lacks an exact Recording MBID"
    elif any(
        alias.provider != "musicbrainz" or alias.source_id != recording_id
        for alias in wanted
    ):
        status, reason = "BLOCKED", "title alias identity does not match library Item"
    else:
        status, reason = "PROPOSE", "add structured exact-recording aliases"
    additions = tuple(value for value in wanted if value not in previous)
    if not wanted and status == "PROPOSE":
        status, reason = "NO_EVIDENCE", "no eligible exact-recording aliases"
    elif not additions and status == "PROPOSE":
        status, reason = "KEEP", "all structured aliases are already present"
    return TitleAliasPlan(
        item.id, recording_id or "", item.path, item.title,
        previous, additions, status, reason,
    )


def apply_title_alias_plan(library: Library, plan: TitleAliasPlan) -> TitleAliasResult:
    if plan.status != "PROPOSE":
        return TitleAliasResult(plan.item_id, plan.status, reason=plan.reason)
    fresh = library.get_item(plan.item_id)
    if (
        fresh is None
        or fresh.path != plan.audio_path
        or fresh.title != plan.original_title
        or canonical_uuid(fresh.get("mb_trackid")) != plan.recording_mbid
    ):
        return TitleAliasResult(plan.item_id, "BLOCKED", reason="library identity changed")
    if read_title_aliases(library, plan.item_id) != plan.before:
        return TitleAliasResult(plan.item_id, "BLOCKED", reason="structured alias state changed")
    with atomic_credit_application(library):
        with library.transaction() as tx:
            tx.mutate(_CREATE)
            row = tx.query(
                "SELECT COALESCE(MAX(ordinal), -1) AS n FROM noqlenmeta_title_alias "
                "WHERE item_id=?",
                (plan.item_id,),
            )
            ordinal = row[0]["n"] + 1
            for alias in plan.additions:
                tx.mutate(
                    "INSERT INTO noqlenmeta_title_alias "
                    "(item_id, ordinal, recording_mbid, provider, alias_text, "
                    "locale, alias_type, sort_name, is_primary, script) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        plan.item_id, ordinal, alias.source_id, alias.provider,
                        alias.text, alias.locale, alias.alias_type,
                        alias.sort_name, alias.primary, alias.script,
                    ),
                )
                ordinal += 1
    return TitleAliasResult(plan.item_id, "COMMITTED", len(plan.additions))
