# Handoff

## State

Block 011 adds an explicit default-off, strict application gate after `BeetsTargetPlan`. With
`apply: true`, a fully lossless and review-free plan may mutate only the selected `AlbumInfo`; the
listener then returns and normal beets duplicate/apply/add/file lifecycle continues.

## Completed

- `apply` defaults false and remains independent from preview.
- Canonical target-plan integrity and selected metadata `before` values are revalidated.
- Any resolver review or mapping blocker causes zero Noqlen application.
- All values and unique targets are validated/materialized before selected-info mutation.
- Genre tuples become fresh lists; scalar values retain their validated shape.
- Successful application invalidates `raw_data` and `item_data` caches.
- The listener mutates no Items or Albums and invokes no downstream beets lifecycle method.
- A focused in-memory handoff proves later normal `task.apply_metadata()` consumes enrichment.
- Provider failures remain isolated while internal application errors propagate.

## Important decisions

- Application permission requires explicit configuration plus a review-free, blocker-free plan.
- No partial application, hidden coercion, selection, dropping, or delimiter serialization exists.
- Only selected `AlbumInfo` mapped fields are changed; beets owns all later persistence effects.
- Hook placement precedes duplicate resolution. Default `albumartist album` keys are unchanged by
  current targets, while configured custom duplicate keys may observe enrichment.
- `apply: true` is a real feature because normal beets import may later persist enriched values.

## Deferred

- Partial-application policy and provenance persistence.
- `beet noqlenmeta` and preferred `beet nm` alias.
- Confidence calibration, artwork, previews, lyrics, and additional provider adapters.

## Recommended next block

After independent Block 011 review and real-behavior inspection, consider either a separately reviewed
partial-application policy or an application UX/CLI boundary. Do not automatically add a provider or
CLI before auditing this mutation behavior.
