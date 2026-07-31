# Block 025 Requirements

## Goal

Integrate Block 024 identity audit into already accepted album and singleton imports, with safe
preview and explicitly authorized atomic repair of selected metadata.

## Required behavior

- Add independent boolean `identity.enabled`, `identity.preview`, and `identity.apply` settings with
  defaults `false`, `true`, and `false`; reject apply while disabled.
- Consume `IdentityAuditResult` for accepted `AlbumMatch`/`TrackMatch` selections without changing
  beets matching or duplicating identity scoring and ambiguity policy.
- Build effective identity from normal beets selected metadata semantics, including `from_scratch`.
- Preview four-field findings, structural evidence, ambiguity, repair readiness, and application state
  without paths, queries, opaque keys, private data, or raw malformed values.
- Render album current identity from its original per-Item tuple: repeated canonical values once,
  distinct canonical values as `multiple/conflict`, and mixed-marker state as `mixed/missing`.
- For ambiguous ranked results, report assignment counts from the top evaluation without selecting it
  or changing verdict, repair readiness, mapping, or application.
- Map repair-ready missing/conflicting release, release-group, recording, and release-track MBIDs to
  the exact selected `AlbumInfo`/`TrackInfo` application fields.
- Revalidate canonical plan integrity, current context, target type, scope, field, and uniqueness.
- Apply all planned identity fields atomically, restore fields and caches on failure, and invalidate
  affected caches on success.
- Keep identity permissions independent from enrichment configuration and MusicBrainz provider
  enablement.

## Exclusions

No match selection, partial identity repair, Item/Album mutation, direct persistence, library identity
command, tag/file synchronization, AcoustID, fingerprinting, or recording search.
