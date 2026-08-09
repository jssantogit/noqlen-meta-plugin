# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 planning/contracts and AcoustID Stages 01-04 are integrated into `main`.

Current baseline:

```text
f508d30c740891e04c92068d5eafbf9123896431
```

Key Stage 04 commits:

```text
Stage 04 brief: 05738b320dca4eaa12cd84f7e02dc7fa919b58e8
Stage 04A code: 06951e1d3286d418ef52d8979a6cf3965658e28e
Stage 04B code: 24cc1a9c4def5445c63687c781df6af66807ddfa
Stage 04 completion: f508d30c740891e04c92068d5eafbf9123896431
```

ADR 0025 remains Accepted. `contracts.md` remains normative.

## Delivered Architecture

The standalone AcoustID core already owns existing-library target selection, stored-fingerprint reuse, explicitly authorized bounded generation, source stability, bounded lookup, evidence classification, exact database planning, safe preview, and verified database-only application.

No implemented AcoustID stage writes audio files or MusicBrainz fields, submits fingerprints, changes importer/autotagger behavior, or adds structural score.

## Final Stage 05

The approved design is one final implementation stage, not a sequence of 5A/5B and not a precursor to Stage 06.

Brief:

```text
docs/specs/029-acoustid-identity-evidence/stage-05-final-integration.md
```

Stage 05 finishes the product by delivering together:

1. **MusicBrainz compatibility filtering** — decisive AcoustID recording expectations filter already-evaluated complete candidates after structural assignment; scores/assignments/gates remain unchanged and non-decisive evidence is neutral.
2. **Existing-library identity integration** — optional AcoustID evidence under `acoustid.enabled && acoustid.use_for_identity`; identity mode reuses valid stored fingerprints only and never generates missing fingerprints.
3. **Standalone public command** — frozen `--acoustid` / `--fingerprint-missing`, query or `--all`, preview by default, database-only `--apply`, with invalid combinations rejected before local/network work.
4. **Public configuration** — exact frozen `acoustid` subtree validated through `AcoustIDSettings.from_mapping()` with the client key remaining environment-only.

When decisive evidence eliminates every candidate, the stable identity outcome is:

```text
acoustid_recording_conflict
```

The Stage 05 implementation remains existing-library only. Native beets `chroma` continues to own importer acoustic matching and submission.

## Stage 05 Exclusions

- no ordinary provider integration;
- no structural score additions or threshold changes;
- no direct MusicBrainz writes from AcoustID;
- no missing-fingerprint calculation in `--identity`;
- no importer AcoustID behavior;
- no audio-file writes;
- no fingerprint submission;
- no force/partial AcoustID behavior;
- no new AcoustID dependency;
- no version/tag/publication work.

## Next Repository Action

Review the Stage 05 documentation PR. Product implementation starts externally only after the brief is CI-green and squash-merged.

After the Stage 05 product PR itself merges, Block 029 product implementation is complete. Remaining work is completion/release readiness, not another implementation stage.

## Documentation-Only Chat Rule

Repository changes performed from this project chat remain limited to specifications, stage briefs, ADR/context/handoff/completion records, and documentation-only PR administration. Product code is implemented externally after the relevant brief is accepted.
