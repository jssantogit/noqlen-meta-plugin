# ADR 0004: Separate provider capabilities from field authority

- Status: Accepted
- Date: 2026-07-26

## Context

Field Authority intentionally describes conceptual provider preference and may mention providers for
fields their current adapters do not emit. Using authority alone to decide whether to invoke a
provider therefore causes unnecessary work and overstates what policy can prove.

## Decision

- Field Authority and Provider Capabilities are independent concepts.
- Authority remains in `ResolutionPolicy` and expresses product or user preference per field.
- Immutable provider specifications describe only what each concrete adapter can emit today.
- Provider invocation requires an enabled provider and at least one enabled field for which the
  provider has authority and current adapter capability.
- Every provider response is validated for provider identity and declared supported fields before
  entering the resolver.
- Candidate contract violations are internal errors and are not converted to external-service
  `ProviderError` failures.
- Capability metadata remains dependency-light and safe to import without optional provider clients.
- Provider credentials, settings, clients, factories, retries, confidence, and authority remain
  outside capability metadata.
- No dynamic registry, discovery mechanism, or third-party provider framework is introduced.
- Resolution still ends in read-only preview decisions; no metadata is applied.

## Consequences

Authority vocabulary can retain future fallback relationships without triggering adapters that
cannot currently contribute. Adding adapter output requires an explicit capability update, and
undeclared output fails visibly as a programming defect. Provider-specific setup remains explicit.
