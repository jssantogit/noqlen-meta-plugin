"""Provider-independent field authority and metadata resolution."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from types import MappingProxyType

from beetsplug.noqlenmeta.domain import MetadataCandidate, MetadataValue
from beetsplug.noqlenmeta.evidence import MetadataEvidence
from beetsplug.noqlenmeta.providers.specs import BUILTIN_PROVIDER_NAMES, DISCOGS_SPEC


def _name(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    normalized = value.strip().lower()
    if not normalized.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"{label} contains invalid characters")
    return normalized


class ResolutionAction(Enum):
    """The resolver's recommended disposition for one field."""

    KEEP = "keep"
    PROPOSE = "propose"
    REVIEW = "review"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class FieldRule:
    """Authority and safety policy for one canonical metadata field."""

    enabled: bool = False
    authority: tuple[str, ...] = ()
    min_confidence: float = 0.0
    preserve_existing: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a boolean")
        if not isinstance(self.preserve_existing, bool):
            raise TypeError("preserve_existing must be a boolean")

        confidence = self.min_confidence
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not isfinite(confidence)
            or not 0.0 <= confidence <= 1.0
        ):
            raise ValueError("minimum confidence must be a finite number between 0.0 and 1.0")
        object.__setattr__(self, "min_confidence", float(confidence))

        if isinstance(self.authority, str):
            raise TypeError("authority must be a sequence of provider names")
        authority = tuple(_name(provider, "authority provider") for provider in self.authority)
        if len(authority) != len(set(authority)):
            raise ValueError("authority provider names must be unique")
        object.__setattr__(self, "authority", authority)


@dataclass(frozen=True, slots=True)
class ResolutionPolicy:
    """Independent field and provider enablement policy."""

    field_rules: Mapping[str, FieldRule]
    providers: Mapping[str, bool]

    def __post_init__(self) -> None:
        field_rules: dict[str, FieldRule] = {}
        for field, rule in self.field_rules.items():
            normalized = _name(field, "field name")
            if normalized in field_rules:
                raise ValueError("field names must be unique after normalization")
            if not isinstance(rule, FieldRule):
                raise TypeError("field rules must contain FieldRule values")
            field_rules[normalized] = rule

        providers: dict[str, bool] = {}
        for provider, enabled in self.providers.items():
            normalized = _name(provider, "provider name")
            if normalized in providers:
                raise ValueError("provider names must be unique after normalization")
            if not isinstance(enabled, bool):
                raise TypeError("provider enablement must be a boolean")
            providers[normalized] = enabled

        object.__setattr__(self, "field_rules", MappingProxyType(field_rules))
        object.__setattr__(self, "providers", MappingProxyType(providers))

    def is_field_enabled(self, field: str) -> bool:
        rule = self.field_rules.get(_name(field, "field name"))
        return rule.enabled if rule is not None else False

    def is_provider_enabled(self, provider: str) -> bool:
        return self.providers.get(_name(provider, "provider name"), False)

    def provider_has_enabled_authority(self, provider: str) -> bool:
        """Return whether an enabled provider has authority for an enabled field."""
        normalized = _name(provider, "provider name")
        return self.providers.get(normalized, False) and any(
            rule.enabled and normalized in rule.authority for rule in self.field_rules.values()
        )

    def authority_rank(self, field: str, provider: str) -> int | None:
        rule = self.field_rules.get(_name(field, "field name"))
        if rule is None:
            return None
        normalized_provider = _name(provider, "provider name")
        try:
            return rule.authority.index(normalized_provider)
        except ValueError:
            return None

    def confidence_threshold(self, field: str) -> float | None:
        rule = self.field_rules.get(_name(field, "field name"))
        return rule.min_confidence if rule is not None else None

    def preserves_existing(self, field: str) -> bool:
        rule = self.field_rules.get(_name(field, "field name"))
        return rule.preserve_existing if rule is not None else True


@dataclass(frozen=True, slots=True)
class FieldDecision:
    """An immutable, explainable resolution result for one field."""

    field: str
    current_value: MetadataValue | None
    selected: MetadataCandidate | None
    action: ResolutionAction
    reason: str
    alternatives: tuple[MetadataCandidate, ...] = ()

    @property
    def resolved_value(self) -> MetadataValue | None:
        return self.selected.value if self.selected is not None else self.current_value

    @property
    def selected_source(self) -> MetadataCandidate | None:
        return self.selected

    @property
    def contributing_evidence(self) -> tuple[MetadataEvidence, ...]:
        return ()


