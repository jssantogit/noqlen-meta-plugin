# Block 029 Stage 03 Implementation Brief

## Status

Proposed implementation brief for review.

This document authorizes no product implementation until it passes repository
review, CI, and squash merge. Repository work performed from the project chat
remains documentation-only.

Normative precedence remains:

1. `contracts.md`;
2. ADR 0025;
3. this Stage 03 brief;
4. earlier requirements and design documents.

When provisional wording conflicts with the frozen contracts, the frozen
contracts win.

## Baseline

Stage 03 starts after the reviewed Stage 02 implementation and completion record:

```text
Stage 02 code:       5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc
Stage 02 completion: 8fc5cff7deefa3f24e9a092f96fdcd0035eb7d54
```

Stage 03 must preserve all Stage 01 and Stage 02 domain, privacy, target,
fingerprint, subprocess, snapshot, and offline-test invariants.

## Objective

Implement only the AcoustID service lookup boundary needed to turn valid
fingerprint material into bounded recording-level evidence:

- resolve the application client key only at the service boundary;
- perform an injectable HTTPS form POST to the frozen lookup endpoint;
- request only `meta=recordingids` and JSON;
- pace sequential requests with monotonic time;
- bound request and response bytes;
- parse strict UTF-8 JSON and only the schema required by the frozen evidence
  model;
- normalize bounded AcoustID UUID/score/recording-MBID groups through the
  existing Stage 01 evidence boundary;
- cache process-local successful lookup results by a digest of private
  fingerprint material plus rounded duration;
- map credential, transport, timeout, HTTP, service, oversized, malformed, and
  parsing failures to the existing safe reason vocabulary;
- add deterministic offline tests with fake clock, sleeper, transport, and
  synthetic payloads.

Stage 03 performs no database planning or mutation, no command integration, no
public configuration integration, no MusicBrainz candidate filtering, and no
audio-file writes.

## Reviewed Official Service Contract

The implementation targets:

```text
POST https://api.acoustid.org/v2/lookup
Content-Type: application/x-www-form-urlencoded
```

The form body contains only:

```text
client=<application API key>
duration=<rounded whole seconds>
fingerprint=<private fingerprint>
meta=recordingids
format=json
```

The official AcoustID web-service documentation reviewed for this brief states
that fingerprint lookup requires `client`, `duration`, and `fingerprint`,
supports `recordingids`, returns UTF-8 text, and asks clients not to exceed three
requests per second.

Reference:

```text
https://acoustid.org/webservice
```

No release, release-group, track, artist, title, ISRC, source, or expanded
recording metadata is requested or retained.

## Credential Boundary

The exact environment variable remains:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

Requirements:

- resolve it lazily only when a network lookup is actually needed;
- use process environment access through an injectable credential resolver;
- treat missing or empty values as unavailable credentials;
- never place the key in domain values, cache keys, representations, exceptions,
  logs, preview, committed examples, or persistent storage;
- never forward the key to the fingerprint subprocess;
- a missing key maps to `client_key_missing` and performs no network call.

There is no configuration-file fallback in Block 029.

## Lookup Enablement And Laziness

A lookup is attempted only when valid fingerprint material exists and lookup is
enabled by the active AcoustID settings.

When lookup is disabled:

- return unavailable with `lookup_disabled`;
- perform no credential resolution;
- perform no pacing wait;
- perform no cache mutation;
- perform no transport work.

When the client key is missing:

- return unavailable with `client_key_missing`;
- perform no pacing wait;
- perform no transport work.

## Duration Contract

The request sends rounded whole seconds. Stage 03 freezes deterministic half-up
rounding for positive finite durations:

```text
whole_seconds = floor(duration_seconds + 0.5)
```

The request value must be at least `1`. The original duration remains unchanged
in the domain and never participates in evidence scoring.

## Request Encoding And Bound

The form body is UTF-8 `application/x-www-form-urlencoded` bytes. Build the
complete body before opening the request and fail closed when it exceeds:

```text
MAX_LOOKUP_REQUEST_BYTES = 2_097_152  # 2 MiB
```

An oversized body maps to `lookup_failed` without opening a connection.

The request must:

- use HTTPS only;
- target the exact frozen endpoint;
- use POST only;
- set `Content-Type: application/x-www-form-urlencoded`;
- include exactly the five frozen form fields;
- send no fingerprint in a query string or header;
- send no media path, local key, User API key, or unrelated metadata;
- use the validated `timeout_seconds` value;
- perform no automatic retry.

