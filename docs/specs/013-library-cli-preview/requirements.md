# Requirements - Library CLI Preview Boundary

## Goal

Expose one read-only `beet noqlenmeta` command, with preferred `beet nm` alias, for albums already in
the beets library.

## Requirements

- Require a native album query or explicit `--all`; reject both together.
- Avoid provider work before query safety validation and avoid library queries when no provider can
  contribute.
- Adapt persistent Album identity and current values without fuzzy inference or Item queries.
- Share provider collection, candidate validation, resolver, and `ChangePlan` construction with the
  importer.
- Map canonical plans to immutable `LibraryTargetPlan` values using only lossless Album targets.
- Preview mapped changes, target blockers, reviews, kept fields, and skipped fields safely per album.
- Ignore importer application/preview settings for CLI mutation and output.
- Perform zero Album, Item, database, tag, file, art, move, or copy mutation.

## Out Of Scope

`--apply`, singleton or track mode, Item media mapping, interactive review, persistence, tag writing,
and application policy.
