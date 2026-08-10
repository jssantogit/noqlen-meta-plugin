# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 — AcoustID recording-level identity evidence — has completed product implementation.

Current `main` baseline:

```text
c5eabf80bbbe0f661aaa8867a78b3ebb83f0b3e3
```

Key final commits:

```text
Stage 05 brief:       f78700846c531a99a02edd3102f3fba8f87c0f9f
Stage 05 reviewed:    9b76ff87b14440ddc576a0f0d84277ee8c8d5d23
Stage 05 product:     c5eabf80bbbe0f661aaa8867a78b3ebb83f0b3e3
Final product CI:     run 74, success
```

ADR 0025 remains Accepted. `contracts.md` remains the architectural reference for Block 029.

## Delivered Product

Block 029 now includes the complete existing-library AcoustID workflow:

1. Album/singleton selection and refresh.
2. Stored fingerprint reuse and explicitly authorized standalone `fpcalc` generation.
3. Source-file stability checks.
4. Bounded AcoustID `recordingids` lookup and recording-level evidence classification.
5. Safe standalone planning/preview and verified database-only application of `acoustid_id` / `acoustid_fingerprint`.
6. Pure decisive-recording compatibility filtering over MusicBrainz candidates after structural evaluation.
7. Optional AcoustID evidence in existing-library `--identity`, with no missing-fingerprint generation.
8. Public `--acoustid` / `--fingerprint-missing` command handling and frozen `acoustid` configuration.

## Safety Boundaries

The final implementation still has no:

- AcoustID structural score or threshold relaxation;
- direct MusicBrainz field write from AcoustID;
- release-occurrence selection from AcoustID alone;
- audio-file write or fingerprint submission;
- Noqlen-owned importer fingerprint generation/autotagger path;
- force/partial AcoustID repair;
- hidden fingerprint generation in `--identity`;
- new AcoustID Python dependency.

Native beets `chroma` continues to own importer acoustic matching/submission behavior.

## Final Review History

External review found and resolved one Stage 05 ordering issue: standalone previews now render after all planning and before application.

PR #19 CI run 73 then failed during test collection because one new test imported `tests.identity.helpers` from a non-package `tests` directory. The fix kept the UUID helper local to `tests/acoustid/test_command.py`. CI run 74 subsequently passed all repository gates on the final reviewed head.

## Next Repository Action

Finish the single documentation-only Block 029 completion/release-readiness PR. It should:

- record Stage 05 / Block 029 completion;
- synchronize task/context/handoff state;
- replace the empty Unreleased changelog entry with the delivered AcoustID capability;
- keep public command/configuration/troubleshooting material aligned;
- pass repository CI.

After that, Block 029 is closed. Any 1.1.0 version bump, tag, GitHub release, or PyPI publication is a separate release decision, not Stage 06.

## Documentation-Only Chat Rule

Repository changes performed from this project chat remain specifications, ADR/context/handoff/completion records, public documentation, and release administration. Future product behavior belongs to a new explicitly approved block.
