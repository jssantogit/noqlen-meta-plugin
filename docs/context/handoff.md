# Handoff

## State

Block 008 separates Field Authority from concrete adapter capabilities. Discogs and iTunes are called
only when enabled policy and immutable capability metadata intersect, and successful responses are
contract-validated before one existing Field Authority resolver pass. Selected import state remains
unchanged.

## Completed

- Dependency-light immutable specs define exact Discogs and iTunes adapter capabilities and display
  names without importing optional network clients.
- Concrete providers expose supported fields from the same authoritative specs.
- Policy now precisely reports enabled authority; orchestration separately intersects authority with
  adapter capability.
- iTunes does no work for unsupported labels/styles and Discogs does no work for unsupported cover.
- Provider identity and emitted fields are validated before resolution; contract defects propagate.
- Expected `ProviderError` failures remain safely isolated by a shared collection helper.
- Existing authority ordering, network behavior, one resolver pass, preview output, and read-only
  snapshots remain unchanged.

## Important decisions

- Authority is product/user preference; capability is concrete adapter reality today.
- Capability metadata contains no credentials, settings, clients, factories, or authority ranking.
- The integration remains explicit for two providers; no dynamic discovery was introduced.
- Contract violations are internal errors, not external service unavailability.
- Resolution creates preview decisions only and never writes.

## Deferred

- ChangePlan, metadata application, provenance persistence, and field-specific merge policy.
- `beet noqlenmeta` and preferred `beet nm` alias.
- Confidence calibration, artwork, previews, lyrics, and additional provider adapters.

## Recommended next block

After independent Block 008 review, the preferred next design candidate is a read-only `ChangePlan`
between decisions and any future application. Do not implement writes without that separate block.
