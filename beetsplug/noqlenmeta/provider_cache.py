"""Command-lifetime cache for exact provider entity lookups."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntityFetchProfile:
    """Deterministic acquisition coverage for one exact entity response."""

    includes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        values = tuple(sorted({_include(value) for value in self.includes}))
        object.__setattr__(self, "includes", values)


@dataclass(frozen=True, slots=True)
class EntityCacheKey:
    provider: str
    entity_type: str
    entity_id: str
    schema_version: str = "v1"
    profile: EntityFetchProfile = EntityFetchProfile()

    def __post_init__(self) -> None:
        for field in ("provider", "entity_type", "entity_id", "schema_version"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
            normalized = value.strip()
            if field in {"provider", "entity_type"}:
                normalized = normalized.casefold()
            object.__setattr__(self, field, normalized)
        if not isinstance(self.profile, EntityFetchProfile):
            raise TypeError("profile must be an EntityFetchProfile")


def _include(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("include must be a non-empty string")
    return value.strip()


class CommandEntityCache:
    """Reuse successful and definitive-missing responses for one execution."""

    def __init__(self) -> None:
        self._payloads: dict[EntityCacheKey, Mapping[str, object]] = {}
        self._missing: set[EntityCacheKey] = set()

    def get_or_fetch(
        self,
        key: EntityCacheKey,
        fetcher: Callable[[], Mapping[str, object] | None],
    ) -> Mapping[str, object] | None:
        if key in self._payloads:
            return self._payloads[key]
        if key in self._missing:
            return None
        payload = fetcher()
        if payload is None:
            self._missing.add(key)
            return None
        self._payloads[key] = payload
        return payload
