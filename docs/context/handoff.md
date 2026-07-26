# Handoff

## State

Block 002 defines the first production metadata domain and provider boundary. The package still has
no network behavior, concrete provider, resolver, or beets enrichment hook.

The project is an external beets plugin named `noqlenmeta`. Beets remains responsible for candidate matching and import flow. Noqlen Meta is intended to enrich the selected release by gathering field-level candidates from multiple providers, resolving those candidates according to authority/confidence policy, preserving provenance, and exposing reviewable changes before eventual writes.

## Completed

- Repository identity and project direction documented.
- External beets plugin package scaffolded under `beetsplug/noqlenmeta`.
- Python packaging and baseline development dependencies defined.
- Noqlen Playbook agent contract added.
- Real-first, fixture-backed provider policy documented.
- Initial architecture decision recorded.
- Baseline CI, lint, test, and contamination checks defined.
- Immutable album-level `ReleaseEnrichmentContext` with generic `ExternalIdentifier` values.
- Validated field-level `MetadataCandidate` with structured scalar/multi-value data, source details,
  and inclusive `0.0..1.0` confidence.
- Synchronous `MetadataProvider` protocol and minimal `ProviderError` boundary.
- Offline focused contract tests using synthetic values.

## Important decisions

- Prefer an external beets plugin over a beets fork.
- Do not replace the beets matcher in the initial scope.
- Treat provider integration as enrichment after release identification.
- Implement real production adapters directly; use sanitized fixtures for deterministic default tests.
- Keep live network tests opt-in.
- Never use real music-library data in automated tests.
- Keep release context album-level and limited to artist/title plus practical search hints.
- Represent future provider IDs as namespaced values instead of adding provider-specific fields.
- Require candidates to identify a provider source record; defer authority and cross-provider
  confidence interpretation.

## Not implemented

- Provider adapters.
- Field authority.
- Cross-provider confidence calibration.
- Resolver.
- Provenance storage.
- Import hooks or enrichment commands.
- Dry-run/review user experience.

## Recommended next block

Implement a **Discogs album-level enrichment adapter** as Block 003. It is a useful proof of the
contract because it can use artist/title, year, barcode, catalog number, and external IDs to produce
structured candidates such as label, genres/styles, country, and related release metadata without
changing beets matching.

Keep the adapter production-first and fixture-backed: use a narrow private HTTP boundary, sanitized
representative response fixtures, deterministic default tests, opt-in live checks only if scoped,
and `ProviderError` translation for client/service failures.

Suggested scope decisions for Block 003:

- Discogs authentication/configuration boundary and dependency choice.
- Release search/lookup strategy using `ReleaseEnrichmentContext`.
- Normalization into existing `MetadataCandidate` values only.
- Sanitized fixture tests for success, no-match, malformed response, and service failure.
- No resolver, authority policy, persistence, or beets lifecycle integration.
