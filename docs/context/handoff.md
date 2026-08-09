# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 planning, contract freeze, Stage 01,
and Stage 02 product implementation are merged into `main`.

```text
Planning:            6ad71d68347e23cecd45225900a10a8287acca54
Contracts:           9945ed9cd693abc04b250d10239151b3281a7762
Stage 01 brief:      262aa688ac552b7ebb19156ed3c9a58a0f24ed06
Stage 01 code:       26506a79f23a899a810640b1a2bfa8d80a5c4c20
Stage 01 completion: 2f01c1d070d93b78bfba269439ca7b44de5c3e87
Stage 02 brief:      56082b173c46d0ef47fc5808a9ababbc0004aa38
Stage 02 code:       5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc
```

PR #9 delivered the Stage 02 implementation from reviewed head
`32cb2b2e275e9bf3a0b5e495d3e24ae8511344b0`. CI run 53 passed on rerun after a
GitHub Actions outage and the PR was squash-merged on 2026-08-09.

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
- Stage 02 brief:
  `docs/specs/029-acoustid-identity-evidence/stage-02-existing-values-targets-backend.md`
- Stage 02 completion record:
  `docs/specs/029-acoustid-identity-evidence/stage-02-completion.md`

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

Stage 01 provides the side-effect-free domain, evidence-policy, and internal
configuration foundation: canonical identifiers, redacted fingerprint-bearing
values, bounded deterministic result normalization, pure recording-support
classification, and strict immutable settings/defaults.

## Completed Stage 02

Stage 02 provides the local existing-library and fingerprint-generation
boundary:

### Target selection

- reuses `beetsplug/noqlenmeta/identity/library.py` unchanged;
- converts complete fresh Albums and fresh singletons into AcoustID targets;
- preserves Album, singleton, and Item deterministic ordering;
- preserves stable `library-item:<id>` local keys;
- rejects missing targets and membership changes during refresh;
- retains media paths privately without display conversion.

### Existing values and lazy preparation

- validates `acoustid_id` and `acoustid_fingerprint` as `missing`, `valid`, or
  `malformed`;
- treats a stored AcoustID UUID as current state only, never fresh evidence;
- reuses stored fingerprint material only with finite positive duration;
- reusable material performs no stat, backend construction, executable
  discovery, or subprocess work;
- unauthorized missing or unusable material performs no filesystem/backend work;
- authorized generation acquires exact pre/post source snapshots.

### Backend strategy

The production backend directly invokes:

```text
<configured fpcalc> -json -length 120 -- <private media path>
```

The runner is no-shell, disconnected-stdin, timeout-bounded, output-bounded,
nonblocking, and sanitized. It caps retained stdout at 1 MiB and stderr at 64
KiB. Termination, kill, post-kill reap, and reader cleanup are all bounded.

`NOQLENMETA_ACOUSTID_API_KEY` is removed from the child environment without
being resolved or used.

### Source stability

Generated material requires equal no-follow regular-file snapshots immediately
before and after backend execution. Device, inode, size, and nanosecond mtime are
compared exactly. Symlinks and unsupported snapshot semantics fail closed.

A separate helper re-acquires and compares the generated source snapshot for a
future application stage.

## Preserved Stage 02 Exclusions

Stage 02 performs no:

- AcoustID HTTPS lookup or service payload parsing;
- service API-key resolution;
- database mapping or application;
- command parser/dispatch or public configuration integration;
- MusicBrainz compatibility filtering;
- ordinary provider/importer integration;
- dependency, optional-extra, package metadata, workflow, version, tag, release,
  README, changelog, or public-site changes;
- audio-file writes.

## Next Documentation Stage

No Stage 03 implementation is authorized yet.

The next documentation task is to define Stage 03 for the bounded AcoustID HTTPS
transport and lookup-normalization boundary. The brief should cover:

- API-key resolution only at the service transport boundary;
- bounded form-POST lookup requesting only `meta=recordingids`;
- sequential request pacing using monotonic time;
- request/response limits and strict UTF-8 JSON/schema validation;
- process-local caching keyed without exposing raw fingerprint material;
- deterministic fake-clock/fake-transport pacing, cache, and failure tests;
- safe mapping from transport/service failures to the frozen reason vocabulary.

Stage 03 must still exclude database mapping/application, command/public
configuration integration, MusicBrainz candidate filtering, ordinary
provider/importer integration, package/release work, and audio-file writes
unless its own reviewed brief explicitly authorizes them.

## Stop Condition

Merge the Stage 02 completion record before preparing the Stage 03 product
brief. No Stage 03 product implementation is performed from this chat.
