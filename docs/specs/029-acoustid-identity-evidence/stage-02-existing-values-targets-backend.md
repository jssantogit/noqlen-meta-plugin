# Block 029 Stage 02 Implementation Brief

## Status

Approved implementation brief after documentation review, green CI, and squash
merge.

This document authorizes product implementation only outside the project chat.
Repository work performed from the chat remains documentation-only.

Normative precedence is:

1. `contracts.md`;
2. ADR 0025;
3. this Stage 02 brief;
4. the earlier requirements and design documents.

When provisional design wording conflicts with the frozen contracts or this
narrower stage boundary, the frozen contracts and this brief win.

## Baseline

Stage 02 starts from the completed Stage 01 foundation merged as:

```text
26506a79f23a899a810640b1a2bfa8d80a5c4c20
```

The Stage 01 completion record is:

```text
docs/specs/029-acoustid-identity-evidence/stage-01-completion.md
```

Stage 02 must preserve all Stage 01 domain, privacy, normalization, settings,
and offline-test invariants.

## Objective

Implement the local existing-library and fingerprint-generation boundary for
AcoustID evidence:

- fresh complete Album and singleton target selection;
- stable database-ID local keys and deterministic Item order;
- validation of existing beets `acoustid_id` and `acoustid_fingerprint` values;
- lazy reuse of valid stored fingerprint material;
- explicitly authorized generation of missing or unusable fingerprint material;
- a direct, injectable, bounded `fpcalc` backend;
- no-follow source-file snapshot acquisition;
- pre/post-generation source stability checks;
- later stale-snapshot verification;
- generic, path-free, fingerprint-free outcomes and tests.

Stage 02 finishes before any AcoustID service request, database plan, database
mutation, command flag, public configuration, MusicBrainz candidate filtering,
package-extra change, or public documentation change.

## Reviewed Backend Decision

Stage 02 selects a direct `fpcalc` subprocess boundary rather than adding
`pyacoustid`.

Reasons:

- the frozen configuration already names the `fpcalc` executable;
- the official utility supports JSON output, an explicit processed-duration
  limit, and `--` before a file path;
- direct execution allows this project to enforce its own timeout, stdout,
  stderr, environment, process-termination, parsing, and privacy contracts;
- `pyacoustid` includes broader fingerprinting and HTTP behavior that is not
  needed in this stage;
- no new Python dependency is necessary;
- native beets `chroma` continues to own importer fingerprinting and autotagger
  integration.

The production argument vector is frozen for Stage 02 as:

```text
<configured fpcalc> -json -length 120 -- <private media path>
```

`120` is an internal backend safety constant and is not a public configuration
setting. The returned duration must be the finite positive duration reported by
`fpcalc`; the evidence classifier still does not use duration as a score.

Stage 02 must not import `acoustid`, `requests`, `audioread`, or a Chromaprint
Python binding.

## Stage Boundary

### In scope

- New AcoustID-specific immutable target and existing-value state values.
- Conversion from the established fresh identity-library target selector into
  AcoustID-specific targets.
- Existing beets field validation without treating a stored AcoustID UUID as
  fresh evidence.
- Lazy fingerprint preparation using existing material or an injected backend.
- A direct production `fpcalc` backend.
- A bounded, testable subprocess runner.
- No-follow regular-file snapshots before and after generation.
- Exact snapshot equality checks and later verification helpers.
- Synthetic, temporary-library, temporary-file, and fake-process tests.

### Out of scope

- AcoustID HTTPS lookup or response parsing.
- API-key resolution or any service credential object.
- `NOQLENMETA_ACOUSTID_API_KEY` use by product logic.
- Evidence lookup orchestration.
- `AcoustIDTargetResult` with service evidence or a database plan.
- Database field mapping, `KEEP`/`PROPOSE`/`REVIEW`/`BLOCKED`, or Item stores.
- Command parser options or command dispatch.
- Integration into `configuration.default_config()`.
- MusicBrainz identity compatibility filtering.
- Provider registration or ordinary `MetadataCandidate` output.
- Importer integration, listeners, or native `beet fingerprint` changes.
- Audio-file tag writes.
- Dependencies, optional extras, package metadata, workflows, versions, tags,
  releases, README, site documentation, or changelog changes.

