# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools
for beets.

## Profile

`core-lib`

## Context Level

`full` for Block 029 while the Stage 04 standalone workflow brief is under
review.

## Tool Mode

Repository work from the project chat is documentation-only. Allowed changes are
limited to specs, stage briefs, ADRs, context, handoff, completion records, and
documentation-only PR administration.

Product code, implementation tests, dependencies, package metadata, workflows,
versions, tags, and releases are implemented outside this chat after their
documentation stage is approved.

## Active Block

Block 029 - AcoustID recording-level identity evidence.

Planning, contract freeze, and Stages 01-03 are integrated into `main`.

Important commits:

```text
6ad71d68347e23cecd45225900a10a8287acca54  planning
9945ed9cd693abc04b250d10239151b3281a7762  contract freeze
262aa688ac552b7ebb19156ed3c9a58a0f24ed06  Stage 01 brief
26506a79f23a899a810640b1a2bfa8d80a5c4c20  Stage 01 implementation
2f01c1d070d93b78bfba269439ca7b44de5c3e87  Stage 01 completion
56082b173c46d0ef47fc5808a9ababbc0004aa38  Stage 02 brief
5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc  Stage 02 implementation
8fc5cff7deefa3f24e9a092f96fdcd0035eb7d54  Stage 02 completion
ad06a3e3a61cbdb8b506b14afbfc72b1d18e75ee  Stage 03 brief
45c6dc20666b79bb057e34596e131a109ac22b38  Stage 03 implementation
f7f29052ad9fc2c3f919e14991908d08a4bf0c4f  Stage 03 completion
```

PR #12 delivered Stage 03 product code from reviewed head
`89bbef8cd4588ec904f71cafa5a1e772f449b6ff`. CI run 59 passed all nine repository
jobs before squash merge on 2026-08-09. PR #13 recorded Stage 03 completion and
was also squash-merged.

## Normative Artifacts

- `docs/specs/029-acoustid-identity-evidence/contracts.md`
- `docs/adr/0025-acoustid-recording-evidence.md`
- `docs/specs/029-acoustid-identity-evidence/requirements.md`
- `docs/specs/029-acoustid-identity-evidence/design.md`
- `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- `docs/specs/029-acoustid-identity-evidence/tasks.md`
- Stage 01-03 implementation/completion briefs
- `docs/specs/029-acoustid-identity-evidence/stage-04-preview-mapping-database-application.md`
  on the current documentation branch

`contracts.md` remains normative when earlier planning wording differs. The Stage
04 brief may narrow implementation scope but cannot weaken the frozen product
contract.

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

## Completed Stages 01-03

Stage 01 provides immutable domain values, canonical identifiers, redacted
fingerprint material, deterministic bounded evidence normalization/classification,
and exact internal settings/defaults.

Stage 02 provides fresh Album/singleton targets, existing-value validation, lazy
fingerprint reuse, explicitly authorized bounded direct `fpcalc`, no-follow
source snapshots, exact source-stability verification, and deterministic offline
coverage. The existing identity-library selector remains unmodified.

Stage 03 provides lazy client-key resolution, exact bounded HTTPS form POST,
strict UTF-8/JSON/schema parsing, result bounding, no retry, monotonic pacing,
process-local digest caching, reuse of Stage 01 evidence classification,
sanitized failures, and deterministic offline tests.

## Proposed Stage 04

Stage 04 is one reviewed design with two sequential product PRs separated by the
mutation boundary:

### Stage 04A - Planning + Preview

- compose existing Stage 02 fingerprint preparation and Stage 03 lookup;
- capture an exact AcoustID target/database snapshot including membership,
  private path, length, and exact raw current AcoustID values;
- retain malformed current values exactly enough to detect concurrent changes;
- map only `acoustid_id` and `acoustid_fingerprint` to
  `KEEP | PROPOSE | REVIEW | BLOCKED`;
- add `AcoustIDTargetResult`;
- render path-free/fingerprint-free preview;
- perform zero database mutation.

### Stage 04B - Verified Database Apply

- consume only fully prepared Stage 04A results;
- perform global preflight of every selected target before the first mutation;
- re-fetch exact target state and re-verify generated source snapshots;
- treat any `REVIEW`, `BLOCKED`, stale target, stale current value, changed path,
  or stale source as a complete pre-write blocker;
- persist only planned `acoustid_id` / `acoustid_fingerprint` Item fields;
- use target-level transactional/rollback semantics matching the established
  library-identity philosophy;
- never perform fingerprint/backend/network work or file writes.

There is no partial or force behavior. A safe proposal elsewhere does not bypass
a conflict.

## Stage 04 Delivery Rule

The Stage 04 documentation brief must be reviewed, CI-green, and squash-merged
before either product branch begins.

Then:

1. implement/review/merge `feature/029-acoustid-stage-04a`;
2. implement/review/merge `feature/029-acoustid-stage-04b` from the new `main`;
3. record Stage 04 completion in one documentation-only follow-up.

Public command/configuration integration and MusicBrainz filtering are not part
of Stage 04.

## Stop Condition

Do not begin Stage 04A product implementation until the current documentation
brief passes review, repository CI, and squash merge. Do not begin Stage 04B
until Stage 04A itself has passed review, CI, and squash merge. Product
implementation remains outside this chat.
