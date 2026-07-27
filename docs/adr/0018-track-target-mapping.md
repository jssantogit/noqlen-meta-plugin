# ADR 0018: Map canonical track changes only to lossless TrackInfo targets

- Status: Accepted
- Date: 2026-07-27

## Context

Block 021 produces canonical selected-track `ChangePlan` values without deciding whether normal
beets can represent them. Block 022 needs an explicit, read-only target boundary before any future
track application can be considered.

## Decision

1. Canonical track planning and target representation remain separate boundaries.
2. `TrackTargetPlan` maps only already-`PROPOSED` changes in `ChangePlan.changes`.
3. Resolver reviews remain resolver reviews and are not duplicated as mapping blockers.
4. Mapping blockers represent valid canonical changes that normal selected `TrackInfo` cannot
   represent losslessly.
5. Plain `lyrics` maps losslessly and exclusively to `TrackInfo.lyrics`.
6. Internal lyric content and newlines are preserved exactly without normalization or inspection.
7. `synced_lyrics` has no normal lossless selected-`TrackInfo` target in supported beets 2.12.x.
8. A flexible `synced_lyrics` database key is rejected because normal Item file writing does not
   preserve its synchronized semantics.
9. Mapping `synced_lyrics` to `lyrics` is rejected because it collapses distinct canonical fields and
   collides when LRCLIB supplies both forms.
10. Native SYLT and file-specific application remain deferred.
11. Unknown future track fields block rather than becoming arbitrary flexible attributes.
12. Track target descriptors and their registry are explicit and immutable.
13. The pure mapper accepts `ChangePlan` and is independent of `SelectedImportTrack`.
14. `ImportTrackPlanningResult` carries both its canonical `ChangePlan` and `TrackTargetPlan`.
15. Preview exposes mapping counts, lossless targets, and fixed blocker reasons without raw lyrics.
16. `apply: true` grants no track write authority in this block.
17. Existing release application remains unchanged.
18. The library CLI remains album-only.
19. Strict or partial track application policy remains deferred.
20. Physical file synchronization remains deferred.
21. A later application block may mutate only already-lossless mapped track targets and must add
    integrity and stale-state guards.
22. MusicBrainz identity audit/repair remains a separate later subsystem.

## Consequences

Plain and synchronized LRCLIB values can coexist truthfully: plain lyrics are mapped while
synchronized lyrics remain visibly blocked. Mapping itself grants no mutation, persistence, or file
write authority.
