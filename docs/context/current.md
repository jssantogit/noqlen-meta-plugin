# Current Context

## Project

Noqlen Meta — multi-provider metadata enrichment and MusicBrainz identity tools for beets.

Profile: `core-lib`.

## Active Block

Block 029 — AcoustID recording-level identity evidence.

Planning, contract freeze, and Stages 01-04 are integrated into `main`.

Current `main` baseline:

```text
f508d30c740891e04c92068d5eafbf9123896431
```

Version 1.0.0 remains the released baseline. Block 029 is intended for the 1.1.0 release family; no version bump has been made.

## Normative Precedence

1. `docs/specs/029-acoustid-identity-evidence/contracts.md`
2. `docs/adr/0025-acoustid-recording-evidence.md`
3. the current reviewed stage brief
4. older requirements/design wording

## Delivered Through Stage 04

The implemented AcoustID core provides:

- existing-library Album/singleton selection and exact refresh;
- stored fingerprint reuse and explicitly authorized bounded `fpcalc` generation;
- generated-source stability snapshots;
- bounded HTTPS `recordingids` lookup with strict parsing, privacy, pacing, caching, and no retry;
- decisive/ambiguous/no-match/unavailable recording evidence;
- exact standalone planning snapshots and canonical database plans;
- path-free/fingerprint-free preview;
- verified database-only application of `acoustid_id` and `acoustid_fingerprint` with global preflight, narrow persistence, target savepoints, rollback, post-commit verification, and conservative uncertain-commit reporting.

AcoustID still adds no structural score, writes no MusicBrainz field directly, chooses no release occurrence, writes no audio file, submits no fingerprint, and does not replace native beets `chroma` importer behavior.

## Active Stage 05 — Final Integration

Stage 05 is the **last product implementation stage** for Block 029. There is no Stage 06.

Approved brief:

```text
docs/specs/029-acoustid-identity-evidence/stage-05-final-integration.md
```

It combines the remaining product work in one implementation PR:

- pure decisive-recording expectations and MusicBrainz candidate compatibility filtering after existing structural evaluation;
- unchanged structural scores, assignments, thresholds, and safety gates;
- frozen `acoustid_recording_conflict` when decisive evidence rejects all candidates;
- optional AcoustID evidence in existing-library `--identity`, with no missing-fingerprint generation;
- standalone `--acoustid` / `--fingerprint-missing` command integration using Stage 02-04 boundaries;
- exact public `acoustid` configuration subtree validated through `AcoustIDSettings.from_mapping()`;
- early invalid-option rejection and lazy backend/environment/network behavior;
- no importer AcoustID behavior, no file writes, no direct MusicBrainz writes, no new dependency, and no release/version work.

## After Stage 05

After the Stage 05 product PR merges, Block 029 product implementation is complete. Remaining work is completion/release readiness only: public docs, changelog, built-artifact validation, final review, and any later version/tag/publication decision.

## Tool Boundary

Repository changes made from the project chat remain documentation-only. Product implementation continues externally after the Stage 05 brief is reviewed, CI-green, and merged.

## Stop Condition

Do not begin Stage 05 product implementation until the current Stage 05 documentation PR passes review, repository CI, and squash merge.
