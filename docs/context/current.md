# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools for beets.

## Profile

`core-lib`

## Context Level

`full` for Block 029 AcoustID/Chromaprint identity-evidence planning.

## Tool Mode

Direct repository planning and architecture review. This branch may change only
internal specs, ADRs, and context. It does not change product behavior, package
metadata, dependencies, public documentation, workflows, tags, or publication.

## Active Block

Block 029 - AcoustID recording-level identity evidence.

Block 029 is in planning/spec review. No implementation stage is active.

## Active Spec

- `docs/specs/029-acoustid-identity-evidence/requirements.md`
- `docs/specs/029-acoustid-identity-evidence/design.md`
- `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- `docs/specs/029-acoustid-identity-evidence/tasks.md`

## Active ADRs

- Proposed: `docs/adr/0025-acoustid-recording-evidence.md`
- Existing identity foundation:
  - `docs/adr/0020-musicbrainz-identity-audit-engine.md`
  - `docs/adr/0021-importer-identity-preview-repair.md`
  - `docs/adr/0022-library-identity-audit-repair.md`
  - `docs/adr/0023-identity-tag-synchronization.md`

## Released Baseline

Version 1.0.0 was released on 2026-08-02. The tag, PyPI Trusted Publishing,
GitHub Release, matching artifact hashes, and Read the Docs `latest`, `stable`,
and `v1.0.0` builds are complete. The Block 029 branch starts from post-release
`main` commit `cb8e8afd40998a1240f93528a7e8584b77f167d1`.

## Planning Decision

AcoustID is a separate recording-level identity-evidence subsystem, not an
ordinary metadata provider. It may identify or support a MusicBrainz recording
MBID, but it cannot directly select or write release, release-group, or release-
track MBIDs. Complete four-field identity continues to come only from complete
MusicBrainz release candidates and the existing structural audit.

The first scope is existing-library Albums and singletons. It reuses existing
beets AcoustID fields, calculates missing fingerprints only with explicit
authority, uses a bounded HTTPS lookup boundary, previews evidence, and may
store only AcoustID fields in the beets database. It writes no audio files,
has no force mode, performs no submission, and does not duplicate native beets
`chroma` importer matching.

Decisive recording evidence filters MusicBrainz candidates after their existing
structural assignments are calculated. It adds no structural score and cannot
rescue weak or ambiguous candidates.

## Next Gate

Review the planning diff and ADR 0025. After reviewer approval, mark the ADR
Accepted, freeze public option/configuration names, and begin the first focused
implementation stage for immutable domain and configuration contracts.

## Stop Condition

Do not add AcoustID production code, dependency metadata, public commands,
version changes, tags, or publication behavior on this planning branch. Do not
begin implementation until the Block 029 planning PR is reviewed and merged.
