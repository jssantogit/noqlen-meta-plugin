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
