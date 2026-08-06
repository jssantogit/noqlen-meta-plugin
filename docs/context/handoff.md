# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 planning, contract freeze, Stage 01
brief, Stage 01 implementation, and the Stage 01 completion record are merged
into `main`.

```text
Planning:            6ad71d68347e23cecd45225900a10a8287acca54
Contracts:           9945ed9cd693abc04b250d10239151b3281a7762
Stage 01 brief:      262aa688ac552b7ebb19156ed3c9a58a0f24ed06
Stage 01 code:       26506a79f23a899a810640b1a2bfa8d80a5c4c20
Stage 01 completion: 2f01c1d070d93b78bfba269439ca7b44de5c3e87
```

PR #5 delivered the Stage 01 implementation and passed CI run 45. PR #6
recorded Stage 01 completion and passed CI run 47.

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

## Stage 02 Documentation Decision

The Stage 02 brief covers the local existing-value and fingerprint-generation
boundary only.

### Target selection

The implementation must reuse the existing fresh identity-library selector in:

```text
beetsplug/noqlenmeta/identity/library.py
```

It converts those selected values into AcoustID-specific immutable targets. It
must not duplicate or modify the selector.

The retained behavior is:

- Item query expansion to complete fresh Albums and fresh singletons;
- Album order by Album database ID;
- singleton order by Item database ID;
- Album Item order by disc, track, then Item ID;
- stable `library-item:<id>` local keys;
- changed membership rejected during refresh.

### Existing values

The stage validates current beets `acoustid_id` and
`acoustid_fingerprint` values as `missing`, `valid`, or `malformed`.

A stored AcoustID UUID is current state only. It is not fresh recording
evidence. A valid stored fingerprint may be reused only with a finite positive
Item duration.

A reusable fingerprint must avoid backend creation, executable resolution,
filesystem stat, and subprocess work. Missing or unusable material is generated
only when settings or a future invocation override explicitly authorize it.

### Backend strategy

The selected initial backend is a direct, injected `fpcalc` subprocess. No
`pyacoustid` dependency is added.

Frozen production argument vector for this stage:

```text
<configured fpcalc> -json -length 120 -- <private media path>
```

The runner is no-shell, timed, output-bounded, and sanitized. It caps retained
stdout at 1 MiB and stderr at 64 KiB, terminates on timeout or overflow, and
never exposes command, path, fingerprint, stdout, stderr, or raw operating-
system errors.

The child environment must not contain `NOQLENMETA_ACOUSTID_API_KEY`. Stage 02
does not resolve or use the service credential.

### Source stability

Generated material requires no-follow regular-file snapshots immediately before
and after backend execution. The exact device, inode, size, and nanosecond mtime
values must match. Symlinks and unsupported snapshot semantics fail closed.

A separate verification helper re-acquires and compares the source snapshot for
a future application stage, but Stage 02 performs no database application.

## Stage 02 Expected Product Files

```text
beetsplug/noqlenmeta/acoustid/__init__.py
beetsplug/noqlenmeta/acoustid/domain.py
beetsplug/noqlenmeta/acoustid/library.py
beetsplug/noqlenmeta/acoustid/backend.py
tests/acoustid/test_domain.py
tests/acoustid/test_library.py
tests/acoustid/test_backend.py
```

A small test-only `tests/acoustid/conftest.py` is conditionally allowed. No
identity-library file may change.

## Stage 02 Explicit Exclusions

- AcoustID HTTPS lookup and payload parsing;
- service API-key resolution;
- database mapping and application;
- command parser and dispatch;
- public configuration integration;
- MusicBrainz compatibility filtering;
- ordinary provider and importer integration;
- dependencies, optional extras, package metadata, workflows, public docs,
  changelog, version, tag, and release changes;
- audio-file writes.

## External Review Gate

The external Stage 02 branch must provide:

- focused domain, library, backend, evidence, and settings test results;
- Ruff results for the AcoustID package and tests;
- complete offline test-suite results;
- contamination and diff checks;
- a diff confined to the Stage 02 allowlist;
- proof of lazy backend creation and no-file-work reuse paths;
- proof of bounded runner timeout and stdout/stderr handling;
- proof of no-follow snapshot behavior and stale rejection;
- proof that no path, command, key, fingerprint, stdout, or stderr appears in
  representations or errors.

## Stop Condition

Merge the Stage 02 documentation brief before creating the product branch. No
product implementation is performed from this chat.
