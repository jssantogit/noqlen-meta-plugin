# ADR 0003: Resolve metadata with per-field authority

- Status: Accepted
- Date: 2026-07-26

## Context

Normalized provider candidates need explicit, reviewable decisions before any metadata can be applied.
One global provider ranking would incorrectly assume that every provider has equal authority across
identity, classification, lyrics, artwork, and edition metadata.

The final product is expected to expose `beet noqlenmeta` with the preferred short alias `beet nm`.
Its configuration is expected to have independent `fields` and `providers` sections so users can
control what metadata is wanted separately from where it may come from.

## Decision

- Authority is ordered per canonical field, not globally per provider.
- Field enablement and provider enablement are independent policy dimensions.
- A candidate must meet the field's minimum confidence before authority ordering applies; among
  eligible candidates, authority outranks raw confidence.
- Unknown fields are disabled, unknown providers are disabled, and providers unlisted in a field's
  authority chain are ineligible by default.
- Existing conflicting metadata is preserved and sent to review by default.
- Resolution returns immutable field decisions and never performs writes.
- Multi-provider semantic merging is deferred to a separate architectural block.

The future CLI and configuration will map onto these contracts but are not implemented by this
decision.

## Consequences

- Adding a provider cannot silently change fields until both provider enablement and field authority
  permit it.
- Confidence remains provider-local eligibility information rather than a universal ranking system.
- Lower-authority disagreement remains available as contender provenance without forcing review when
  a unique higher-authority candidate exists.
- Same-provider ambiguity and existing-value conflicts remain visible before any application layer.
- Genres, styles, identifiers, lyrics, credits, and artwork are not prematurely given one shared
  merge behavior.
