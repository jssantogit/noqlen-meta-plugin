# Block 029 Frozen Contracts

## Status

Accepted and frozen for Block 029 on 2026-08-03.

This document is the normative implementation contract for the first AcoustID
update. It refines the earlier planning language in `requirements.md` and
`design.md`. When provisional wording conflicts with this document, this
document wins.

This branch remains documentation-only. It changes no product code, package
metadata, dependency, command parser, configuration default, workflow, version,
tag, or public release.

## Product Boundary

AcoustID is a recording-level identity-evidence subsystem. It is not an
ordinary metadata provider and must not enter the ordinary provider resolver.

The subsystem may:

- reuse a valid stored Chromaprint fingerprint;
- calculate a missing fingerprint under explicit authority;
- query AcoustID for bounded recording-ID evidence;
- preview and store `acoustid_id` and `acoustid_fingerprint` in the beets
  database;
- reject a complete MusicBrainz release candidate whose assigned recording
  conflicts with decisive acoustic evidence.

The subsystem may not:

- write any MusicBrainz field directly;
- infer release, release-group, medium, or release-track identity from an
  AcoustID payload;
- add points to the existing MusicBrainz structural score;
- rescue a weak, incomplete, ambiguous, or insufficient-margin MusicBrainz
  candidate;
- write audio-file tags;
- submit fingerprints;
- provide importer autotagger candidates;
- add force or partial identity behavior.

## Frozen Command Contract

The following option names are frozen for Block 029 implementation:

```text
--acoustid
--fingerprint-missing
```

They compose with these existing options:

```text
--apply
--all
```

### Supported forms

```text
beet nm --acoustid QUERY
beet nm --acoustid --fingerprint-missing QUERY
beet nm --acoustid --apply QUERY
beet nm --acoustid --fingerprint-missing --apply QUERY
beet nm --acoustid --all
beet nm --acoustid --fingerprint-missing --all
beet nm --acoustid --apply --all
beet nm --acoustid --fingerprint-missing --apply --all
```

### Meaning

- `--acoustid` selects the standalone AcoustID evidence mode and is explicit
  authority to inspect selected existing-library targets and perform configured
  lookups for that invocation.
- `--fingerprint-missing` permits local calculation only for selected Items that
  do not already have a valid stored fingerprint.
- `--apply` authorizes database changes only. It never authorizes file writes.
- `--all` retains the existing command-wide meaning of selecting all targets in
  the chosen mode.
- A normal query and `--all` are mutually exclusive.
- Preview remains the default.

### Invalid combinations

The command must reject these combinations before target selection, backend
work, or network work:

```text
--acoustid with --identity
--acoustid with --identity-tags
--acoustid with --write
--acoustid with --partial
--fingerprint-missing without --acoustid
```

No `--force` option will be introduced.

Changing either frozen option name or its authority semantics requires an ADR
amendment before product code changes.

## Frozen Configuration Contract

The exact intended default subtree is:

