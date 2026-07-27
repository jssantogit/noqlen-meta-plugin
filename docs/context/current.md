# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 022 because it adds a pure target-representation boundary after the existing
canonical selected-track `ChangePlan` while retaining the read-only importer boundary.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output.

## Active block

Block 022 - Lossless Track Target Mapping.

## Active spec

`docs/specs/022-track-target-mapping/`

## Active ADRs

- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0013-configurable-resolution-policy.md`
- `docs/adr/0014-lastfm-community-genre-enrichment.md`
- `docs/adr/0015-track-enrichment-boundary.md`
- `docs/adr/0016-lrclib-track-lyrics-provider.md`
- `docs/adr/0017-importer-track-planning-preview.md`
- `docs/adr/0018-track-target-mapping.md`

## Allowed files

Track mapping/planning/preview code, focused tests, `README.md`, ADR 0018, Block 022
requirements/design/tasks/review, and the current context/handoff documents.

## Forbidden files

TrackInfo/Item mutation, track application modes or policy, database persistence, tag/file writes,
native SYLT application, library track CLI modes, LRCLIB transport changes, search or rematching,
and MusicBrainz identity repair.

## Behavior budget

Already-proposed canonical track changes may be analyzed against an explicit `TrackInfo` target map.
Plain lyrics map losslessly; synchronized lyrics and unknown fields block visibly. Existing release
and album-only CLI behavior remain unchanged, and track mapping grants no write authority.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

Immutable lossless track mapping, synchronized blockers, safe target-aware preview, beets contract
evidence, coexistence, and the no-write boundary are tested and documented; final validation passes.

## Completion state

Implementation, documentation, and final offline validation are complete. Focused validation passes
85 tests; the full suite passes 766 tests with 5 opt-in live tests skipped. Lint, repository
contamination, and diff-whitespace checks pass.

## Stop condition

Stop after Block 022 target mapping. Do not add track application, persistence, file writes, native
SYLT support, library track modes, or identity repair.
