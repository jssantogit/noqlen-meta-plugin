# Block 029 Stage 01 Implementation Brief

## Status

Approved implementation brief for work performed outside the project chat.

This document does not authorize repository product changes from the chat. It
translates the accepted ADR and frozen contracts into one reviewable external
implementation stage.

Normative precedence is:

1. `contracts.md`;
2. ADR 0025;
3. this stage brief;
4. the earlier requirements and design documents.

When this brief appears to conflict with `contracts.md`, the frozen contract
wins.

## Objective

Implement the dependency-light, side-effect-free foundation for AcoustID
recording evidence:

- immutable domain values;
- pure evidence classification;
- frozen settings values and validation;
- redacted representations;
- stable machine-readable reasons;
- focused offline tests.

Stage 01 must finish without performing network access, executing a subprocess,
reading or mutating a beets database, inspecting a media file, changing the
public command parser, or exposing the intended configuration subtree through
the plugin's public default tree.

## Stage Boundary

### In scope

- A new dependency-light `beetsplug.noqlenmeta.acoustid` package or equivalent
  internal package boundary.
- Immutable enums and dataclasses required by the frozen domain vocabulary.
- Canonical AcoustID UUID and MusicBrainz recording-MBID validation.
- The pure recording-support and ambiguity algorithm from `contracts.md`.
- A pure settings/default factory matching the frozen AcoustID subtree.
- Validation of every frozen boolean and numeric setting.
- Safe reason vocabulary and redacted fingerprint-bearing representations.
- Offline unit tests for all of the above.

### Out of scope

- `urllib`, `requests`, sockets, HTTP clients, or any other network transport.
- `subprocess`, executable discovery, Chromaprint, or `fpcalc` execution.
- Environment-variable access, including reading
  `NOQLENMETA_ACOUSTID_API_KEY`.
- `os.stat`, filesystem snapshots, path resolution, symlink handling, or media
  inspection.
- beets `Library`, `Album`, or `Item` selection and mutation.
- command flags, command dispatch, importer integration, or event listeners.
- MusicBrainz candidate filtering or changes to the existing identity audit.
- addition to `BUILTIN_PROVIDER_SPECS` or ordinary `MetadataCandidate` output.
- direct integration of the AcoustID subtree into
  `configuration.default_config()`.
- public documentation, package extras, dependencies, version changes,
  workflows, tags, or releases.

The standalone settings factory is intentionally not wired into the plugin's
public configuration tree in this stage. That avoids advertising or activating
an incomplete feature and avoids premature public-documentation drift. The
frozen subtree is integrated only in the later command/documentation stage.

## Expected Internal Layout

The exact module split may be adjusted during review, but a narrow expected
shape is:

```text
beetsplug/noqlenmeta/acoustid/
  __init__.py
  domain.py
  evidence.py
  settings.py

tests/acoustid/
  test_domain.py
  test_evidence.py
  test_settings.py
```

The new package must not import beets, provider adapters, the command module,
network libraries, or subprocess helpers.

## Required Domain Values

### `AcoustIDFingerprintOrigin`

Exact serialized values:

```text
existing
generated
```

### `AcoustIDEvidenceVerdict`

Exact serialized values:

```text
unavailable
no_match
ambiguous
decisive
```

### Stable reason vocabulary

Stage 01 centralizes at least these frozen values:

```text
fingerprint_reused
fingerprint_generated
fingerprint_missing
fingerprint_backend_unavailable
fingerprint_failed
lookup_disabled
client_key_missing
lookup_failed
no_result_above_minimum
competing_recordings
insufficient_margin
recording_decisive
existing_value_conflict
stale_target
stale_source_file
```

A string enum is preferred so preview and later application code cannot invent
near-duplicate reason text. Stage 01 does not need to produce every reason; it
must make the complete frozen vocabulary available without side effects.

### Fingerprint material

`AcoustIDFingerprintMaterial` or an equivalently named frozen value contains:

- a non-empty path-free local key;
- private non-empty bounded fingerprint text;
- finite positive duration in seconds;
- `AcoustIDFingerprintOrigin`;
- optional generated-source snapshot data.

Required invariants:

