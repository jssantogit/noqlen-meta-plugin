# Requirements - Safe Selected-Track Application

## Goal

Apply only losslessly mapped selected-track changes to the already-selected `TrackInfo`, leaving all
downstream Item, database, and file behavior to beets.

## Requirements

- Add track-specific strict/partial modes, immutable results, and explicit safe parsing.
- Recompute and compare canonical target-plan integrity before policy evaluation.
- Strictly block per track on any review or mapping blocker; partial applies mapped changes only.
- Recompute Block 021 effective current state with explicit `from_scratch` immediately before write.
- Validate exact stale state, scalar-string values, target shapes, and unique targets before mutation.
- Mutate only selected `TrackInfo.lyrics` and invalidate only its `raw_data` and `item_data` caches.
- Never call match application, Item/Album persistence, or file-writing APIs.
- Execute track planning for preview or application and keep all output free of lyric values.
- Keep release application independent and the library CLI album-only.
