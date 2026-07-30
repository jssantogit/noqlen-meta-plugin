# ADR 0019: Apply lossless changes only to selected TrackInfo

- Status: Accepted
- Date: 2026-07-30

## Context

Block 022 maps canonical selected-track changes to lossless `TrackInfo` targets but grants no write
authority. The first track application boundary must preserve normal importer ownership while
preventing forged plans, stale state, partial mutation, or synchronized-lyrics semantic loss.

## Decision

1. Noqlen track application mutates only the already-selected `TrackInfo`.
2. Noqlen never calls `AlbumMatch.apply_metadata()` or `TrackMatch.apply_metadata()`.
3. Noqlen does not directly mutate Items; beets owns later Item update, persistence, and file lifecycle.
4. Existing importer `apply: true` grants guarded release and track selected-metadata mutation.
5. The configured `apply_mode` string is parsed independently into a track-specific mode.
6. Strict remains the default and blocks one track on any resolver review or mapping blocker.
7. Partial applies only already-resolved `TrackTargetPlan.mapped_changes` and withholds reviews and
   blockers.
8. Application consumes the exact planning result target plan and recomputes its canonical mapping
   before policy evaluation.
9. Effective current state is recomputed immediately before mutation with Block 021 semantics and an
   explicit `from_scratch` value.
10. Every stale value uses exact type/value equality; every value, shape, and unique target is
    validated before mutation.
11. Atomicity is per selected track. Tracks and release/track boundaries evaluate independently;
    there is no album-wide rollback.
12. The only writable target is `lyrics -> TrackInfo.lyrics`; `synced_lyrics` remains blocked.
13. Effective-current stale validation temporarily refreshes selected `TrackInfo.raw_data` and
    `TrackInfo.item_data` plus, for an album match, the selected `AlbumInfo.raw_data` and
    `AlbumInfo.item_data` consumed by `merge_with_album()`.
14. Temporary stale-validation refresh restores the exact pre-attempt cache objects and presence for
    both selected metadata objects. Successful track mutation then permanently invalidates only the
    selected TrackInfo `raw_data` and `item_data`; AlbumInfo cache state remains unchanged.
15. `preview: false` with `apply: true` may execute track providers and emits only sanitized status
    logs. With both disabled, no track provider executes.
16. The library CLI remains album-only and keeps its separate `--partial` policy.
17. Noqlen does not call `Item.store`, file-write/sync methods, or `Album.store` in this boundary.
    Normal downstream beets may later persist or write the selected plain lyrics.
18. MusicBrainz/Navidrome identity audit and repair remains separate later work.

## Consequences

Plain lyrics can be safely prepared on selected metadata while the Item remains unchanged during the
callback. Later normal beets match application consumes the updated uncached selected data.
Synchronized lyrics remain visible but unwritable, and partial mode cannot weaken resolver or mapping
authority.
