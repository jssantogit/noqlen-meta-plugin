# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 020 because it adds one track provider and narrow external-service boundary while
leaving resolver, mapping, application, and user-facing execution behavior unchanged.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 020 - LRCLIB Track Lyrics Provider.

## Active spec

`docs/specs/020-lrclib-track-lyrics/`

## Active ADRs

- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0013-configurable-resolution-policy.md`
- `docs/adr/0014-lastfm-community-genre-enrichment.md`
- `docs/adr/0015-track-enrichment-boundary.md`
- `docs/adr/0016-lrclib-track-lyrics-provider.md`

## Allowed files

LRCLIB provider/transport, provider spec and disabled configuration, focused tests and synthetic
fixtures, README, ADR 0016, Block 020 specs, and context/handoff documents.

## Forbidden files

LRCLIB search or fuzzy matching, resolver/planner duplication, target mapping, track execution,
application or persistence, fingerprints, persistent cache, concurrency, CLI flags, and file writes.

## Behavior budget

Exact selected-track lyrics may become canonical candidates. Existing release provider results,
album CLI/importer behavior, authority defaults, mapping, application, persistence, and file semantics
remain unchanged.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

LRCLIB exact lookup, validation, safety, cache, pacing, and shared planning are tested and documented;
release execution remains isolated and all offline validation passes.

## Stop condition

Stop after Block 020. Do not add track execution, current-state precedence, mapping, or application.
