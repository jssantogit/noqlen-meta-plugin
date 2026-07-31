# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context Level

`standard` for completed Block 026 persisted library identity audit/repair.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output.

## Active Block

Block 026 - Library Identity Audit/Repair (complete); Block 027 is next.

## Active Spec

`docs/specs/026-library-identity-audit-repair/`

## Active ADRs

- `docs/adr/0015-track-enrichment-boundary.md`
- `docs/adr/0019-safe-selected-track-application.md`
- `docs/adr/0020-musicbrainz-identity-audit-engine.md`
- `docs/adr/0021-importer-identity-preview-repair.md`
- `docs/adr/0022-library-identity-audit-repair.md`

## Completion State

Block 026 is complete. The existing `noqlenmeta`/`nm` command has an explicit `--identity` mode that
audits complete persisted Albums and standalone Items through Block 024. Preview is always rendered,
and only `--identity --apply` can repair the four fixed MusicBrainz identity columns in the beets
database. Planning uses fresh exact path-free snapshots, completes before writes, and applies each
eligible target only after creating one real SQLite savepoint. That savepoint contains the pre-write
complete snapshot, identity updates, row checks, and a final complete expected-post snapshot derived
only from the original snapshot and canonical plan. Apply-mode results render as each target
completes, so a later stale failure preserves visible earlier commits and is marked accordingly
without claiming command-wide rollback. Post-commit verification and events remain unchanged.
Ordinary enrichment and importer identity authority remain separate.

Validation passes 35 focused application/command tests, 222 identity tests, and 1,022 full offline
tests with 5 live tests skipped. Ruff, repository contamination, and diff-whitespace checks pass.

Identity tag synchronization is still absent. No physical files or tags are read or written by
Block 026.

## Stop Condition

Proceed next to Block 027 Identity Tag Synchronization, then Block 028 v1.0 Hardening and Release,
then STOP. Do not add tag synchronization early.
