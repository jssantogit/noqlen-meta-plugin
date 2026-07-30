# Handoff

## State

Block 024 adds an internal read-only MusicBrainz identity audit engine. It globally assigns local
tracks to hydrated release tracks, ranks album structure without using existing MBIDs as evidence,
and compares all four v1.0 identity fields only after unique strong selection.

## Completed

- Immutable validated local context, MusicBrainz candidate, policy, score, finding, and result types.
- Conservative Unicode text comparison and explicit pair/release weights bounded to 0-100.
- Deterministic O(n^3) global assignment for reordered, unequal, multidisc, and large albums.
- Conservative minimum-score, margin, pair-strength, completeness, uniqueness, and singleton policy.
- Confirmed, missing, conflict, and ambiguous semantics with conflict precedence.
- Pure beets 2.12 AlbumInfo normalization and bounded injectable MusicBrainz acquisition.
- Relevance-preserving source bounding: sorted exact IDs, primary search order, then singleton
  alternate-query order, with first-occurrence deduplication and no ranking contribution.
- Release duration aggregation includes only comparable assigned pairs; unavailable duration removes
  its weight, while available disagreement remains penalized.
- Offline synthetic regression coverage, including Forge positional-mapping and wrong-existing-ID
  weaknesses.
- Focused validation passes 66 tests; the full suite passes 866 tests with 5 opt-in live tests
  skipped. Ruff, repository contamination, and diff-whitespace checks pass.

## Important Decisions

- Identity selection is separate from enrichment Field Authority, resolver, and ChangePlan.
- Existing IDs are audited values, never positive score evidence or candidate priority.
- Search results are hydrated before scoring and near-equal releases remain ambiguous.
- Positional mapping is rejected; recording MBIDs may repeat only across distinct release tracks.
- The engine has no write authority and no importer, CLI, database, tag, or file integration.

## Deferred

- Importer identity preview and explicitly authorized selected-metadata repair in Block 025.
- Library identity audit/repair in Block 026 and tag synchronization in Block 027.
- AcoustID and fingerprint evidence after v1.0.

## Next Direction

Proceed only to Block 025 after Block 024 review. Block 025 must consume `IdentityAuditResult` rather
than duplicate assignment or scoring. Preserve the frozen finish line: 025 importer identity,
026 library identity, 027 tag synchronization, 028 v1.0 hardening/release, then stop.