- an existing fingerprint has no generated-source snapshot;
- a generated fingerprint requires a generated-source snapshot;
- duration rejects booleans, non-finite numbers, zero, and negative values;
- fingerprint and local key reject non-strings and empty/whitespace-only text;
- the fingerprint has a named defensive maximum length;
- the defensive length is an internal safety constant, not a public setting;
- constructor, `repr`, exception text, equality-failure output, and test failure
  messages must not expose the fingerprint.

Stage 01 may define an immutable source-snapshot value with the exact fields
needed later, but it must not acquire a snapshot from the filesystem. Snapshot
acquisition and verification belong to a later stage.

### `AcoustIDResultGroup`

The frozen value contains only:

- canonical AcoustID UUID;
- finite score from `0.0` through `1.0`;
- a non-empty tuple of unique canonical MusicBrainz recording MBIDs.

Required invariants:

- UUIDs are stored in canonical lowercase hyphenated form;
- recording MBIDs are canonicalized, deduplicated, and deterministically
  ordered;
- booleans are invalid scores;
- malformed identifiers are rejected before construction;
- no title, artist, duration, release, release group, medium, release track,
  URL, raw payload, path, key, or fingerprint field exists;
- no result group may retain more than the frozen hard maximum of 50 recording
  MBIDs.

### `AcoustIDEvidencePolicy`

The pure policy contains exactly:

```text
min_score
min_margin
max_results
max_recordings_per_result
```

Validation matches the frozen public bounds:

| Field | Accepted values |
| --- | --- |
| `min_score` | finite float from `0.0` through `1.0` |
| `min_margin` | finite float from `0.0` through `1.0` |
| `max_results` | integer from `1` through `20` |
| `max_recordings_per_result` | integer from `1` through `50` |

Integer fields reject booleans. Numeric fields may accept integers only when
they are not booleans and are normalized to floats where appropriate.

### `AcoustIDTrackEvidence`

The immutable evidence value contains:

- path-free local key;
- optional fingerprint origin;
- bounded normalized result groups;
- verdict;
- optional selected AcoustID UUID;
- optional selected recording MBID;
- one stable reason value;
- safe score, margin, and count data needed by later preview code.

Verdict invariants:

- `decisive` requires both selected identifiers and reason
  `recording_decisive`;
- non-decisive verdicts prohibit selected identifiers;
- `no_match` uses `no_result_above_minimum`;
- a top-score tie between different recordings uses `competing_recordings`;
- a unique top recording below the required runner-up margin uses
  `insufficient_margin`;
- unavailable evidence uses one of the relevant unavailable reason values and
  does not fabricate result identifiers;
- local keys and reason values are always present;
- result counts and numeric preview values are finite and internally
  consistent.

`AcoustIDTargetResult`, database snapshots, selected beets targets, and database
plans are not implemented in Stage 01 because they depend on later library and
application boundaries.

## Pure Evidence Classifier

Implement a pure function that receives already normalized result groups and an
`AcoustIDEvidencePolicy`. It performs no provider-payload parsing and has no
side effects.

The exact algorithm is:

1. Apply the policy bounds deterministically before classification.
2. Discard groups below `min_score`.
3. For each recording MBID, define support as the highest eligible group score
   containing that recording.
4. Do not sum or average duplicate support.
5. Return `no_match` when no eligible recording remains.
6. Order recordings by descending support and canonical MBID only for
   deterministic inspection.
7. Return `ambiguous` with `competing_recordings` when different recordings
   share the highest support.
8. When a runner-up exists, return `ambiguous` with `insufficient_margin` when
   top support minus runner-up support is less than `min_margin`.
9. Otherwise return `decisive` for the unique top recording.
10. Select the AcoustID UUID from the highest-scoring eligible group supporting
    the selected recording. Canonical AcoustID UUID order breaks a tie only
    among groups that support the same selected recording.

The margin comparison is inclusive: a difference exactly equal to
`min_margin` passes.

The classifier must not inspect or accept title, artist, duration, track
position, album information, release data, or current MusicBrainz fields. It
must not produce or modify a MusicBrainz structural score.

## Frozen Settings Value

Stage 01 implements a pure settings value and fresh factory equivalent to:

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

Validation requirements:

