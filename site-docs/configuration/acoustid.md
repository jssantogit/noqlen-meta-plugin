# AcoustID

AcoustID is a separate existing-library recording-evidence workflow. It is not
ordinary semantic enrichment.

```yaml
acoustid:
  enabled: true
  reuse_existing: true
  compute_missing: false
  lookup: true
  use_for_identity: true
```

Noqlen can reuse a valid stored fingerprint. Standalone AcoustID mode may
calculate a missing fingerprint only with explicit permission; identity mode
never calculates one. Calculation invokes the configured `fpcalc` executable.

Lookup uses the environment-only `NOQLENMETA_ACOUSTID_API_KEY`. Score, margin,
result count, recordings per result, timeout, request rate, and process-local
cache bounds are configurable. With `enabled` and `use_for_identity`, decisive
recording evidence may filter incompatible MusicBrainz candidates without
adding score or lowering identity thresholds.

Native beets/chroma owns importer acoustic matching and fingerprint submission.
Noqlen does not replace it. See the [Configuration Reference](../technical-reference/configuration.md#acoustid-controls)
for every setting and range.
