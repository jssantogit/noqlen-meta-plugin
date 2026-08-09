# Block 029 Stage 04 Implementation Brief

## Status

Proposed implementation brief for review.

This document authorizes no product implementation until it passes repository
review, CI, and squash merge. Repository work performed from the project chat
remains documentation-only.

Normative precedence remains:

1. `contracts.md`;
2. ADR 0025;
3. this Stage 04 brief;
4. earlier requirements and design documents.

When provisional wording conflicts with the frozen contracts, the frozen
contracts win.

## Baseline

Stage 04 starts after reviewed Stage 03 implementation and completion:

```text
Stage 03 code:       45c6dc20666b79bb057e34596e131a109ac22b38
Stage 03 completion: f7f29052ad9fc2c3f919e14991908d08a4bf0c4f
```

Stages 01-03 already own domain/evidence policy, fresh Album/singleton target
selection, stored-value validation, bounded fingerprint preparation, generated
source snapshots, HTTPS lookup, pacing, caching, and evidence classification.
Stage 04 must compose those boundaries rather than duplicate them.

## Objective

Implement the standalone existing-library workflow between Stage 03 evidence and
a later public command integration:

```text
fresh selected AcoustID target
-> exact AcoustID planning snapshot
-> fingerprint preparation
-> optional bounded lookup / track evidence
-> immutable database mapping
-> path-free, fingerprint-free preview
-> verified database-only application
```

Stage 04 is intentionally one reviewed design with two product PRs:

- **Stage 04A — Planning + Preview:** side-effect-free with respect to the beets
  database; it may use the already-authorized Stage 02 backend and Stage 03
  lookup boundaries while building a plan.
- **Stage 04B — Database Apply:** consumes fully prepared Stage 04A results,
  performs command/application-unit-wide stale preflight before the first
  mutation, and stores only approved Item database fields.

The mutation boundary between 04A and 04B is deliberate. Stage 04A must merge
and pass review before Stage 04B begins.

## Explicit Exclusions

Neither Stage 04 product PR may add or change:

- `--acoustid`, `--fingerprint-missing`, parser, dispatch, or public command
  behavior;
- the public `configuration.default_config()` AcoustID subtree;
- MusicBrainz candidate filtering or identity orchestration;
- ordinary provider or importer behavior;
- importer/autotagger acoustic matching;
- audio-file tag writes or `Item.write()` calls;
- fingerprint submission;
- force or partial application behavior;
- dependencies, package metadata, workflows, versions, tags, or releases;
- public README/MkDocs/changelog content.

Those remain later reviewed stages.

# Stage 04A — Planning + Preview

## 04A Boundary

Stage 04A owns only composition, exact planning state, immutable database plans,
and rendering. It performs no database mutation.

A Stage 04A workflow may invoke existing Stage 02 fingerprint preparation and
existing Stage 03 lookup because those are already frozen side-effect boundaries.
It must not reimplement their subprocess, source-snapshot, transport, cache,
pacing, or evidence logic.

## Exact Planning Snapshot

Add a dedicated immutable exact AcoustID target snapshot. It must preserve the
exact state that can invalidate the resulting plan without exposing private
material in representations.

For the target, retain:

- target kind;
- Album ID or singleton state;
- deterministic ordered Item membership.

For each Item, retain at least:

- `local_key`;
- Item database ID;
- Album membership ID;
- exact media path privately and with `repr=False`;
- exact finite/current `length` value used by stored-fingerprint lookup
  preparation;
- exact raw current `acoustid_id` database value;
- exact raw current `acoustid_fingerprint` privately and with `repr=False`.

The snapshot is stricter than `AcoustIDExistingValues`. A malformed stored value
must remain distinguishable from a different malformed value so a concurrent
change such as `bad-a` -> `bad-b` is detected during stale verification.

Snapshot equality is exact. It must not canonicalize away a database change.
Path and fingerprint material remain private in `repr`, errors, and preview.

No MusicBrainz field enters this snapshot.

## Per-Track Workflow Composition

For each selected Item, Stage 04A must:

1. use the Stage 02 `prepare_fingerprint` boundary;
2. preserve its stable preparation reason;
3. when valid material exists, pass that material to the Stage 03
   `AcoustIDLookupService` boundary;
4. when no material exists, produce the corresponding unavailable workflow
   outcome without inventing recording evidence;
