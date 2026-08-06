# Block 029 Stage 01 Completion Record

## Status

Complete and merged on 2026-08-06.

Stage 01 was implemented outside the project chat, reviewed against the frozen
contracts, validated by CI, and squash-merged through PR #5.

```text
PR: https://github.com/jssantogit/noqlen-meta-plugin/pull/5
Reviewed head: c91f34d3d175c4ace558fc431d55d2b62dc55c68
Main commit: 26506a79f23a899a810640b1a2bfa8d80a5c4c20
CI: run 45, success
```

This record changes no product behavior. It documents the externally completed
implementation stage.

## Delivered Scope

Stage 01 added the dependency-light and side-effect-free AcoustID foundation:

- immutable fingerprint-origin, evidence-verdict, reason, fingerprint-material,
  result-group, evidence-policy, source-snapshot, and track-evidence values;
- canonical AcoustID UUID and MusicBrainz recording-MBID validation;
- redacted fingerprint-bearing representations and generic validation errors;
- deterministic result bounding and conflict detection;
- pure recording-support, tie, score, and margin classification;
- exact internal AcoustID settings values and a fresh immutable default factory;
- strict boolean, numeric, count, timeout, rate, cache, and executable-name
  validation;
- deterministic synthetic offline tests.

The implementation lives in:

```text
beetsplug/noqlenmeta/acoustid/__init__.py
beetsplug/noqlenmeta/acoustid/domain.py
beetsplug/noqlenmeta/acoustid/evidence.py
beetsplug/noqlenmeta/acoustid/settings.py
```

The focused tests live in:

```text
tests/acoustid/__init__.py
tests/acoustid/test_domain.py
tests/acoustid/test_evidence.py
tests/acoustid/test_settings.py
```

The empty test-package marker was accepted because it prevents pytest module
name collisions with existing top-level test modules.

## Review Findings Resolved

The external implementation was amended until these safety properties held:

1. Exact duplicate AcoustID groups may collapse, but the same AcoustID UUID with
   conflicting score or recording content is rejected instead of silently
   discarding evidence.
2. Whitespace is removed before path-free local-key validation, so `.` and `..`
   cannot enter through padded forms.
3. Direct construction of immutable evidence cannot fabricate a decisive state
   when multiple recordings tie or when a competing recording has equal or
   greater support.
4. Eligible result and recording counts, top support, runner-up support, and
   margin must agree with the normalized result groups.
5. Fingerprint material is absent from representations and validation errors.

## Completed Task Mapping

The following Block 029 work is complete:

### Domain and policy

- immutable Stage 01 domain values;
- validation of strings, identifiers, scores, margins, durations, counts, and
  verdict invariants;
- redacted fingerprint representations;
- decisive, ambiguous, no-match, and unavailable evidence states;
- score, margin, competing-recording, malformed-group, deterministic-ordering,
  duplicate-conflict, and fabricated-state tests.

`AcoustIDTargetResult`, selected beets targets, database snapshots, and database
plans remain intentionally deferred.

### Internal configuration foundation

- internal fresh settings/default factory with `enabled: false`;
- exact frozen values and validation bounds;
- unknown and missing setting rejection;
- no shared mutable state;
- no credential field and no environment access.

Public `configuration.default_config()` integration, credential resolution,
command options, and command validation remain deferred.

### Pure evidence classification

- bounded normalization to AcoustID UUID, score, and recording MBIDs only;
- highest-score recording support without accumulation;
- inclusive minimum score and margin behavior;
- top-score tie ambiguity;
- deterministic same-recording AcoustID UUID tie-breaking;
- no title, artist, duration, release, release-track, or MusicBrainz score input.

## Validation Evidence

The implementation report recorded:

```text
focused AcoustID tests: 132 passed before review amendments
full suite: 1247 passed, 5 skipped before review amendments
Ruff: all checks passed
repository contamination check: passed
git diff --check: passed
```

The amended head then passed repository CI run 45 before squash merge. CI is the
final repository-level acceptance signal for the merged implementation.

## Preserved Exclusions

Stage 01 introduced none of the following:

- network or AcoustID service transport;
- environment-key reading;
- subprocess or `fpcalc` execution;
- filesystem inspection or source-snapshot acquisition;
- beets Library, Album, Item, or database integration;
- command parser or importer integration;
- ordinary metadata-provider registration;
- MusicBrainz compatibility filtering or field writes;
- public configuration defaults;
- dependency, package metadata, workflow, version, tag, or release changes.

## Next Stage Boundary

Stage 02 is not active yet. Its documentation brief must be reviewed before any
new product branch starts.

The intended Stage 02 subject is:

- reading and validating existing beets AcoustID values;
- selecting fresh existing-library Albums and singletons;
- stable local keys and deterministic item order;
- a bounded, injectable fingerprint backend;
- backend discovery only when explicitly authorized calculation is needed;
- source-file snapshot acquisition and stale verification contracts.

Stage 02 must still exclude:

- AcoustID HTTPS lookup;
- API-key resolution;
- command integration;
- database application;
- MusicBrainz compatibility filtering;
- package and release work.

Those capabilities require later documentation stages and independent review.
