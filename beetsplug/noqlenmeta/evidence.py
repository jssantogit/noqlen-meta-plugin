"""Typed evidence envelope for ordinary provider metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import TypeAlias

from beetsplug.noqlenmeta.domain import ExternalIdentifier, MetadataValue
from beetsplug.noqlenmeta.field_contracts import (
    EntityKind,
    IdentifierCollection,
    PartialDate,
    field_contract,
)
from beetsplug.noqlenmeta.providers.specs import ProviderScope

CanonicalValue: TypeAlias = MetadataValue | PartialDate | IdentifierCollection


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class SubjectRef:
    """The musical entity an evidence value explicitly describes."""

    entity: EntityKind
    identities: tuple[ExternalIdentifier, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.entity, EntityKind):
            raise TypeError("entity must be an EntityKind")
        identities = tuple(self.identities)
        if not identities:
            raise ValueError("subject requires at least one known identity")
        if not all(isinstance(identity, ExternalIdentifier) for identity in identities):
            raise TypeError("identities must contain ExternalIdentifier values")
        if len(identities) != len(set(identities)):
            raise ValueError("subject identities must be unique")
        object.__setattr__(self, "identities", identities)


class AcquisitionMethod(Enum):
    EXACT_LOOKUP = "exact_lookup"
    STRUCTURALLY_VALIDATED = "structurally_validated"
    SEARCHED_CANDIDATE = "searched_candidate"
    SUPPORTING_TRAVERSAL = "supporting_traversal"


@dataclass(frozen=True, slots=True)
class AcquisitionProvenance:
    """How a provider acquired or matched an asserted subject."""

    method: AcquisitionMethod
    supporting_entity: EntityKind | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.method, AcquisitionMethod):
            raise TypeError("method must be an AcquisitionMethod")
        if self.supporting_entity is not None and not isinstance(
            self.supporting_entity, EntityKind
        ):
            raise TypeError("supporting_entity must be an EntityKind")
        if self.method is AcquisitionMethod.SUPPORTING_TRAVERSAL and self.supporting_entity is None:
            raise ValueError("supporting traversal requires a supporting entity")


@dataclass(frozen=True, slots=True)
class MetadataEvidence:
    """Ordinary canonical metadata plus acquisition and subject provenance."""

    field: str
    value: CanonicalValue
    subject: SubjectRef
    provider: str
    acquisition_scope: ProviderScope
    source_id: str
    provenance: AcquisitionProvenance
    source_url: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        contract = field_contract(self.field)
        object.__setattr__(self, "field", contract.canonical_name)
        if not isinstance(
            self.value,
            (str, int, float, bool, tuple, PartialDate, IdentifierCollection),
        ):
            raise TypeError("canonical value has an unsupported type")
        if isinstance(self.value, tuple) and (
            not self.value
            or any(not isinstance(value, str) or not value.strip() for value in self.value)
        ):
            raise ValueError("canonical multi-value must contain non-empty strings")
        if isinstance(self.value, float) and not isfinite(self.value):
            raise ValueError("canonical numeric value must be finite")
        if not isinstance(self.subject, SubjectRef):
            raise TypeError("subject must be a SubjectRef")
        if self.subject.entity not in contract.allowed_entities:
            raise ValueError(
                f"asserted entity {self.subject.entity.value!r} is not allowed for "
                f"field {contract.canonical_name!r}"
            )
        object.__setattr__(self, "provider", _text(self.provider, "provider"))
        if not isinstance(self.acquisition_scope, ProviderScope):
            raise TypeError("acquisition_scope must be a ProviderScope")
        object.__setattr__(self, "source_id", _text(self.source_id, "source ID"))
        if not isinstance(self.provenance, AcquisitionProvenance):
            raise TypeError("provenance must be an AcquisitionProvenance")
        if self.source_url is not None:
            object.__setattr__(self, "source_url", _text(self.source_url, "source URL"))
        if self.confidence is not None:
            confidence = self.confidence
            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not isfinite(confidence)
                or not 0.0 <= confidence <= 1.0
            ):
                raise ValueError("confidence must be a finite number between 0.0 and 1.0")
            object.__setattr__(self, "confidence", float(confidence))
