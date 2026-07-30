# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context Level

`standard` for Block 024 because it adds an isolated identity domain, structural assignment/scoring,
and an injectable MusicBrainz source without importer, CLI, or persistence integration.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output.

## Active Block

Block 024 - MusicBrainz Identity Audit Engine.

## Active Spec

`docs/specs/024-musicbrainz-identity-audit/`

## Active ADRs

- `docs/adr/0015-track-enrichment-boundary.md`
- `docs/adr/0019-safe-selected-track-application.md`
- `docs/adr/0020-musicbrainz-identity-audit-engine.md`

## Allowed Files

The isolated identity package, focused identity tests, README, ADR 0020, Block 024 specs, and
context/handoff documents.

## Forbidden Behavior

Importer identity integration, library identity CLI, MBID mutation, AlbumInfo/TrackInfo/Item/Album
mutation, database persistence, tag/file writes, AcoustID/fingerprinting, recording search, new
configuration, and enrichment resolver/ChangePlan reuse.

## Completion State

The read-only identity domain, global assignment, structural scoring, conservative selection and
field comparison, plus the injectable beets MusicBrainz source are complete. Source bounding now
preserves exact-ID priority and MusicBrainz search relevance with first-occurrence deduplication;
acquisition order remains excluded from structural ranking. Release-level duration now uses only
assigned pairs with comparable local and candidate lengths and renormalizes when that evidence is
unavailable. Focused validation passes 66 tests; the full suite passes 866 tests with 5 opt-in live
tests skipped. Ruff, repository contamination, and diff-whitespace checks pass.

## Stop Condition

Stop after Block 024. Do not add importer/CLI identity preview or repair. The frozen roadmap remains:
024 Identity Audit Engine, 025 Importer Identity Preview/Repair, 026 Library Identity Audit/Repair,
027 Identity Tag Synchronization, 028 v1.0 Hardening and Release, then stop.
