from collections.abc import Sequence

import pytest

from beetsplug.noqlenmeta.domain import MetadataCandidate, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.providers import MetadataProvider, ProviderError


class SampleProvider:
    name = "sample"
    supported_fields = frozenset({"label"})

    def get_candidates(
        self, context: ReleaseEnrichmentContext
    ) -> Sequence[MetadataCandidate]:
        return (
            MetadataCandidate(
                field="label",
                value=f"{context.album_title} Label",
                provider=self.name,
                confidence=0.8,
                source_id="release-001",
            ),
        )


def test_minimal_provider_implementation_satisfies_runtime_contract() -> None:
    provider = SampleProvider()
    context = ReleaseEnrichmentContext("Synthetic Artist", "Synthetic Album")

    assert isinstance(provider, MetadataProvider)
    assert provider.get_candidates(context)[0].provider == provider.name


def test_provider_error_is_a_single_service_boundary() -> None:
    with pytest.raises(ProviderError, match="unavailable"):
        raise ProviderError("sample provider unavailable")
