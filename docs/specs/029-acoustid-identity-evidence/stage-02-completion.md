# Block 029 Stage 02 Completion Record

## Status

Complete and merged on 2026-08-09.

Stage 02 was implemented outside the project chat, reviewed against the frozen
contracts and the approved Stage 02 brief, validated by CI, and squash-merged
through PR #9.

```text
PR: https://github.com/jssantogit/noqlen-meta-plugin/pull/9
Reviewed head: 32cb2b2e275e9bf3a0b5e495d3e24ae8511344b0
Main commit: 5c7bd25f7ce1a4880b96f3dea25a2f7dd9d9d5bc
CI: run 53, rerun success
```

Earlier CI attempts were disrupted by a GitHub Actions service outage. The
accepted head was later rerun without code changes and all nine repository jobs
completed successfully. This record changes no product behavior.

## Delivered Scope

Stage 02 added the local existing-library and fingerprint-generation boundary:

- AcoustID-specific immutable Album and singleton targets converted from the
  established fresh identity-library selector;
- stable `library-item:<id>` keys and deterministic target/Item ordering;
- fresh validation of stored `acoustid_id` and `acoustid_fingerprint` values as
  `missing`, `valid`, or `malformed`;
- lazy reuse of valid stored fingerprint material only with finite positive
  duration;
- explicitly authorized generation of missing or unusable fingerprints;
- an injectable direct `fpcalc` backend with the frozen production argument
  vector;
- a no-shell, disconnected-stdin subprocess boundary with bounded timeout,
  stdout, stderr, termination, kill, reap, and reader cleanup;
- child-environment removal of `NOQLENMETA_ACOUSTID_API_KEY` without resolving
  or using the credential;
- no-follow regular-file source snapshots before and after generation;
- exact source-stability comparison and a later-use verification helper;
- deterministic offline tests requiring no network, audio fixture, or installed
  `fpcalc` binary.

The implementation lives in:

```text
beetsplug/noqlenmeta/acoustid/__init__.py
beetsplug/noqlenmeta/acoustid/domain.py
beetsplug/noqlenmeta/acoustid/library.py
beetsplug/noqlenmeta/acoustid/backend.py
```

The Stage 02 test expansion lives in:

```text
tests/acoustid/test_domain.py
tests/acoustid/test_library.py
tests/acoustid/test_backend.py
```

The established selector in `beetsplug/noqlenmeta/identity/library.py` was
reused without modification.

## Review Findings Resolved

The external implementation was amended until these additional safety
properties held:

1. Pipe readers require nonblocking descriptors and never fall back to blocking
   `stream.read()` behavior.
2. Reader-thread cleanup uses only bounded joins.
3. Process termination uses a bounded wait, then kill, then another bounded
   wait; no post-kill reap can block indefinitely.
4. A second `TimeoutExpired` after kill is converted to the generic internal
   process failure without exposing raw process information.
5. Descendants retaining pipe descriptors cannot keep the caller blocked past
   the bounded cleanup window.
6. Paths, executable names, environment-key values, fingerprints, stdout,
   stderr, and raw operating-system/process exceptions remain absent from public
   errors and representations.

## Completed Task Mapping

### Existing values and targets

Complete Album/singleton selection now preserves the established fresh-library
semantics, database-ID ordering, Item ordering, stable local keys, and membership
refresh checks. Existing AcoustID values are read only from fresh selected Items.
Selection itself performs no filesystem or backend work.

A stored AcoustID UUID remains current state only and is not treated as fresh
recording evidence. A reusable stored fingerprint requires a finite positive
Item duration.

### Fingerprint preparation and backend

Reusable material avoids backend creation, executable discovery, filesystem
stat, and subprocess work. Unauthorized missing or malformed material also
remains fully lazy.

Authorized generation invokes exactly:

```text
<configured fpcalc> -json -length 120 -- <private media path>
```

The runner enforces:

- `shell=False` and `DEVNULL` stdin;
- concurrent nonblocking stdout/stderr draining;
- 1 MiB retained stdout and 64 KiB retained stderr limits;
- validated timeout bounds;
- bounded terminate, kill, post-kill reap, and reader cleanup;
- zero exit status;
- strict bounded UTF-8 JSON parsing;
- generic sanitized failure states.

### Source stability

Generated fingerprint material exists only after equal no-follow regular-file
snapshots immediately before and after backend execution. Device, inode, size,
and nanosecond mtime are compared exactly. Symlinks, unsupported semantics,
missing files, malformed stat values, and changed sources fail closed.

## Validation Evidence

The final reviewed head passed CI run 53 after the GitHub Actions incident was
resolved. The successful matrix included:

- Python 3.10, 3.11, 3.12, 3.13, and 3.14;
- beets 2.12.0 minimum compatibility;
- latest beets below 3;
- Ruff and full offline tests;
- repository contamination checks;
- strict documentation validation/build;
- package build, metadata validation, archive inspection, and clean-install
  smoke testing.

The PR diff remained confined to the seven Stage 02 allowlisted product/test
files.

## Preserved Exclusions

Stage 02 introduced none of the following:

- AcoustID HTTPS lookup or service payload parsing;
- service API-key resolution or use;
- evidence lookup orchestration;
- database mapping or application;
- command parser/dispatch integration;
- public configuration integration;
- MusicBrainz candidate filtering;
- ordinary provider or importer integration;
- new dependencies or optional extras;
- package metadata, workflow, version, tag, release, README, changelog, or public
  site-documentation changes;
- audio-file writes.

## Next Stage Boundary

No new product implementation stage is active yet.

The next documentation stage should define Stage 03 for the bounded AcoustID
HTTPS transport and lookup-normalization boundary, including:

- service credential resolution only at the transport boundary;
- bounded HTTPS form-POST lookup requesting only `meta=recordingids`;
- sequential request pacing within the configured ceiling;
- bounded request/response handling and strict JSON/schema validation;
- process-local caching keyed without exposing raw fingerprint material;
- deterministic fake-clock/fake-transport offline tests;
- safe mapping of transport/service failures to existing evidence reasons.

Stage 03 must still exclude database application, command/public configuration
integration, MusicBrainz candidate filtering, provider/importer integration,
package release work, and audio-file writes unless its own reviewed brief
explicitly authorizes them.
