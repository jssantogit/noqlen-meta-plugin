"""Specialized genre adaptation before generic metadata resolution."""

from __future__ import annotations

from collections.abc import Sequence

from beetsplug.noqlenmeta.domain import MetadataCandidate, MetadataValue
from beetsplug.noqlenmeta.genre_evidence import GenreEvidence, GenreEvidenceKind
from beetsplug.noqlenmeta.genre_resolution import GenreSettings, resolve_genres
from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
    GenreTaxonomy,
)
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.resolver import FieldDecision, ResolutionAction, ResolutionPolicy


def genre_evidence_from_release_candidates(
    candidates: Sequence[MetadataCandidate],
    *,
    policy: ResolutionPolicy,
    settings: GenreSettings,
    taxonomy: GenreTaxonomy = DEFAULT_GENRE_TAXONOMY,
) -> tuple[GenreEvidence, ...]:
    """Adapt already-collected release metadata without changing collection."""
    rule = policy.field_rules.get("genres")
    if rule is None or not rule.enabled:
        return ()

    evidence: list[GenreEvidence] = []
    for candidate in candidates:
        field = candidate.field.casefold()
        provider = candidate.provider.casefold()
        if field not in {"genres", "styles"}:
            continue
        if (
            not policy.is_provider_enabled(provider)
            or policy.authority_rank("genres", provider) is None
            or candidate.confidence < rule.min_confidence
        ):
            continue
        if field == "styles" and (
            provider != "discogs" or not settings.promote_styles
        ):
            continue

        values = candidate.value if isinstance(candidate.value, tuple) else (candidate.value,)
        for value in values:
            if not isinstance(value, str):
                continue
            classification = taxonomy.classify(value)
            if classification.category is not GenreSemanticCategory.GENRE:
                continue
            if field == "styles":
                kind = GenreEvidenceKind.PROMOTED_STYLE
            elif provider == "lastfm":
                kind = GenreEvidenceKind.COMMUNITY_TAG
            else:
                kind = GenreEvidenceKind.GENRE
            evidence.append(
                GenreEvidence(
                    genre=classification.canonical_name,
                    provider=provider,
                    scope=ProviderScope.RELEASE,
                    kind=kind,
                    confidence=candidate.confidence,
                    source_id=candidate.source_id,
                    source_url=candidate.source_url,
                )
            )
    return tuple(evidence)


def resolve_release_genre_decision(
    current_value: MetadataValue | None,
    candidates: Sequence[MetadataCandidate],
    *,
    policy: ResolutionPolicy,
    settings: GenreSettings,
    taxonomy: GenreTaxonomy = DEFAULT_GENRE_TAXONOMY,
) -> FieldDecision | None:
    """Resolve one aggregate genre decision that rejoins ordinary planning."""
    if not policy.is_field_enabled("genres"):
        return None
    evidence = genre_evidence_from_release_candidates(
        candidates, policy=policy, settings=settings, taxonomy=taxonomy
    )
    if not evidence:
        return None
    resolution = resolve_genres(
        evidence,
        settings=settings,
        taxonomy=taxonomy,
        min_confidence=policy.confidence_threshold("genres") or 0.0,
    )
    if not resolution.genres:
        return None

    selected = MetadataCandidate(
        field="genres",
        value=resolution.genres,
        provider="noqlen",
        confidence=max(item.confidence for item in resolution.evidence),
        source_id=f"genre-taxonomy:{taxonomy.snapshot_id}",
    )
    provenance = "; ".join(resolution.explanation)
    if current_value is None:
        action = ResolutionAction.PROPOSE
        disposition = "current value is missing"
    elif type(current_value) is type(selected.value) and current_value == selected.value:
        action = ResolutionAction.KEEP
        disposition = "current value already agrees"
    elif policy.preserves_existing("genres"):
        action = ResolutionAction.REVIEW
        disposition = "existing conflicting value is preserved"
    else:
        action = ResolutionAction.PROPOSE
        disposition = "policy allows replacing the existing value"
    return FieldDecision(
        field="genres",
        current_value=current_value,
        selected=selected,
        action=action,
        reason=f"resolved specialized genre evidence ({provenance}); {disposition}",
    )
