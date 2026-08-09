# Block 029 Stage 05 — Final AcoustID Integration

## Status

Approved design for the final implementation stage of Block 029.

Baseline:

```text
f508d30c740891e04c92068d5eafbf9123896431
```

Stage 05 is the **last product implementation stage** for Block 029. There is no Stage 06. After Stage 05 merges, remaining work is Block 029 completion/release readiness only: public documentation, changelog/package validation, final review, and any later version/tag/publication decision.

Normative precedence:

1. `contracts.md`
2. ADR 0025
3. this Stage 05 brief
4. older requirements/design wording

This brief authorizes one product branch and one product PR.

## Goal

Finish the user-facing AcoustID feature by integrating the already-delivered standalone AcoustID core with:

- the existing-library MusicBrainz identity audit as recording compatibility evidence;
- the frozen standalone `--acoustid` / `--fingerprint-missing` command surface;
- the frozen public `acoustid` configuration subtree.

The implementation must preserve the existing MusicBrainz structural safety model, remain database-only for AcoustID application, and keep importer acoustic matching owned by native beets `chroma`.

## Explicit Non-Goals

Stage 05 must not:

- add AcoustID or Chromaprint to the ordinary metadata provider resolver;
- add any structural score component or bonus;
- change existing MusicBrainz scoring weights or thresholds;
- derive release, release-group, medium, or release-track identity from AcoustID;
- write MusicBrainz fields directly from AcoustID payloads;
- generate fingerprints silently during `--identity`;
- add importer fingerprint generation or AcoustID autotagger candidates;
- write audio files or call `Item.write()` from AcoustID mode;
- submit fingerprints;
- add force or partial AcoustID behavior;
- add new AcoustID Python dependencies;
- bump version, tag, publish, or perform release administration.

## 1. Pure Recording Expectations

Add a pure immutable representation of decisive AcoustID recording expectations keyed by existing identity `local_key`.

Rules:

- only `AcoustIDEvidenceVerdict.DECISIVE` contributes an expectation;
- the expectation value is the canonical decisive MusicBrainz recording MBID;
- unavailable, no-match, and ambiguous evidence contribute nothing and are neutral;
- duplicate/conflicting expectations for one local key fail closed;
- stored `acoustid_id` is not evidence;
- no title, artist, duration, release, release-group, medium, or release-track data enters the expectation model.

The mapping must be deterministic and independent of MusicBrainz candidate scoring.

## 2. Candidate Compatibility Filter

The filter operates on already-produced `IdentityCandidateEvaluation` values.

It must not call `evaluate_identity_candidate()`, `assign_identity_tracks()`, or any scorer itself.

For every decisive local-key expectation:

1. find the existing assignment for that local key in the candidate evaluation;
2. resolve the assigned `candidate_index` to the candidate track;
3. compare that track's canonical `recording_mbid` to the expected decisive recording MBID;
4. any mismatch makes the candidate acoustically incompatible.

A candidate is compatible only when every decisive expectation that can be checked against its complete assignment matches.

The compatibility result must be represented separately from structural score data. Existing `IdentityScoreBreakdown`, pair scores, assignments, candidate ordering inputs, and structural components remain unchanged.

Malformed/inconsistent assignment structure must fail closed rather than being treated as compatible.

## 3. Audit Ordering And Safety Gates

The integrated identity flow is:

```text
MusicBrainz candidates
-> existing structural evaluation/assignment unchanged
-> AcoustID recording compatibility filter
-> existing safety gates unchanged on compatible evaluations
-> existing four-field findings from the selected complete candidate
```

The filter may remove structurally evaluated candidates. It never changes any evaluation score.

After filtering, the surviving top candidate must still pass the existing gates with the same policy values:

- minimum total score;
- valid candidate identity;
- complete local-track assignment when required;
- no ambiguous assignment;
- minimum pair score;
- unique minimum margin against the remaining compatible runner-up.

This allows decisive AcoustID evidence to remove an incompatible runner-up, as intended by ADR 0025, while never adding score or relaxing any gate.

AcoustID must not make a candidate eligible when that candidate itself has weak score, weak pair assignment, incomplete assignment, or ambiguous assignment.

When decisive evidence removes every structurally evaluated candidate, return:

