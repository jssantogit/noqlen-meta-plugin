# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools for beets.

## Profile

`core-lib`

## Context Level

`full` for the final pre-tag v1.0.0 release-state synchronization.

## Tool Mode

Direct repository administration for documentation-only release-state updates.
No product behavior, package metadata, workflow, tag, or publication is changed.

## Active Block

No development block. Block 028 is complete and merged; this is a final
pre-tag administrative state update, not Block 029.

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

Block 028 and the atime-sensitive test hotfix are complete and merged. Final
`main` CI is green across Python 3.10-3.14, the supported beets boundaries,
documentation, and package validation. The production stale-source guard remains
unchanged. All owner-confirmed external setup gates required before tagging are
complete.

Remaining work is to merge this documentation-only release-state update, wait
for its resulting `main` CI to pass, create `v1.0.0`, verify the release workflow
and first PyPI publication, create or verify the GitHub Release and versioned
Read the Docs build, and complete post-release checks. PyPI project ownership
will be established by the first publication. No development scope is reopened.

## Stop Condition

There is no next development block. Do not create Block 029, tag, publish, or
run the release workflow during this pre-tag state update.
