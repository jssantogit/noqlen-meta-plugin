# Block 029 Stage 03 Completion Record

## Status

Complete and merged on 2026-08-09.

Stage 03 was implemented outside the project chat, reviewed against the frozen
contracts and approved Stage 03 brief, hardened through external review, validated
by repository CI, and squash-merged through PR #12.

```text
PR: https://github.com/jssantogit/noqlen-meta-plugin/pull/12
Reviewed head: 89bbef8cd4588ec904f71cafa5a1e772f449b6ff
Main commit: 45c6dc20666b79bb057e34596e131a109ac22b38
CI: run 59, success
```

This record changes no product behavior.

## Delivered Scope

Stage 03 added the bounded AcoustID HTTPS lookup boundary needed to convert valid
fingerprint material into recording-level evidence:

- lazy resolution of `NOQLENMETA_ACOUSTID_API_KEY` only when an uncached network
  lookup is actually required;
- exact HTTPS form POST to `https://api.acoustid.org/v2/lookup`;
- exactly five form fields: `client`, rounded `duration`, private `fingerprint`,
  `meta=recordingids`, and `format=json`;
- deterministic half-up whole-second duration rounding;
- no automatic retry and fail-closed redirect behavior;
- verified TLS through the standard HTTPS stack;
- a 2 MiB request cap before opening transport;
- incremental response reads with a 1 MiB retained-response cap;
- strict UTF-8 JSON parsing, rejection of non-standard numeric constants, and
  strict retained-schema validation;
- retention only of AcoustID UUID, score, and recording MBIDs;
- reuse of the existing Stage 01 evidence classifier rather than a second
  scoring/classification algorithm;
- sequential process-local pacing with injectable monotonic clock and sleeper;
- bounded process-local successful-result caching using a framed SHA-256 digest
  without raw fingerprint or client key;
- deterministic fully offline service tests.

The implementation lives in:

```text
beetsplug/noqlenmeta/acoustid/__init__.py
beetsplug/noqlenmeta/acoustid/domain.py
beetsplug/noqlenmeta/acoustid/service.py
```

Stage 03 tests live in:

```text
tests/acoustid/test_service.py
```

No Stage 02 selector or fingerprint-backend implementation was refactored.

## Review Findings Resolved

External review hardened the implementation until these additional properties
held:

1. The default HTTPS transport is constructed lazily only after lookup is
   enabled, cache misses, credentials are valid, the request is encodable and
   within bounds, and pacing reaches a real transport attempt.
2. Lookup-disabled, missing-key, oversized-request, and cache-hit paths perform
   no default transport construction.
3. Expected operational failures remain safe `lookup_failed` outcomes, while
   unexpected injected-component/programming failures propagate only through
   sanitized generic boundary errors instead of being silently misclassified.
4. Credential-resolver failures do not become false `client_key_missing`
   outcomes.
5. Non-encodable private fingerprint or client-key material fails closed before
   network work without exposing the private value.
6. HTTP response-reader failures from `http.client`, including
   `IncompleteRead`, are treated as expected read failures, close the response,
   map to `lookup_failed`, and are not cached.
7. Partial response content, client keys, fingerprints, paths, request bodies,
   raw response bodies, and raw network/provider exception text remain absent
   from public outcomes and propagated sanitized errors.
8. Conflicting duplicate AcoustID result groups fail closed before evidence
   classification.

## Completed Task Mapping

### Credential, request, and transport boundary

Lookup remains fully lazy when disabled. A cache hit avoids credential
resolution, pacing, transport construction, and network work. Missing credentials
stop before pacing and transport.

The production request contract is:

```text
POST https://api.acoustid.org/v2/lookup
Content-Type: application/x-www-form-urlencoded

client=<application API key>
duration=<rounded whole seconds>
fingerprint=<private fingerprint>
meta=recordingids
format=json
```

The complete encoded request is bounded before transport opens. Redirects are
rejected, TLS verification remains enabled, and there is no retry for timeout,
429, 5xx, or any other failure.

### Response and evidence boundary

Responses are read incrementally and closed on success or failure. The parser
accepts only strict UTF-8 JSON with service status `ok`, inspects only the
configured bounded number of result/recording entries, and retains only:

```text
results[].id
results[].score
results[].recordings[].id
```

Unknown service metadata is ignored. Empty or absent results are valid no-match
lookups. Malformed retained fields and conflicting duplicates fail closed.

Normalized groups are handed to the existing Stage 01 evidence classifier, so
minimum-score, support, ambiguity, tie, margin, and decisive-recording behavior
remain owned by one domain algorithm.

### Pacing and cache

Sequential uncached network attempts use monotonic pacing at the configured rate
up to the frozen 3 requests/second ceiling. Cache hits do not sleep or consume a
rate slot. Once transport is entered, a failed network attempt consumes its slot.
Impossible monotonic-clock movement fails closed.

Successful parsed lookups may be cached process-locally under the configured
entry bound. Cache keys are framed SHA-256 digests over private fingerprint bytes
and rounded duration; raw fingerprint and client key never enter cache keys or
representations. Transport, service, parsing, and schema failures are not cached.

## Validation Evidence

CI run 59 completed successfully for the final reviewed head. All nine repository
jobs passed:

- Python 3.10;
- Python 3.11;
- Python 3.12;
- Python 3.13;
- Python 3.14;
- beets minimum 2.12.0;
- beets latest below 3;
- documentation;
- package.

The Python matrix ran lint, offline tests, and repository hygiene. Compatibility,
strict documentation build, package metadata/archive inspection, and clean-install
smoke testing also passed.

The final PR diff remained confined to four Stage 03 allowlisted product/test
files.

## Preserved Exclusions

Stage 03 introduced none of the following:

- database snapshots, plans, stores, or application workflow;
- `AcoustIDTargetResult` application ownership;
- standalone public preview rendering;
- command parser/dispatch or `--acoustid` integration;
- public configuration integration;
- MusicBrainz candidate filtering;
- ordinary provider/importer integration;
- fingerprint submission or User API-key handling;
- new dependencies, optional extras, package metadata, or workflow changes;
- README, public site docs, changelog, version, tag, release, or publication
  changes;
- audio-file writes.

## Next Stage Boundary

No new product implementation stage is active yet.

The next documentation stage should define the standalone AcoustID workflow
boundary around preview, exact database mapping/planning, stale-state protection,
and database-only application. It must preserve all-plan-before-first-write
semantics, re-fetch exact target state before mutation, and re-verify generated
source snapshots before mutation.

That stage should still exclude MusicBrainz candidate filtering, public command
and configuration integration, provider/importer integration, package/release
work, and all audio-file writes unless its own reviewed brief explicitly
separates and authorizes those concerns.
