# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 010 because it introduces a target-representation safety boundary after
`ChangePlan` and integrates that boundary into the beets import preview.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 010 - Read-Only Beets Target Mapping.

## Active spec

`docs/specs/010-beets-target-mapping/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`
- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0005-change-plan-boundary.md`
- `docs/adr/0006-beets-target-mapping.md`

## Allowed files

One dependency-light beets mapping module, minimal plugin/integration changes, focused tests, README,
ADR 0006, Block 010 specs, and context/handoff documents.

## Forbidden files

Candidate application, beets/file/database mutation, lossy serialization policy, CLI, semantic field
merging, persistence, provider/resolver redesign, network behavior changes, additional providers,
configuration changes, and beets core.

## Behavior budget

Existing provider orchestration, one resolver pass, and ChangePlan translation remain unchanged.
Planned changes are mapped deterministically only when they fit current `AlbumInfo` targets without
information loss, then rendered in a read-only target preview.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

Lossless mappings and target blockers are explicit, malformed shapes fail visibly, provenance and
structured genres remain intact, the real preview consumes `BeetsTargetPlan`, import state remains
unchanged, and baseline validation is green.

## Stop condition

Stop after Block 010. Do not define application policy, mutate `AlbumInfo`, or add metadata writes,
providers, mapping configuration, CLI, lyrics, or artwork.
