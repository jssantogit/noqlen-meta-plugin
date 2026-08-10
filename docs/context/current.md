# Current Context

## Project

Noqlen Meta — multi-provider metadata enrichment and MusicBrainz identity tools for beets.

Profile: `core-lib`.

## Active State

Block 029 — AcoustID recording-level identity evidence — has completed product implementation.

Current `main` baseline:

```text
c5eabf80bbbe0f661aaa8867a78b3ebb83f0b3e3
```

Version 1.0.0 remains the released baseline. Block 029 is intended for the 1.1.0 release family; no version bump, tag, or publication has been made.

## Normative References

1. `docs/specs/029-acoustid-identity-evidence/contracts.md`
2. `docs/adr/0025-acoustid-recording-evidence.md`
3. `docs/specs/029-acoustid-identity-evidence/stage-05-completion.md`

## Delivered Block 029

The integrated AcoustID feature now provides:

- complete existing-library Album/singleton selection and exact refresh;
- valid stored fingerprint reuse and explicitly authorized bounded `fpcalc` generation in standalone mode;
- generated-source stability snapshots;
- bounded HTTPS `recordingids` lookup with strict parsing, privacy, pacing, caching, and no retry;
- decisive/ambiguous/no-match/unavailable recording evidence;
- exact standalone planning, path-free/fingerprint-free preview, and verified database-only application of `acoustid_id` / `acoustid_fingerprint`;
- decisive-recording compatibility filtering over already-evaluated MusicBrainz release candidates without score or assignment changes;
- optional AcoustID evidence in existing-library `--identity`, with missing-fingerprint generation explicitly forbidden;
- standalone `--acoustid` / `--fingerprint-missing` command handling;
- the frozen public `acoustid` configuration subtree.

## Safety Boundaries

AcoustID remains recording-level evidence rather than a generic provider. It does not:

- add structural score or relax MusicBrainz gates;
- select a release occurrence by itself;
- write MusicBrainz fields directly;
- write audio files;
- submit fingerprints;
- generate missing fingerprints during `--identity`;
- replace native beets `chroma` importer behavior.

## Final Validation

Stage 05 PR #19 was reviewed at head:

```text
9b76ff87b14440ddc576a0f0d84277ee8c8d5d23
```

CI run 74 passed Python 3.10-3.14, beets 2.12.0 and latest `<3`, docs, package validation, full offline tests, lint, and hygiene before squash merge to `c5eabf80...`.

## Current Work

Only Block 029 completion/release readiness remains:

- completion record and context synchronization;
- release notes/public-doc final alignment;
- documentation-only completion PR CI;
- later decision on 1.1.0 version bump, tag, and publication.

There is no Stage 06 and no remaining Block 029 product implementation stage.

## Tool Boundary

Repository changes made from the project chat remain documentation-only. Any future product implementation belongs to a new explicitly defined block rather than extending Block 029 implicitly.
