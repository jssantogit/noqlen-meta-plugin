# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 planning and contract freeze were
approved, passed CI, and were squash-merged to `main` as:

```text
6ad71d68347e23cecd45225900a10a8287acca54
9945ed9cd693abc04b250d10239151b3281a7762
```

ADR 0025 is Accepted. The command, configuration, credential, lookup, domain,
evidence, mapping, preview, privacy, and beets `chroma` coexistence contracts are
frozen in `contracts.md`.

The current documentation branch prepares the first external implementation
brief. It contains no product code, implementation tests, dependency, package
metadata, workflow, version, tag, or release change.

## Documentation-Only Chat Rule

Repository changes performed from the project chat are limited to:

- specifications and stage briefs;
- ADRs;
- context and handoff documents;
- documentation-only PR administration.

Implementation happens outside this chat after the corresponding brief is
approved.

## Normative Artifacts

- Requirements:
  `docs/specs/029-acoustid-identity-evidence/requirements.md`
- Design:
  `docs/specs/029-acoustid-identity-evidence/design.md`
- Forge-to-Meta parity matrix:
  `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- Frozen contracts:
  `docs/specs/029-acoustid-identity-evidence/contracts.md`
- Task sequence:
  `docs/specs/029-acoustid-identity-evidence/tasks.md`
- Stage 01 implementation brief:
  `docs/specs/029-acoustid-identity-evidence/stage-01-domain-policy-configuration.md`
- Accepted architecture decision:
  `docs/adr/0025-acoustid-recording-evidence.md`

`contracts.md` wins over provisional planning text. The Stage 01 brief narrows
only the first external implementation branch and cannot weaken the frozen
contracts.

## Accepted Architecture

AcoustID is a separate recording-level identity-evidence subsystem. It is not
an ordinary provider and cannot emit ordinary `MetadataCandidate` values.

The first complete product scope remains:

- existing-library Albums and singletons;
- reuse of valid beets AcoustID fields;
- explicit missing-fingerprint calculation;
- bounded HTTPS POST lookup with `meta=recordingids`;
- path-free and fingerprint-free preview;
- database-only storage of `acoustid_id` and `acoustid_fingerprint`;
- optional recording compatibility filtering for the existing MusicBrainz
  identity audit.

AcoustID adds no structural score, writes no MusicBrainz field, chooses no
release occurrence, writes no audio file, submits no fingerprint, and provides
no duplicate importer autotagger.

## Frozen Interface Summary

New intended options:

```text
--acoustid
--fingerprint-missing
```

They compose with existing `--apply` and `--all` as defined in `contracts.md`.

The intended settings subtree remains:

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

The exact environment variable is:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

## Stage 01 External Implementation

The approved first implementation stage is defined in
`stage-01-domain-policy-configuration.md`.

### Required scope

- immutable fingerprint-origin and evidence-verdict enums;
- stable reason vocabulary;
- immutable, redacted fingerprint material;
- canonical AcoustID result groups containing recording MBIDs only;
- validated pure evidence policy;
- immutable track evidence and verdict invariants;
- pure support, score, tie, and margin classification;
- internal fresh settings/default factory matching the frozen subtree;
- strict settings validation;
- deterministic offline tests.

### Explicit exclusions

- network transport and environment-key reading;
- subprocess or `fpcalc` execution;
- filesystem and source-snapshot acquisition;
- beets target selection or database mutation;
- command parser and public default-tree integration;
- MusicBrainz compatibility filtering;
- ordinary-provider registration;
- public documentation, package, dependency, version, workflow, tag, or release
  changes.

The public plugin default tree remains unchanged in Stage 01. The exact
AcoustID defaults are first implemented as an internal fresh settings factory;
public configuration integration occurs only when the command and public docs
are delivered together.

## Stage 01 Critical Algorithm

For already normalized result groups:

1. retain groups at or above `min_score` within policy bounds;
2. define each recording's support as its highest eligible group score;
3. never accumulate duplicate support;
4. return `no_match` when no eligible recording remains;
5. return `ambiguous` for a top-score tie between different recordings;
6. return `ambiguous` when a runner-up is closer than `min_margin`;
7. treat a difference exactly equal to `min_margin` as passing;
8. otherwise select the unique top recording and the highest-scoring AcoustID
   UUID supporting it;
9. use canonical UUID ordering only to break a same-recording tie.

Title, artist, duration, position, release structure, assignment, and
MusicBrainz score do not enter this classifier.

## External Review Gate

The external Stage 01 branch must provide:

- focused domain, evidence, and settings test results;
- Ruff results for the new package and tests;
- the complete offline test-suite result;
- a diff confined to the Stage 01 allowlist;
- proof that fingerprint values do not appear in representations or errors;
- proof that no network, subprocess, filesystem, beets, command, or provider
  integration entered the stage.

Stage 01 completes only after reviewer PASS, green CI, and squash merge.

## Next Documentation Work

After Stage 01 is externally implemented and merged, prepare a separate
documentation brief for Stage 02: existing beets values, fresh library targets,
and the bounded fingerprint backend. Stage 02 must still exclude network lookup
and database application until their own briefs are approved.

## Stop Condition

This chat stops at documentation, review contracts, and PR administration. No
product implementation is performed here.
