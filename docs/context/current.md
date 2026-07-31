# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context Level

`standard` for integrated Block 025 importer identity preview/repair and its selected-metadata safety
boundary.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output.

## Active Block

Block 025 - Importer Identity Preview/Repair (integrated); Block 026 is next.

## Active Spec

`docs/specs/025-importer-identity-preview-repair/`

## Active ADRs

- `docs/adr/0015-track-enrichment-boundary.md`
- `docs/adr/0019-safe-selected-track-application.md`
- `docs/adr/0020-musicbrainz-identity-audit-engine.md`
- `docs/adr/0021-importer-identity-preview-repair.md`

## Allowed Files

Block 025 importer identity modules, the plugin entry point and identity exports, focused identity
tests, `README.md`, ADR 0021, the four Block 025 spec documents, and these current/handoff documents.

## Forbidden Behavior

Library identity CLI/repair, Item/Album mutation, direct database persistence, identity tag/file
synchronization, AcoustID/fingerprinting, recording search, and enrichment resolver/ChangePlan reuse.

## Completion State

Block 025 is integrated. Accepted album and singleton matches can independently audit and preview the
four MusicBrainz identity fields, then explicitly apply one canonical, stale-checked, atomic repair
set to selected `AlbumInfo`/`TrackInfo` metadata. Ambiguity and non-repair-ready evidence never write.
Normal beets retains persistence/file ownership. Library identity audit/repair and identity tag sync
are absent; AcoustID/fingerprinting remains excluded. Album preview now interprets original per-Item
identity tuples safely, and ambiguous preview counts reflect top-ranked assignment evidence without
selecting it. Focused preview/plugin validation passes 48 tests, the identity suite passes 166 tests,
and the full offline suite passes 966 tests with 5 live tests skipped.

## Stop Condition

Stop after integrated Block 025. Block 026 is next; do not add tag synchronization early. The frozen
remaining roadmap is 026 Library Identity Audit/Repair, 027 Identity Tag Synchronization, 028 v1.0
Hardening and Release, then STOP.
