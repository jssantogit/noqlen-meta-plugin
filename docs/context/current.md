# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools for beets.

## Profile

`core-lib`

## Context Level

`full` for final Block 028 v1.0 hardening, documentation, and release preparation.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output.

## Active Block

Block 028 - v1.0 Hardening, Documentation Site, and Release Preparation (complete).

## Active Spec

`docs/specs/028-v1-hardening-docs-release/`

## Active ADRs

- `docs/adr/0020-musicbrainz-identity-audit-engine.md`
- `docs/adr/0021-importer-identity-preview-repair.md`
- `docs/adr/0022-library-identity-audit-repair.md`
- `docs/adr/0023-identity-tag-synchronization.md`
- `docs/adr/0024-v1-documentation-release.md`

## Completion State

Block 028 prepared the final v1.0.0 release candidate. The public manual lives under
`site-docs`, while internal ADR/spec/context material remains excluded from MkDocs. README is a short
GitHub/PyPI landing page. Package metadata, command help, documentation/default coverage checks,
synthetic release workflows, CI compatibility/docs/package jobs, and a tag-only trusted-publishing
workflow are complete. Python support is bounded to 3.10-3.14 in source and wheel metadata; v1.0.0
does not claim Python 3.15. Release tags must match the package version and resolve to commits
contained in remote `main` before build or OIDC publication. Authenticated checkout obtains complete
refs without persisting credentials; the workflow then validates local `origin/main` and ancestry
without a network Git operation, failing closed when the ref is absent. Validation passes 1,105 offline tests
with 5 live tests deselected, 165 focused
tests on both beets 2.12.0 and 2.13.1, focused Python 3.10-3.14 smoke tests, strict documentation,
Ruff, hygiene, package/Twine/content inspection, and clean-install discovery/help. No provider,
field, matcher, command, or write behavior was added.

## Stop Condition

Block 028 implementation is complete and the v1.0.0 release candidate is prepared. After reviewer
PASS and merge there is no next development block: STOP. Owner-controlled external release ceremony
remains.
