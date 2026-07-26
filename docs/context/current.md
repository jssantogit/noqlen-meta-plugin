# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 014 because it adds one conservative persistent Album write boundary without
redesigning providers, resolution, ChangePlan, importer application, or beets persistence.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 014 - Strict Library Database Application.

## Active spec

`docs/specs/014-library-db-application/`

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

## Allowed files

One library application module, minimal CLI/renderer integration, focused tests, README, ADR 0010,
Block 014 specs, and context/handoff documents.

## Forbidden files

CLI partial policy, direct Item orchestration, file-tag writes, media mapping, path/art/file changes,
interactive review, command-wide rollback, provider/resolver redesign, network behavior changes,
additional providers, and beets core.

## Behavior budget

Existing importer behavior remains unchanged. CLI preview remains default. Explicit `--apply`
strictly persists only review-free, blocker-free mapped Album changes through normal beets database
storage. File tags remain unchanged.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

One Subcommand owns `noqlenmeta` and `nm`; `--apply` is the only CLI write permission; all Albums are
planned before strict per-Album application; guards prevent forged, dirty, stale, malformed, or
duplicate-target writes; stale checks use a fresh persisted Album snapshot; normal beets Album
storage updates Album and inherited Item database rows; no physical tag operation occurs; and
baseline validation is green.

## Stop condition

Stop after Block 014. Do not add partial CLI application, tag synchronization, direct Item
orchestration, media mapping, rollback infrastructure, providers, provenance persistence, lyrics, or
artwork.