Redirect behavior must fail closed so private POST data and the client key are
never forwarded automatically to a different origin.

TLS verification remains enabled through the standard HTTPS stack. No insecure
SSL context is permitted.

## Injectable Transport

HTTP I/O must live behind a small injectable boundary suitable for deterministic
offline tests. The default implementation may use the Python standard library;
Stage 03 adds no dependency.

Transport and response objects must redact private body content in
representations. Expected network exceptions must never escape with raw provider
or operating-system text.

## Response Bound

Read the response incrementally and cap retained bytes before JSON parsing:

```text
MAX_LOOKUP_RESPONSE_BYTES = 1_048_576  # 1 MiB
```

If the response exceeds the cap, close it and return `lookup_failed`. The reader
must never use an unbounded read that can retain an arbitrary body in memory.

## HTTP And Service Status

Only a successful HTTPS response proceeds to JSON/schema parsing.

Expected HTTP, URL, TLS, timeout, connection, rejected-redirect, read, and size
failures map to `lookup_failed`. There is no retry for HTTP 429, 5xx, timeout, or
any other failure.

A parsed service response proceeds only when:

```json
{"status": "ok", ...}
```

Any non-`ok`, missing, or malformed service status maps to `lookup_failed`. Raw
service error fields are ignored and never surfaced.

## Strict JSON And Schema Boundary

Response bytes must decode as strict UTF-8 and parse as one complete JSON value.
Reject non-standard numeric constants such as `NaN` and `Infinity`.

The top-level value must be an object. `results`, when present, must be an array.
An absent or empty `results` array is a valid no-match lookup rather than a
transport failure.

Retain only:

```text
results[].id
results[].score
results[].recordings[].id
```

Everything else is ignored. No title, artist, duration, release,
release-group, track, source, ISRC, URL, raw payload, or unknown subtree enters
the domain.

Malformed retained fields fail closed as `lookup_failed`; they are never repaired
from unrelated payload metadata.

## Defensive Result Bounding

Use the existing validated settings:

```text
max_results
max_recordings_per_result
```

The parser must inspect and retain at most `max_results` result groups and at
most `max_recordings_per_result` recording IDs per retained group before domain
construction.

Canonical UUID, score, duplicate/conflict, minimum-score, support, tie, margin,
and deterministic-order behavior remains owned by existing Stage 01 domain and
evidence code. Stage 03 must not create a second evidence algorithm.

## Sequential Rate Limiting

The official service ceiling is three requests per second and the frozen
`requests_per_second` setting is already validated as positive and at most 3.0.

Use process-local sequential pacing with injectable monotonic clock and sleeper:

```text
minimum_interval = 1.0 / requests_per_second
```

Before each uncached network request:

1. inspect monotonic time;
2. compare with the previous network request start;
3. sleep only the positive remaining interval;
4. start the request;
5. record the actual monotonic request-start time.

Requirements:

- cache hits do not consume rate slots or sleep;
- disabled lookup and missing credentials do not consume slots;
- failed network attempts do consume a slot once transport is entered;
- impossible monotonic-clock movement fails closed as `lookup_failed`;
- Stage 03 introduces no concurrent request orchestration.

## Process-Local Cache

Caching is bounded by existing `cache_entries`; `0` disables caching.

The key must not contain raw fingerprint or client key. Use SHA-256 over an
explicitly framed/versioned byte sequence containing:

- fingerprint UTF-8 bytes;
- rounded whole-second duration.

The value may contain only normalized safe lookup content. It must never retain
raw fingerprint, client key, request body, raw response, media path, or exception
text.

Cache successful parsed lookup results only. Do not cache transport or service
failures. Use deterministic bounded eviction and process-local memory only; no
persistent cache is introduced.

## Safe Outcome Boundary

Stage 03 may add a small immutable lookup outcome suitable for later workflow
integration. It may contain a path-free `local_key`, bounded normalized result
groups, existing evidence verdict/reason values, and already-approved safe
counts/scores.

It must never contain fingerprint text, client key, raw request/response, media
path, URL parameters, or raw exception text in its representation.

Reuse the frozen reasons:

```text
lookup_disabled
client_key_missing
lookup_failed
no_result_above_minimum
competing_recordings
insufficient_margin
recording_decisive
```

Do not add transport-specific public reason strings without a reviewed contract
amendment.

