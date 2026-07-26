"""Boundary implemented by production metadata providers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from beetsplug.noqlenmeta.domain import MetadataCandidate, ReleaseEnrichmentContext


class ProviderError(RuntimeError):
    """A provider operation failed at its external-service boundary."""


@runtime_checkable
class MetadataProvider(Protocol):
    """Synchronous contract for a normalized metadata provider adapter."""

    name: str

    def get_candidates(
        self, context: ReleaseEnrichmentContext
    ) -> Sequence[MetadataCandidate]:
        """Return normalized field candidates for an identified release."""
        ...
