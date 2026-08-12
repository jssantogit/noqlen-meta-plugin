# AcoustID

AcoustID is a separate **existing-library recording-evidence workflow**. It is
not an ordinary metadata provider and it does not replace beets/chroma during
import.

## Two ways to use it

Standalone mode is explicit:

```bash
beet nm --acoustid QUERY
```

The standalone command is allowed even when `acoustid.enabled` is `false`.
`acoustid.enabled` instead controls whether AcoustID may also contribute
recording evidence to `beet nm --identity`.

A practical starting configuration is:

```yaml
acoustid:
  enabled: false
  reuse_existing: true
  compute_missing: false
  lookup: true
  use_for_identity: true
```

## What each setting does

| Setting | Default | What it does |
| --- | ---: | --- |
| `enabled` | `false` | Enables optional AcoustID evidence inside `--identity`. It is not required for the explicit `--acoustid` command. |
| `reuse_existing` | `true` | Reuses a valid fingerprint already stored in the beets library. A stored AcoustID ID by itself is not fresh fingerprint evidence. |
| `compute_missing` | `false` | Allows standalone AcoustID mode to calculate a missing fingerprint from the audio file. `--fingerprint-missing` can grant the same permission for one invocation. Identity mode never calculates a missing fingerprint. |
| `lookup` | `true` | Allows an AcoustID network lookup when valid fingerprint material is available. |
| `use_for_identity` | `true` | When AcoustID integration is enabled, decisive recording evidence may remove incompatible MusicBrainz identity candidates. It does not add score or lower identity thresholds. |
| `min_score` | `0.90` | Minimum AcoustID result score accepted as evidence. |
| `min_margin` | `0.05` | Minimum margin required to treat one recording result as uniquely decisive. |
| `max_results` | `5` | Maximum result groups retained from one lookup. |
| `max_recordings_per_result` | `10` | Maximum recording MBIDs retained from each result group. |
| `timeout_seconds` | `15.0` | Timeout used by AcoustID/fingerprint work. |
| `requests_per_second` | `3.0` | Process-local lookup rate ceiling. |
| `cache_entries` | `256` | Maximum number of process-local lookup-cache entries; `0` disables that cache. |
| `fpcalc` | `fpcalc` | Executable name/path used when fingerprint calculation is authorized. |

The Technical Reference contains the accepted numeric ranges for the bounded
settings.

## Missing fingerprints

There are two ways to permit standalone calculation.

Per command:

```bash
beet nm --acoustid --fingerprint-missing QUERY
```

Or persist the permission in configuration:

```yaml
acoustid:
  compute_missing: true
```

Both are restricted to standalone AcoustID mode. `--identity` never calculates
missing fingerprints, even when `compute_missing: true`.

Calculation reads the audio file through `fpcalc`; AcoustID mode never writes
to the audio file.

## Lookup credentials

Lookup uses the environment-only client key:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

There is intentionally no API-key field in YAML. Keep the key out of committed
configuration files.

## Use AcoustID with identity audit

```yaml
acoustid:
  enabled: true
  lookup: true
  use_for_identity: true
```

With valid fingerprint material and decisive evidence, AcoustID may filter
MusicBrainz candidates that require incompatible Recording MBIDs. It does not
choose a release by itself.

Native beets/chroma continues to own importer acoustic matching and fingerprint
submission. See the [AcoustID command](../commands/acoustid.md) for the workflow
and the [Configuration Reference](../technical-reference/configuration.md#acoustid-controls)
for exact ranges and validation rules.
