# Block 029 Design

## Architectural Boundary

AcoustID is not added to `BUILTIN_PROVIDER_SPECS` and does not emit ordinary
`MetadataCandidate` values. The ordinary provider resolver is field-oriented
and target-independent, while an acoustic fingerprint is evidence about the
identity of one concrete audio file. Mixing those concepts would let ordinary
metadata authority influence MusicBrainz identity and would weaken the existing
separation established by ADR 0020.

Block 029 adds a dedicated subsystem under a provisional
`beetsplug.noqlenmeta.acoustid` package. It has four boundaries:

```text
fresh beets Item selection
-> existing fingerprint/ID inspection or explicit local fingerprinting
-> bounded AcoustID lookup and evidence classification
-> preview, AcoustID-field database plan, or MusicBrainz candidate filtering
```

The subsystem cannot write files and cannot create a complete MusicBrainz
release identity.

## Scope

The first implementation supports existing-library Albums and singletons. That
scope has fresh `Item` objects, stable database IDs, paths for optional local
fingerprinting, and established stale-state application patterns.

Importer fingerprint generation and autotagger candidate creation are deferred.
Users who need acoustic matching during import continue to use the native beets
`chroma` plugin. A later block may consume AcoustID fields already attached to
selected importer metadata, but it must not duplicate beets matching.

## Proposed Public Mode

The existing command receives a mutually exclusive mode:

```text
beet nm --acoustid QUERY
beet nm --acoustid --fingerprint-missing QUERY
beet nm --acoustid --apply QUERY
beet nm --acoustid --fingerprint-missing --apply QUERY
beet nm --acoustid --all
```

Provisional semantics:

- `--acoustid` selects the AcoustID evidence mode.
- Preview is always available and writes nothing.
- `--fingerprint-missing` explicitly permits local calculation for selected
  Items that lack a valid stored fingerprint.
- `--apply` stores only approved AcoustID fields in the beets database.
- `--all` retains its existing meaning inside the selected mode.
- `--partial`, `--write`, and `--identity-tags` are invalid with
  `--acoustid`.
- No `--force` option exists.

The final option names remain subject to command-contract tests before the
implementation branch is accepted.

## Proposed Configuration

A separate top-level section avoids presenting AcoustID as an ordinary provider:

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
    timeout_seconds: 15
    requests_per_second: 3
    cache_entries: 256
    fpcalc: fpcalc
```

Rules:

- command-line `--fingerprint-missing` may enable calculation for that run even
  when `compute_missing` is false;
- `compute_missing` never affects ordinary enrichment;
- `lookup: true` requires `NOQLENMETA_ACOUSTID_API_KEY` when network work is
  needed;
- a missing key produces an unavailable lookup result, not a configuration
  secret fallback;
- all numeric values reject booleans, non-finite numbers, and unsafe bounds;
- the complete default tree and public example remain exact production mirrors.

## Domain Model

### Selected target

`SelectedAcoustIDTarget` contains one complete fresh Album or one fresh
singleton, retaining stable database IDs and deterministic Item order.

`SelectedAcoustIDItem` retains:

- a path-free `local_key` derived from the Item database ID;
- the fresh `Item` object;
- current `acoustid_id` and `acoustid_fingerprint` values;
- artist, title, album, duration, and current recording MBID;
- the media path privately for optional backend execution.

### Fingerprint material

`AcoustIDFingerprintMaterial` contains:

- `local_key`;
- fingerprint text held privately inside the plan/evidence object;
- duration in whole or finite positive seconds;
- origin: `existing` or `generated`;
- an optional source-file snapshot for generated material.

Its representation and preview helpers must redact the fingerprint.

### Service results

`AcoustIDResultGroup` contains:

- canonical AcoustID UUID;
- finite score from 0.0 to 1.0;
- a bounded tuple of canonical MusicBrainz recording MBIDs.

No release, release-group, medium, or release-track value enters this model.
Provider payloads can contain such data, but the normalizer intentionally
ignores it.

### Track evidence

`AcoustIDTrackEvidence` contains:

- local key and fingerprint origin;
- bounded normalized result groups;
- verdict: `unavailable`, `no_match`, `ambiguous`, or `decisive`;
- optional selected AcoustID UUID and selected recording MBID;
- a stable machine-readable reason;
- safe counts and scores for preview.

The selected recording exists only for a decisive verdict.

### Target result

`AcoustIDEvidenceResult` contains the selected target, exact database snapshot,
per-track evidence, and a database target plan. It does not contain an audio-
file write plan.

## Existing-Value Reuse

For each Item:

1. Validate an existing stored fingerprint.
2. Reuse it without discovering or invoking a backend.
3. Reuse a valid existing AcoustID UUID as current state, not as proof that a
   new lookup result is correct.
4. When no fingerprint exists and calculation is not authorized, classify the
   track as unavailable with reason `fingerprint_missing`.
5. When calculation is authorized, invoke the bounded backend once.

A stored AcoustID ID without a fingerprint can be shown and preserved, but it
cannot independently provide recording evidence unless a future official API
path supports a defensible reverse lookup contract.

## Fingerprint Backend

The backend is an injected protocol:

```python
class FingerprintBackend(Protocol):
    def fingerprint(self, path: bytes) -> FingerprintResult: ...
