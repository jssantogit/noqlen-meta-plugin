# ADR 0020: Add a read-only MusicBrainz identity audit engine

- Status: Accepted
- Date: 2026-07-30

## Context

Noqlen needs to assess whether local MusicBrainz release, release-group, recording, and release-track
identities are structurally supported. Ordinary enrichment begins after identity selection and its
Field Authority, resolver, and ChangePlan contracts must not decide or repair identity.

## Decision

1. Identity audit is a separate subsystem from metadata enrichment.
2. The audited fields are release, release group, recording, and release track MBIDs.
3. Existing IDs are comparison targets and never positive ranking evidence.
4. MusicBrainz search results are hydrated to complete release and track identities before scoring.
5. Candidate bounding preserves acquisition relevance: sorted exact existing release IDs come first,
   followed by album search and singleton alternate-search results in MusicBrainz order. Canonical
   release IDs are first-occurrence deduplicated before the bound. Acquisition order controls
   inclusion only and never contributes to structural score or margin. If exact IDs alone exceed the
   defensive bound, only the first bounded sorted IDs are fetched.
6. Singles add a distinct track-artist/track-title release query and use stricter score and margin
   thresholds.
7. AcoustID, Chromaprint, and recording search are excluded from v1.0.
8. Local and remote tracks use one deterministic global minimum-cost assignment.
9. Positional `zip` mapping is rejected, including for reordered and multidisc releases.
10. Pair assignment uses title, duration, artist, and explicit medium/position evidence.
11. Titles and album-wide track structure dominate scoring; optional release metadata cannot rescue a
    weak candidate.
12. Pair and release scores have explicit weights and remain bounded from 0 to 100. Release-level
    duration evidence includes only assigned pairs with both local and candidate durations. If none
    are comparable, its weight is removed and remaining structural evidence is renormalized; missing
    duration is neither a match nor a mismatch.
13. Selection requires both a minimum score and a unique minimum margin.
14. Near ties remain ambiguous; lexical release-ID ordering provides determinism only.
15. Audit verdicts are confirmed, missing, conflict, or ambiguous.
16. Conflict supersedes missing in the overall verdict.
17. Malformed existing IDs remain valid audit input and become conflicts after strong selection.
18. Malformed or incomplete source IDs are source contract errors.
19. Multidisc medium, medium index, and flattened index remain explicit.
20. Unmatched local tracks prevent repair-ready status by default.
21. An existing-ID anchored candidate receives no structural score or ranking bonus; its acquisition
    priority only fulfills the source promise to include exact local identities for auditing.
22. Recording IDs may legitimately repeat when occurrence-specific release-track IDs and positions are
    distinct; release-track IDs must remain unique.
23. Production acquisition uses beets 2.12 MusicBrainz plugin facilities, not custom raw HTTP.
24. The source boundary is injectable and normal tests remain offline.
25. The engine and its result are immutable, pure, and read-only.
26. Block 024 adds no importer integration.
27. Block 024 adds no public CLI integration.
28. No AlbumInfo, TrackInfo, Item, Album, database, tag, or file mutation is permitted.
29. Block 025 owns importer identity preview and explicitly authorized application.
30. Block 026 owns library identity audit and repair.
31. Navidrome interoperability motivation does not change MusicBrainz identity semantics.
32. The v1.0 scope remains frozen at Blocks 024 through 028.

## Consequences

Later workflows can consume one conservative `IdentityAuditResult` without reimplementing assignment,
scoring, ambiguity, or field comparison. Candidate evaluations remain available for safe future
preview, while ambiguous audits select no identity and are never repair-ready.
