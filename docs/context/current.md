# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 009 because it introduces a safety boundary between resolution and any future
metadata application while integrating that boundary into the beets import lifecycle.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 009 - Read-Only ChangePlan.

## Active spec

`docs/specs/009-change-plan/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`
- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0005-change-plan-boundary.md`

## Allowed files

One dependency-light ChangePlan module, minimal plugin/integration changes, focused tests, README,
ADR 0005, Block 009 specs, and context/handoff documents.

## Forbidden files

Candidate application, beets/file/database mutation, target-field mapping, serialization policy, CLI,
semantic field merging, persistence, provider/resolver redesign, network behavior changes, additional
providers, configuration changes, and beets core.

## Behavior budget

Existing provider orchestration and one resolver pass remain unchanged. Resolved decisions are
translated into a deterministic immutable ChangePlan and rendered as a read-only plan preview.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

PROPOSE/REVIEW/KEEP/SKIP translate correctly, provenance and structured values remain intact,
inconsistent decisions fail visibly, the real preview consumes the plan, import state remains
unchanged, and baseline validation is green.

## Stop condition

Stop after Block 009. Do not define beets application mapping, apply decisions, or add metadata
writes, providers, configuration, CLI, lyrics, or artwork.
