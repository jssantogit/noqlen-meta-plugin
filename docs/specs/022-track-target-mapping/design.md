# Design - Track Target Mapping

## Flow

```text
selected Item <-> TrackInfo
  -> TrackEnrichmentContext
  -> LRCLIB candidates
  -> Field Authority and FieldDecision
  -> canonical ChangePlan
  -> pure TrackTargetPlan
  -> sanitized preview
  -> stop before application
```

`TRACK_FIELD_TARGETS` is an immutable track-specific registry containing only the lossless
`lyrics -> TrackInfo.lyrics` scalar-string mapping. The mapper iterates proposed canonical changes in
field order, preserves plain lyric strings exactly, emits the synchronized-lyrics semantic blocker,
and emits a generic blocker for unknown fields. Reviews remain solely on the source `ChangePlan`.

`ImportTrackPlanningResult` keeps the selected track, context, resolver output, canonical plan, and
target plan together. Preview joins mapping consequences to `PROPOSE` decisions by canonical field
and shows only content counts plus fixed safe target metadata. No application mode or mutation is
introduced.
