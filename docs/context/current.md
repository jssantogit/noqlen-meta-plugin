# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools
for beets.

## Profile

`core-lib`

## Context Level

`full` for Block 029 after completion of the local existing-value,
fingerprint-backend, and source-snapshot stage.

## Tool Mode

Repository work from the project chat is documentation-only. Allowed changes are
limited to specs, stage briefs, ADRs, context, handoff, completion records, and
documentation-only PR administration.

Product code, implementation tests, dependencies, package metadata, workflows,
versions, tags, and releases are implemented outside this chat after their
documentation stage is approved.

## Active Block

Block 029 - AcoustID recording-level identity evidence.

Planning, contract freeze, Stage 01, and Stage 02 product implementation are now
integrated into `main`.

Important commits:

```text
6ad71d68347e23cecd45225900a10a8287acca54  planning
9945ed9cd693abc04b250d10239151b3281a7762  contract freeze
262aa688ac552b7ebb19156ed3c9a58a0f24ed06  Stage 01 brief
26506a79f23a899a810640b1a2bfa8d80a5c4c20  Stage 01 implementation
2f01c1d070d93b78bfba269439ca7b44de5c3e87  Stage 01 completion record
56082b173c46d0ef47fc5808a9ababbc0004aa38  Stage 02 brief
5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc  Stage 02 implementation
```

PR #9 delivered Stage 02 product code. The reviewed head was
`32cb2b2e275e9bf3a0b5e495d3e24ae8511344b0`; CI run 53 passed on rerun after a
GitHub Actions outage, and the PR was squash-merged on 2026-08-09.

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
- `docs/specs/029-acoustid-identity-evidence/stage-02-completion.md`

`contracts.md` remains normative when earlier planning wording differs.

## Released Baseline

Version 1.0.0 was released on 2026-08-02. Block 029 remains intended for the
1.1.0 release family. No version bump has been made.

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

The merged implementation provides immutable AcoustID domain values, canonical
identifier validation, redacted fingerprint material, deterministic evidence
normalization/classification, and exact internal settings/defaults.

## Completed Stage 02 Foundation

The merged implementation now also provides:

- AcoustID-specific conversion of fresh Album/singleton identity targets;
- stable Item database-ID local keys and deterministic order;
- fresh validation of existing `acoustid_id` and `acoustid_fingerprint` values;
- fully lazy reuse of valid stored fingerprint material;
- explicitly authorized local fingerprint generation;
- direct bounded `fpcalc` execution with nonblocking pipe readers;
- bounded terminate, kill, post-kill reap, and reader cleanup;
- sanitized child environment with the AcoustID service key removed;
- no-follow regular-file snapshots before and after generation;
- exact source-stability verification helpers;
- deterministic offline tests across the supported Python and beets matrix.

The existing identity-library selector remains unmodified.

## Next Documentation Stage

No Stage 03 product implementation is active yet.

The next repository work from this chat is a Stage 03 documentation brief for
the bounded AcoustID HTTPS transport and lookup-normalization boundary.

The brief should define:

1. service API-key resolution only at the transport boundary;
2. bounded HTTPS form POST requesting only `meta=recordingids`;
3. sequential request pacing within the configured ceiling;
4. request/response limits and strict UTF-8 JSON/schema validation;
5. process-local cache keys that do not expose raw fingerprint material;
6. deterministic fake-clock/fake-transport offline tests;
7. sanitized mapping of transport/service failures to existing evidence reasons.

Stage 03 must still exclude database mapping/application, command integration,
public configuration integration, MusicBrainz candidate filtering, ordinary
provider/importer integration, package/release work, and audio-file writes unless
its own reviewed brief explicitly authorizes them.

## Stop Condition

Prepare, review, pass CI, and squash-merge the Stage 02 completion record before
starting the Stage 03 product brief. No Stage 03 product implementation is
performed from this chat.
