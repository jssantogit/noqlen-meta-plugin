# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 013 because it adds a read-only library entry point and target adapter without
redesigning providers, resolution, ChangePlan, importer application, or the beets lifecycle.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 013 - Library CLI Preview Boundary.

## Active spec

`docs/specs/013-library-cli-preview/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`
- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0005-change-plan-boundary.md`
- `docs/adr/0006-beets-target-mapping.md`
- `docs/adr/0007-strict-selected-release-application.md`
- `docs/adr/0008-partial-application-policy.md`
- `docs/adr/0009-library-cli-preview-boundary.md`

## Allowed files

Minimal plugin/integration changes, explicit library adapters and mapping, focused tests, README,
ADR 0009, Block 013 specs, and context/handoff documents.

## Forbidden files

`--apply`, lossy mapping, direct Item/Album mutation, database/tag/file writes, singleton or track
mode, interactive review, persistence, provider/resolver redesign, network behavior changes,
additional providers, and beets core.

## Behavior budget

Existing importer behavior remains unchanged. CLI and importer share provider/resolver/ChangePlan
planning, then diverge into their explicit target adapters. The library command always previews and
never mutates persistent Albums, Items, tags, files, or importer objects.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

One Subcommand owns `noqlenmeta` and `nm`, query intent is explicit, native Album queries and
read-only adapters feed the shared planning path, persistent target reality and blockers are visible,
importer configuration grants no CLI writes, and baseline validation is green.

## Stop condition

Stop after Block 013. Do not add CLI application, direct downstream writes, singleton/track mode,
providers, mapping configuration, provenance persistence, lyrics, artwork, or Block 014 behavior.
