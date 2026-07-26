# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 011 because it introduces the first selected-release mutation boundary after
the existing target plan without redesigning providers, resolution, planning, or mapping.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 011 - Strict Opt-In Selected-Release Application.

## Active spec

`docs/specs/011-strict-application/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`
- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0005-change-plan-boundary.md`
- `docs/adr/0006-beets-target-mapping.md`
- `docs/adr/0007-strict-selected-release-application.md`

## Allowed files

One small beets application module, minimal plugin/integration changes, focused tests, README, ADR
0007, Block 011 specs, and context/handoff documents.

## Forbidden files

Partial application, direct Item/Album mutation, downstream beets application calls, database/tag/file
writes, lossy serialization, CLI, persistence, provider/resolver redesign, network behavior changes,
additional providers, and beets core.

## Behavior budget

Existing provider orchestration, resolution, ChangePlan translation, and target mapping remain
unchanged. Explicit `apply: true` may mutate only a fully lossless, review-free selected `AlbumInfo`;
all downstream importer behavior remains owned by beets.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

Application defaults off, preview/apply remain independent, all safety checks precede mutation,
reviews or blockers cause zero mutation, caches are invalidated, later beets application consumes the
selected enrichment, and baseline validation is green.

## Stop condition

Stop after Block 011. Do not add partial application, direct downstream writes, providers, mapping
configuration, CLI, lyrics, artwork, or Block 012 behavior.