```yaml
noqlenmeta:
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

### Setting semantics

`enabled`
: Controls optional AcoustID evidence use by the existing `--identity` mode.
  The explicit standalone `--acoustid` command is sufficient authority for its
  own invocation even when this setting is false.

`reuse_existing`
: Permits reuse of a valid stored `acoustid_fingerprint`. A stored
  `acoustid_id` remains current state and is never treated as fresh recording
  evidence by itself.

`compute_missing`
: Permits missing-fingerprint calculation in standalone AcoustID mode. The
  command-line `--fingerprint-missing` option enables the same authority for one
  invocation. Block 029 identity mode never calculates a missing fingerprint;
  it may consume only valid fingerprints already stored in the database.

`lookup`
: Permits AcoustID network lookup when valid fingerprint material exists. When
  false, standalone mode may still preview or calculate a fingerprint and may
  plan that fingerprint for database application.

`use_for_identity`
: Permits decisive evidence to filter MusicBrainz candidates during
  `--identity`. It has effect only when `enabled` is true. It never changes the
  standalone AcoustID field plan.

`min_score`
: Inclusive minimum AcoustID result score. Default `0.90`.

`min_margin`
: Inclusive minimum difference between the best support for the selected
  recording and the best support for a different recording. Default `0.05`.
  The margin gate is satisfied without a runner-up when only one recording MBID
  remains after normalization.

`max_results`
: Maximum normalized AcoustID result groups retained from one lookup.

`max_recordings_per_result`
: Maximum recording MBIDs retained from one result group.

`timeout_seconds`
: Timeout for one fingerprint backend invocation or one service request. A
  future implementation may split this setting only through a reviewed contract
  amendment.

`requests_per_second`
: Process-local sequential request ceiling. It may not exceed the official
  service ceiling of `3.0`.

`cache_entries`
: Maximum process-local lookup cache entries. `0` disables caching. No raw
  response or fingerprint is persisted.

`fpcalc`
: Non-empty executable name or configured path used only when authorized
  calculation is actually required.

### Validation bounds

Configuration rejects booleans where numbers are required, non-finite numbers,
and values outside these bounds:

| Setting | Accepted values |
| --- | --- |
| `min_score` | finite float from `0.0` through `1.0` |
| `min_margin` | finite float from `0.0` through `1.0` |
| `max_results` | integer from `1` through `20` |
| `max_recordings_per_result` | integer from `1` through `50` |
| `timeout_seconds` | finite float from `1.0` through `60.0` |
| `requests_per_second` | finite float greater than `0.0` and at most `3.0` |
| `cache_entries` | integer from `0` through `4096` |
| `fpcalc` | non-empty string |

All boolean leaves require actual booleans.

## Credential Contract

The exact environment variable is:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

No fallback configuration key is added in Block 029. The value is read only at
the service boundary and is never placed in a domain object, cache key, preview,
debug output, exception, committed example, or persistent storage.

A missing key produces an unavailable lookup result when lookup would otherwise
be needed. It does not prevent local fingerprint preview or authorized local
fingerprint calculation.

## Frozen Lookup Contract

The service request uses:

```text
POST https://api.acoustid.org/v2/lookup
Content-Type: application/x-www-form-urlencoded
```

The form body contains only:

```text
client=<environment key>
duration=<rounded whole seconds>
fingerprint=<private fingerprint>
meta=recordingids
format=json
```

The initial implementation requests `recordingids`, not release metadata and
not expanded recording metadata. This is intentional:

- AcoustID supplies recording identity evidence only;
- title, artist, duration, track order, release structure, and assignment remain
  the responsibility of the existing MusicBrainz audit;
- no second textual or duration scoring system is introduced;
- release-specific provider data cannot accidentally enter the domain.

The lookup transport is sequential, paced, bounded, injectable, and sanitized.
There is no automatic retry in Block 029.

## Frozen Domain Vocabulary

The implementation uses these concepts. Exact Python module placement may
change during implementation, but names and invariants are frozen unless an ADR
amendment says otherwise.

### `AcoustIDFingerprintOrigin`

Values:

```text
existing
generated
```

### `AcoustIDEvidenceVerdict`

Values:

```text
unavailable
no_match
ambiguous
decisive
```

### `AcoustIDFingerprintMaterial`

Contains:

- path-free `local_key`;
- private non-empty bounded fingerprint text;
- finite positive duration in seconds;
- origin;
- generated-source snapshot only when origin is `generated`.

Its representation must redact the fingerprint.

### `AcoustIDResultGroup`

Contains:

- canonical AcoustID UUID;
- finite score from `0.0` through `1.0`;
- non-empty bounded tuple of canonical MusicBrainz recording MBIDs.

It contains no title, artist, duration, release, release-group, medium,
release-track, URL, raw response, or fingerprint.

### `AcoustIDTrackEvidence`

Contains:

- path-free `local_key`;
- fingerprint origin when material exists;
- bounded result groups;
- verdict;
- selected AcoustID UUID only when decisive;
- selected recording MBID only when decisive;
- stable machine-readable reason;
- safe result counts and score values needed for preview.

### `AcoustIDEvidencePolicy`

Contains validated `min_score`, `min_margin`, `max_results`, and
`max_recordings_per_result` values. Transport and backend operational settings
remain outside the pure evidence policy.

### `AcoustIDTargetResult`

Contains:

- selected fresh existing-library target;
- exact database snapshot;
- per-track evidence;
- standalone AcoustID database target plan;
- generated-source snapshots required for stale verification.

It never contains a file-write plan.

## Frozen Evidence Algorithm

For one track:

1. Reject an invalid service status or malformed response as `unavailable`.
2. Bound result groups and recordings before domain construction.
3. Canonicalize and deduplicate AcoustID UUIDs and recording MBIDs.
4. Discard result groups below `min_score`.
5. For each recording MBID, define support as the highest score among eligible
   groups containing that recording. Duplicate groups do not accumulate score.
6. When no eligible recording remains, return `no_match`.
7. Order recordings by descending support and then canonical MBID only for
   deterministic inspection.
8. When two or more recordings share the highest support, return `ambiguous`.
9. When a runner-up exists and the top-minus-runner-up difference is below
   `min_margin`, return `ambiguous`.
10. Otherwise return `decisive` for the unique top recording.
11. Select the AcoustID UUID from the highest-scoring eligible group supporting
    that recording; canonical UUID ordering breaks only same-recording ties.

Textual metadata and recording duration do not modify this algorithm. The
existing MusicBrainz structural audit performs title, artist, duration,
position, completeness, pair-score, total-score, and margin validation.

## MusicBrainz Compatibility Filter

The existing structural candidate evaluation runs first and remains byte-for-
byte equivalent in inputs, weights, scores, assignments, and ordering.

For each decisive local-track evidence item, the compatibility pass checks the
recording MBID assigned by each already-evaluated complete MusicBrainz release
candidate:

```text
assigned recording MBID == decisive AcoustID recording MBID
```

A mismatch makes that candidate acoustically incompatible. Unavailable,
no-match, and ambiguous evidence is neutral.

After incompatible candidates are removed, the existing minimum total score,
pair score, complete assignment, ambiguity, and unique-margin gates run on the
remaining structural evaluations. AcoustID never changes a score component.

When decisive evidence removes every candidate, the audit remains ambiguous
with the stable reason:

```text
acoustid_recording_conflict
```

Four-field MusicBrainz findings still come only from the selected complete
MusicBrainz release candidate.

## Standalone Database Mapping

Only these beets Item fields are eligible:

```text
acoustid_id
acoustid_fingerprint
```

Field states are:

```text
KEEP
PROPOSE
REVIEW
BLOCKED
```

Rules:

- same valid current and proposed value -> `KEEP`;
- empty current field plus an eligible value -> `PROPOSE`;
- conflicting non-empty current value -> `REVIEW`;
- stale or invalid target state -> `BLOCKED`;
- decisive evidence may propose `acoustid_id`;
- existing or generated valid material may propose
  `acoustid_fingerprint` even when lookup is unavailable;
- no MusicBrainz field can enter this plan.

Application is all-plan-before-first-write. Any selected-target, membership,
path, database, current-value, or generated-source snapshot mismatch blocks the
complete application unit before the first store.

## Preview Vocabulary

The path-free and fingerprint-free preview uses these public states:

```text
Fingerprint: REUSED | GENERATED | MISSING | UNAVAILABLE
Lookup:      DECISIVE | AMBIGUOUS | NO_MATCH | UNAVAILABLE
Database:    KEEP | PROPOSE | REVIEW | BLOCKED
```

Stable reasons may include:

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

Preview may show a canonical recording MBID and a shortened AcoustID UUID for a
decisive result. It never shows fingerprints, private paths, keys, raw payloads,
backend commands, backend output, or provider exception text.

## beets `chroma` Coexistence

Native beets `chroma` continues to own importer acoustic matching, import-time
fingerprinting, the existing `beet fingerprint` workflow, and submission through
native beets facilities.

Noqlen Block 029 owns only:

- conservative existing-library evidence preview;
- explicit missing-fingerprint calculation within Noqlen's mode;
- database-only AcoustID field planning/application;
- optional recording compatibility filtering for Noqlen's MusicBrainz identity
  audit.

The two integrations may reuse the same beets database fields but are not
presented as the same command or authority boundary.

## Documentation-Only Chat Boundary

Repository work performed from this chat is limited to documentation, specs,
ADRs, context, handoff, and documentation-only PR administration.

Product code, tests, dependencies, package metadata, workflows, version bumps,
tags, and releases must be implemented and validated outside this chat after
the corresponding documentation contract is approved.