## Existing Selection Boundary To Reuse

The repository already has a reviewed fresh-library boundary in:

```text
beetsplug/noqlenmeta/identity/library.py
```

Its selection behavior is the authoritative base for Stage 02:

- an Item query is evaluated through `Library.items()`;
- matched album Items expand to complete fresh Albums;
- matched standalone Items remain singletons;
- Albums are ordered by database Album ID;
- singletons are ordered by database Item ID;
- Album Items are ordered by positive disc, positive track, and Item ID;
- every retained Item is refreshed from the database;
- local keys use `library-item:<positive Item ID>`;
- duplicate query hits do not duplicate targets;
- refresh rejects changed Album/singleton membership.

Stage 02 must reuse this behavior through a narrow conversion or shared helper.
It must not duplicate the selection algorithm and must not modify the existing
identity-library module in this branch.

The AcoustID package may import the existing selector and convert its selected
values into AcoustID-specific immutable values. It may not expose identity audit
objects through its own public result models.

## Required New Domain Values

Exact names may receive narrow review adjustments, but the responsibilities and
invariants below are required.

### `AcoustIDLibraryTargetKind`

Serialized values:

```text
album
singleton
```

### `AcoustIDStoredValueState`

Serialized values:

```text
missing
valid
malformed
```

This state is used for the current database `acoustid_id` and fingerprint
fields. It does not represent lookup evidence.

### `AcoustIDExistingValues`

An immutable, redacted value containing at least:

- the current AcoustID-ID state;
- an optional canonical AcoustID UUID only when valid;
- the current fingerprint state;
- private valid fingerprint text only when reusable validation succeeds;
- finite positive existing duration when available;
- safe booleans/counts needed by later preview or mapping stages.

Required invariants:

- an empty or whitespace-only AcoustID ID is `missing`;
- a canonicalizable UUID is stored lowercase and hyphenated as `valid`;
- any other non-empty AcoustID ID is `malformed` and its raw value is not
  retained in a public representation;
- an empty or whitespace-only fingerprint is `missing`;
- a fingerprint is `valid` only when it is a string, contains no surrounding
  whitespace, is non-empty, and does not exceed the Stage 01 defensive maximum;
- any other non-empty fingerprint value is `malformed`;
- malformed raw values are never echoed in exceptions or representations;
- a stored AcoustID UUID is current state only and cannot produce a recording
  verdict;
- a stored fingerprint becomes reusable material only when the Item duration is
  finite and positive.

Do not normalize fingerprint text by stripping or rewriting it. A value with
surrounding whitespace is malformed rather than silently changed.

### `SelectedAcoustIDItem`

An immutable value containing at least:

- `local_key`;
- positive Item database ID;
- optional positive Album database ID;
- one fresh exact `beets.library.Item` retained privately;
- a private media path suitable for the backend boundary;
- validated `AcoustIDExistingValues`.

Privacy requirements:

- the Item object and media path are excluded from `repr`;
- no helper exception contains the media path;
- `str`, tuple representations, assertion-oriented production messages, and
  result objects remain path-free and fingerprint-free.

### `SelectedAcoustIDTarget`

An immutable value containing:

- target kind;
- optional Album database ID for an Album target;
- a non-empty tuple of `SelectedAcoustIDItem` values in deterministic order.

Required invariants:

- Album targets require one positive Album ID and all Items must belong to it;
- singleton targets contain exactly one Item with no Album membership;
- Item IDs and local keys are unique;
- order is retained from the established fresh-library selector;
- target values do not expose private paths or fingerprint text.

### `FingerprintBackendResult`

An immutable redacted value containing only:

- finite positive duration in seconds;
- private non-empty fingerprint text within the Stage 01 defensive limit.

It contains no local key, path, executable, command, stdout, stderr, or process
exception.

### `FingerprintPreparationResult`

An immutable result containing:

