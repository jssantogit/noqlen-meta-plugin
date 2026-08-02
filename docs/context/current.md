# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools for beets.

## Profile

`core-lib`

## Context Level

`full` for the final pre-tag external-gate synchronization.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output. This records owner-confirmed external setup; publication remains out of scope.

## Active Block

No development block. Block 028 is complete and merged; this is a small
administrative owner-gate change, not Block 029.

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

Block 028 is complete and merged. The owner confirms that the repository is
public, the MIT License is merged, private vulnerability reporting is enabled,
the GitHub `pypi` environment has a `v*` deployment tag rule, the PyPI Pending
Trusted Publisher is configured, and the Read the Docs public `latest` build
passed.

Remaining work is to merge this administrative sync, confirm final `main` CI,
create `v1.0.0`, verify the release workflow and PyPI publication, create or
verify the GitHub Release when appropriate, and complete post-release checks.
PyPI project ownership will be established by the first publication. No
development scope is reopened.

## Stop Condition

There is no next development block. Do not create Block 029, tag, publish,
merge, or run the release workflow during this administrative sync.
