# Use AcoustID

Preview existing-library recording evidence:

```bash
beet nm --acoustid QUERY
```

The standalone command is explicit authority, so it works even when
`noqlenmeta.acoustid.enabled` is `false`.

A valid stored fingerprint can be reused. Missing-fingerprint calculation is
allowed only in standalone AcoustID mode. You can grant that permission for one
invocation:

```bash
beet nm --acoustid --fingerprint-missing QUERY
```

or enable the corresponding configuration policy:

```yaml
acoustid:
  compute_missing: true
```

`--identity` never calculates a missing fingerprint, including when the config
permission is enabled.

Add `--apply` separately when you want the prepared standalone result persisted:

```bash
beet nm --acoustid --apply QUERY
```

Standalone application changes only `acoustid_id` and
`acoustid_fingerprint` in the beets database. AcoustID never writes audio files.

When `acoustid.enabled`, `lookup`, and `use_for_identity` permit it, decisive
AcoustID evidence may filter incompatible MusicBrainz identity candidates
without adding score or lowering identity gates. Native beets/chroma still owns
importer acoustic matching and fingerprint submission.

See [AcoustID Configuration](../configuration/acoustid.md) for all settings.