5. retain generated-source snapshot material only when Stage 02 generated it;
6. map the resulting eligible values to the standalone AcoustID database plan.

No textual metadata or MusicBrainz score is added here.

A stored `acoustid_id` remains current database state only. It is never promoted
to fresh recording evidence without a decisive Stage 03 lookup result.

## Database Plan Model

The frozen public planning states remain:

```text
KEEP
PROPOSE
REVIEW
BLOCKED
```

The implementation may choose narrow immutable Python type names, but every
planned change must identify only:

```text
acoustid_id
acoustid_fingerprint
```

A field plan must retain enough private source/current state to prove that a
later application still corresponds to the exact Stage 04A plan.

### `acoustid_id`

An eligible proposed ID exists only when track evidence is `decisive`.

- empty current value + decisive selected AcoustID UUID -> `PROPOSE`;
- same valid canonical current UUID + same decisive UUID -> `KEEP`;
- any different non-empty current value -> `REVIEW`;
- malformed non-empty current value + proposed UUID -> `REVIEW`;
- non-decisive evidence -> preserve current value and plan no ID mutation.

Unavailable, no-match, or ambiguous evidence never clears or replaces a stored
ID.

### `acoustid_fingerprint`

An eligible fingerprint value comes from valid existing or generated Stage 02
material.

- empty current value + eligible generated/material value -> `PROPOSE`;
- same valid current value + same eligible material -> `KEEP`;
- any different non-empty current value -> `REVIEW`;
- malformed non-empty current value + eligible material -> `REVIEW`;
- no eligible material -> preserve current value and plan no mutation.

A generated valid fingerprint may be `PROPOSE` even when lookup is disabled or
unavailable.

No plan may clear a non-empty AcoustID field.

## Strict Conflict Semantics

Stage 04 has no partial application mode.

Any `REVIEW` or `BLOCKED` state in any selected target blocks the complete later
application unit before the first database mutation. A safe proposal in another
field or another target does not bypass a conflict.

This matches the frozen no-force/no-partial product contract.

## `AcoustIDTargetResult`

Stage 04A adds the frozen `AcoustIDTargetResult` concept. It contains:

- the selected fresh AcoustID target;
- the exact AcoustID planning snapshot;
- deterministic per-track fingerprint/evidence outcomes;
- the standalone AcoustID database target plan;
- generated-source snapshots required by later stale verification.

It contains no file-write plan and no MusicBrainz database plan.

Its representation must not expose:

- media paths;
- raw fingerprints;
- client credentials;
- raw provider/backend payloads or exceptions.

The result is complete enough for Stage 04B to validate and apply without
performing another fingerprint calculation or AcoustID lookup.

## Canonical Planning Requirement

The database plan must be reproducible from its immutable Stage 04A source
values. Application must reject tampered or internally inconsistent plans rather
than trusting arbitrary caller-created change tuples.

Stage 04A may expose a pure canonical mapping helper so Stage 04B can revalidate
that the supplied plan equals the plan implied by its retained source/result.

## Preview

Preview is a pure projection of `AcoustIDTargetResult`. Rendering must perform no
Library read, filesystem stat, backend execution, environment access, network
request, or mutation.

Per-track public vocabulary remains:

```text
Fingerprint  REUSED | GENERATED | MISSING | UNAVAILABLE
Lookup       DECISIVE | AMBIGUOUS | NO_MATCH | UNAVAILABLE
AcoustID     shortened identifier or none
Recording    canonical recording MBID or none
Database     KEEP | PROPOSE | REVIEW | BLOCKED
Reason       stable safe reason
```

When both database fields have states, the track-level displayed database state
uses deterministic severity:

```text
BLOCKED > REVIEW > PROPOSE > KEEP
```

Target/Album summaries may report safe counts only.

Preview never prints:

- a complete fingerprint;
- a private media path;
- the AcoustID client key;
- a raw backend command/output;
- a raw HTTP body or provider exception;
- unrelated database values.

A canonical recording MBID is safe to display for decisive evidence. The full
AcoustID UUID remains internally available; public rendering uses a stable
shortened form.

## 04A Product Allowlist

The external 04A implementation should normally be limited to narrow additive
files such as:

```text
beetsplug/noqlenmeta/acoustid/mapping.py
beetsplug/noqlenmeta/acoustid/workflow.py
beetsplug/noqlenmeta/acoustid/preview.py
beetsplug/noqlenmeta/acoustid/domain.py        # additive values/helpers only
beetsplug/noqlenmeta/acoustid/__init__.py      # additive exports only

tests/acoustid/test_mapping.py
tests/acoustid/test_workflow.py
tests/acoustid/test_preview.py
```

