# Block 029 Stage 05 — Final AcoustID Integration

## Status

Approved design for the **last product implementation stage** of Block 029.

Baseline:

```text
f508d30c740891e04c92068d5eafbf9123896431
```

There is no Stage 06. After Stage 05 merges, remaining work is Block 029 completion/release readiness only.

Normative precedence:

1. `contracts.md`
2. ADR 0025
3. this brief
4. older requirements/design wording

This brief authorizes one product branch and one product PR.

## Goal

Finish the AcoustID feature by integrating the Stage 01-04 core with:

- existing-library MusicBrainz identity as recording compatibility evidence;
- standalone `--acoustid` / `--fingerprint-missing` command handling;
- the frozen public `acoustid` configuration subtree.

Do not add a second scoring system, a second AcoustID workflow, or another implementation stage.

## 1. MusicBrainz Recording Compatibility

### Expectations

Create a pure immutable mapping from decisive AcoustID evidence to:

```text
local_key -> canonical recording MBID
```

Only `DECISIVE` evidence contributes. `UNAVAILABLE`, `NO_MATCH`, and `AMBIGUOUS` are neutral. Stored `acoustid_id` is current state, never fresh evidence.

Duplicate/conflicting expectations for one local key fail closed.

### Filter

Operate only on already-produced `IdentityCandidateEvaluation` values. Do not recalculate scoring or assignment.

For every decisive expectation:

1. find that `local_key` in the existing assignment;
2. resolve its existing `candidate_index`;
3. compare the assigned candidate track `recording_mbid` with the decisive recording MBID.

Mismatch, missing assignment, invalid candidate index, or inconsistent assignment structure makes that candidate incompatible.

Compatibility must be represented separately from structural score data. Existing score components, pair scores, assignments, and candidate identities remain unchanged.

### Audit order

```text
existing MusicBrainz candidates
-> existing evaluation/assignment unchanged
-> AcoustID compatibility filter
-> existing safety gates unchanged on surviving evaluations
-> existing four-field findings from selected complete candidate
```

The filter may remove candidates but never changes score or threshold values.

The surviving top candidate must still pass the existing:

- minimum total score;
- candidate-identity safety;
- complete assignment gate;
- assignment-ambiguity gate;
- minimum pair score;
- minimum margin against the remaining compatible runner-up.

This may remove an incompatible runner-up and resolve a structural near-tie, but AcoustID never makes a weak/incomplete/ambiguous surviving candidate pass a gate.

If decisive evidence removes every candidate, return exactly:

```text
verdict = AMBIGUOUS
reason = acoustid_recording_conflict
selected_candidate = None
selected_evaluation = None
field_findings = ()
repair_ready = False
```

With no decisive expectations, existing audit behavior must remain unchanged.

## 2. Existing-Library `--identity` Integration

AcoustID filtering applies only to the existing-library identity command. Importer behavior remains unchanged.

Enable acoustic filtering only when:

```text
acoustid.enabled == true
acoustid.use_for_identity == true
```

Identity mode may:

- reuse a valid stored fingerprint when configured;
- perform configured lookup using the existing Stage 03 service;
- feed decisive recording expectations into the pure compatibility filter.

Identity mode may **not** calculate a missing fingerprint, even when `compute_missing=true`. Missing fingerprint, disabled lookup, missing credential, lookup failure, no-match, and ambiguous evidence are neutral.

Identity mode does not apply standalone AcoustID database plans and does not write AcoustID fields.

Existing `audit_musicbrainz_identity()` callers that do not opt into AcoustID evidence must keep current semantics.

## 3. Standalone Command Integration

Add exactly:

```text
--acoustid
--fingerprint-missing
```

Standalone flow:

```text
validate CLI/config
-> select complete existing-library targets
-> plan every target with existing Stage 04 workflow
-> preview planned targets
-> when --apply: apply the complete prepared unit with Stage 04 application
```

Rules:

- preview remains default;
- `--apply` is database-only;
- `--fingerprint-missing` grants calculation authority only for standalone AcoustID mode;
- query and `--all` remain mutually exclusive;
- reuse Stage 02-04 selection, fingerprint, service, mapping, preview, stale-check, and application boundaries;
- do not duplicate them in the command layer.

