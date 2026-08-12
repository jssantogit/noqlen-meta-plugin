# Use AcoustID

Preview existing-library recording evidence:

```bash
beet nm --acoustid QUERY
```

A valid stored fingerprint can be reused. Permit calculation for a selected
Item that lacks one only in standalone mode:

```bash
beet nm --acoustid --fingerprint-missing QUERY
```

Add `--apply` separately to persist only `acoustid_id` and
`acoustid_fingerprint`. AcoustID never writes audio files, and identity mode
never calculates a missing fingerprint.

With configured enablement, decisive AcoustID evidence may filter incompatible
MusicBrainz identity candidates without adding score or lowering gates. Native
beets/chroma still owns importer acoustic matching and fingerprint submission.
