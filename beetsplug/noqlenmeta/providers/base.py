"""Boundary implemented by production metadata providers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from beetsplug.noqlenmeta.domain import (
    ArtistEnrichmentContext,
    MetadataCandidate,
    ReleaseEnrichmentContext,
    TrackEnrichmentContext,
)
from beetsplug.noqlenmeta.evidence import MetadataEvidence


class ProviderError(RuntimeError):
    """A provider operation failed at its external-service boundary."""


class ProviderContractError(RuntimeError):
    """A provider adapter violated its internal candidate output contract."""


@dataclass(frozen=True, slots=True)
class ReleaseProviderEnrichment:
    """V2 candidates and V3 evidence acquired from one concrete release response."""

    candidates: tuple[MetadataCandidate, ...] = ()
    evidence: tuple[MetadataEvidence, ...] = ()


@runtime_checkable
class ReleaseMetadataProvider(Protocol):
    """Synchronous contract for a normalized release metadata provider."""

    name: str
    supported_fields: frozenset[str]

    def get_candidates(
        self, context: ReleaseEnrichmentContext
    ) -> Sequence[MetadataCandidate]:
        """Return normalized field candidates for an identified release."""
        ...


@runtime_checkable
class TrackMetadataProvider(Protocol):
    """Synchronous contract for a normalized track metadata provider."""

    name: str
    supported_fields: frozenset[str]

    def get_candidates(
        self, context: TrackEnrichmentContext
    ) -> Sequence[MetadataCandidate]:
        """Return normalized field candidates for an identified track."""
        ...


@runtime_checkable
class ArtistMetadataProvider(Protocol):
    """Synchronous contract for a normalized artist metadata provider."""

    name: str
    supported_fields: frozenset[str]

    def get_candidates(
        self, context: ArtistEnrichmentContext
    ) -> Sequence[MetadataCandidate]:
        """Return normalized field candidates for an identified artist."""
        ...
