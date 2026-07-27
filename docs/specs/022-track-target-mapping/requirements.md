# Requirements - Track Target Mapping

## Goal

Determine which already-proposed canonical track changes normal selected `TrackInfo` can represent
losslessly, without adding track writes.

## Requirements

- Reuse `MetadataCandidate`, `FieldDecision`, and `ChangePlan`; add no track resolver or canonical plan.
- Map only `ChangePlan.changes` through a pure immutable `TrackTargetPlan`.
- Map canonical `lyrics` exactly to `TrackInfo.lyrics` as a scalar string.
- Block canonical `synced_lyrics` with a fixed safe reason and no target field.
- Block unknown future canonical track fields rather than creating flexible targets.
- Keep resolver reviews separate while `requires_review` reflects reviews or mapping blockers.
- Render target counts and consequences without lyric text, timestamps, snippets, or unsafe identity.
- Preserve release behavior and the album-only library CLI.
- Add no `TrackInfo`, Item, database, tag, or file mutation, including when `apply: true`.
