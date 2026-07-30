# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context Level

`standard` for Block 023 because it adds one guarded mutation boundary after the existing pure
selected-track target plan while preserving downstream beets ownership.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output.

## Active Block

Block 023 - Safe Selected-Track Application.

## Active Spec

`docs/specs/023-safe-selected-track-application/`

## Active ADRs

- `docs/adr/0007-strict-selected-release-application.md`
- `docs/adr/0008-partial-application-policy.md`
- `docs/adr/0015-track-enrichment-boundary.md`
- `docs/adr/0017-importer-track-planning-preview.md`
- `docs/adr/0018-track-target-mapping.md`
- `docs/adr/0019-safe-selected-track-application.md`

## Allowed Files

Track application and preview code, importer integration, focused tests, README, ADR 0019, Block 023
specs, and context/handoff documents.

## Forbidden Behavior

Direct Item/Album mutation, match application calls, database persistence, tag/file writes, native
SYLT or synchronized-lyrics persistence, library track CLI, provider redesign, identity repair, and
album-wide rollback.

## Completion State

Implementation and final offline validation are complete. Focused validation passes 176 tests; the
full suite passes 798 tests with 5 opt-in live tests skipped. Lint, repository contamination, and
diff-whitespace checks pass.

## Stop Condition

Stop after Block 023. Do not add further lyrics persistence or identity audit/repair in this block.
