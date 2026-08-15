from __future__ import annotations

import logging

import pytest


@pytest.fixture(autouse=True)
def propagate_beets_logs_for_capture(request: pytest.FixtureRequest) -> object:
    """Let pytest's root handler capture beets logs without changing production."""
    if "caplog" not in request.fixturenames:
        yield
        return
    logger = logging.getLogger("beets")
    original = logger.propagate
    logger.propagate = True
    yield
    logger.propagate = original
