"""Tests for the SQLite rollback boundary used by beets/Noqlen writes."""

import pytest
from beets.library import Library

from beetsplug.noqlenmeta.database_transaction import atomic_credit_application


def test_savepoint_undoes_completed_nested_transactions_on_failure() -> None:
    library = Library(":memory:", set_music_dir=False)
    with library.transaction() as tx:
        tx.mutate("CREATE TABLE noqlenmeta_test_atomic (value TEXT NOT NULL)")
        tx.mutate("INSERT INTO noqlenmeta_test_atomic VALUES ('before')")

    with pytest.raises(RuntimeError, match="abort"):
        with atomic_credit_application(library):
            with library.transaction() as tx:
                tx.mutate("INSERT INTO noqlenmeta_test_atomic VALUES ('during')")
            raise RuntimeError("abort")

    with library.transaction() as tx:
        rows = tx.query("SELECT value FROM noqlenmeta_test_atomic ORDER BY rowid")
    assert [row["value"] for row in rows] == ["before"]


def test_savepoint_commits_successful_nested_writes() -> None:
    library = Library(":memory:", set_music_dir=False)
    with library.transaction() as tx:
        tx.mutate("CREATE TABLE noqlenmeta_test_atomic (value TEXT NOT NULL)")

    with atomic_credit_application(library):
        with library.transaction() as tx:
            tx.mutate("INSERT INTO noqlenmeta_test_atomic VALUES ('success')")

    with library.transaction() as tx:
        rows = tx.query("SELECT value FROM noqlenmeta_test_atomic")
    assert [row["value"] for row in rows] == ["success"]
