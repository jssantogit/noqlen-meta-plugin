# Current Context

## Project

Noqlen Meta - multi-provider metadata enrichment and MusicBrainz identity tools for beets.

## Profile

`core-lib`

## Context Level

`full` for the post-Block-028 license and public-release owner gates.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output. External release setup and publication remain out of scope.

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

Block 028 received reviewer PASS and was merged to `main`. The owner selected
MIT, and the canonical `LICENSE` plus PEP 639 package metadata are prepared.
The owner also selected public repository visibility, but that external change
is not complete until GitHub reports the repository as public.

Still pending are making the repository public, enabling private vulnerability
reporting, configuring the GitHub `pypi` environment and PyPI trusted
publisher, importing and building Read the Docs, creating the `v1.0.0` tag,
and verifying publication. No tag, upload, visibility change, external setup,
provider, field, matcher, command, or write behavior is part of this change.

## Stop Condition

There is no next development block. After the owner-gate branch is reviewed,
the remaining actions are the external owner release ceremony. Do not create
Block 029, tag, publish, or claim public visibility before external confirmation.
