# Design - Safe Selected-Track Application

## Flow

```text
selected track -> LRCLIB -> ChangePlan -> TrackTargetPlan
  -> integrity check -> strict/partial policy -> effective-current stale check
  -> target/value/uniqueness validation -> selected TrackInfo mutation
  -> cache invalidation -> stop before beets match application
```

`apply_track_target_plan` owns one narrow mutation boundary. It remaps `plan.source`, evaluates policy,
reuses `effective_current_values_for_import_track`, validates the full mapped subset, then assigns the
verified fields. Strict blocked outcomes and partial withheld fields are ordinary results; malformed
or stale contracts raise `TrackApplicationError` before target mutation.

Effective-current stale validation snapshots exact `raw_data` and `item_data` cache presence and
objects, removes those caches from selected TrackInfo and, for album matches, selected AlbumInfo, then
evaluates the real selected application surface. A `finally` block removes recomputed entries and
restores only the exact caches that existed before. After successful assignment, only TrackInfo caches
are invalidated permanently. AlbumInfo metadata and cache state are not track application targets.

The importer builds one planning result per selected mapping and passes its exact target plan to
application. Preview receives the optional application result. Without preview, fixed logs report only
counts and status. Provider failures remain fail-open per track; contract and application errors
propagate.
