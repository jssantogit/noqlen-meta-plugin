# Handoff

## State

Block 012 preserves Block 011 strict application as the default and adds explicit
`apply_mode: partial`. Partial mode may mutate only `BeetsTargetPlan.mapped_changes` as one atomic
subset while reviews and mapping blockers remain withheld and visible. Normal beets lifecycle still
owns every downstream effect.

## Completed

- `apply` defaults false, `apply_mode` defaults strict, and only normalized strict/partial values are
  accepted when application is enabled.
- Invalid enabled modes fail before provider work.
- Strict reviews or blockers still cause zero Noqlen mutation, including default direct API calls.
- Partial mode applies mapped changes only; reviews and blockers are withheld, never selected,
  reduced, or serialized.
- No-eligible partial outcomes are valid no-ops with truthful result, preview, and log state.
- Canonical integrity, stale mapped state, all values, and unique targets are validated before any
  eligible mutation, so contract failures abort the full mapped subset.
- Successful strict or partial mutation invalidates `raw_data` and `item_data` caches.
- The listener mutates no Items or Albums and invokes no downstream beets lifecycle method.
- Focused handoff tests prove normal later beets application consumes the selected mapped subset.
- Provider failures remain isolated while internal application errors propagate.

## Important decisions

- Application permission remains explicit; partial behavior requires an explicit mode.
- Partial means applying the independently safe mapped subset, not field-by-field failure recovery.
- Withheld fields remain in planning and preview and receive no new stale-state contract.
- Only selected `AlbumInfo` mapped fields are changed; beets owns all later persistence effects.
- Hook placement precedes duplicate resolution. Default `albumartist album` keys are unchanged by
  current targets, while configured custom duplicate keys may observe enrichment.
- `apply: true` is a real feature because normal beets import may later persist enriched values.

## Deferred

- Provenance persistence.
- `beet noqlenmeta` and preferred `beet nm` alias.
- Confidence calibration, artwork, previews, lyrics, and additional provider adapters.

## Recommended next block

After independent Block 012 review, the preferred next candidate is the first user-facing command
boundary, `beet noqlenmeta` with `beet nm`, reusing the same resolver-to-application pipeline. Do not
begin that CLI or create a second enrichment engine inside Block 012.