- every boolean leaf requires an actual boolean;
- `min_score`: finite `0.0` through `1.0`;
- `min_margin`: finite `0.0` through `1.0`;
- `max_results`: integer `1` through `20`;
- `max_recordings_per_result`: integer `1` through `50`;
- `timeout_seconds`: finite `1.0` through `60.0`;
- `requests_per_second`: finite greater than `0.0` and at most `3.0`;
- `cache_entries`: integer `0` through `4096`;
- `fpcalc`: non-empty string after validation;
- unknown keys are rejected rather than ignored;
- missing keys are filled only by the fresh default factory, not by silently
  accepting an incomplete supposedly complete settings object;
- each default call returns an independent tree/value with no shared mutable
  descendants.

The settings object contains no client key and does not read the environment.

## Error And Privacy Contract

Errors use stable generic messages and identify field names without echoing
sensitive values.

Tests must prove that none of these can appear in `repr` or validation errors:

- raw fingerprint text;
- a private path;
- the environment variable's value;
- a raw service payload.

Stage 01 contains no logger and no debug-output implementation.

## Required Test Matrix

### Domain tests

- canonical and malformed AcoustID UUIDs;
- canonical and malformed recording MBIDs;
- empty and duplicate recording sets;
- score boundaries `0.0` and `1.0`;
- NaN, infinity, negative score, score above one, and boolean score;
- existing/generated fingerprint snapshot invariants;
- duration validation;
- fingerprint maximum-length boundary;
- redacted `repr` and redacted validation failures;
- decisive and non-decisive evidence invariants.

### Evidence tests

- no eligible group -> `no_match`;
- one eligible recording -> `decisive`;
- exact `min_score` passes;
- below `min_score` fails;
- exact `min_margin` passes;
- below-margin runner-up remains ambiguous;
- equal top support across recordings remains ambiguous;
- duplicate groups do not accumulate support;
- one group containing multiple recordings remains ambiguous when they share
  the same top support;
- same-recording AcoustID-ID tie resolves by canonical UUID only;
- input order does not change the verdict or selected identifiers;
- policy result and recording bounds are deterministic;
- no title, artist, duration, release, or release-track input exists.

### Settings tests

- exact fresh defaults;
- no shared mutable default state;
- every numeric lower and upper boundary;
- booleans rejected as numbers;
- NaN and infinities rejected;
- every integer range boundary;
- empty and whitespace-only `fpcalc` rejected;
- unknown keys rejected;
- no environment access during import, default creation, or validation.

## Change Allowlist For The External Stage

Expected product changes are limited to:

```text
beetsplug/noqlenmeta/acoustid/__init__.py
beetsplug/noqlenmeta/acoustid/domain.py
beetsplug/noqlenmeta/acoustid/evidence.py
beetsplug/noqlenmeta/acoustid/settings.py
tests/acoustid/test_domain.py
tests/acoustid/test_evidence.py
tests/acoustid/test_settings.py
```

Narrow export adjustments are allowed when needed. Any change to the command
module, ordinary provider registry, identity audit, `pyproject.toml`, public
configuration defaults, workflows, README, public site, version, or release
files is out of scope and requires a new reviewed stage.

## Acceptance Commands

The external implementation report must include the exact results of:

```bash
python -m pytest tests/acoustid/test_domain.py \
  tests/acoustid/test_evidence.py \
  tests/acoustid/test_settings.py
python -m ruff check beetsplug/noqlenmeta/acoustid tests/acoustid
python -m pytest
```

The final full suite must remain offline and green on the supported Python and
beets CI matrix.

## Reviewer Checklist

The reviewer must confirm:

- [ ] the diff stays inside the Stage 01 allowlist;
- [ ] no network, subprocess, filesystem, database, command, or importer work
  was introduced;
- [ ] AcoustID is not registered as an ordinary provider;
- [ ] no complete MusicBrainz identity value can be created or written;
- [ ] exact frozen defaults and validation bounds are represented internally;
- [ ] public plugin defaults remain unchanged in this stage;
- [ ] the evidence algorithm exactly follows `contracts.md`;
- [ ] score duplication never accumulates support;
- [ ] exact score and margin boundaries are tested;
- [ ] fingerprints are absent from repr, errors, logs, and test output;
- [ ] all tests are deterministic, synthetic, and offline;
- [ ] full CI remains green.

## Completion And Handoff

Stage 01 is complete only after external implementation, reviewer PASS, green
CI, and squash merge.

The next stage may then specify existing beets values, selected library targets,
and the bounded fingerprint backend. It must not begin network lookup or
database application until its own documentation brief is approved.
