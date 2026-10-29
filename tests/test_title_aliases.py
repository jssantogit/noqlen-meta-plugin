"""V3 exact-recording alias records, preserving locale/type without retagging."""

from pathlib import Path

import pytest
from beets.library import Item, Library

from beetsplug.noqlenmeta.title_aliases import (
    TitleAlias,
    apply_title_alias_plan,
    parse_recording_aliases,
    plan_title_aliases,
    read_title_aliases,
)

RECORDING = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def target(tmp_path: Path) -> tuple[Library, Item]:
    library = Library(str(tmp_path / "library.db"), set_music_dir=False)
    item = Item(
        path=str(tmp_path / "track.flac").encode(),
        artist="Synthetic Artist",
        title="Original Title",
        mb_trackid=RECORDING,
    )
    library.add(item)
    return library, item


def aliases() -> tuple[TitleAlias, ...]:
    return (
        TitleAlias("Título localizado", "pt-BR", "Recording name", "musicbrainz", RECORDING),
        TitleAlias("Synthetic transliteration", "en", "Transliteration", "musicbrainz", RECORDING),
    )


def test_parse_aliases_preserves_type_and_locale_without_replacing_title() -> None:
    parsed = parse_recording_aliases({
        "id": RECORDING,
        "title": "Original Title",
        "aliases": [
            {"name": "Título localizado", "locale": "pt-BR", "type": "Recording name"},
            {"name": "Synthetic transliteration", "locale": "en", "type": "Transliteration"},
            {"name": "Original Title", "locale": "en", "type": "Recording name"},
            {"name": "search hint", "type": "Search hint"},
            {"name": "   "},
        ],
    }, RECORDING)
    assert parsed == aliases()


def test_read_without_alias_tables_is_non_mutating(target: tuple[Library, Item]) -> None:
    library, item = target
    assert read_title_aliases(library, item.id) == ()
    with library.transaction() as tx:
        rows = tx.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='noqlenmeta_title_alias'"
        )
    assert rows == []


def test_apply_structured_aliases_preserves_native_title_and_duplicates(
    target: tuple[Library, Item],
) -> None:
    library, item = target
    plan = plan_title_aliases(library, item, aliases())
    assert plan.status == "PROPOSE"
    assert read_title_aliases(library, item.id) == ()

    outcome = apply_title_alias_plan(library, plan)
    assert outcome.stored == 2
    assert read_title_aliases(library, item.id) == aliases()
    assert library.get_item(item.id).title == "Original Title"
    assert plan_title_aliases(library, item, aliases()).status == "KEEP"


def test_new_aliases_append_without_deleting_existing(
    target: tuple[Library, Item],
) -> None:
    library, item = target
    apply_title_alias_plan(library, plan_title_aliases(library, item, aliases()[:1]))
    result = apply_title_alias_plan(library, plan_title_aliases(library, item, aliases()))
    assert result.stored == 1
    assert read_title_aliases(library, item.id) == aliases()


def test_stale_recording_identity_blocks_alias_application(
    target: tuple[Library, Item],
) -> None:
    library, item = target
    plan = plan_title_aliases(library, item, aliases())
    item.mb_trackid = "22222222-2222-4222-8222-222222222222"
    item.store()
    result = apply_title_alias_plan(library, plan)
    assert result.status == "BLOCKED"
    assert read_title_aliases(library, item.id) == ()


def test_wrong_recording_evidence_is_withheld(
    target: tuple[Library, Item],
) -> None:
    library, item = target
    unrelated = TitleAlias(
        "Wrong edition", "pt-BR", "Recording name", "musicbrainz",
        "22222222-2222-4222-8222-222222222222"
    )
    assert plan_title_aliases(library, item, (unrelated,)).status == "BLOCKED"


def test_proposed_aliases_are_not_written_without_apply(
    target: tuple[Library, Item],
) -> None:
    library, item = target
    plan = plan_title_aliases(library, item, aliases())
    assert plan.status == "PROPOSE"
    assert read_title_aliases(library, item.id) == ()


def test_duplicate_text_with_distinct_locale_remains_distinct(
    target: tuple[Library, Item],
) -> None:
    library, item = target
    records = (
        TitleAlias("Common Name", "en", "Recording name", "musicbrainz", RECORDING),
        TitleAlias("Common Name", "pt-BR", "Recording name", "musicbrainz", RECORDING),
    )
    apply_title_alias_plan(library, plan_title_aliases(library, item, records))
    assert set(read_title_aliases(library, item.id)) == set(records)
