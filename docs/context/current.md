# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools for beets.

## Profile

`core-lib`

## Context Level

`full` for the accepted Block 029 contracts and the external Stage 01
implementation brief.

## Tool Mode

Documentation-only repository administration from the project chat. Work here
is limited to specs, ADRs, context, handoff, and documentation-only PRs. Product
code, tests, dependencies, package metadata, workflows, versions, tags, and
releases are outside this chat boundary.

## Active Block

Block 029 - AcoustID recording-level identity evidence.

The planning and contract-freeze PRs were approved, passed CI, and were
squash-merged to `main` as:

```text
6ad71d68347e23cecd45225900a10a8287acca54
9945ed9cd693abc04b250d10239151b3281a7762
```

No product implementation is performed from this chat.

## Active Spec

- `docs/specs/029-acoustid-identity-evidence/requirements.md`
- `docs/specs/029-acoustid-identity-evidence/design.md`
- `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- `docs/specs/029-acoustid-identity-evidence/contracts.md`
- `docs/specs/029-acoustid-identity-evidence/tasks.md`
- `docs/specs/029-acoustid-identity-evidence/stage-01-domain-policy-configuration.md`

`contracts.md` is normative when earlier provisional planning wording differs.
The Stage 01 brief is normative only for the scope and acceptance of the first
external implementation branch.

## Active ADRs

- Accepted: `docs/adr/0025-acoustid-recording-evidence.md`
- Existing identity foundation:
  - `docs/adr/0020-musicbrainz-identity-audit-engine.md`
  - `docs/adr/0021-importer-identity-preview-repair.md`
  - `docs/adr/0022-library-identity-audit-repair.md`
  - `docs/adr/0023-identity-tag-synchronization.md`

## Released Baseline

Version 1.0.0 was released on 2026-08-02. The tag, PyPI Trusted Publishing,
GitHub Release, matching artifact hashes, and Read the Docs `latest`, `stable`,
and `v1.0.0` builds remain complete.

Block 029 remains intended for the 1.1.0 release family, but no version bump has
been made.

## Frozen Decision

AcoustID is a separate recording-level identity-evidence subsystem, not an
ordinary metadata provider. The first product scope is existing-library Albums
and singletons.

The frozen standalone interface is:

```text
--acoustid
--fingerprint-missing
```

It composes with existing `--apply` and `--all`. Application is database-only
and may target only `acoustid_id` and `acoustid_fingerprint`.

The service lookup uses bounded HTTPS POST and requests `meta=recordingids`.
AcoustID evidence uses provider score, competing recording support, and
canonical recording IDs only. Title, artist, duration, position, complete
assignment, structural score, and release margin remain exclusively within the
existing MusicBrainz audit.

Decisive evidence can reject incompatible complete MusicBrainz release
candidates after structural assignment. It adds no score and cannot write a
MusicBrainz ID directly.

## Next External Implementation Stage

Stage 01 is defined in
`stage-01-domain-policy-configuration.md`. It is limited to:

1. immutable AcoustID domain values;
2. pure score/margin/ambiguity classification;
3. an internal frozen settings/default factory and validation;
4. redacted fingerprint-bearing representations;
5. stable machine reasons;
6. deterministic offline tests.

Stage 01 explicitly excludes network transport, subprocess execution,
filesystem access, beets database work, command integration, MusicBrainz
filtering, public configuration integration, package changes, and release work.

## Stop Condition

This documentation branch stops after the Stage 01 brief, context synchronization,
green CI, and squash merge. Do not add product code or implementation tests from
this chat.
