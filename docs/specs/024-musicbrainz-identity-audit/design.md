# Block 024 Design

## Flow

```text
IdentityAlbumContext
  -> hydrated MusicBrainzReleaseIdentity candidates
  -> global rectangular minimum-cost track assignment
  -> bounded pair and release score breakdowns
  -> unique strong-candidate policy
  -> deterministic four-field comparison
  -> IdentityAuditResult
```

## Boundaries

`identity/domain.py` owns immutable validated values and policy. `assignment.py` owns conservative text
and pair scoring plus an O(n^3) pure-Python assignment. `scoring.py` owns explicit album-wide weights
and ranking. `audit.py` owns eligibility, findings, verdicts, and the injectable source protocol.
`musicbrainz.py` copies actual beets 2.12 `AlbumInfo`/`TrackInfo` fields and bounds official-plugin
candidate acquisition.

Existing MBIDs do not enter assignment or score functions. Candidate extras reduce count coverage;
unmatched local tracks block default eligibility. Repeated recording IDs are allowed only as separate
release-track occurrences. No function mutates its inputs or performs application.
