# Block 029 Tasks

## Status

Block 029 product implementation is complete.

```text
Final product PR:      #19
Final reviewed head:   9b76ff87b14440ddc576a0f0d84277ee8c8d5d23
Main commit:           c5eabf80bbbe0f661aaa8867a78b3ebb83f0b3e3
Final product CI:      run 74, success
```

There is no Stage 06.

Detailed stage history and review findings are recorded in the Stage 01-05 briefs/completion records; this file now tracks only meaningful completion/release state rather than repeating those contracts.

## Completed Architecture And Product Work

- [x] Freeze AcoustID as recording-level identity evidence rather than a generic metadata provider.
- [x] Accept ADR 0025 and freeze command/configuration/privacy/coexistence contracts.
- [x] Keep native beets `chroma` ownership of importer acoustic matching/submission.
- [x] Implement immutable AcoustID domain/settings/evidence classification.
- [x] Implement existing-library Album/singleton selection and exact refresh.
- [x] Reuse valid stored fingerprints only under frozen policy.
- [x] Implement bounded direct `fpcalc` generation with explicit authority, source snapshots, subprocess/privacy bounds, and no new Python dependency.
- [x] Implement bounded HTTPS `recordingids` lookup with lazy credential resolution, strict parsing, pacing, caching, no retry, and offline normal CI.
- [x] Implement exact standalone planning, conflict semantics, private snapshots, and path/fingerprint-free preview.
- [x] Implement global stale/review preflight and verified database-only application limited to `acoustid_id` / `acoustid_fingerprint`.
- [x] Implement conservative transaction/commit uncertainty reporting and post-commit verification/notification semantics.
- [x] Implement decisive recording expectations and MusicBrainz candidate compatibility filtering after existing structural evaluation.
- [x] Preserve structural scores, assignments, pair scores, thresholds, and all existing identity gates.
- [x] Keep unavailable/no-match/ambiguous AcoustID evidence neutral.
- [x] Return `acoustid_recording_conflict` when decisive evidence rejects all candidates.
- [x] Integrate optional AcoustID evidence into existing-library `--identity` only.
- [x] Prohibit missing-fingerprint generation during `--identity`, including when `compute_missing=true`.
- [x] Add standalone `--acoustid` and `--fingerprint-missing` authority.
- [x] Preserve query XOR `--all`, database-only `--apply`, and early invalid-option rejection.
- [x] Integrate the exact public `acoustid` subtree through `AcoustIDSettings.from_mapping()`.
- [x] Preserve lazy backend/environment/network boundaries.
- [x] Preserve zero AcoustID audio-file writes, fingerprint submission, direct MusicBrainz writes, force/partial behavior, and importer integration.
- [x] Render all standalone target previews after complete planning and before application.

## Final Product Validation

- [x] Python 3.10 full offline tests/lint/hygiene.
- [x] Python 3.11 full offline tests/lint/hygiene.
- [x] Python 3.12 full offline tests/lint/hygiene.
- [x] Python 3.13 full offline tests/lint/hygiene.
- [x] Python 3.14 full offline tests/lint/hygiene.
- [x] beets minimum 2.12.0 compatibility.
- [x] latest beets below 3 compatibility.
- [x] documentation contract and strict documentation build.
- [x] package build and rendered metadata validation.
- [x] wheel/sdist archive inspection.
- [x] clean-install smoke test.
- [x] normal CI remains independent of live AcoustID, API key, real `fpcalc`, and audio-file writes.
- [x] Stage 05 external-review findings resolved before merge.

## Completion And Release Readiness

- [x] Record Stage 05 / Block 029 product implementation completion.
- [x] Synchronize current context and handoff to the merged Stage 05 baseline.
- [x] Public command and configuration references include standalone AcoustID and identity-filter behavior.
- [x] Public configuration examples include the frozen `acoustid` subtree.
- [ ] Replace the empty `Unreleased` changelog entry with Block 029 user-facing changes.
- [ ] Add concise README capability/write-boundary coverage for AcoustID.
- [ ] Add practical AcoustID troubleshooting coverage, including credential/fingerprint/chroma boundaries.
- [ ] Pass CI on the documentation-only completion/release-readiness PR.
- [ ] Obtain final documentation/release-readiness reviewer PASS.

After these items merge, Block 029 is closed. A version bump, tag, GitHub release, and PyPI publication are separate release administration decisions.

## Explicitly Deferred

- [ ] AcoustID fingerprint submission with user credentials and consent.
- [ ] Importer fingerprint generation owned by Noqlen.
- [ ] AcoustID-generated beets autotagger candidates.
- [ ] Direct AcoustID or generic metadata file writes.
- [ ] Force or partial identity repair.
- [ ] Direct release, release-group, or release-track identity from AcoustID.
