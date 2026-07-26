import os

import pytest

from beetsplug.noqlenmeta.domain import ExternalIdentifier, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.providers.itunes import ITunesProvider

PUBLIC_COLLECTION_ID = "1097861387"


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("NOQLEN_LIVE_TESTS") != "1",
    reason="set NOQLEN_LIVE_TESTS=1 to contact iTunes",
)
def test_live_direct_collection_lookup() -> None:
    context = ReleaseEnrichmentContext(
        album_artist="Radiohead",
        album_title="OK Computer",
        external_ids=(ExternalIdentifier("itunes.collection", PUBLIC_COLLECTION_ID),),
    )

    candidates = ITunesProvider().get_candidates(context)

    assert candidates
    assert all(candidate.provider == "itunes" for candidate in candidates)
    assert all(candidate.source_id == PUBLIC_COLLECTION_ID for candidate in candidates)
    assert {candidate.field for candidate in candidates} & {"genres", "year"}
