import os

import pytest

from beetsplug.noqlenmeta.domain import ExternalIdentifier, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.providers.discogs import DiscogsProvider

PUBLIC_RELEASE_ID = "1"


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("NOQLEN_LIVE_TESTS") != "1",
    reason="set NOQLEN_LIVE_TESTS=1 to contact Discogs",
)
def test_live_direct_release_lookup() -> None:
    context = ReleaseEnrichmentContext(
        album_artist="The Persuader",
        album_title="Stockholm",
        external_ids=(ExternalIdentifier("discogs.release", PUBLIC_RELEASE_ID),),
    )

    candidates = DiscogsProvider().get_candidates(context)

    assert candidates
    assert all(candidate.provider == "discogs" for candidate in candidates)
    assert all(candidate.source_id == PUBLIC_RELEASE_ID for candidate in candidates)
