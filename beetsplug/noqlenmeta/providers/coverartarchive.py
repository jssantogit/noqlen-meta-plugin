"""Exact Cover Art Archive metadata boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests

_BASE_URL = "https://coverartarchive.org"
_TIMEOUT = (5.0, 15.0)


class CoverArtArchiveError(RuntimeError):
    """Base error for the Cover Art Archive boundary."""


class CoverArtArchiveUnavailable(CoverArtArchiveError):
    """The Cover Art Archive could not provide a trustworthy response."""


class CoverArtArchiveClient:
    """Fetch exact CAA metadata without downloading image bytes."""

    def __init__(self, *, session: Any | None = None) -> None:
        self._session = session or requests.Session()

    def get_release(self, release_mbid: str) -> Mapping[str, object] | None:
        return self._get(f"{_BASE_URL}/release/{release_mbid}")

    def get_release_group(self, release_group_mbid: str) -> Mapping[str, object] | None:
        return self._get(f"{_BASE_URL}/release-group/{release_group_mbid}")

    def _get(self, url: str) -> Mapping[str, object] | None:
        try:
            response = self._session.get(url, timeout=_TIMEOUT)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError, TypeError) as error:
            raise CoverArtArchiveUnavailable("Cover Art Archive request unavailable") from error

        if not isinstance(payload, Mapping):
            raise CoverArtArchiveUnavailable("Cover Art Archive returned invalid JSON")
        images = payload.get("images")
        release = payload.get("release")
        if not isinstance(images, list) or not isinstance(release, str):
            raise CoverArtArchiveUnavailable("Cover Art Archive returned invalid metadata")
        return payload
