# ADR 0025: Add AcoustID as recording-level identity evidence

- Status: Proposed
- Date: 2026-08-03

## Context

Noqlen Meta 1.0.0 can audit and repair a coherent MusicBrainz release,
release-group, recording, and release-track identity. Candidate acquisition and
selection are deliberately structural: complete MusicBrainz releases are
assigned against local tracks and must satisfy score, pair, completeness, and
margin requirements. ADR 0020 explicitly excluded AcoustID and Chromaprint from
the frozen v1.0 scope.

Noqlen Forge Core already generates or reuses Chromaprint fingerprints, queries
AcoustID, and exposes AcoustID and MusicBrainz identifiers. That implementation
contains useful operational behavior, but it also treats AcoustID as a generic
metadata authority and can derive release-specific identity by selecting
release data attached to a recording result. A MusicBrainz recording may occur
on many releases, and a release-track MBID identifies one occurrence. Therefore
a fingerprint match cannot safely choose the first release, medium, or track
returned by a provider payload.

beets also has a native `chroma` plugin for import-time acoustic matching and
stores `acoustid_id` and `acoustid_fingerprint` fields. Noqlen must cooperate
with that surface rather than create a competing autotagger.

## Decision

1. Block 029 introduces a dedicated AcoustID identity-evidence subsystem.
2. AcoustID is not an ordinary metadata provider and does not emit ordinary
   field candidates through the release/track enrichment resolver.
3. The initial product scope is existing-library Albums and singletons.
4. Importer fingerprint generation and AcoustID autotagger candidates remain
   owned by native beets `chroma` and are deferred from Block 029.
5. Valid existing beets AcoustID fields are inspected and reused before local
   fingerprint calculation or network lookup.
6. Missing fingerprints are calculated only under explicit AcoustID authority;
   ordinary enrichment and default identity audit never calculate them
   silently.
7. Fingerprint generation is behind an injected, bounded Chromaprint backend.
8. Backend discovery is skipped when all required fingerprints already exist.
9. Generated fingerprint material retains a no-follow source-file snapshot and
   cannot be applied after the source changes.
10. AcoustID lookup uses an independent, bounded HTTPS POST transport.
11. The transport uses a dedicated environment-supplied application client key,
    sequential service-aware pacing, bounded time/bytes/counts, a bounded
    process-local digest-keyed cache, and sanitized errors.
12. Fingerprint submission is not implemented.
13. The normalized service model retains only AcoustID UUIDs, scores, and
    MusicBrainz recording MBIDs.
14. Release, release-group, medium, and release-track data returned by AcoustID
    are intentionally ignored.
15. Multiple bounded result groups are retained until uniqueness and margin are
    proven; selecting the first result is forbidden.
16. A track's evidence verdict is unavailable, no match, ambiguous, or
    decisive.
17. Decisive evidence requires a validated minimum score, minimum margin, and
    exactly one defensible canonical recording MBID.
18. Local duration, artist, and title are corroborating or veto evidence only;
    they cannot create a recording identity.
19. AcoustID does not write any MusicBrainz field directly.
20. A complete four-field identity continues to originate only from a complete
    MusicBrainz release candidate.
21. Existing structural MusicBrainz evaluations and score components are
    calculated unchanged.
22. Decisive AcoustID recording evidence is applied after structural assignment
    as a compatibility filter: the assigned candidate recording must match the
    local track's decisive recording evidence.
23. AcoustID evidence adds no structural score and cannot rescue a weak,
    incomplete, ambiguous, or low-margin MusicBrainz candidate.
24. Unavailable, no-match, and ambiguous AcoustID evidence is neutral.
25. When decisive evidence rejects every otherwise eligible MusicBrainz
    candidate, identity remains ambiguous and not repair-ready.
26. A standalone AcoustID mode previews evidence and may apply only
    `acoustid_id` and `acoustid_fingerprint` to supported beets database Items.
27. Standalone AcoustID application plans every selected target and verifies
    exact database and generated-file snapshots before the first mutation.
28. Existing conflicting non-empty AcoustID values remain review blockers.
29. AcoustID mode has no force or partial mode.
30. AcoustID mode never writes audio files. Native beets behavior remains the
    authority for any later generic tag synchronization.
31. Public output never exposes full fingerprints, keys, raw responses, backend
    output, provider exceptions, or private paths.
32. Normal tests inject backend and transport boundaries and remain offline;
    real service tests are optional and do not gate CI.
33. The base package remains free of unnecessary AcoustID dependencies. Any
    optional Python extra is selected only after a supported-Python backend
    compatibility spike.
34. Block 029 planning does not bump the package version, modify production
    behavior, create a tag, or publish a release.

## Consequences

AcoustID can disambiguate recording identity without becoming a shortcut around
the existing release-level safety model. A decisive fingerprint match may
remove structurally plausible but recording-incompatible releases, while the
MusicBrainz audit still proves the exact release, release group, occurrence, and
complete track assignment.

Users can reuse fields produced by beets `chroma`, explicitly fingerprint an
existing library, preview service evidence, and store AcoustID fields without
Noqlen acquiring generic file-write authority. Missing tools, credentials, or
service availability remain visible but non-fatal.

The first implementation is intentionally narrower than Forge Core. It rejects
direct MusicBrainz writes from provider payloads, first-release shortcuts,
force paths, submission, automatic whole-library fingerprinting, and duplicate
import-time matching. This requires more explicit domain and stale-state code,
but keeps the new capability compatible with the v1 safety contracts.

The ADR remains Proposed until the Block 029 planning branch receives reviewer
approval. Implementation must not begin by weakening any decision above.
