# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 016 because it adds one anchored provider through existing context,
orchestration, resolver, planning, mapping, and application boundaries without changing writes.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 016 - Anchored MusicBrainz Release Enrichment.

## Active spec

`docs/specs/016-musicbrainz-enrichment/`

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
- `docs/adr/0012-anchored-musicbrainz-enrichment.md`

## Allowed files

MusicBrainz provider/spec, shared release-ID context adapters, provider orchestration/configuration,
focused tests and fixture, README, ADR 0012, Block 016 specs, and context/handoff documents.

## Forbidden files

MusicBrainz search or matching, release-group/recording/credit/tag/art/lyrics work, authority redesign,
application or persistence semantics, media-to-Item mapping, CLI flags, caching/concurrency, beets core,
and physical file operations.

## Behavior budget

An enabled MusicBrainz provider may enrich only an exact validated release MBID already known by
beets. Existing Field Authority decides winners. Mapping, strict/partial application, database writes,
and file behavior remain unchanged.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

MusicBrainz is a disabled built-in provider; exact release IDs flow from importer and library
contexts; direct narrow beets-client lookup emits six normalized fields; missing or ambiguous IDs do
no I/O; authority becomes operational without redesign; fixture-backed tests and opt-in live smoke
exist; and baseline validation is green.

## Stop condition

Stop after Block 016. Do not add MusicBrainz matching, deeper canonical fields, another provider, or
file-tag synchronization.
