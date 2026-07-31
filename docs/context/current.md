# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context Level

`standard` for completed Block 027 identity tag synchronization.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell output.

## Active Block

Block 027 - Identity Tag Synchronization (complete); Block 028 is next.

## Active Spec

`docs/specs/027-identity-tag-synchronization/`

## Active ADRs

- `docs/adr/0020-musicbrainz-identity-audit-engine.md`
- `docs/adr/0021-importer-identity-preview-repair.md`
- `docs/adr/0022-library-identity-audit-repair.md`
- `docs/adr/0023-identity-tag-synchronization.md`

## Completion State

Block 027 is complete. The existing `noqlenmeta`/`nm` command has an explicit `--identity-tags`
mode that selects complete persisted Albums and standalone Items using normal Item queries. Preview
is the default. Only `--identity-tags --write` can replace media files and update operational Item
`mtime`; ordinary `--apply`, importer settings, and identity database repair grant no file authority.

The database is the source of truth and must contain complete canonical coherent release,
release-group, recording, and release-track identity. Synchronization touches only those four
MediaFile fields. Planning snapshots every selected database target, exact source stat fingerprint,
current identity, unrelated writable logical tags, and supported filesystem metadata before a
command-wide preflight. Writes use verified same-directory candidates and rollback backups, reopen
the replaced source, update only Item `mtime` under a fixed-column savepoint, and emit post-success
`after_write` then `database_change` events. The mutable pre-write `write` hook is intentionally not
emitted. Explicit source/mtime phases restore safely rolled-back failures and retain a path-private
original backup when commit state is uncertain; such uncertainty is integrity-critical and committed.
Preview claims capability only after a real candidate round trip, and empty paths block without
filesystem access while valid files continue. Paths and raw errors remain private. Tiny
generated-silence fixtures prove real FLAC, MP3, M4A, Ogg Vorbis, and Opus round trips offline.
Candidate and backup fallback copies read sources through `O_NOATIME` no-follow descriptors; files
without that support block before replacement. Safe restoration verifies original mtime and one final
link in addition to content, tags, and supported metadata.
Validation passes 51 focused fix tests, 288 identity tests, and 1,088 full offline tests with 5 live
tests skipped. Ruff, repository contamination, and diff-whitespace checks pass.

## Stop Condition

Proceed next to Block 028 v1.0 Hardening and Release, then STOP. Add no new provider or metadata
feature.
