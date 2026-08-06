# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools
for beets.

## Profile

`core-lib`

## Context Level

`full` for Block 029 after completion of the AcoustID domain, evidence-policy,
and internal-settings foundation.

## Tool Mode

Repository work from the project chat is documentation-only. Allowed changes are
limited to specs, stage briefs, ADRs, context, handoff, completion records, and
documentation-only PR administration.

Product code, implementation tests, dependencies, package metadata, workflows,
versions, tags, and releases are implemented outside this chat after their
documentation stage is approved.

## Active Block

Block 029 - AcoustID recording-level identity evidence.

Planning, contract freeze, Stage 01 brief, and Stage 01 implementation are now
integrated into `main`.

Important commits:

```text
6ad71d68347e23cecd45225900a10a8287acca54  planning
9945ed9cd693abc04b250d10239151b3281a7762  contract freeze
262aa688ac552b7ebb19156ed3c9a58a0f24ed06  Stage 01 brief
26506a79f23a899a810640b1a2bfa8d80a5c4c20  Stage 01 implementation
```

PR #5 passed CI run 45 and was squash-merged on 2026-08-06.

## Normative Artifacts

- `docs/specs/029-acoustid-identity-evidence/contracts.md`
- `docs/adr/0025-acoustid-recording-evidence.md`
- `docs/specs/029-acoustid-identity-evidence/requirements.md`
- `docs/specs/029-acoustid-identity-evidence/design.md`
- `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- `docs/specs/029-acoustid-identity-evidence/tasks.md`
- `docs/specs/029-acoustid-identity-evidence/stage-01-domain-policy-configuration.md`
- `docs/specs/029-acoustid-identity-evidence/stage-01-completion.md`

`contracts.md` remains normative when earlier planning wording differs. The
Stage 01 brief and completion record define and report only the first external
implementation stage.

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

The merged implementation now provides:

- immutable AcoustID domain values and stable reason vocabulary;
- canonical AcoustID UUID and recording-MBID validation;
- redacted fingerprint material;
- deterministic bounded result normalization;
- pure highest-support, tie, score, and margin classification;
- internal immutable settings and exact frozen defaults;
- strict offline validation and synthetic tests.

The implementation performs no network, subprocess, filesystem, beets database,
command, provider, or MusicBrainz integration.

## Next Documentation Stage

No new implementation stage is active.

The next repository work from this chat is a Stage 02 documentation brief for:

1. existing beets AcoustID values;
2. fresh Album and singleton target selection;
3. stable local keys and deterministic Item order;
4. bounded fingerprint-backend execution;
5. source-file snapshot acquisition and stale verification.

Stage 02 must still exclude HTTPS lookup, API-key resolution, database
application, command integration, MusicBrainz filtering, package changes, and
release work unless a reviewed brief explicitly changes that boundary.

## Stop Condition

Do not begin Stage 02 product implementation until its documentation brief has
passed review, CI, and squash merge.