```text
verdict = AMBIGUOUS
reason = acoustid_recording_conflict
selected_candidate = None
selected_evaluation = None
field_findings = ()
repair_ready = False
```

When no decisive expectations exist, the audit result must remain behaviorally equivalent to the existing non-AcoustID audit.

Four-field MusicBrainz findings remain derived only from the selected complete MusicBrainz release candidate.

## 4. Identity Integration Boundary

Do not change the semantics of existing `audit_musicbrainz_identity()` callers that do not opt into AcoustID evidence.

Add a narrow pure entry point/helper that composes existing structural evaluation with optional recording expectations, or extend the audit through an optional immutable expectations argument if that preserves current behavior exactly when omitted.

Existing importer identity behavior remains unchanged in Block 029.

AcoustID identity integration applies to the existing-library `--identity` workflow only.

When public settings satisfy:

```text
acoustid.enabled == true
acoustid.use_for_identity == true
```

then, for each selected existing-library target:

- reuse only a valid stored fingerprint when `reuse_existing` permits it;
- never calculate a missing fingerprint;
- perform lookup only when `lookup` permits it and valid material exists;
- use the configured evidence policy;
- treat missing fingerprint, unavailable backend state, missing credential, lookup failure, no-match, and ambiguous evidence as neutral for MusicBrainz filtering;
- feed only decisive recording expectations into the compatibility filter.

`compute_missing` and `--fingerprint-missing` do not grant fingerprint-generation authority to `--identity`.

Identity mode must not apply standalone AcoustID database plans. Its AcoustID use is evidence-only.

## 5. Standalone CLI

Add exactly the frozen options:

```text
--acoustid
--fingerprint-missing
```

`--acoustid` selects the standalone AcoustID mode.

`--fingerprint-missing` grants missing-fingerprint calculation authority for that standalone invocation only.

Standalone flow:

```text
validate CLI/config
-> select all complete existing-library targets
-> plan every target with plan_acoustid_target()
-> render preview for every planned target
-> when --apply: apply_acoustid_results() to the complete prepared application unit
```

Preview remains the default.

`--apply` grants database-only application of the Stage 04 plans. It never grants file-write authority.

`--all` preserves the existing command-wide all-target meaning. Query and `--all` are mutually exclusive.

The implementation must reuse Stage 02-04 boundaries rather than duplicate selection, backend, service, mapping, preview, stale verification, or application logic.

## 6. CLI Validation Before Work

Reject invalid combinations before target selection, filesystem/backend work, credential lookup, or network work:

```text
--acoustid with --identity
--acoustid with --identity-tags
--acoustid with --write
--acoustid with --partial
--fingerprint-missing without --acoustid
```

Preserve existing validation for `--write`, `--partial`, query vs `--all`, and identity modes.

No `--force` option is introduced.

## 7. Public Configuration

Add exactly this subtree to `configuration.default_config()`:

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

Build runtime settings through `AcoustIDSettings.from_mapping()` rather than duplicating validation rules in the plugin command layer.

Unknown/missing/invalid AcoustID settings fail before AcoustID target work.

The public defaults and internal `default_acoustid_settings()` must remain in exact semantic parity.

The client key remains exclusively:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

It is not added to configuration.

## 8. Lazy Operational Boundaries

Standalone and identity integration must preserve lazy behavior:

- no backend construction when a valid stored fingerprint is reused or calculation is unauthorized;
- no `fpcalc` invocation when missing calculation is not authorized;
- no environment key resolution unless a real uncached lookup is needed;
- no network when lookup is disabled, no valid material exists, or a lookup cache hit satisfies the request;
- identity mode never invokes missing-fingerprint calculation.

Normal CI remains fully offline and requires no API key, real `fpcalc`, or audio fixture.

## 9. Existing-Library Scope Only

Block 029 remains existing-library only for Noqlen-owned AcoustID behavior.

Do not add AcoustID handling to importer `import_task_choice`.

Native beets `chroma` continues to own importer acoustic matching, import-time fingerprinting, `beet fingerprint`, submission, and autotagger candidates.

## 10. Privacy And Output

Standalone preview continues using Stage 04's frozen renderer and vocabulary.

New command, integration, result, warning, and error paths must not expose:

