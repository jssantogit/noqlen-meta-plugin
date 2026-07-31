# Handoff

## State

Block 026 is complete. Persisted library MusicBrainz identity audit/repair exists as the explicit
`--identity` mode on the existing `noqlenmeta`/`nm` command.

## Completed

- Item-query selection that expands complete Albums, deduplicates them, and supports standalone
  singleton Items; `--all` covers both kinds once in deterministic database-ID order.
- Fresh immutable selected boundaries and exact path-free stale snapshots.
- Album and singleton Block 024 contexts, including multidisc ordering and conservative flattened
  positions.
- Album-plus-Item release identity aggregation with private mixed-missing state and direct per-Item
  track identity.
- One retained-source audit per complete target, sanitized per-target source failures, and always-on
  privacy-safe preview.
- Immutable mapping to every differing fixed Album/Item identity column.
- Full planning before writes, command-wide preflight, and a final complete snapshot rebuilt after
  per-target root transaction acquisition but before SAVEPOINT creation.
- One real SQLite savepoint per complete Album-plus-Items or singleton repair using public
  transaction SQL APIs and bound parameters.
- In-savepoint and fresh post-commit verification with deterministic post-commit database events.
- Immediate apply-mode rendering, with safe committed-state annotation if a later target races after
  earlier changes committed.
- Real temporary-database regression for beets 2.12 exceptional root commit and savepoint rollback.
- Validation: 31 focused tests and 218 identity tests pass; the full offline suite passes 1,018 tests
  with 5 live tests skipped. Ruff, contamination, and diff-whitespace checks pass.

## Important Decisions

- Only `--identity --apply` authorizes persisted library identity repair.
- Bare `nm --apply` remains ordinary enrichment; importer identity settings do not grant library
  writes.
- Identity has no partial or force mode, and ambiguous/non-ready evidence never writes.
- Block 026 is database-only. No model store, tag/file, importer application, or private connection
  path participates in identity repair.

## Deferred

- Block 027 explicit synchronization of confirmed database MBIDs to supported audio-file tags.
- AcoustID, Chromaprint, fingerprinting, and recording search remain outside v1.0.

## Next Direction

Proceed to Block 027, then Block 028, then STOP.