Exact filenames may be reduced when existing modules are a cleaner fit. A wider
production diff requires explicit review justification.

## 04A Acceptance Tests

Normal tests remain deterministic and offline. Cover at least:

- Album and singleton exact snapshot construction;
- deterministic membership/order preservation;
- exact raw malformed-value snapshot changes remaining detectable;
- reused fingerprint -> no generated fingerprint proposal;
- generated fingerprint + decisive lookup -> expected fingerprint/ID proposal;
- generated fingerprint + unavailable lookup -> fingerprint-only proposal;
- decisive ID equal to current -> `KEEP`;
- conflicting valid ID -> `REVIEW`;
- conflicting/malformed non-empty fingerprint -> `REVIEW`;
- no-match/ambiguous/unavailable lookup never clears existing values;
- no MusicBrainz field can enter any plan;
- target result and plan representations redact path/fingerprint material;
- renderer uses only frozen safe vocabulary;
- renderer cannot trigger Library/filesystem/backend/network work;
- Stage 04A performs zero database stores/mutations.

# Stage 04B — Verified Database Application

## 04B Boundary

Stage 04B receives already-prepared Stage 04A `AcoustIDTargetResult` values.
It must not:

- calculate fingerprints;
- repeat AcoustID lookup;
- reinterpret evidence scores;
- create new proposals;
- broaden field authority.

Its job is stale verification and database persistence only.

## Application Unit

The application entry point accepts the complete tuple/sequence of target
results selected for one future standalone invocation. This is the application
unit.

Before the first database mutation, Stage 04B must complete a global preflight
for every result in the unit.

The preflight validates:

1. every result and plan has the supported exact type;
2. every plan is canonical for its retained Stage 04A source/result;
3. no target contains `REVIEW` or `BLOCKED`;
4. target identities are not duplicated;
5. one Item database ID/local key cannot appear in more than one selected target;
6. every selected target can be refreshed through the existing Stage 02 refresh
   boundary;
7. refreshed target kind, Album/singleton membership, Item IDs, deterministic
   order, paths, lengths, and exact raw AcoustID fields match the Stage 04A
   snapshot;
8. every generated fingerprint source still matches its exact Stage 02
   `AcoustIDSourceSnapshot` using the existing verification helper;
9. every proposed/current relationship still matches the immutable plan.

If any check fails, the entire application unit is blocked before the first
store.

No backend, service, or credential access occurs during preflight.

## Stale-State Rules

The complete application unit is blocked before the first mutation when any
selected target has changed in:

- target kind;
- Album/singleton membership;
- Item membership or order;
- Item database identity;
- media path;
- length used by planned evidence;
- `acoustid_id` raw current value;
- `acoustid_fingerprint` raw current value;
- generated source-file device/inode/size/mtime snapshot.

Missing targets or unsupported source-snapshot semantics also fail closed.

Stable safe reasons remain `stale_target` and `stale_source_file` where a public
reason is needed. Raw changed values and paths are not included in errors.

## Mutation Authority

After global preflight succeeds, application may change only fields marked
`PROPOSE`:

```text
acoustid_id
acoustid_fingerprint
```

`KEEP` performs no database write for that field.

The implementation must use supported beets model/database persistence in a way
that stores only the explicitly planned fields. It must not rely on a broad
`store()` that can accidentally persist unrelated dirty model state.

Compatibility tests at the minimum supported beets boundary and latest `<3`
boundary must prove both AcoustID fields persist, reload, and query correctly.

Application must not modify:

- any `mb_*` field;
- title/artist/album/length/path/mtime or unrelated metadata;
- audio-file contents or tags.

No `Item.write()` or equivalent file-write path is permitted.

## Transaction And Verification Semantics

Reuse the established Noqlen library-identity philosophy instead of inventing a
weaker apply path:

- global stale preflight completes for the entire application unit before the
  first mutation;
- each selected target is then applied atomically inside a real beets/SQLite
  transaction or savepoint boundary;
- current rows are checked again inside the target transaction immediately
  before their updates;
- only planned fields are persisted;
- the target is re-read and verified before target commit/release;
- on an in-target failure, that target rolls back;
- after commit, fresh Item models are re-read and planned values are verified;
- normal `database_change` notification behavior is preserved only for
  successfully committed changed Items.

