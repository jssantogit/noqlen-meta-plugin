# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools
for beets.

## Profile

`core-lib`

## Context Level

`full` for Block 029 after completion of AcoustID Stage 03 and before definition
of the next standalone workflow stage.

## Tool Mode

Repository work from the project chat is documentation-only. Allowed changes are
limited to specs, stage briefs, ADRs, context, handoff, completion records, and
documentation-only PR administration.

Product code, implementation tests, dependencies, package metadata, workflows,
versions, tags, and releases are implemented outside this chat after their
documentation stage is approved.

## Active Block

Block 029 - AcoustID recording-level identity evidence.

Planning, contract freeze, and Stages 01-03 are integrated into `main`.

Important commits:

```text
6ad71d68347e23cecd45225900a10a8287acca54  planning
9945ed9cd693abc04b250d10239151b3281a7762  contract freeze
262aa688ac552b7ebb19156ed3c9a58a0f24ed06  Stage 01 brief
26506a79f23a899a810640b1a2bfa8d80a5c4c20  Stage 01 implementation
2f01c1d070d93b78bfba269439ca7b44de5c3e87  Stage 01 completion
56082b173c46d0ef47fc5808a9ababbc0004aa38  Stage 02 brief
5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc  Stage 02 implementation
8fc5cff7deefa3f24e9a092f96fdcd0035eb7d54  Stage 02 completion
ad06a3e3a61cbdb8b506b14afbfc72b1d18e75ee  Stage 03 brief
45c6dc20666b79bb057e34596e131a109ac22b38  Stage 03 implementation
```

PR #12 delivered Stage 03 product code from reviewed head
`89bbef8cd4588ec904f71cafa5a1e772f449b6ff`. CI run 59 passed all nine repository
jobs before squash merge on 2026-08-09.

The Stage 03 completion record is being added in the current documentation-only
branch.

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

`contracts.md` remains normative when earlier planning wording differs. Future
stage briefs may narrow implementation scope but cannot weaken the frozen product
contract.

## Released Baseline

Version 1.0.0 was released on 2026-08-02. Block 029 remains intended for the
1.1.0 release family. No version bump has been made.

## Frozen Product Decision

AcoustID is a separate recording-level identity-evidence subsystem, not an
ordinary metadata provider.

The complete intended product scope remains existing-library Albums and
singletons with:

- reuse of valid stored fingerprints;
- explicitly authorized missing-fingerprint calculation;
- bounded HTTPS POST lookup requesting `meta=recordingids`;
- path-free and fingerprint-free preview;
- database-only storage of `acoustid_id` and `acoustid_fingerprint`;
- optional compatibility filtering for complete MusicBrainz release candidates.

AcoustID adds no structural score, writes no MusicBrainz field directly, chooses
no release occurrence, writes no audio file, submits no fingerprint, and does
not duplicate native beets importer acoustic matching.

## Completed Stage 01

Stage 01 provides immutable domain values, canonical identifiers, redacted
fingerprint material, deterministic bounded evidence normalization/classification,
and exact internal settings/defaults.

## Completed Stage 02

Stage 02 provides fresh Album/singleton targets, existing-value validation, lazy
fingerprint reuse, explicitly authorized bounded direct `fpcalc`, no-follow
source snapshots, exact source-stability verification, and deterministic offline
coverage. The existing identity-library selector remains unmodified.

## Completed Stage 03

Stage 03 provides the standalone AcoustID HTTPS lookup boundary:

- lazy client-key resolution only for a real uncached lookup;
- exact HTTPS form POST to `https://api.acoustid.org/v2/lookup`;
- only the five frozen form fields;
- no retry and fail-closed redirects;
- verified TLS;
- 2 MiB request and 1 MiB incremental response caps;
- strict UTF-8 JSON/service/schema validation;
- bounded retention of only AcoustID UUID, score, and recording MBIDs;
- reuse of the Stage 01 evidence classifier;
- sequential monotonic pacing up to 3 req/s;
- framed SHA-256 process-local cache keys with successful-result caching only;
- sanitized operational failures and separately sanitized unexpected boundary
  failures;
- deterministic offline tests, including incomplete/truncated HTTP reads.

## Next Stage

No Stage 04 product implementation is active or authorized yet.

The next documentation stage should define the standalone workflow boundary for
path-free preview, exact database mapping/planning, stale-state validation, and
database-only application. It must preserve all-plan-before-first-write behavior,
re-fetch exact target state before mutation, and re-verify generated source
snapshots immediately before mutation.

MusicBrainz candidate filtering, public command/configuration integration,
provider/importer integration, release work, and audio-file writes remain outside
that next stage unless a reviewed brief explicitly separates and authorizes them.

## Stop Condition

Do not begin Stage 04 product implementation until its design/brief has been
reviewed, repository CI has passed, and the documentation PR has been
squash-merged. Product implementation remains outside this chat.
