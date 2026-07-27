# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 015 because it extends the audited persistent Album write boundary with one
explicit policy mode without redesigning providers, resolution, mapping, importer application, or
beets persistence.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 015 - Safe Partial Library Database Application.

## Active spec

`docs/specs/015-partial-library-application/`

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
- `docs/adr/0010-strict-library-database-application.md`
- `docs/adr/0011-partial-library-application-policy.md`

## Allowed files

The existing library application boundary, minimal CLI/renderer integration, focused tests, README,
ADR 0011, Block 015 specs, and context/handoff documents.

## Forbidden files

Direct Item orchestration, file-tag writes, media mapping, path/art/file changes, per-field exception
recovery, interactive review, command-wide rollback, provider/resolver redesign, network behavior
changes, additional providers, and beets core.

## Behavior budget

Existing importer behavior remains unchanged. CLI preview remains default and `--apply` remains
strict by default. Explicit `--apply --partial` may persist the atomically validated mapped subset
while reviews and mapping blockers remain withheld. File tags remain unchanged.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

One Subcommand owns `noqlenmeta` and `nm`; `--partial` requires `--apply`; strict remains default;
partial persists only mapped resolved changes as one validated subset; all Albums are planned before
application; forged, dirty, stale, malformed, and duplicate-target guards remain mandatory; normal
beets Album storage updates Album and inherited Item database rows; no physical tag operation occurs;
and baseline validation is green.

## Stop condition

Stop after Block 015. Do not add tag synchronization, direct Item orchestration, media mapping,
rollback infrastructure, providers, provenance persistence, lyrics, or artwork.
