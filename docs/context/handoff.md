# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 planning, contract freeze, Stage 01
brief, and Stage 01 implementation are merged into `main`.

```text
Planning:       6ad71d68347e23cecd45225900a10a8287acca54
Contracts:      9945ed9cd693abc04b250d10239151b3281a7762
Stage 01 brief: 262aa688ac552b7ebb19156ed3c9a58a0f24ed06
Stage 01 code:  26506a79f23a899a810640b1a2bfa8d80a5c4c20
```

PR #5 used reviewed head
`c91f34d3d175c4ace558fc431d55d2b62dc55c68`, passed CI run 45, and was
squash-merged on 2026-08-06.

ADR 0025 remains Accepted. `contracts.md` remains the normative product
contract.

## Documentation-Only Chat Rule

Repository changes performed from this project chat are limited to:

- specifications and stage briefs;
- ADRs;
- context and handoff documents;
- completion records;
- documentation-only PR administration.

Product implementation happens outside this chat after the matching brief is
approved.

## Normative Artifacts

- Frozen contracts:
  `docs/specs/029-acoustid-identity-evidence/contracts.md`
- Accepted ADR:
  `docs/adr/0025-acoustid-recording-evidence.md`
- Requirements and design:
  `docs/specs/029-acoustid-identity-evidence/requirements.md`
  `docs/specs/029-acoustid-identity-evidence/design.md`
- Forge-to-Meta parity matrix:
  `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- Task sequence:
  `docs/specs/029-acoustid-identity-evidence/tasks.md`
- Stage 01 brief:
  `docs/specs/029-acoustid-identity-evidence/stage-01-domain-policy-configuration.md`
- Stage 01 completion record:
  `docs/specs/029-acoustid-identity-evidence/stage-01-completion.md`

## Accepted Product Architecture

AcoustID is recording-level identity evidence. It is not an ordinary metadata
provider and cannot emit ordinary metadata candidates.

The complete intended product scope remains:

- existing-library Albums and singletons;
- reuse of valid stored AcoustID fingerprints;
- explicitly authorized missing-fingerprint calculation;
- bounded HTTPS POST lookup with `meta=recordingids`;
- path-free and fingerprint-free preview;
- database-only storage of `acoustid_id` and `acoustid_fingerprint`;
- optional recording compatibility filtering for complete MusicBrainz release
  candidates.

AcoustID adds no structural score, writes no MusicBrainz field directly, chooses
no release occurrence, writes no audio file, submits no fingerprint, and does
not duplicate the native beets importer autotagger.

The frozen intended options remain:

```text
--acoustid
--fingerprint-missing
```

The frozen intended settings remain:

```yaml
acoustid:
  enabled: false
  reuse_existing: true
  compute_missing: false
  lookup: true
  use_for_identity: true
  min_score: 0.90
  min_margin: 0.05
  max_results: 5
  max_recordings_per_result: 10
  timeout_seconds: 15.0
  requests_per_second: 3.0
  cache_entries: 256
  fpcalc: fpcalc
```

The exact future credential variable remains:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

## Completed Stage 01

The merged Stage 01 implementation provides:

- immutable fingerprint-origin, verdict, reason, fingerprint-material,
  result-group, evidence-policy, source-snapshot, and track-evidence values;
- canonical AcoustID UUID and MusicBrainz recording-MBID validation;
- redacted fingerprint representations and generic validation errors;
- conflict-safe and deterministic result normalization;
- pure highest-support, score, tie, and margin classification;
- exact internal immutable settings and fresh defaults;
- strict synthetic offline tests.

Review amendments established these important invariants:

- conflicting duplicate AcoustID groups are rejected;
- padded `.` and `..` local keys are rejected;
- decisive evidence cannot hide tied or stronger competing recordings;
- eligible counts, top support, runner-up support, and margin must agree with the
  result groups;
- fingerprints do not appear in representations or validation errors.

Stage 01 intentionally contains no network, environment-key, subprocess,
filesystem, beets database, command, provider, MusicBrainz integration, public
configuration, dependency, workflow, version, tag, or release work.

## Next Stage

No product stage is currently authorized.

The next documentation task is to define Stage 02 for:

1. reading and validating existing beets AcoustID fields;
2. fresh existing-library Album and singleton target selection;
3. stable database-ID local keys and deterministic Item order;
4. an injectable, bounded fingerprint backend;
5. backend discovery only for explicitly authorized missing calculations;
6. source-file snapshot acquisition and stale verification.

Stage 02 must still exclude:

- AcoustID HTTPS lookup and response parsing;
- API-key resolution;
- database application;
- command integration;
- MusicBrainz compatibility filtering;
- public configuration integration;
- dependencies, package metadata, version, tag, and release work.

Any change to those exclusions requires a separately reviewed documentation
contract.

## Stop Condition

Prepare and merge the Stage 02 documentation brief before starting any new
product branch. No product implementation is performed from this chat.
