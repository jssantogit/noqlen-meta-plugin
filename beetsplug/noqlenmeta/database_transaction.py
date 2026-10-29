"""Explicit SQLite savepoint for multi-model beets application.

beets dbcore.Transaction's root exit may commit even when the context exits
with an exception. An outer Library.transaction() alone is not a rollback
guarantee for writes that cross Model.store() and plugin-owned SQL.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from beets.library import Library


@contextmanager
def atomic_credit_application(library: Library) -> Iterator[None]:
    """Keep native model and structured-credit writes in one rollback unit."""
    with library.transaction() as tx:
        tx.mutate("SAVEPOINT noqlenmeta_credit_application")
        try:
            yield
        except BaseException:
            tx.mutate("ROLLBACK TO SAVEPOINT noqlenmeta_credit_application")
            tx.mutate("RELEASE SAVEPOINT noqlenmeta_credit_application")
            raise
        else:
            tx.mutate("RELEASE SAVEPOINT noqlenmeta_credit_application")
