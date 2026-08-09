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
```

PR #12 delivered Stage 03 from reviewed head
`89bbef8cd4588ec904f71cafa5a1e772f449b6ff`. CI run 59 passed all nine jobs and
the PR was squash-merged on 2026-08-09.

The current documentation-only branch records Stage 03 completion and
synchronizes project context before Stage 04 is designed.

ADR 0025 remains Accepted. `contracts.md` remains the normative product contract.

## Documentation-Only Chat Rule

Repository changes performed from this project chat are limited to specs, stage
briefs, ADRs, context/handoff, completion records, and documentation-only PR
administration. Product implementation happens outside this chat after its brief
is approved.

## Normative Artifacts

- `docs/specs/029-acoustid-identity-evidence/contracts.md`
- `docs/adr/0025-acoustid-recording-evidence.md`
- `docs/specs/029-acoustid-identity-evidence/requirements.md`
- `docs/specs/029-acoustid-identity-evidence/design.md`
- `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- `docs/specs/029-acoustid-identity-evidence/tasks.md`
- `docs/specs/029-acoustid-identity-evidence/stage-01-domain-policy-configuration.md`
- `docs/specs/029-acoustid-identity-evidence/stage-01-completion.md`
- `docs/specs/029-acoustid-identity-evidence/stage-02-existing-values-targets-backend.md`
- `docs/specs/029-acoustid-identity-evidence/stage-02-completion.md`
- `docs/specs/029-acoustid-identity-evidence/stage-03-https-transport-lookup.md`
- `docs/specs/029-acoustid-identity-evidence/stage-03-completion.md`

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

Frozen options remain:

```text
--acoustid
--fingerprint-missing
```

Frozen service credential remains:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

## Completed Stage 01

Stage 01 provides the side-effect-free domain, evidence-policy, and internal
configuration foundation: canonical identifiers, redacted fingerprint-bearing
values, bounded deterministic normalization, pure evidence classification, and
strict immutable settings/defaults.

## Completed Stage 02

Stage 02 provides:

- fresh AcoustID Album/singleton target conversion with stable local keys;
- existing `acoustid_id`/`acoustid_fingerprint` validation;
- fully lazy valid fingerprint reuse;
- explicitly authorized direct `fpcalc` generation;
- no-shell, bounded, nonblocking and sanitized subprocess execution;
- bounded terminate/kill/post-kill reap and reader cleanup;
- no-follow regular-file snapshots before/after generation;
- exact generated-source snapshot verification helper;
- deterministic offline tests across supported Python/beets CI.

The existing identity-library selector was not modified.

## Completed Stage 03

Stage 03 provides:

- lazy `NOQLENMETA_ACOUSTID_API_KEY` resolution only when network lookup is
  actually needed;
- exact bounded HTTPS form POST to the frozen AcoustID lookup endpoint;
- no retry, fail-closed redirects, and verified TLS;
- strict request and incremental response byte caps;
- strict UTF-8 JSON/service/schema validation;
- bounded retention only of AcoustID UUID, score, and recording MBIDs;
- reuse of the existing Stage 01 evidence classifier;
- monotonic sequential pacing within the 3 req/s ceiling;
- process-local digest cache without raw fingerprint or credential material;
- sanitized operational failures, including `IncompleteRead`, without caching;
- separately sanitized unexpected boundary/programmer failures;
- deterministic offline coverage with no mandatory live network test.

## Next Stage

No Stage 04 implementation is authorized yet.

The next documentation stage should define the standalone workflow around:

- path-free and fingerprint-free preview;
- exact database mapping and immutable plans;
- `AcoustIDTargetResult` ownership;
- exact selected-target/database snapshots;
- all-plan-before-first-write behavior;
- re-fetch and verification of target state immediately before mutation;
- re-verification of generated source snapshots before mutation;
- database-only writes of planned `acoustid_id` and `acoustid_fingerprint`
  fields;
- conflict, stale-state, no-op, and rollback-before-first-write tests.

MusicBrainz candidate filtering, command/public configuration integration,
provider/importer integration, dependencies, release work, and audio-file writes
remain deferred unless a later reviewed stage explicitly authorizes them.

## Stop Condition

Design and review the Stage 04 documentation before creating its external product
branch. The documentation must pass repository CI and be squash-merged first.
