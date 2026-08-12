# AcoustID Problems

## No Fingerprint Was Available

A valid stored fingerprint is reused when allowed. Standalone mode can calculate
a missing fingerprint only with `--fingerprint-missing` or the corresponding
configured permission. Confirm that the configured `fpcalc` executable exists.
Identity mode never calculates missing fingerprints.

## The Client Key Is Missing

Lookup requires `NOQLENMETA_ACOUSTID_API_KEY` in the environment that runs
beets. There is no YAML credential field. Do not print or commit the key.

## No Result Was Decisive

Check `min_score`, `min_margin`, `max_results`, and
`max_recordings_per_result`. A result below threshold or without a unique
recording margin is correctly withheld. Do not lower gates without
understanding the evidence.

## Identity Was Not Filtered

Identity filtering requires `acoustid.enabled`, `use_for_identity`, lookup
permission, valid fingerprint material, and decisive recording compatibility.
AcoustID removes incompatible candidates; it does not add structural score,
lower identity thresholds, or choose a release by itself.

Native beets/chroma owns importer acoustic matching and submission. See
[AcoustID Configuration](../configuration/acoustid.md).
