# Handoff

## State

Block 022 adds a pure target-mapping boundary after canonical selected-track planning. Plain lyrics
map losslessly to `TrackInfo.lyrics`; synchronized lyrics remain a visible mapping blocker. Track
mapping is still preview-only and stops before application.

## Completed

- `TrackTargetShape`, immutable descriptors, mapping results, blockers, and registry are track-specific.
- `TRACK_FIELD_TARGETS` contains exactly `lyrics -> TrackInfo.lyrics`.
- Plain lyric strings and internal newlines are preserved exactly.
- `synced_lyrics` never becomes plain lyrics or a flexible target; unknown fields also block.
- Resolver reviews remain only on `ChangePlan`; target-plan review status combines both boundaries.
- Planning results and safe preview expose mapped and blocked target consequences.
- Actual beets 2.12.0 contract tests cover `TrackInfo.item_data`, modeled Item fields, and media fields.
- Focused validation passes 85 tests; the full suite passes 766 tests with 5 opt-in live tests
  skipped. Lint, repository contamination, and diff-whitespace checks pass.

## Important decisions

- Canonical planning and target representation are separate; no second resolver or `ChangePlan` exists.
- Plain lyrics are lossless on selected `TrackInfo`; synchronized lyrics are not lossless on the
  normal modeled Item/file-write surface.
- Track `apply` authority still does not exist. Importer `apply: true` governs release `AlbumInfo` only.
- Release application remains unchanged and the library CLI remains album-only.
- No track mutation, database/store operation, tag write, or file behavior exists.

## Deferred

- Safe selected-track application consuming only `TrackTargetPlan.mapped_changes`, with explicit
  strict/partial policy plus integrity and stale-state guards.
- Native synchronized/SYLT target strategy and physical file synchronization.
- Fingerprint generation, identity audit/repair, network identity lookup, and track CLI modes.

## Recommended next block

After independent Block 022 review, Block 023 may add safe selected-track application for only
losslessly mapped changes. It must define application policy and stale-state safeguards before any
mutation, while leaving synchronized-lyrics physical support deferred unless separately reviewed.