- path-free local key;
- optional `AcoustIDFingerprintMaterial`;
- one stable Stage 01 reason;
- safe state needed by later preview code.

Allowed successful reasons in this stage are:

```text
fingerprint_reused
fingerprint_generated
```

Allowed unavailable/blocking reasons are:

```text
fingerprint_missing
fingerprint_backend_unavailable
fingerprint_failed
stale_source_file
```

Required invariants:

- reused material has origin `existing` and no source snapshot;
- generated material has origin `generated` and an exact source snapshot;
- success requires material;
- failure/unavailable outcomes prohibit material;
- no lookup verdict or AcoustID result group is fabricated in Stage 02.

## Fresh Target Selection

Implement a pure-looking library adapter such as:

```python
select_acoustid_targets(library, query=None)
refresh_acoustid_target(library, selected)
```

The adapter may call the existing identity-library selector and refresh helper,
then convert their outputs.

Required behavior:

1. Require the exact supported `Library`, `Album`, and `Item` types used by the
   existing library boundary.
2. Preserve complete Album expansion and singleton selection.
3. Preserve Album-first then singleton ordering.
4. Preserve deterministic Item ordering.
5. Preserve `library-item:<id>` local keys.
6. Validate existing AcoustID fields only from fresh Item values.
7. Retain the media path privately without converting it to display text.
8. Refresh must reject missing targets and membership changes.
9. Refresh must not compare or mutate database fields.
10. Selection performs no filesystem stat and no backend work.

Stage 02 does not introduce `--all`; passing `query=None` merely retains the
existing selector behavior for a future command stage.

## Existing Fingerprint Reuse And Calculation Authority

Fingerprint preparation receives a selected Item, validated Stage 01 settings,
and one invocation-scoped boolean representing future
`--fingerprint-missing` authority.

Effective calculation authority is:

```text
settings.compute_missing OR invocation_allows_missing_calculation
```

The exact order is:

1. When `settings.reuse_existing` is true and a valid stored fingerprint plus a
   finite positive existing duration are available, return reused material.
2. In that case, do not instantiate a backend, resolve an executable, stat a
   file, or start a subprocess.
3. A valid stored `acoustid_id` is retained as current state only.
4. When no reusable material exists and calculation is not authorized, return
   `fingerprint_missing`.
5. When calculation is authorized, acquire a pre-execution no-follow snapshot.
6. Invoke the injected backend exactly once.
7. Acquire a post-execution no-follow snapshot.
8. Require the pre and post snapshots to be exactly equal.
9. Only then create generated `AcoustIDFingerprintMaterial`.

A malformed stored fingerprint may be replaced by generated material in memory
when calculation is authorized. Stage 02 does not decide whether that current
non-empty database value can later be overwritten; the mapping stage will treat
such conflicts conservatively.

The backend must be supplied lazily, for example through a factory, so tests can
prove that reuse and unauthorized-missing paths do not discover or instantiate
it.

## Source-File Snapshot Contract

Use the Stage 01 `AcoustIDSourceSnapshot` fields:

```text
device
inode
size
mtime_ns
```

The production snapshot function must:

- use no-follow stat semantics;
- reject symbolic links;
- require a regular file;
- reject unsupported or malformed stat values;
- return only the four immutable snapshot fields;
- never place a path in the snapshot or an exception;
- fail closed when the platform cannot provide the required semantics.

Generation requires equal snapshots immediately before and after backend
execution. A mismatch returns `stale_source_file` and discards the generated
fingerprint.

Provide a separate verification helper that re-acquires the no-follow snapshot
and compares it with a retained generated snapshot. Stage 02 tests this helper,
but no database application calls it yet.

The comparison is exact. No timestamp tolerance, inode fallback, path fallback,
or content hash is introduced in this stage.

## Fingerprint Backend Protocol

Define an injectable protocol similar to:

```python
class FingerprintBackend(Protocol):
    def fingerprint(self, path: bytes | str) -> FingerprintBackendResult: ...
```

The production backend is initialized from the validated `fpcalc` and
`timeout_seconds` settings. Construction must not discover or execute the
backend.

