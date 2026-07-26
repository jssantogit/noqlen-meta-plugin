# ADR 0007: Apply metadata only through a strict selected-release boundary

- Status: Accepted
- Date: 2026-07-26

## Context

`BeetsTargetPlan` identifies lossless target representations but grants no write permission. The
first application boundary must remain opt-in, preserve the beets importer lifecycle, and prevent a
partially safe plan from producing partial metadata changes.

The plugin runs at `import_task_choice`, before beets duplicate resolution and `_apply_choice`.
Current beets default album duplicate keys are `albumartist album`; current Noqlen targets do not
modify either field. Custom duplicate keys such as `year`, `label`, `catalognum`, or `barcode` may
intentionally observe selected-release enrichment.

## Decision

- `apply` is explicit and defaults to `false`; `preview` and `apply` are independent.
- The first application boundary mutates only the already-selected `AlbumInfo` at `task.match.info`.
- Noqlen never invokes `task.apply_metadata()`, match application, library addition, or file handling.
- beets remains owner of Item application, Album/library addition, file handling, and tag writing.
- Application is strict and all-or-nothing: any resolver `REVIEW` or mapping blocker applies nothing.
- Partial application and automatic acceptance or dropping of blockers do not exist.
- The target plan must equal the canonical mapping of its source `ChangePlan`.
- Current selected metadata must canonically match every planned `before` value.
- Every target value and unique target field is validated before any mutation occurs.
- Immutable genre tuples become fresh lists only at application; scalar shapes are never coerced.
- Successful mutation invalidates only the known dependent `raw_data` and `item_data` caches.
- Internal application contract errors fail visibly; external `ProviderError` failures remain isolated.
- Mutation occurs before duplicate resolution because of the lifecycle hook placement.
- Current targets leave default duplicate identity keys unchanged, while custom duplicate keys may
  observe enriched values.
- Downstream database and file persistence remain normal beets behavior. Therefore `apply: true` is
  not a dry run even though Noqlen itself performs none of those downstream writes.

## Consequences

The default remains non-mutating. Enabled application may be blocked frequently when providers emit
unsupported or multi-valued singular fields, but no information is silently discarded and no safe
subset is applied. A future block may separately review partial-application policy.
