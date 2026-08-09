# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools
for beets.

## Profile

`core-lib`

## Context Level

`full` for Block 029 after completion of Stage 02 and during review of the
bounded AcoustID HTTPS transport stage.

## Tool Mode

Repository work from the project chat is documentation-only. Allowed changes are
limited to specs, stage briefs, ADRs, context, handoff, completion records, and
documentation-only PR administration.

Product code, implementation tests, dependencies, package metadata, workflows,
versions, tags, and releases are implemented outside this chat after their
documentation stage is approved.

## Active Block

Block 029 - AcoustID recording-level identity evidence.

Planning, contract freeze, Stage 01, Stage 02 implementation, and the Stage 02
completion record are integrated into `main`.

Important commits:

```text
6ad71d68347e23cecd45225900a10a8287acca54  planning
9945ed9cd693abc04b250d10239151b3281a7762  contract freeze
262aa688ac552b7ebb19156ed3c9a58a0f24ed06  Stage 01 brief
26506a79f23a899a810640b1a2bfa8d80a5c4c20  Stage 01 implementation
2f01c1d070d93b78bfba269439ca7b44de5c3e87  Stage 01 completion record
56082b173c46d0ef47fc5808a9ababbc0004aa38  Stage 02 brief
5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc  Stage 02 implementation
8fc5cff7deefa3f24e9a092f96fdcd0035eb7d54  Stage 02 completion record
```

PR #9 delivered Stage 02 product code from reviewed head
`32cb2b2e275e9bf3a0b5e495d3e24ae8511344b0`; CI run 53 passed and the PR was
squash-merged. PR #10 recorded Stage 02 completion; CI run 55 passed and it was
squash-merged on 2026-08-09.

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
- `docs/specs/029-acoustid-identity-evidence/stage-03-https-transport-lookup.md`

`contracts.md` remains normative when earlier planning wording differs. The
Stage 03 brief narrows only the third external implementation branch and cannot
weaken the frozen product contract.

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
not duplicate native beets importer acoustic matching.

## Completed Foundations

Stage 01 provides immutable domain values, canonical identifiers, redacted
fingerprint material, deterministic bounded evidence normalization/classification,
and exact internal settings/defaults.

Stage 02 provides fresh Album/singleton AcoustID targets, existing-value
validation, fully lazy fingerprint reuse, explicitly authorized bounded direct
`fpcalc`, no-follow source snapshots, exact source-stability verification, and
deterministic offline coverage. The existing identity-library selector remains
unmodified.

## Active Stage 03 Documentation

The proposed Stage 03 brief is:

```text
docs/specs/029-acoustid-identity-evidence/stage-03-https-transport-lookup.md
```

The official AcoustID web-service contract was revalidated on 2026-08-09 before
writing the brief. Stage 03 freezes:

- service credential resolution only at the lookup boundary;
- exact HTTPS form POST to `https://api.acoustid.org/v2/lookup`;
- only `client`, rounded `duration`, private `fingerprint`,
  `meta=recordingids`, and `format=json`;
- no retry;
- sequential monotonic pacing at configured rate up to 3 req/s;
- 2 MiB request and 1 MiB response defensive caps;
- strict UTF-8 JSON/service/schema validation;
- only AcoustID UUID, score, and recording MBID retention;
- SHA-256 framed cache keys without raw fingerprint or credential;
- process-local successful-result cache only;
- generic safe mapping to `lookup_disabled`, `client_key_missing`, and
  `lookup_failed` before existing evidence classification;
- fully deterministic offline tests and no mandatory live service test.

## Stage 03 Exclusions

Stage 03 still excludes:

- database mapping, snapshots, application, and stores;
- standalone preview rendering;
- command parser/dispatch and public configuration integration;
- MusicBrainz candidate filtering;
- provider/importer integration;
- submission or User API-key handling;
- dependencies, package/workflow/release/public-doc changes;
- audio-file writes.

## Stop Condition

Do not begin Stage 03 product implementation until the Stage 03 brief has passed
review, repository CI, and squash merge. Product implementation remains outside
this chat.