## Error Sanitization

No public result or exception may expose:

- API key;
- fingerprint;
- media path;
- request body or parameterized URL;
- raw response bytes/text or HTTP body;
- server error message;
- raw `urllib`, socket, SSL, or OS exception text;
- cache digest inputs.

Expected operational failures become safe outcomes. Programmer/type-contract
violations may raise generic errors but must still redact private values.

## Required Offline Tests

Normal CI remains fully offline.

Credential/laziness tests:

- lookup disabled performs no credential/cache/pacing/transport work;
- missing key performs no pacing/transport work;
- key never appears in repr/errors;
- environment access is injectable and occurs only at the lookup boundary.

Request tests:

- exact endpoint, POST method, five form fields, content type, timeout;
- exact `meta=recordingids` and `format=json`;
- half-up duration rounding;
- request-size boundary at and above 2 MiB;
- redirect rejection and no retry;
- no private metadata outside the body.

Response tests:

- strict UTF-8 and one complete JSON value;
- reject NaN/Infinity and malformed JSON;
- require service status `ok`;
- empty results is valid;
- response-size boundary at and above 1 MiB;
- incremental bounded reads;
- unknown metadata ignored;
- only ID/score/recording-ID fields retained;
- max result and recording bounds applied before domain construction.

Pacing tests:

- first request does not sleep unnecessarily;
- sequential misses honor the configured interval;
- cache hits do not sleep;
- failed network attempts consume a slot;
- rates below 3.0 calculate the expected interval;
- monotonic anomalies fail closed;
- no wall-clock dependency.

Cache tests:

- key changes with fingerprint or rounded duration;
- raw private inputs absent from key/repr;
- zero entries disables cache;
- deterministic bounded eviction;
- successful cache hit avoids pacing and transport;
- failures are not cached.

Failure tests cover synthetic timeout, HTTP 4xx/5xx/429, redirect, TLS/URL
failure, oversized response, invalid UTF-8, malformed JSON, bad schema,
non-`ok` service status, invalid retained IDs/scores, and sanitization.

Any live test must be optional, explicitly marked, excluded from normal CI, and
must never use a committed real client key.

## Expected Product File Allowlist

Expected Stage 03 product changes are limited to:

```text
beetsplug/noqlenmeta/acoustid/__init__.py
beetsplug/noqlenmeta/acoustid/domain.py
beetsplug/noqlenmeta/acoustid/evidence.py
beetsplug/noqlenmeta/acoustid/service.py
tests/acoustid/test_domain.py
tests/acoustid/test_evidence.py
tests/acoustid/test_service.py
```

A small test-only `tests/acoustid/conftest.py` is conditionally allowed.
Implementation may omit unchanged listed files. Any product file outside this
allowlist requires explicit reviewer justification.

No Stage 02 selector or fingerprint-backend refactor is authorized except a
minimal import/export adjustment required by the new service boundary.

## Explicit Stage 03 Exclusions

Stage 03 must not add or change:

- database snapshots, plans, stores, or application workflow;
- `AcoustIDTargetResult` application ownership;
- public preview rendering;
- `--acoustid`, `--fingerprint-missing`, parser, dispatch, or command validation;
- public configuration integration;
- MusicBrainz candidate filtering or assignment logic;
- ordinary provider registration/resolution;
- importer hooks or native beets `chroma` behavior;
- fingerprint submission or User API-key handling;
- dependencies, optional extras, workflow configuration, package metadata;
- README, public site docs, changelog, version, tag, release, publication;
- audio-file writes.

## Reviewer Gate

Before Stage 03 product code may merge, the external implementation report must
show:

- diff confined to the approved allowlist;
- focused Stage 03 tests passing;
- full offline suite passing;
- Ruff and repository hygiene/diff checks passing;
- no real network access in normal tests;
- exact endpoint/form contract tests;
- deterministic pacing/cache tests;
- request/response boundary tests;
- proof that no key, fingerprint, path, request body, raw response, or raw
  network exception appears in representations/errors;
- supported Python and beets CI green.

Final acceptance requires external reviewer PASS plus green repository CI.

## Next Stage Boundary

After Stage 03 is implemented, reviewed, merged, and recorded complete, a later
stage may define standalone preview, database mapping, exact database snapshots,
and all-plan-before-first-write application.

That later stage must re-verify generated source snapshots before mutation and
remain database-only with no audio-file writes.
