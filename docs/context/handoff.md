# Handoff

## State

Block 025 is integrated. It consumes the Block 024 audit for an already accepted album or singleton
match, renders a privacy-safe importer preview, and can explicitly prepare one atomic identity repair
on selected metadata for normal beets application.

## Completed

- Separate boolean identity enable, preview, and apply settings with conservative defaults.
- Accepted AlbumMatch/TrackMatch extraction and effective post-beets context prediction, including
  `from_scratch`.
- Direct reuse of Block 024 assignment, scoring, selection, ambiguity, and field comparison.
- Sanitized preview of evidence, findings, repair readiness, and application state.
- Album preview renders repeated canonical IDs once, distinct IDs as `multiple/conflict`, and mixed
  state as `mixed/missing`; ambiguous counts use top-ranked evidence without selecting it.
- Canonical album/singleton mapping to selected `AlbumInfo`/`TrackInfo` identity fields.
- Forged-plan, stale-context, target-shape, scope, uniqueness, atomic rollback, and cache guards.
- Selected metadata mutation only; normal beets still owns persistence and file behavior.

## Important Decisions

- Identity settings and application authority are separate from enrichment and provider settings.
- Noqlen audits only the selected match and never changes beets match selection.
- Ambiguous or non-repair-ready evidence produces no repair; identity has no partial mode.
- The entire target set is revalidated and applied atomically or not at all.
- Noqlen mutates only selected metadata; Item, Album, database, tags, and files remain out of bounds.

## Deferred

- Library identity audit/repair in Block 026.
- Identity tag synchronization in Block 027.
- AcoustID, Chromaprint, fingerprinting, and recording search after v1.0.

## Next Direction

Proceed to Block 026 library identity audit/repair. Library identity and tag synchronization are
currently absent. Preserve the frozen remaining roadmap: 026 library identity, 027 tag
synchronization, 028 v1.0 hardening/release, then STOP.
