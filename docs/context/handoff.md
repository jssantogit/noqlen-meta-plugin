# Handoff

## State

Block 023 adds the first safe selected-track write boundary. With importer `apply: true`, only
losslessly mapped fields on the already-selected `TrackInfo` may change. Noqlen stops before match
application; normal beets owns Item updates, persistence, and files.

## Completed

- Track-specific strict/partial parsing and immutable application results.
- Canonical target-plan integrity and effective-current stale-state guards.
- Full target/value/uniqueness validation before per-track atomic mutation.
- Plain lyrics application only; synchronized lyrics remain blocked.
- TrackInfo `raw_data` and `item_data` cache invalidation.
- Preview-enabled and preview-disabled importer application.
- Real TrackMatch/AlbumMatch downstream ownership tests and forbidden-write sentinels.
- Independent release/track and per-track outcomes with provider fail-open behavior.
- Focused validation passes 176 tests; the full suite passes 798 tests with 5 live tests skipped.
- Lint, repository contamination, and diff-whitespace checks pass.

## Important Decisions

- Existing `apply` authorizes both selected-release and selected-track guarded boundaries.
- The same configured string is parsed into distinct release and track mode types.
- Strict blocks one selected track on review or mapping blockers; partial applies mapped changes only.
- Noqlen never calls match application, Item update/store/write/sync, or Album store for track work.
- The library CLI remains album-only.

## Deferred

- Native synchronized/SYLT target strategy and physical file synchronization.
- MusicBrainz/Navidrome identity audit and repair, including later AcoustID recording evidence.
- Track database backfill or library track command modes.

## Next Direction

Pause further lyrics persistence work. A separately reviewed Noqlen Identity Audit / Repair direction
should address MusicBrainz recording/release-track and release/release-group identity quality.