Stage 04 does **not** promise rollback of targets already committed if a later
unexpected target-level failure occurs. This matches the existing library
identity command model and avoids a long command-wide transaction. Any surfaced
error after earlier commits must explicitly mark commit state as such.

The important no-partial contract is about **known review/stale blockers**: all
of those must be discovered in global preflight and block before the first
write.

## Application Results And Errors

Use immutable sanitized result/error values sufficient to distinguish:

- confirmed no-op;
- applied database changes;
- blocked preflight;
- target rolled back before commit;
- committed change followed by post-commit verification/notification failure;
- later failure after earlier target commits.

Errors must not include media paths, fingerprints, raw database values, client
keys, backend output, HTTP bodies, or provider exceptions.

## 04B Product Allowlist

The external 04B implementation should normally be limited to:

```text
beetsplug/noqlenmeta/acoustid/application.py
beetsplug/noqlenmeta/acoustid/domain.py        # additive result/error values only
beetsplug/noqlenmeta/acoustid/__init__.py      # additive exports only

tests/acoustid/test_application.py
```

Narrow changes to Stage 04A mapping/workflow code are allowed only when review
finds a real canonical-plan defect; they must not broaden scope.

No command/parser/configuration/MusicBrainz integration file belongs in 04B.

## 04B Acceptance Tests

Cover at least:

- all results are preflighted before the first mutation;
- one stale later target causes zero writes across the complete application unit;
- changed membership/order/path/length/current ID/current fingerprint each block
  before the first write;
- malformed-current-value replacement between plan and apply is detected exactly;
- changed/missing generated source snapshot blocks before the first write;
- duplicate target/Item identities block before the first write;
- `REVIEW` anywhere blocks all otherwise safe proposals;
- all-`KEEP` application is a true no-op with no store;
- successful ID-only, fingerprint-only, and two-field application;
- only `acoustid_id` / `acoustid_fingerprint` are persisted;
- unrelated dirty Item state cannot leak into persistence;
- no MusicBrainz field changes;
- no audio-file write function is called;
- in-target failure rolls the target back;
- in-transaction verification catches a concurrent/current-row mismatch;
- post-commit fresh verification succeeds for valid application;
- post-commit failure reports committed state accurately;
- a later target failure reports earlier committed changes accurately;
- notifications happen only after successful commit and only for changed Items;
- normal tests require no real fpcalc binary, audio fixture, client key, or
  network access.

# Delivery Sequence

After this documentation brief is reviewed, CI-green, and squash-merged:

1. create external product branch `feature/029-acoustid-stage-04a`;
2. implement only Stage 04A Planning + Preview;
3. run focused/full offline tests, Ruff, hygiene, supported Python/beets CI, and
   external review;
4. squash-merge 04A only after PASS;
5. create external product branch `feature/029-acoustid-stage-04b` from the new
   `main`;
6. implement only Stage 04B Verified Database Application;
7. run the same repository gates and external review;
8. squash-merge 04B only after PASS;
9. create one Stage 04 completion record covering both accepted product PRs.

No public command integration begins between 04A and 04B.

# Reviewer Blockers

Request changes if 04A or 04B:

- writes any MusicBrainz field;
- writes an audio file;
- clears/replaces a conflicting non-empty AcoustID value automatically;
- introduces partial/force behavior;
- mutates the database from 04A;
- performs backend/network work from 04B;
- plans/applies a field beyond the two frozen AcoustID Item fields;
- exposes a fingerprint, path, key, raw response, or raw provider exception;
- skips exact malformed-value stale detection;
- writes before the complete application unit passes stale/source preflight;
- broad-stores unrelated dirty Item state;
- silently continues after a known `REVIEW`, `BLOCKED`, stale target, or stale
  generated source;
- reimplements Stage 01 evidence scoring, Stage 02 fingerprinting, or Stage 03
  transport;
- changes command/configuration/MusicBrainz/provider/importer/package/release
  surfaces;
- uses live network or a real fpcalc binary in normal CI.

# Completion Gate

Stage 04 is complete only after **both** 04A and 04B product PRs are independently
reviewed, CI-green, and squash-merged, followed by a documentation-only Stage 04
completion record.

The next implementation stage after Stage 04 remains the pure MusicBrainz
recording-compatibility filter. Public command/configuration integration remains
later.