Expected failures are converted to internal sanitized backend exceptions or
safe preparation reasons. They must not retain provider command text, paths,
stdout, stderr, raw fingerprint text, or operating-system exception text.

## Bounded Subprocess Runner

The direct runner is injectable and independently tested.

Requirements:

- one argument vector and `shell=False`;
- stdin disconnected or set to `DEVNULL`;
- stdout and stderr drained concurrently;
- hard stdout storage limit of 1 MiB;
- hard stderr storage limit of 64 KiB;
- timeout from validated `timeout_seconds`;
- process termination on timeout or output overflow;
- bounded grace followed by kill when termination does not finish;
- no command, path, stdout, stderr, or raw exception in public errors;
- no automatic retry;
- non-zero exit status is failure;
- the configured executable is used only when fingerprint generation is
  authorized and required.

The child environment must not contain `NOQLENMETA_ACOUSTID_API_KEY`. The
implementation must remove that exact variable before launch without logging or
persisting its value. Stage 02 does not otherwise resolve or use the credential.

Tests may exercise the generic bounded runner with `sys.executable`; production
`fpcalc` tests use an injected fake runner and do not require Chromaprint in CI.

## `fpcalc` Parsing Contract

The production backend invokes:

```text
<fpcalc> -json -length 120 -- <path>
```

Parsing requirements:

- stdout must be valid UTF-8 JSON after the byte bound is enforced;
- the top-level value must be an object;
- `duration` is required and must be a finite positive number;
- `fingerprint` is required and must be a non-empty string within the Stage 01
  defensive maximum;
- booleans are invalid numeric duration values;
- unknown bounded JSON keys may be ignored and must not be retained;
- trailing non-whitespace bytes are invalid;
- stderr is never parsed as a fallback;
- text/key-value output is not accepted in the production path;
- no raw output enters an exception, representation, or log.

Executable missing maps to `fingerprint_backend_unavailable`. Timeout,
termination, output overflow, non-zero exit, invalid UTF-8, malformed JSON,
missing fields, and invalid field values map to `fingerprint_failed`.

## Required Test Matrix

### Library selection tests

- Item query expands a matched Album Item to the complete fresh Album;
- a matched singleton remains one singleton;
- mixed matches produce Albums first and singletons second;
- duplicate query matches do not duplicate targets;
- Album order is database-ID order;
- singleton order is database-ID order;
- Item order is disc, track, Item ID with missing positions last;
- local keys are stable database-ID keys;
- fresh Item instances are retained;
- unsupported library/query return types fail generically;
- missing Album/Item and changed membership fail generically;
- selection performs no stat and no backend work;
- target and Item representations contain no path or fingerprint.

### Existing-value tests

- empty ID and fingerprint states;
- valid uppercase AcoustID UUID canonicalization;
- malformed non-empty AcoustID UUID state without raw-value disclosure;
- valid existing fingerprint and positive finite duration;
- blank, whitespace-padded, non-string, and oversized fingerprint states;
- invalid Item duration prevents reuse;
- stored AcoustID ID alone never produces evidence or fingerprint material;
- raw fingerprint does not appear in repr, exceptions, or assertion-oriented
  production messages.

### Lazy preparation tests

- valid reusable material avoids backend factory creation;
- `reuse_existing=false` bypasses stored material;
- unauthorized missing material avoids stat and backend creation;
- settings authority permits generation;
- invocation authority permits generation;
- backend is invoked exactly once per generated Item;
- malformed stored fingerprint may generate only with authority;
- generated material retains the post-generation snapshot;
- backend unavailable, backend failure, and stale file produce exact safe
  reasons;
- no outcome contains a path, command, fingerprint, stdout, or stderr.

### Snapshot tests

- regular-file snapshot succeeds;
- symlink is rejected;
- directory and non-regular files are rejected;
- before/after equality succeeds;
- device, inode, size, or mtime change fails;
- later verification succeeds for unchanged source;
- later verification rejects changed or missing source;
- snapshot exceptions are generic and path-free;
- unsupported no-follow semantics fail closed.

### Runner and backend tests

- exact production argument vector including `-json`, `-length`, `120`, and
  `--`;
