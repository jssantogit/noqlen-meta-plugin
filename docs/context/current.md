# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools for beets.

## Profile

`core-lib`

## Context Level

`full` for post-v1.0.0 release synchronization and the start of update planning.

## Tool Mode

Direct repository administration for release-state documentation and validation
contracts. No product behavior, package metadata, workflow, or published tag is
changed in this branch.

## Active Block

No active development block. Block 028 is complete, and version 1.0.0 has been
published. This post-release synchronization does not reopen the frozen v1
release scope.

## Active Spec

None. The completed Block 028 spec remains at
`docs/specs/028-v1-hardening-docs-release/` for historical context.

## Active ADRs

- `docs/adr/0020-musicbrainz-identity-audit-engine.md`
- `docs/adr/0021-importer-identity-preview-repair.md`
- `docs/adr/0022-library-identity-audit-repair.md`
- `docs/adr/0023-identity-tag-synchronization.md`
- `docs/adr/0024-v1-documentation-release.md`

## Completion State

Version 1.0.0 was released on 2026-08-02. The `v1.0.0` tag, GitHub Release,
PyPI Trusted Publishing workflow, PyPI project ownership, published wheel and
sdist, matching artifact hashes, and Read the Docs `latest`, `stable`, and
`v1.0.0` builds are complete. Final release CI passed across Python 3.10-3.14,
the supported beets boundaries, documentation, and package validation.

The public-package clean-install discovery check and public `beet nm --help`
check remain explicit in `RELEASE_CHECKLIST.md` until run. They do not make the
published release incomplete.

## Next Planned Work

Plan the first post-v1 update around AcoustID/Chromaprint identity evidence.
Begin with a parity audit against Noqlen Forge Core and the existing beets
integration surface, then define safety boundaries, configuration, target
mapping, dependency strategy, tests, and documentation before implementation.
No AcoustID product scope is frozen yet.

## Stop Condition

This branch records the completed release state only. Do not add AcoustID code,
bump the package version, alter release workflows, or create a new tag here.
