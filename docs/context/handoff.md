# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 planning/contracts and AcoustID Stages 01-04 are integrated into `main`.

```text
Planning:            6ad71d68347e23cecd45225900a10a8287acca54
Contracts:           9945ed9cd693abc04b250d10239151b3281a7762
Stage 01 code:       26506a79f23a899a810640b1a2bfa8d80a5c4c20
Stage 01 completion: 2f01c1d070d93b78bfba269439ca7b44de5c3e87
Stage 02 code:       5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc
Stage 02 completion: 8fc5cff7deefa3f24e9a092f96fdcd0035eb7d54
Stage 03 code:       45c6dc20666b79bb057e34596e131a109ac22b38
Stage 03 completion: f7f29052ad9fc2c3f919e14991908d08a4bf0c4f
Stage 04 brief:      05738b320dca4eaa12cd84f7e02dc7fa919b58e8
Stage 04A code:      06951e1d3286d418ef52d8979a6cf3965658e28e
Stage 04B code:      24cc1a9c4def5445c63687c781df6af66807ddfa
```

Stage 04A was delivered by PR #15 from reviewed head `7957afb3b122a6e0a79a2174eb624efbcd608ba1`; CI run 65 passed before squash merge.

Stage 04B was delivered by PR #16 from final reviewed head `2d887ec4ad9cd9945e097133a66b2fc86dae1268`; CI run 67 passed before squash merge.

ADR 0025 remains Accepted. `contracts.md` remains normative.

## Delivered Architecture

AcoustID is recording-level identity evidence, not an ordinary metadata provider.

The implemented standalone core now provides:

- fresh existing-library Album/singleton targets;
- stored fingerprint reuse and explicitly authorized bounded local generation;
- exact generated-source stability checks;
- bounded HTTPS `recordingids` lookup;
- decisive/ambiguous/no-match/unavailable recording evidence;
- exact standalone planning snapshots;
- `KEEP | PROPOSE | REVIEW | BLOCKED` database plans limited to `acoustid_id` and `acoustid_fingerprint`;
- path-free/fingerprint-free preview;
- verified database-only application with global preflight, exact stale checks, narrow SQL, per-target savepoints, rollback, fresh post-commit verification, and accurate uncertain-commit reporting.

No AcoustID stage so far writes audio files or MusicBrainz fields, submits fingerprints, modifies importer/autotagger behavior, or adds structural score.

Frozen future standalone options remain:

```text
--acoustid
--fingerprint-missing
```

Frozen service credential remains:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

## Review Note From Stage 04B

External review found and fixed one commit-state blocker before merge. Releasing the target savepoint is not proof that the root transaction committed. Root transaction exit failures now report `COMMIT_UNCERTAIN`; only earlier targets with confirmed commits are counted as committed.

## Next Repository Action

Define the narrow next stage for **MusicBrainz recording-compatibility filtering**.

The next stage must remain pure with respect to persistence and should only:

1. derive recording expectations from decisive AcoustID evidence;
2. compare those expectations against already structurally evaluated complete MusicBrainz candidates/assignments;
3. reject incompatible complete candidates without changing structural scores;
4. treat non-decisive AcoustID evidence as neutral;
5. surface the frozen `acoustid_recording_conflict` outcome when decisive evidence rejects every candidate.

It must not yet add public command/configuration integration.

## Documentation-Only Chat Rule

Repository changes performed from this project chat remain limited to specifications, stage briefs, ADR/context/handoff/completion records, and documentation-only PR administration. Product code continues to be implemented externally after the relevant brief is accepted.
