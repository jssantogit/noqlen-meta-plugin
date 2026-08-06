# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools
for beets.

## Profile

`core-lib`

## Context Level

`full` for Block 029 after completion of Stage 01 and during documentation of
the local existing-value and fingerprint-backend stage.

## Tool Mode

Repository work from the project chat is documentation-only. Allowed changes are
limited to specs, stage briefs, ADRs, context, handoff, completion records, and
documentation-only PR administration.

Product code, implementation tests, dependencies, package metadata, workflows,
versions, tags, and releases are implemented outside this chat after their
documentation stage is approved.

## Active Block

Block 029 - AcoustID recording-level identity evidence.

Planning, contract freeze, Stage 01 brief, Stage 01 implementation, and the
Stage 01 completion record are integrated into `main`.

Important commits:

```text
6ad71d68347e23cecd45225900a10a8287acca54  planning
9945ed9cd693abc04b250d10239151b3281a7762  contract freeze
262aa688ac552b7ebb19156ed3c9a58a0f24ed06  Stage 01 brief
26506a79f23a899a810640b1a2bfa8d80a5c4c20  Stage 01 implementation
2f01c1d070d93b78bfba269439ca7b44de5c3e87  Stage 01 completion record
```

PR #5 delivered Stage 01 product code and passed CI run 45. PR #6 recorded its
completion and passed CI run 47.

## Normative Artifacts

- `docs/specs/029-acoustid-identity-evidence/contracts.md`
- `docs/adr/0025-acoustid-recording-evidence.md`
- `docs/specs/029-acoustid-identity-evidence/requirements.md`
- `docs/specs/029-acoustid-identity-evidence/design.md`
- `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- `docs/specs/029-acoustid-identity-evidence/tasks.md`
- `docs/specs/029-acoustid-identity-evidence/stage-01-domain-policy-configuration.md`
- `docs/specs/029-acoustid-identity-evidence/stage-01-completion.md`
- `docs/specs/029-acoustid-identity-evidence/stage-02-existing-values-targets-backend.md`

`contracts.md` remains normative when earlier planning wording differs. The
Stage 02 brief narrows only the second external implementation branch and cannot
weaken the frozen product contract.

## Released Baseline

Version 1.0.0 was released on 2026-08-02. The public tag, PyPI publication,
GitHub Release, matching artifact hashes, and Read the Docs builds remain
complete.

Block 029 remains intended for the 1.1.0 release family. No version bump has
been made.

## Frozen Product Decision

AcoustID is a separate recording-level identity-evidence subsystem, not an
ordinary metadata provider.

The complete intended product scope remains existing-library Albums and
singletons with:

- reuse of valid stored fingerprints;
- explicitly authorized missing-fingerprint calculation;
- bounded HTTPS POST lookup requesting `meta=recordingids`;
- path-free and fingerprint-free preview;
- database-only storage of `acoustid_id` and `acoustid_fingerprint`;
- optional compatibility filtering for complete MusicBrainz release candidates.

AcoustID adds no structural score, writes no MusicBrainz field directly, chooses
no release occurrence, writes no audio file, submits no fingerprint, and does
not duplicate the native beets importer autotagger.

The frozen intended command options remain:

```text
--acoustid
--fingerprint-missing
```

## Completed Stage 01 Foundation

The merged implementation provides:

- immutable AcoustID domain values and stable reason vocabulary;
- canonical AcoustID UUID and recording-MBID validation;
- redacted fingerprint material;
- deterministic bounded result normalization;
- pure highest-support, tie, score, and margin classification;
- internal immutable settings and exact frozen defaults;
- strict offline validation and synthetic tests.

The implementation performs no network, subprocess, filesystem, beets database,
command, provider, or MusicBrainz integration.

## Active Stage 02 Documentation

The active documentation brief is:

```text
docs/specs/029-acoustid-identity-evidence/stage-02-existing-values-targets-backend.md
```

Its external implementation scope is limited to:

1. AcoustID-specific conversion of the established fresh Album/singleton
   selector;
2. stable Item database-ID local keys and deterministic order;
3. validation of existing `acoustid_id` and `acoustid_fingerprint` values;
4. lazy reuse of valid stored fingerprint material;
5. explicitly authorized missing or unusable fingerprint generation;
6. a direct, injectable, timeout- and output-bounded `fpcalc` backend;
7. no-follow regular-file snapshots before and after generation;
8. later source-snapshot verification helpers;
9. deterministic offline tests.

The backend decision is direct `fpcalc`, not `pyacoustid`. The exact production
argument vector is:

```text
<configured fpcalc> -json -length 120 -- <private media path>
```

The existing identity-library selector is reused without modification. Stage 02
must not duplicate or refactor that selection algorithm.

## Stage 02 Exclusions

Stage 02 still excludes:

- HTTPS lookup and response parsing;
- service API-key resolution;
- evidence lookup orchestration;
- database mapping and application;
- command parser and dispatch integration;
- public configuration integration;
- MusicBrainz compatibility filtering;
- provider or importer integration;
- dependencies, optional extras, package metadata, workflows, versions, tags,
  releases, README, site documentation, and changelog changes;
- all audio-file writes.

## Stop Condition

Do not begin Stage 02 product implementation until this documentation brief has
passed review, CI, and squash merge.
