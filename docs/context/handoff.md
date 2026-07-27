# Handoff

## State

Block 021 executes read-only planning for selected importer album-match and singleton tracks when
preview is enabled. It reuses LRCLIB, Field Authority, the resolver, and `ChangePlan`, and stops before
track target mapping or application. Implementation, documentation, and final offline validation are
complete.

## Completed

- Selected `AlbumMatch` mappings are planned in order without extras; singleton `TrackMatch` produces
  one plan and no matcher call is added.
- LRCLIB runs only for preview-enabled eligible track fields and uses one lazy retained provider
  instance across tracks.
- Effective current values mirror beets 2.12.x: album `TrackInfo.merge_with_album(AlbumInfo)` or
  singleton `TrackInfo.item_data` overlays the appropriate local/cleared baseline.
- Actual album and singleton `apply_metadata()` parity tests cover both fields, both `from_scratch`
  modes, and selected-value presence or absence.
- Preview exposes plan actions and character/line summaries without raw lyric content.
- Provider failures fail open with sanitized output, contract errors propagate, and release/track
  plans coexist without track mutation.
- Fix-focused planning and importer validation passes 59 tests; the full suite passes 745 tests with
  5 opt-in live tests skipped. Lint, repository contamination, and diff-whitespace checks pass.

## Important decisions

- `from_scratch: false` retains Item-local canonical metadata before selected metadata overlays it.
- `from_scratch: true` mirrors `Item.clear()`: modeled writable media fields clear, flexible metadata
  survives, and selected metadata overlays last.
- Current beets behavior therefore clears omitted `lyrics` but retains omitted `synced_lyrics`.
- Track `apply` authority does not exist. Importer `apply: true` still governs release `AlbumInfo` only.
- The library CLI remains album-only and does not execute LRCLIB.
- No track mapping, mutation, database/store operation, tag write, or file behavior exists.

## Deferred

- Track target mapping/application and persistent/file write policy after this boundary is reviewed.
- Decide where or whether `synced_lyrics` should apply: beets does not model it as a standard
  persistent Item media field, and its Lyrics plugin stores canonical LRC text in `Item.lyrics` while
  passing native SYLT separately for file writes. Block 021 does not choose among a flexible database
  value, file-only tag, canonical-lyrics mapping, or another explicit target.
- Fingerprint generation, network identity lookup, cache, concurrency, and track CLI modes.

## Recommended next block

After independent Block 021 review, a separate Block 022 may design selected-track target mapping and
strict importer application. It must explicitly resolve synchronized-lyrics target semantics and
must not conflate persistent library Item or physical-file application with the importer boundary.
