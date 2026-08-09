# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 planning, contract freeze, and AcoustID
Stages 01-03 are merged into `main`.

```text
Planning:            6ad71d68347e23cecd45225900a10a8287acca54
Contracts:           9945ed9cd693abc04b250d10239151b3281a7762
Stage 01 brief:      262aa688ac552b7ebb19156ed3c9a58a0f24ed06
Stage 01 code:       26506a79f23a899a810640b1a2bfa8d80a5c4c20
Stage 01 completion: 2f01c1d070d93b78bfba269439ca7b44de5c3e87
Stage 02 brief:      56082b173c46d0ef47fc5808a9ababbc0004aa38
Stage 02 code:       5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc
Stage 02 completion: 8fc5cff7deefa3f24e9a092f96fdcd0035eb7d54
Stage 03 brief:      ad06a3e3a61cbdb8b506b14afbfc72b1d18e75ee
Stage 03 code:       45c6dc20666b79bb057e34596e131a109ac22b38
Stage 03 completion: f7f29052ad9fc2c3f919e14991908d08a4bf0c4f
```

PR #12 delivered Stage 03 from reviewed head
`89bbef8cd4588ec904f71cafa5a1e772f449b6ff`; CI run 59 passed all nine jobs.
PR #13 then recorded Stage 03 completion.

The current documentation branch is:

```text
docs/029-acoustid-stage-04-workflow
```

It proposes the single Stage 04 design split into 04A Planning + Preview and 04B
Verified Database Application.

ADR 0025 remains Accepted. `contracts.md` remains the normative product contract.

## Documentation-Only Chat Rule

Repository changes performed from this project chat are limited to specs, stage
briefs, ADRs, context/handoff, completion records, and documentation-only PR
administration. Product implementation happens outside this chat after its brief
is approved.

## Accepted Product Architecture

AcoustID is recording-level identity evidence, not an ordinary metadata provider.
The complete intended flow remains:

- existing-library Albums and singletons;
- reuse or explicitly authorized local generation of fingerprint material;
- bounded HTTPS lookup with `meta=recordingids`;
- path-free/fingerprint-free preview;
- database-only `acoustid_id` and `acoustid_fingerprint` application;
- optional recording compatibility filtering for complete MusicBrainz release
  candidates.

It never adds structural score, writes MusicBrainz fields directly, chooses a
release occurrence, writes audio files, submits fingerprints, or replaces native
beets `chroma` importer behavior.

Frozen standalone options remain:

```text
--acoustid
--fingerprint-missing
```

Frozen service credential remains:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

## Completed Stage 01

Stage 01 owns canonical AcoustID/recording identifiers, immutable redacted
fingerprint/evidence values, bounded deterministic evidence classification, and
strict internal settings/defaults.

## Completed Stage 02

Stage 02 owns fresh Album/singleton target selection/conversion, exact refresh,
stored-value validation, lazy fingerprint reuse, explicitly authorized bounded
direct `fpcalc`, and no-follow generated-source snapshots/verification.

## Completed Stage 03

Stage 03 owns lazy client-key resolution, exact bounded HTTPS POST lookup,
strict retained schema, no retry, verified TLS, fail-closed redirects,
request/response caps, sequential monotonic pacing, process-local digest cache,
Stage 01 evidence classification reuse, sanitized failures, and fully offline
normal tests.

## Proposed Stage 04 Design

Document:

```text
docs/specs/029-acoustid-identity-evidence/
  stage-04-preview-mapping-database-application.md
```

Stage 04 is deliberately one design with two sequential implementation PRs.

### 04A - Planning + Preview

Purpose: create the complete immutable standalone AcoustID result without any
beets database mutation.

Key decisions:

- compose Stage 02 fingerprint preparation and Stage 03 lookup; do not duplicate
  them;
- add an exact AcoustID planning snapshot with target kind, membership/order,
  Item IDs, private path, length, and exact raw current `acoustid_id` /
  `acoustid_fingerprint`;
- preserve raw malformed current state so different malformed values are not
  treated as equal during stale checks;
- map only the two frozen AcoustID Item fields;
- states remain `KEEP | PROPOSE | REVIEW | BLOCKED`;
- decisive evidence alone may propose `acoustid_id`;
- generated/valid fingerprint material may propose `acoustid_fingerprint` even
  when lookup is unavailable;
- any different non-empty current value is `REVIEW`, never overwritten;
- add `AcoustIDTargetResult` containing target, exact snapshot, per-track
  outcomes/evidence, database plan, and generated-source snapshots;
- preview is pure, path-free, fingerprint-free, and performs no further I/O;
- 04A performs zero database mutation.

### 04B - Verified Database Application

Purpose: apply only already-prepared 04A plans.

Key decisions:

- accept the complete target-result application unit;
- perform canonical-plan validation and stale/source preflight for every target
  before the first mutation;
- detect duplicate target/Item identities;
- refresh via the existing AcoustID refresh boundary;
- require exact equality for membership/order/path/length/raw current AcoustID
  values;
- re-verify every generated Stage 02 source snapshot;
- any `REVIEW`, `BLOCKED`, stale target, changed current value, changed path, or
  stale source blocks the complete unit before the first store;
- persist only fields marked `PROPOSE` and only
  `acoustid_id`/`acoustid_fingerprint`;
- avoid broad stores that could leak unrelated dirty Item state;
- use target-level transaction/savepoint, in-transaction verification, rollback,
  fresh post-commit verification, and normal database-change notification
  semantics;
- no backend/network work and no audio-file writes;
- no promise to roll back targets already committed if a later unexpected target
  failure occurs; report committed state accurately, matching the existing
  library-identity philosophy.

There is no force or partial behavior.

## Proposed Product Sequence After Brief Merge

```text
feature/029-acoustid-stage-04a
  -> Planning + Preview only
  -> review + full CI + squash merge

feature/029-acoustid-stage-04b
  -> Database Application only
  -> branch from new main
  -> review + full CI + squash merge

then documentation-only Stage 04 completion record
```

Do not start 04B before 04A is merged.

## Explicit Stage 04 Exclusions

- command/parser/dispatch integration;
- public AcoustID configuration subtree;
- MusicBrainz compatibility filtering;
- ordinary provider/importer integration;
- dependency/package/workflow/version/release changes;
- public docs/changelog;
- audio-file writes or fingerprint submission.

## Next Repository Action

1. review the Stage 04 documentation diff;
2. run repository CI on the documentation PR;
3. squash-merge the brief only after PASS;
4. then prepare the external OpenCode implementation prompt for 04A only.

## Stop Condition

No Stage 04 product code is authorized until the current documentation PR has
passed review, CI, and squash merge. After that, only 04A is authorized first;
04B remains blocked until 04A is separately accepted and merged.