Reject before target selection, filesystem/backend work, environment access, or network:

```text
--acoustid with --identity
--acoustid with --identity-tags
--acoustid with --write
--acoustid with --partial
--fingerprint-missing without --acoustid
```

Preserve all existing command validation. Add no `--force` behavior.

## 4. Public Configuration

Add the exact frozen subtree to `configuration.default_config()`:

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

Build runtime settings through `AcoustIDSettings.from_mapping()`; do not duplicate range/type validation in the plugin layer.

Public defaults and `default_acoustid_settings()` must remain semantically identical.

The client key remains environment-only:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

Invalid/missing/unknown AcoustID configuration fails before AcoustID target work.

## 5. Lazy And Privacy Boundaries

Preserve existing laziness:

- no backend construction when calculation is unnecessary/unauthorized;
- no `fpcalc` when missing calculation is unauthorized;
- no environment key resolution unless a real uncached lookup is needed;
- no network when lookup is disabled, material is unavailable, or cache satisfies lookup;
- `--identity` never invokes fingerprint generation.

Never expose fingerprints, private paths, API keys, backend output, raw HTTP material, or raw provider/OS exception text.

Normal CI remains offline with no API key, real `fpcalc`, or live AcoustID dependency.

## 6. Scope Boundaries

Block 029 remains existing-library only for Noqlen-owned AcoustID behavior. Native beets `chroma` continues to own importer acoustic matching, import-time fingerprinting, submission, and autotagger candidates.

Stage 05 must not:

- add AcoustID to the ordinary provider resolver;
- add/modify structural scoring or thresholds;
- derive release/release-group/release-track identity from AcoustID;
- write MusicBrainz fields directly from AcoustID;
- write audio files;
- submit fingerprints;
- add force/partial AcoustID behavior;
- add new AcoustID Python dependencies;
- bump version, tag, publish, or perform release administration.

Expected product files are limited to the command/configuration surface, identity audit/compatibility surface, optional AcoustID exports, and focused tests. Stage 02-04 internals should change only for a concrete integration defect and only minimally.

## 7. Required Tests

### Compatibility and audit

Cover:

- decisive match and mismatch;
- multiple decisive expectations;
- neutral non-decisive evidence;
- repeated recording MBIDs on different release-track occurrences;
- multidisc and bonus-track candidates;
- malformed/inconsistent assignment fail-closed;
- all candidates rejected -> `acoustid_recording_conflict`;
- no decisive evidence -> existing audit result unchanged;
- score components, pair scores, and assignments unchanged;
- surviving weak-score, weak-pair, incomplete, or ambiguous candidates still fail existing gates;
- margin remains the existing gate over surviving compatible evaluations.

### Existing-library identity

Cover:

- AcoustID disabled or `use_for_identity=false` -> unchanged identity behavior;
- stored fingerprint + decisive lookup filters candidates;
- missing fingerprint is neutral and never invokes backend;
- `compute_missing=true` still cannot generate in `--identity`;
- lookup disabled/missing key/failure/no-match/ambiguous are neutral;
- conflict prevents repair-ready identity result;
- identity mode performs no AcoustID database write.

### Standalone command/config

Cover:

- query and `--all` preview;
- `--fingerprint-missing` authority;
- database-only `--apply`;
- every target planned before application;
- Stage 04 blockers/stale behavior remains authoritative;
- every invalid option combination fails before local/network work;
- exact public default subtree and parity with internal defaults;
- invalid/unknown/missing settings;
- no client key in config;
- no audio-file write.

Final CI must continue passing supported Python 3.10-3.14, beets minimum 2.12.0, latest beets below 3, and existing docs/package jobs.

## 8. Merge Gate And Completion

Before product merge require:

- focused Stage 05 tests;
- full AcoustID + identity suites;
- Ruff;
- full offline repository tests;
- hygiene/contamination check;
- `git diff --check`;
- CI green on the final reviewed head;
- external review for score drift, hidden identity fingerprint generation, file-write authority, and scope drift.

After Stage 05 product merge, **Block 029 product implementation is complete**.

Then perform one documentation-only completion/release-readiness pass: public docs, changelog, built-artifact validation, final reviewer PASS, and any later version/tag/publication decision. That is not Stage 06.
