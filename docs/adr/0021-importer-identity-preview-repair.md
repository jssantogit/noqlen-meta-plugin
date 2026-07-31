# ADR 0021: Add importer identity preview and repair

- Status: Accepted
- Date: 2026-07-31

## Context

Block 024 can conservatively identify MusicBrainz identity findings but has no importer authority.
Block 025 must expose those findings for an already accepted beets match and optionally prepare safe
selected metadata for normal beets application without merging identity and enrichment policy.

## Decision

1. Importer identity consumes the unchanged Block 024 acquisition, assignment, scoring, selection,
   ambiguity, and comparison engine.
2. Identity remains separate from enrichment, Field Authority, the resolver, `ChangePlan`, and
   enrichment target plans.
3. Dedicated strict-boolean `identity.enabled`, `identity.preview`, and `identity.apply` settings
   default to `false`, `true`, and `false`.
4. Ordinary `apply` never grants identity repair.
5. Identity apply never grants ordinary enrichment application.
6. Accepted `AlbumMatch` and `TrackMatch` selections are supported.
7. The existing selected mapping is reused; Noqlen does not rematch.
8. One AlbumMatch produces one context, acquisition, and audit.
9. Local keys are opaque ordinals, never paths, and are never displayed.
10. Effective current identity follows real beets overlay and `from_scratch` semantics.
11. Selected `raw_data`, `item_data`, and merged application surfaces are recomputed fresh.
12. Read-only planning restores exact prior cache presence and object identity.
13. Mixed present/missing album IDs are retained with fixed internal malformed markers.
14. Internal mixed markers never score, print literally, enter exact-ID fetches, or apply.
15. Structural evidence comes from selected metadata, with only the documented conservative singleton
    fallbacks.
16. Existing IDs remain comparison-only and never boost score or rank.
17. AlbumMatch release identity targets selected `AlbumInfo` fields.
18. AlbumMatch recording and release-track identity targets assigned selected `TrackInfo` fields.
19. TrackMatch recording and release-track identity targets native selected `TrackInfo` fields.
20. TrackMatch album identity targets canonical Item-field keys on `TrackInfo`; beets 2.12 lifecycle
    tests prove those keys reach the Item later.
21. Noqlen never directly mutates an Item.
22. Identity target mapping is immutable and deterministic.
23. Ambiguous and confirmed audits map no changes.
24. Missing or conflicting findings map only when the Block 024 result is repair-ready.
25. Identity has no partial mode.
26. Repair is atomic for the entire selected match.
27. Application recomputes target-plan integrity before policy or mutation.
28. Application stale-checks the full fresh effective context, including structure and identity.
29. Every target, field, scope, UUID, and duplicate pair validates before mutation.
30. Failure restores exact prior field presence, values, and relevant caches.
31. Success invalidates only affected selected metadata caches.
32. Noqlen never calls `match.apply_metadata()`.
33. Beets owns later Item update, database lifecycle, and file/tag lifecycle.
34. Source failures fail open with a sanitized warning.
35. Mapping, stale-plan, and application safety failures are not swallowed.
36. Identity executes after ordinary release and track enrichment.
37. Identity works when all ordinary providers are disabled.
38. Preview may show canonical MBIDs but never paths, local keys, queries, source URLs, or raw malformed
    values.
39. Block 025 adds no library identity command.
40. AcoustID, Chromaprint, fingerprinting, and recording search remain excluded.
41. Block 026 owns library identity audit and repair.
42. The frozen roadmap remains Block 026, Block 027 identity tag synchronization, Block 028 v1.0
    hardening/release, then STOP.

## Consequences

Importer users can inspect and explicitly authorize conservative identity repair without changing
who owns match selection, persistence, or file writes. Any ambiguity, stale state, unsafe mapping, or
application failure prevents the entire identity change set.
