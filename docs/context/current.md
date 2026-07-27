# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 021 because it adds a read-only importer execution and preview boundary around
selected tracks while reusing existing provider, resolver, and `ChangePlan` contracts.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output.

## Active block

Block 021 - Importer Track Planning Preview.

## Active spec

`docs/specs/021-importer-track-planning-preview/`

## Active ADRs

- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0013-configurable-resolution-policy.md`
- `docs/adr/0014-lastfm-community-genre-enrichment.md`
- `docs/adr/0015-track-enrichment-boundary.md`
- `docs/adr/0016-lrclib-track-lyrics-provider.md`
- `docs/adr/0017-importer-track-planning-preview.md`

## Allowed files

Track integration/planning/preview and importer entry-point code, focused tests, `README.md`, ADR
0017, Block 021 requirements/design/tasks/review, and the current context/handoff documents.

## Forbidden files

Track target mapping, TrackInfo/Item mutation, application, database persistence, tag/file writes,
library track CLI modes, LRCLIB transport changes, search or rematching, and deciding
`synced_lyrics` target semantics.

## Behavior budget

Eligible LRCLIB candidates may be planned and safely summarized for selected importer tracks when
preview is enabled. Existing release behavior and album-only library CLI behavior remain unchanged;
track planning has no write authority even when importer release application is enabled.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

Album/singleton selected-track planning, beets `from_scratch` parity, safe summaries, provider failure
isolation, coexistence, and the no-write boundary are tested and documented; final validation passes.

## Completion state

Implementation, documentation, and final offline validation are complete. The focused Block 021
suite passes 161 tests; the full suite passes 723 tests with 5 opt-in live tests skipped. Lint,
repository contamination, and diff-whitespace checks pass.

## Stop condition

Stop after Block 021 preview planning. Do not add track target mapping, application, persistence, file
writes, library track modes, or decide future `synced_lyrics` target semantics.
