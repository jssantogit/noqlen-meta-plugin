# Current Context

## Project

Noqlen Meta — multi-provider metadata enrichment and MusicBrainz identity tools for beets.

Profile: `core-lib`.

## Active Block

Block 029 — AcoustID recording-level identity evidence.

Planning, contract freeze, and Stages 01-04 are integrated into `main`.

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

Version 1.0.0 remains the released baseline. Block 029 is intended for the 1.1.0 release family; no version bump has been made.

## Normative Artifacts

1. `docs/specs/029-acoustid-identity-evidence/contracts.md`
2. `docs/adr/0025-acoustid-recording-evidence.md`
3. the current reviewed stage brief
4. older requirements/design documents

`contracts.md` wins on conflict.

## Delivered Through Stage 04

- immutable AcoustID/fingerprint/evidence domain and internal policy;
- fresh Album/singleton target selection and exact refresh;
- valid stored fingerprint reuse and explicitly authorized bounded `fpcalc` generation;
- exact generated-source snapshots and verification;
- bounded HTTPS AcoustID lookup with strict parsing, pacing, caching, privacy, and no retry;
- recording-level evidence classification;
- exact standalone planning snapshots and canonical database plans;
- path-free/fingerprint-free preview;
- database-only verified application of `acoustid_id` and `acoustid_fingerprint`;
- global preflight before first write, target savepoints, rollback, post-commit verification, and conservative uncertain-commit reporting.

AcoustID still adds no structural score, writes no MusicBrainz field directly, chooses no release occurrence, writes no audio file, submits no fingerprint, and does not replace native beets `chroma` importer behavior.

## Next Stage

The next implementation boundary is the **pure MusicBrainz recording-compatibility filter**.

It should:

- map decisive AcoustID evidence to local-key recording expectations;
- run only after existing MusicBrainz candidate structure/assignments are evaluated;
- preserve every existing structural score component and threshold;
- treat unavailable, no-match, and ambiguous AcoustID evidence as neutral;
- reject complete candidates that contradict decisive recording evidence;
- return the frozen conflict reason when decisive evidence rejects every candidate;
- never allow AcoustID to rescue weak structure, weak assignments, incomplete assignments, or insufficient margin;
- write no MusicBrainz or audio-file fields.

Public command/configuration integration remains later.

## Tool Boundary

Repository changes made from the project chat remain documentation-only. Product implementation continues externally after its stage brief is approved.

## Stop Condition

Do not begin the MusicBrainz compatibility-filter product implementation until its narrow stage brief is reviewed, CI-green, and merged.
