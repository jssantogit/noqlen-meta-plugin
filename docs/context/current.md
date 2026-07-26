# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 012 because it adds an explicit application policy after the existing target
plan without redesigning providers, resolution, planning, mapping, or the beets lifecycle.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 012 - Explicit Safe Partial Application Policy.

## Active spec

`docs/specs/012-partial-application-policy/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`
- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0005-change-plan-boundary.md`
- `docs/adr/0006-beets-target-mapping.md`
- `docs/adr/0007-strict-selected-release-application.md`
- `docs/adr/0008-partial-application-policy.md`

## Allowed files

The existing beets application module, minimal plugin/integration changes, focused tests, README,
ADR 0008, Block 012 specs, and context/handoff documents.

## Forbidden files

Review acceptance, lossy mapping, per-field error recovery, direct Item/Album mutation, downstream
beets application calls, database/tag/file writes, CLI, persistence, provider/resolver redesign,
network behavior changes, additional providers, and beets core.

## Behavior budget

Existing provider orchestration, resolution, ChangePlan translation, target mapping, and lifecycle
remain unchanged. Strict application stays default. Explicit partial mode may atomically mutate only
the mapped subset on selected `AlbumInfo`; reviews and mapping blockers remain withheld.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

Application defaults off and strict, invalid enabled modes fail before provider work, strict behavior
is unchanged, partial mode applies only an atomically prevalidated mapped subset, withheld fields
remain visible, caches are invalidated, and baseline validation is green.

## Stop condition

Stop after Block 012. Do not add CLI behavior, direct downstream writes, providers, mapping
configuration, provenance persistence, lyrics, artwork, or Block 013 behavior.
