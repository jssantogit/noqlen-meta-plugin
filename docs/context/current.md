# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools for beets.

## Profile

`core-lib`

## Context Level

`full` for the accepted Block 029 AcoustID/Chromaprint contract freeze.

## Tool Mode

Documentation-only repository administration from the project chat. Work here
is limited to specs, ADRs, context, handoff, and documentation-only PRs. Product
code, tests, dependencies, package metadata, workflows, versions, tags, and
releases are outside this chat boundary.

## Active Block

Block 029 - AcoustID recording-level identity evidence.

The planning PR was approved, passed CI, and was squash-merged to `main` as
commit `6ad71d68347e23cecd45225900a10a8287acca54`.

No implementation stage is active in this chat.

## Active Spec

- `docs/specs/029-acoustid-identity-evidence/requirements.md`
- `docs/specs/029-acoustid-identity-evidence/design.md`
- `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- `docs/specs/029-acoustid-identity-evidence/contracts.md`
- `docs/specs/029-acoustid-identity-evidence/tasks.md`

`contracts.md` is normative when earlier provisional planning wording differs.

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
ordinary metadata provider. The first scope is existing-library Albums and
singletons.

The frozen standalone interface is:

```text
--acoustid
--fingerprint-missing
```

It composes with existing `--apply` and `--all`. Application is database-only
and may target only `acoustid_id` and `acoustid_fingerprint`.

The exact configuration subtree, validation bounds, environment variable,
domain vocabulary, evidence algorithm, preview states, and beets `chroma`
coexistence rules are frozen in `contracts.md`.

The service lookup uses bounded HTTPS POST and requests `meta=recordingids`.
AcoustID evidence uses provider score, competing recording support, and
canonical recording IDs only. Title, artist, duration, position, complete
assignment, structural score, and release margin remain exclusively within the
existing MusicBrainz audit.

Decisive evidence can reject incompatible complete MusicBrainz release
candidates after structural assignment. It adds no score and cannot write a
MusicBrainz ID directly.

## Next External Implementation Stage

Outside this chat, implementation may begin with immutable domain, evidence
policy, and configuration contracts only. The first implementation stage must
not include network transport, subprocess execution, database mutation,
MusicBrainz integration, packaging changes, or public release work.

## Stop Condition

This documentation branch stops after ADR acceptance, interface freeze, context
synchronization, green CI, and merge. Do not add product code or implementation
tests from this chat.