- full fingerprints;
- private media paths;
- API keys;
- backend commands/output;
- raw HTTP request/response material;
- provider/raw OS exception text.

MusicBrainz identity preview may surface the stable `acoustid_recording_conflict` reason but does not need to print private AcoustID material.

## 11. Product Allowlist

The expected product diff is narrow and should normally stay within files serving these responsibilities:

```text
beetsplug/noqlenmeta/__init__.py
beetsplug/noqlenmeta/configuration.py
beetsplug/noqlenmeta/identity/audit.py
beetsplug/noqlenmeta/identity/__init__.py
beetsplug/noqlenmeta/identity/<new acoustid compatibility module>.py
beetsplug/noqlenmeta/acoustid/__init__.py   # exports only if required

corresponding focused tests under tests/identity/, tests/acoustid/, and command/config tests
```

Stage 05 must not refactor Stage 02-04 internals unless a concrete integration defect requires a minimal correction. Any product file outside this boundary requires explicit justification in the implementation report.

No dependency, package metadata, workflow, version, or release file belongs in the Stage 05 product PR unless a test-only compatibility adjustment is strictly necessary and explicitly justified.

## 12. Required Compatibility Tests

### Pure compatibility

Cover:

- one decisive expectation matches;
- one decisive expectation conflicts;
- multiple decisive expectations all match;
- one mismatch rejects candidate;
- unavailable/no-match/ambiguous evidence is neutral;
- repeated recording MBIDs on different release-track occurrences;
- multidisc releases;
- bonus tracks;
- malformed/inconsistent assignment fails closed;
- deterministic result ordering.

### Audit invariance

Prove:

- with no decisive expectations, existing audit output is unchanged;
- structural score components are byte-for-byte/value-for-value unchanged by AcoustID filtering;
- pair scores and assignments are unchanged;
- AcoustID cannot rescue a candidate below minimum score;
- AcoustID cannot rescue weak pair assignment;
- AcoustID cannot rescue incomplete assignment;
- AcoustID cannot rescue ambiguous assignment;
- compatible surviving candidates still pass the unchanged margin gate;
- all candidates rejected -> `acoustid_recording_conflict`.

### Existing-library identity integration

Cover:

- disabled AcoustID -> existing identity behavior unchanged;
- `enabled=true`, `use_for_identity=false` -> unchanged;
- valid stored fingerprint + decisive lookup filters candidates;
- missing fingerprint is neutral and does not invoke backend;
- `compute_missing=true` still does not generate under `--identity`;
- lookup disabled/missing key/failure/no-match/ambiguous are neutral;
- decisive conflict prevents repair-ready identity result;
- no AcoustID database writes occur from identity mode.

### Standalone command

Cover:

- query preview;
- `--all` preview;
- `--fingerprint-missing` authority;
- `--apply` database-only application;
- complete planning before first application call;
- Stage 04 `REVIEW`/`BLOCKED`/stale behavior remains authoritative;
- all invalid option combinations are rejected before selection/backend/network;
- no audio-file writes.

### Configuration

Cover:

- exact public default subtree;
- parity with internal defaults;
- each invalid type/range and unknown/missing setting through public command integration;
- no client key in configuration.

### Compatibility matrix

Final Stage 05 CI must pass the repository-supported matrix:

- Python 3.10-3.14;
- beets minimum 2.12.0;
- latest beets below 3;
- documentation/package jobs already present in repository CI.

No live AcoustID test gates CI.

## 13. Verification And Review Gate

Before Stage 05 product merge, require:

- focused compatibility/audit tests;
- focused command/config/standalone tests;
- complete `tests/acoustid` and identity test suites;
- Ruff;
- full repository offline test suite;
- repository contamination/hygiene check;
- `git diff --check`;
- CI green on the final reviewed head;
- external review confirming no score drift, no hidden fingerprint generation in identity mode, no file-write authority, and no scope drift.

## 14. Completion Boundary

After Stage 05 product PR is reviewed, CI-green, and squash-merged:

- Block 029 product implementation is complete;
- create one documentation-only Block 029 / Stage 05 completion record;
- update public docs and changelog for release readiness;
- validate built artifacts and compatibility as required by repository release practice;
- obtain final reviewer PASS before any version bump/tag/publication decision.

These activities are completion/release readiness, **not another implementation stage**.
