# Block 029 Stage 04 Completion Record

## Status

Complete and merged on 2026-08-09.

Stage 04 was delivered as two product PRs separated by the mutation boundary:

```text
Stage 04 brief: 05738b320dca4eaa12cd84f7e02dc7fa919b58e8

04A PR:          #15
04A reviewed:    7957afb3b122a6e0a79a2174eb624efbcd608ba1
04A main commit: 06951e1d3286d418ef52d8979a6cf3965658e28e
04A CI:          run 65, success

04B PR:          #16
04B reviewed:    2d887ec4ad9cd9945e097133a66b2fc86dae1268
04B main commit: 24cc1a9c4def5445c63687c781df6af66807ddfa
04B CI:          run 67, success
```

This record changes no product behavior.

## Delivered

### Stage 04A — Planning + Preview

- exact immutable AcoustID planning snapshots for Albums and singletons;
- exact raw current `acoustid_id` / `acoustid_fingerprint` retention for stale detection;
- composition of existing Stage 02 fingerprint preparation and Stage 03 lookup/evidence;
- canonical database planning limited to `acoustid_id` and `acoustid_fingerprint`;
- `KEEP | PROPOSE | REVIEW | BLOCKED` conflict semantics;
- immutable `AcoustIDTargetResult` with generated-source snapshots for later verification;
- deterministic path-free and fingerprint-free preview;
- zero database mutation from the planning/preview stage.

### Stage 04B — Verified Database Application

- global preflight of the complete application unit before the first write;
- rejection of noncanonical plans, duplicate target/item identities, `REVIEW`, `BLOCKED`, stale targets, changed exact raw values, and stale generated sources;
- exact target refresh and generated-source re-verification before mutation;
- narrow SQL persistence only for fields marked `PROPOSE` and only for `acoustid_id` / `acoustid_fingerprint`;
- isolation from unrelated dirty Item state;
- target-level savepoint, in-transaction revalidation, rollback, post-commit fresh verification, and `database_change` notifications only for successfully committed changed Items;
- conservative `COMMIT_UNCERTAIN` handling when the root transaction boundary does not prove commit;
- accurate accounting of earlier confirmed target commits when a later target fails;
- no backend, network, credential, MusicBrainz, or audio-file write authority.

## Review Finding Resolved

External review found one Stage 04B blocker: the initial implementation treated inner savepoint release as proof that the root transaction had committed. That could falsely report `committed=True` when the root transaction exit itself failed.

The final reviewed head removed that inference. A root transaction boundary failure is now `COMMIT_UNCERTAIN`; the current target is not counted as committed unless the transaction returns normally. Earlier targets that were already confirmed committed remain reported accurately.

## Validation

The final reviewed Stage 04A and 04B heads both passed the repository CI matrix before squash merge. Normal AcoustID tests remain offline and require no live AcoustID service, API key, real `fpcalc` execution, or audio-file fixture for application behavior.

The Stage 04 product diffs remained inside their approved allowlists. No public command/configuration, MusicBrainz candidate-filtering, provider/importer, package, version, release, or public-documentation surface was added.

## Next Boundary

The next product stage is the pure MusicBrainz recording-compatibility filter described by the frozen AcoustID contracts:

- convert decisive AcoustID evidence to recording expectations;
- evaluate compatibility only after existing MusicBrainz structural candidate evaluation/assignments;
- preserve all existing structural score components and thresholds;
- treat unavailable/no-match/ambiguous AcoustID evidence as neutral;
- reject complete candidates that contradict decisive recording evidence;
- never let AcoustID rescue structurally weak or incomplete candidates;
- still perform no AcoustID-driven MusicBrainz writes.

Public command/configuration integration remains a later stage.