```

The production backend initially targets the official Chromaprint `fpcalc`
interface. Implementation must first determine whether a narrow direct
subprocess or a compatible optional Python wrapper provides the best supported-
Python and cross-platform behavior. The decision must not affect the evidence
or application contracts.

Backend requirements:

- executable discovery happens only when calculation is needed;
- one argument vector, no shell;
- bounded timeout and captured bytes;
- bounded JSON or key-value parsing;
- finite positive duration and non-empty bounded fingerprint;
- sanitized errors;
- no command/path/fingerprint in public output.

A generated result captures a no-follow source snapshot containing only values
needed for stale verification, such as device, inode, size, and nanosecond
modification time. Symbolic links and unsupported snapshot semantics fail
closed before a generated fingerprint can be applied.

## HTTPS Lookup Transport

The transport is independent from fingerprint generation. It uses the official
HTTPS v2 lookup endpoint with a form-encoded POST body containing:

```text
client
fingerprint
rounded duration
meta=recordingids
format=json
```

Only recording IDs are requested because release-specific data is outside the
AcoustID authority boundary.

The transport provides:

- sequential process-local pacing at no more than the configured ceiling;
- monotonic timing and injectable sleep;
- one bounded timeout;
- bounded request and response sizes;
- bounded result and recording counts;
- strict JSON and schema validation;
- sanitized handling of HTTP, timeout, service, and rate-limit failures;
- a bounded process-local cache keyed by a digest of fingerprint and duration,
  never by raw fingerprint text in logs or persistent storage.

No retry occurs unless a later implementation requirement defines a bounded,
service-compliant retry rule. Fingerprint submission is absent.

## Evidence Classification

Normalization first discards malformed result groups and recording identifiers.
It then evaluates only groups at or above `min_score`.

For every eligible group, recording MBIDs are canonicalized and deduplicated.
The classifier aggregates support by recording MBID while retaining the result
scores and AcoustID IDs that supplied it.

A track is decisive only when all conditions hold:

1. at least one eligible result remains;
2. exactly one recording MBID has the highest defensible support;
3. its best score meets `min_score`;
4. the score margin over the strongest competing recording meets
   `min_margin`;
5. no equally strong result group maps to a different recording;
6. duration does not exceed the configured hard mismatch boundary;
7. optional artist/title corroboration does not produce a hard mismatch.

No eligible result produces `no_match`. Multiple plausible recordings, a weak
margin, or contradictory high-score groups produce `ambiguous`. Backend,
credential, network, or service unavailability produces `unavailable`.

The exact title, artist, duration, and margin thresholds are immutable policy
values with boundary tests. Their weights do not enter MusicBrainz structural
scores.

## Integration With MusicBrainz Identity

The existing MusicBrainz source continues to return complete
`MusicBrainzReleaseIdentity` candidates. Existing structural evaluations are
computed unchanged.

A new pure compatibility pass receives:

```text
IdentityAlbumContext
+ structural candidate evaluations
+ decisive AcoustID evidence by local_key
```

For each decisive local track, it inspects the assignment already calculated
for a candidate. The assigned candidate track must have the same recording MBID
as the acoustic evidence. A mismatch marks that release candidate acoustically
incompatible.

Selection order:

1. acquire complete MusicBrainz candidates;
2. calculate existing structural evaluations and assignments;
3. reject acoustically incompatible evaluations;
4. apply the existing minimum score, pair score, complete assignment, ambiguity,
   and margin gates to the remaining evaluations;
5. generate the existing four-field findings only from the selected complete
   MusicBrainz release candidate.

AcoustID does not modify `IdentityScoreBreakdown`. This prevents acoustic
support from rescuing a weak release structure and lets tests prove the original
score is unchanged.

When evidence is unavailable, no match, or ambiguous, the corresponding local
track adds no filter. When decisive evidence removes every candidate, the audit
returns an ambiguous result with a distinct safe reason such as
`acoustid_recording_conflict`.

## Database Target Mapping

The standalone AcoustID mode maps only:

```text
acoustid_id
acoustid_fingerprint
```

Mapping rules:

- same canonical value -> `KEEP`;
- empty current field plus decisive/generated value -> `PROPOSE`;
- conflicting non-empty current value -> `REVIEW`;
- ambiguous/no-match/unavailable evidence -> no proposed ID;
- a generated fingerprint may be proposed even when lookup is unavailable;
- no MusicBrainz field enters the AcoustID database target plan.

The target mapping must use fields natively supported by the claimed beets
versions. Compatibility tests prove reads, stores, reloads, and query behavior
at both beets boundaries.

## Application Boundary

Application follows all-plan-before-first-write semantics.

Before mutation it re-fetches every selected target and verifies:

- target kind and Album/singleton membership;
- Item IDs and deterministic order;
- exact fields used to build contexts, current values, and plans;
- media path equality when generated fingerprint material is involved;
- the generated source-file snapshot;
- unchanged proposed/current field relationships.

Any mismatch blocks the complete command application before the first store.
Successful application updates only the planned Item database fields and calls
normal beets store methods. It does not write tags or modify operational mtime
fields itself.

## Preview

Preview is path-free and fingerprint-free. One track may render:

```text
Fingerprint  REUSED | GENERATED | MISSING | UNAVAILABLE
Lookup       DECISIVE | AMBIGUOUS | NO_MATCH | UNAVAILABLE
AcoustID     shortened identifier or none
Recording    canonical MBID or none
Database     KEEP | PROPOSE | REVIEW | BLOCKED
Reason       stable safe explanation
```

Album summaries report counts. They do not print raw service errors, raw
responses, full fingerprints, client keys, or private paths.

## Files And Modules

Provisional production layout:

```text
beetsplug/noqlenmeta/acoustid/
  __init__.py
  domain.py
  backend.py
  transport.py
  evidence.py
  library.py
  mapping.py
  application.py
  preview.py
  identity_filter.py
```

Integration changes remain narrow:

- command parser and mode dispatch in `__init__.py`;
- fresh defaults in `configuration.py`;
- optional dependency metadata only when backend validation justifies it;
- identity audit orchestration accepts optional evidence without changing its
  default behavior.

## Test Layout

```text
tests/acoustid/
  test_domain.py
  test_backend.py
  test_transport.py
  test_evidence.py
  test_library.py
  test_mapping.py
  test_application.py
  test_preview.py
  test_identity_filter.py
  test_workflows.py
```

Normal tests use fake subprocess/service boundaries and generated temporary
media. Live tests are separately marked and never gate CI.

## Delivery Sequence

The implementation should use focused branches and reviewer gates:

1. domain, policy, and configuration;
2. existing-value and fingerprint backend boundary;
3. HTTPS service transport and evidence classification;
4. existing-library selection, preview, mapping, and application;
5. pure MusicBrainz identity compatibility filter;
6. command integration, package support, documentation, and release hardening.

No branch may acquire file-write authority or direct release-specific identity
from AcoustID.
