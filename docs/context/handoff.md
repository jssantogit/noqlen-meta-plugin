# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 planning, contract freeze, Stage 01,
Stage 02 implementation, and the Stage 02 completion record are merged into
`main`.

```text
Planning:            6ad71d68347e23cecd45225900a10a8287acca54
Contracts:           9945ed9cd693abc04b250d10239151b3281a7762
Stage 01 brief:      262aa688ac552b7ebb19156ed3c9a58a0f24ed06
Stage 01 code:       26506a79f23a899a810640b1a2bfa8d80a5c4c20
Stage 01 completion: 2f01c1d070d93b78bfba269439ca7b44de5c3e87
Stage 02 brief:      56082b173c46d0ef47fc5808a9ababbc0004aa38
Stage 02 code:       5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc
Stage 02 completion: 8fc5cff7deefa3f24e9a092f96fdcd0035eb7d54
```

PR #9 delivered Stage 02 product code from reviewed head
`32cb2b2e275e9bf3a0b5e495d3e24ae8511344b0`; CI run 53 passed. PR #10 recorded
Stage 02 completion; CI run 55 passed and the PR was squash-merged on 2026-08-09.

ADR 0025 remains Accepted. `contracts.md` remains the normative product
contract.

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
- proposed: `docs/specs/029-acoustid-identity-evidence/stage-03-https-transport-lookup.md`

## Accepted Product Architecture

AcoustID is recording-level identity evidence, not an ordinary metadata
provider. The complete intended flow remains:

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

## Proposed Stage 03

The next product stage is not authorized yet. Its proposed brief is:

```text
docs/specs/029-acoustid-identity-evidence/stage-03-https-transport-lookup.md
```

The AcoustID service contract was revalidated against the official web-service
documentation on 2026-08-09.

The proposed Stage 03 boundary freezes:

- lazy application-key resolution only at network lookup;
- exact POST to `https://api.acoustid.org/v2/lookup`;
- exact form fields: client, rounded duration, fingerprint,
  `meta=recordingids`, `format=json`;
- no retry and fail-closed redirect behavior;
- sequential monotonic pacing at no more than 3 requests/second;
- 2 MiB request and 1 MiB response caps;
- strict UTF-8 JSON plus service/schema validation;
- retention only of result AcoustID UUID, score, and recording MBIDs;
- bounded parsing by existing `max_results` and
  `max_recordings_per_result` settings;
- framed SHA-256 process-local cache key without raw fingerprint or key;
- cache of successful parsed lookups only;
- safe use of existing reasons (`lookup_disabled`, `client_key_missing`,
  `lookup_failed`) and existing Stage 01 classifier;
- deterministic fake-clock/fake-transport tests with normal CI fully offline.

## Preserved Stage 03 Exclusions

No Stage 03 product branch may add database planning/application, command or
public-config integration, preview rendering, MusicBrainz filtering, provider or
importer registration, fingerprint submission, User API-key handling,
dependencies, package/workflow/release/public-doc changes, or audio-file writes.

## Stop Condition

Review, pass CI, and squash-merge the Stage 03 brief before creating its product
branch. Stage 03 implementation remains outside this chat.
