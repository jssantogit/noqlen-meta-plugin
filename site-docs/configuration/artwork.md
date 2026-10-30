# Artwork

Noqlen can select an approved main-front image from Cover Art Archive for an
identified album.

```yaml
fields:
  cover: true
providers:
  coverartarchive:
    enabled: true
artwork:
  size: original
  replace_existing: false
```

The default preserves an existing `cover.jpg` or embedded image. Set
`replace_existing: true` only when Noqlen should replace curated artwork with
the selected CAA front.

`size` accepts `original`, `1200`, `500`, or `250`. Explicit thumbnail sizes are
maxima. Sidecars are named `cover.jpg`; multidisc albums receive identical
verified bytes in each real disc directory, and `Album.artpath` records the
canonical sidecar.

Ordinary `--apply` may write and verify sidecars without mutating audio files.
`--apply --write` may additionally embed the already prepared image. See the
[Fields Reference](../technical-reference/fields.md) for exact boundaries.


## Back artwork (V3, opt-in)

Set `noqlenmeta.fields.back_artwork: true` to request an approved Cover Art
Archive `Back` image for the **exact selected release**. On an existing-library
album, `--apply` can create a guarded `back.jpg` in the verified disc
directories. It will not overwrite an existing `back.jpg`, replace the front
cover, alter `Album.artpath`, or silently embed Back artwork in audio files.
Competing images require REVIEW; a failure while writing multiple disc
directories triggers conservative rollback of newly created sidecars.

**Not included in V3.0:** artwork printed on the disc surface (Disc/Medium art)
and mapping different Medium images to specific disc numbers. This is planned
for evaluation in a later version, and must never be confused with `back.jpg`.
