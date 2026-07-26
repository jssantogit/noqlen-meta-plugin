# ADR 0006: Map canonical changes to beets only when lossless

- Status: Accepted
- Date: 2026-07-26

## Context

`ChangePlan` describes canonical metadata consequences independently from beets. Before any future
application boundary, the plugin must determine whether those consequences fit the current
`AlbumInfo` representation without discarding or serializing information.

## Decision

- Noqlen canonical metadata remains independent from beets representation.
- Target mapping occurs after `ChangePlan` and performs no resolution.
- Only lossless mappings enter an immutable, read-only `BeetsTargetPlan`.
- `genres` maps as a structured tuple to the beets list field `genres`; list materialization is
  deferred to a future application boundary.
- `country` and `year` map directly to their singular beets fields.
- `styles`, `labels`, `catalog_numbers`, `barcodes`, and `media` map to `style`, `label`,
  `catalognum`, `barcode`, and `media` only when exactly one canonical value exists.
- Multi-value to singular conversion is blocked by default. Values are never picked, dropped, or
  serialized with hidden delimiters.
- `format_descriptions` has no supported direct `AlbumInfo` target.
- Valid future canonical fields without a registered target become mapping blockers rather than
  internal errors.
- Mapping blockers describe target limitations. Malformed canonical shapes or invalid mapping
  definitions raise `BeetsMappingError` as contract defects.
- Original `PlannedChange` values and provenance remain reachable from mapped changes and blockers.
- No target object is mutated and no metadata, database, tags, files, plans, or provenance are
  written.

## Consequences

Preview can distinguish resolver review from target-model limitations. A fully mapped plan grants no
write permission. Actual list materialization, pre-apply checks, mutation, and application policy
remain deferred to a separately reviewed block.
