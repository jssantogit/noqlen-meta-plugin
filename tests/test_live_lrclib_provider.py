import os

import pytest

from beetsplug.noqlenmeta.domain import TrackEnrichmentContext
from beetsplug.noqlenmeta.providers.lrclib import LRCLIBProvider


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("NOQLEN_LIVE_TESTS") != "1",
    reason="set NOQLEN_LIVE_TESTS=1 to contact LRCLIB",
)
def test_live_documented_exact_signature_lookup() -> None:
    context = TrackEnrichmentContext(
        artist="Powfu",
        title="death bed (coffee for your head)",
        album_title="Some Boring Love Stories, Pt. 2",
        duration=173.0,
    )

    candidates = LRCLIBProvider().get_candidates(context)

    assert candidates
    assert all(candidate.provider == "lrclib" for candidate in candidates)
    assert all(candidate.source_id for candidate in candidates)
    assert {candidate.field for candidate in candidates} <= {"lyrics", "synced_lyrics"}
    assert all(isinstance(candidate.value, str) and candidate.value for candidate in candidates)
