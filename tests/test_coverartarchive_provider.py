from collections.abc import Mapping

import pytest
import requests

from beetsplug.noqlenmeta.providers.coverartarchive import (
    CoverArtArchiveClient,
    CoverArtArchiveUnavailable,
)


class Response:
    def __init__(self, status_code: int, payload: object = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self) -> object:
        return self._payload


class Session:
    def __init__(self, response: Response | Exception) -> None:
        self.response = response
        self.calls: list[tuple[str, object]] = []

    def get(self, url: str, *, timeout: object) -> Response:
        self.calls.append((url, timeout))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_client_requests_exact_release_with_finite_timeout() -> None:
    payload = {"images": [], "release": "https://musicbrainz.org/release/release-id"}
    session = Session(Response(200, payload))

    result = CoverArtArchiveClient(session=session).get_release("release-id")

    assert result == payload
    assert session.calls == [
        ("https://coverartarchive.org/release/release-id", (5.0, 15.0))
    ]


def test_client_maps_404_to_definitive_absence() -> None:
    session = Session(Response(404))

    assert CoverArtArchiveClient(session=session).get_release_group("group-id") is None


@pytest.mark.parametrize(
    "response",
    [Response(500), requests.Timeout("slow"), Response(200, []), Response(200, {"images": []})],
)
def test_client_maps_transient_or_invalid_responses_to_unavailable(
    response: Response | Exception,
) -> None:
    client = CoverArtArchiveClient(session=Session(response))

    with pytest.raises(CoverArtArchiveUnavailable):
        client.get_release("release-id")


def test_client_returns_mapping_without_extracting_binary_content() -> None:
    payload: Mapping[str, object] = {
        "images": [{"front": True, "approved": True, "image": "https://example.test/a.jpg"}],
        "release": "https://musicbrainz.org/release/release-id",
    }

    assert CoverArtArchiveClient(session=Session(Response(200, payload))).get_release(
        "release-id"
    ) is payload
