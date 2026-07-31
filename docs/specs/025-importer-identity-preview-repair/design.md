# Block 025 Design

## Flow

```text
accepted AlbumMatch / TrackMatch
  -> selected Item/TrackInfo pairs
  -> effective post-beets identity context
  -> Block 024 IdentityAuditResult
  -> privacy-safe importer preview
  -> canonical identity target plan
  -> optional atomic selected-metadata repair
  -> normal beets importer lifecycle
```

## Boundaries

`identity/importer.py` owns selected-match extraction and effective context prediction.
`identity/importer_preview.py` owns sanitized rendering. `identity/importer_mapping.py` maps only
repair-ready findings to exact selected metadata fields. `identity/importer_application.py` owns
canonical-plan, stale-context, target, atomicity, rollback, and cache guards. Plugin integration owns
the separate identity configuration and lazy source lifecycle.

Album release identities target `AlbumInfo`; assigned recording identities target their selected
`TrackInfo`. Singleton release identities use the selected `TrackInfo` Item-data surface. Preview and
application are independent, but ambiguity always maps to no changes. There is no partial identity
mode: the complete plan succeeds or no identity field changes.

Album-level preview interprets the original per-Item identity tuple rather than the audit finding's
joined display value. Repeated identical canonical IDs render once, distinct canonical IDs render as
`multiple/conflict`, mixed-marker state renders as `mixed/missing`, and malformed raw values remain
hidden. An ambiguous result uses its top-ranked evaluation for assignment counts only; that candidate
remains unselected and cannot authorize repair.

The repair boundary never owns Item/Album persistence, database writes, tags, or files. Normal beets
application remains downstream owner. Block 026 owns library identity; Block 027 owns tag sync;
AcoustID evidence remains outside v1.0.
