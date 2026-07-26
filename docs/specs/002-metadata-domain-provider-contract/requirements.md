# Requirements - Metadata Domain and Provider Contract

## Goal

Define the minimum provider-independent contracts for enriching an album release already
identified by beets.

## Functional requirements

- Represent album artist, title, optional year, barcode, catalog number, and generic external
  identifiers without retaining a beets object.
- Represent one normalized field proposal with a typed scalar or string tuple value, provider,
  confidence, and source reference.
- Enforce non-empty identity fields and source details and confidence within `0.0..1.0`.
- Define a synchronous provider boundary returning only normalized candidates.
- Define one provider-level failure abstraction independent of HTTP/client libraries.

## Non-goals

- Concrete providers or network clients.
- Track-level matching.
- Authority, resolution, persistence, review/apply behavior, or beets lifecycle hooks.
- Provider registries, discovery, caching, dependency injection, or fake-provider frameworks.

## Acceptance criteria

- Domain values are immutable and reject clearly malformed states.
- Multi-value metadata remains structured rather than delimiter-flattened.
- A small production adapter can satisfy the provider protocol without beets-specific logic.
- Focused tests and baseline repository validation pass offline with synthetic data.
