# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 018 because one provider is added through existing provider capability,
orchestration, resolution, mapping, and application boundaries.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 018 - Conservative Last.fm Genre Enrichment.

## Active spec

`docs/specs/018-lastfm-genres/`

## Active ADRs

- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0013-configurable-resolution-policy.md`
- `docs/adr/0014-lastfm-community-genre-enrichment.md`

## Allowed files

Last.fm provider/spec/config/orchestration wiring, focused provider/resolver/importer/CLI tests,
sanitized fixtures, README, ADR 0014, Block 018 specs, and context/handoff documents.

## Forbidden files

Resolver redesign, style/mood inference, mappings, application or persistence changes, search/fuzzy
matching, credentials, dependencies, persistent cache, concurrency, CLI flags, and physical files.

## Behavior budget

Last.fm may contribute one genres candidate from selected-album top tags only after strict identity,
weight, and packaged-vocabulary filtering. Existing authority and write semantics remain unchanged.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

The genres-only provider is bounded, paced, cached, identity-validated, secret-safe, capability-gated,
fixture-tested, documented, and all offline validation passes.

## Stop condition

Stop after Block 018. Do not add Last.fm styles/mood classification or another provider.