- no shell and disconnected stdin;
- exact timeout forwarding;
- successful bounded JSON parsing;
- duration and fingerprint boundaries;
- boolean, NaN, infinity, zero, negative, blank, and oversized outputs rejected;
- invalid UTF-8 and malformed JSON rejected;
- missing required fields rejected;
- non-zero exit rejected;
- missing executable maps to backend unavailable;
- timeout maps to failure and terminates the child;
- stdout overflow terminates the child;
- stderr overflow terminates the child;
- child environment excludes `NOQLENMETA_ACOUSTID_API_KEY`;
- environment key value, path, executable, output, and fingerprint are absent
  from errors and representations;
- no actual `fpcalc` binary, audio fixture, or network is required by normal CI.

### Compatibility tests

- full supported Python matrix remains green;
- minimum and latest supported beets environments exercise fresh Album and
  singleton selection;
- existing identity-library tests remain unchanged and green;
- Stage 01 tests remain unchanged and green.

## Expected Product Layout

Expected changes are limited to:

```text
beetsplug/noqlenmeta/acoustid/__init__.py
beetsplug/noqlenmeta/acoustid/domain.py
beetsplug/noqlenmeta/acoustid/library.py
beetsplug/noqlenmeta/acoustid/backend.py
tests/acoustid/test_domain.py
tests/acoustid/test_library.py
tests/acoustid/test_backend.py
```

`tests/acoustid/__init__.py` remains unchanged. A small
`tests/acoustid/conftest.py` is allowed only when it contains shared synthetic
fixtures for these tests and no product behavior.

No change to `beetsplug/noqlenmeta/identity/library.py` is authorized. If
conversion cannot reuse the existing selector without changing it, stop and
request a documentation amendment rather than refactoring it inside Stage 02.

## Acceptance Commands

The external report must include exact results from:

```bash
python -m pytest \
  tests/acoustid/test_domain.py \
  tests/acoustid/test_library.py \
  tests/acoustid/test_backend.py \
  tests/acoustid/test_evidence.py \
  tests/acoustid/test_settings.py
python -m ruff check beetsplug/noqlenmeta/acoustid tests/acoustid
python -m pytest
python scripts/check_repo_contamination.py
git diff --check
git diff --name-only main...HEAD
git diff --stat main...HEAD
```

Normal tests must remain deterministic and offline.

## Reviewer Checklist

The reviewer must confirm:

- [ ] the diff remains inside the Stage 02 allowlist;
- [ ] the existing identity-library selector is reused without modification;
- [ ] selected Item objects are fresh and targets are complete;
- [ ] local keys and order match the established library boundary;
- [ ] stored AcoustID IDs remain current state rather than evidence;
- [ ] reusable fingerprints avoid all stat, discovery, and subprocess work;
- [ ] unauthorized missing fingerprints avoid all local file work;
- [ ] direct `fpcalc` execution is lazy, injected, no-shell, timed, and
  output-bounded;
- [ ] the child does not receive the AcoustID API-key environment variable;
- [ ] JSON, duration, and fingerprint parsing is strict and bounded;
- [ ] pre/post no-follow snapshots are equal before generated material exists;
- [ ] symlinks and unsupported snapshot semantics fail closed;
- [ ] all public representations and errors remain path-free and
  fingerprint-free;
- [ ] no network, service payload, database plan, store, command, provider,
  MusicBrainz, dependency, package, public-doc, version, or release work entered
  the stage;
- [ ] focused tests, Ruff, full tests, contamination check, and diff check pass;
- [ ] CI is green before squash merge.

## Completion And Handoff

Stage 02 is complete only after:

1. external implementation against this exact boundary;
2. reviewer PASS;
3. green CI;
4. squash merge;
5. a separate documentation-only completion record.

The next stage may define bounded HTTPS lookup, credential resolution at the
service boundary, payload normalization, and composition with the existing pure
evidence classifier.

The next stage must still exclude command integration, database application,
MusicBrainz filtering, public configuration integration, package release work,
and file writes unless its own reviewed brief explicitly authorizes them.