_DEFAULT_AUTHORITY: dict[str, tuple[str, ...]] = {
    "genres": ("musicbrainz", "discogs", "lastfm", "itunes"),
    "styles": ("discogs", "lastfm", "musicbrainz"),
    "labels": ("discogs", "musicbrainz", "itunes"),
    "catalog_numbers": ("discogs", "musicbrainz", "itunes"),
    "barcodes": ("discogs", "musicbrainz", "itunes"),
    "country": ("discogs", "musicbrainz", "itunes"),
    "year": ("musicbrainz", "discogs", "itunes"),
    "media": ("discogs", "musicbrainz", "itunes"),
    "format_descriptions": ("discogs",),
    "moods": ("lastfm", "musicbrainz"),
    "bpm": (),
    "lyrics_languages": ("musicbrainz",),
    "artist_countries": ("musicbrainz",),
    "artist_areas": ("musicbrainz",),
    "artist_languages": ("musicbrainz",),
    "lyrics": ("lrclib",),
    "synced_lyrics": ("lrclib",),
    "cover": ("itunes", "discogs"),
}
def default_resolution_policy() -> ResolutionPolicy:
    """Return the operational field policy with production providers disabled."""

    return ResolutionPolicy(
        field_rules={
            field: FieldRule(
                enabled=field in DISCOGS_SPEC.supported_fields,
                authority=authority,
                min_confidence=0.8,
            )
            for field, authority in _DEFAULT_AUTHORITY.items()
        },
        providers={name: False for name in BUILTIN_PROVIDER_NAMES},
    )


def _value_key(value: MetadataValue) -> tuple[str, str]:
    return type(value).__name__, repr(value)


def _candidate_key(candidate: MetadataCandidate, policy: ResolutionPolicy) -> tuple[object, ...]:
    rank = policy.authority_rank(candidate.field, candidate.provider)
    return (
        rank if rank is not None else len(policy.field_rules) + 1,
        _name(candidate.provider, "candidate provider"),
        -candidate.confidence,
        _value_key(candidate.value),
        candidate.source_id,
        candidate.source_url or "",
    )


def _deduplicate(
    candidates: Sequence[MetadataCandidate], policy: ResolutionPolicy
) -> tuple[MetadataCandidate, ...]:
    ordered = sorted(candidates, key=lambda candidate: _candidate_key(candidate, policy))
    seen: set[tuple[str, tuple[str, str]]] = set()
    unique: list[MetadataCandidate] = []
    for candidate in ordered:
        key = (_name(candidate.provider, "candidate provider"), _value_key(candidate.value))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return tuple(unique)


def resolve_metadata(
    current_values: Mapping[str, MetadataValue],
    candidates: Sequence[MetadataCandidate],
    policy: ResolutionPolicy,
) -> tuple[FieldDecision, ...]:
    """Resolve normalized candidates into decisions without applying metadata."""

    grouped: dict[str, list[MetadataCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[_name(candidate.field, "candidate field")].append(candidate)

    decisions: list[FieldDecision] = []
    for field in sorted(grouped):
        contenders = _deduplicate(grouped[field], policy)
        current = current_values.get(field)
        rule = policy.field_rules.get(field)
        if rule is None or not rule.enabled:
            decisions.append(
                FieldDecision(
                    field,
                    current,
                    None,
                    ResolutionAction.SKIP,
                    "field is disabled by policy",
                    contenders,
                )
            )
            continue

        eligible = tuple(
            candidate
            for candidate in contenders
            if policy.is_provider_enabled(candidate.provider)
            and policy.authority_rank(field, candidate.provider) is not None
            and candidate.confidence >= rule.min_confidence
        )
        if not eligible:
            decisions.append(
                FieldDecision(
                    field,
                    current,
                    None,
                    ResolutionAction.SKIP,
                    "no candidate is eligible under provider, authority, and confidence policy",
                    contenders,
                )
            )
            continue

        winning_rank = min(
            rank
            for candidate in eligible
            if (rank := policy.authority_rank(field, candidate.provider)) is not None
        )
        highest = tuple(
            candidate
            for candidate in eligible
            if policy.authority_rank(field, candidate.provider) == winning_rank
        )
        if len({_value_key(candidate.value) for candidate in highest}) > 1:
            decisions.append(
                FieldDecision(
                    field,
                    current,
                    None,
                    ResolutionAction.REVIEW,
                    (
                        f"highest-authority provider {highest[0].provider!r} "
                        "returned conflicting values"
                    ),
                    contenders,
                )
            )
            continue

        selected = highest[0]
        alternatives = tuple(candidate for candidate in contenders if candidate is not selected)
        authority_reason = f"selected {selected.provider!r} by field authority"
        if current is None:
            action = ResolutionAction.PROPOSE
            reason = f"{authority_reason}; current value is missing"
        elif type(current) is type(selected.value) and current == selected.value:
            action = ResolutionAction.KEEP
            reason = f"{authority_reason}; current value already agrees"
        elif rule.preserve_existing:
            action = ResolutionAction.REVIEW
            reason = f"{authority_reason}; existing conflicting value is preserved"
        else:
            action = ResolutionAction.PROPOSE
            reason = f"{authority_reason}; policy allows replacing the existing value"
        decisions.append(FieldDecision(field, current, selected, action, reason, alternatives))

    return tuple(decisions)
