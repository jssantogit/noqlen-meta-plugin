# Requirements - Provider Capabilities and Orchestration

## Goal

Formalize immutable adapter capabilities independently from Field Authority and use their
intersection to gate and validate read-only multi-provider enrichment.

## Requirements

- Declare dependency-light specs for Discogs and iTunes with exact current output fields.
- Extend the provider protocol with immutable supported fields sourced from those specs.
- Keep authority ordering unchanged in `ResolutionPolicy` and clarify its policy-only query.
- Invoke a provider only when provider enablement, field enablement, authority, and capability
  intersect.
- Validate emitted provider identity and fields, propagating internal contract defects.
- Preserve provider-specific configuration, lazy Discogs loading, isolated external failures, one
  resolver pass, preview branding, and all read-only guarantees.

## Out of scope

New providers, dynamic discovery, network behavior changes, retries, caching, concurrency, metadata
application, persistence, CLI, and ChangePlan are excluded.
