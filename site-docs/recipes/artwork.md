# Add album front and back artwork

**Goal:** enrich a correctly identified album with verified Cover Art Archive
images. Noqlen selects images for the **identified release**, not just
any album that happens to have the same title.

## Configure the image types

```yaml
noqlenmeta:
  fields:
    cover: true
    back_artwork: true
  providers:
    coverartarchive:
      enabled: true
  artwork:
    size: original
    replace_existing: false
```

The front cover (`cover`) is enabled by default; release **Back**
artwork (`back_artwork`) is an optional V3 field. You can omit
`back_artwork` if you only want front covers.

!!! warning "A back cover is not a disc image"
    `back_artwork` means a verified **Back** image of the exact release,
    typically packaging. The printed artwork on each individual disc/Medium
    is **not** implemented in V3.0.

## Preview one album

```bash
beet nm album:"Example Album"
```

Replace the example with an album already imported into beets. A candidate
requires trustworthy album identification and eligible image evidence.
The preview does not create or replace image files.

## Apply only verified artwork

After inspecting the proposal:

```bash
beet nm --apply album:"Example Album"
```

Depending on the selected evidence and local files, this can write guarded
`cover.jpg` and `back.jpg` sidecars. For a verified front cover, Noqlen
can also update the database `Album.artpath`. The back image never
replaces that front path.

Existing images are protected:

- `artwork.replace_existing: false` preserves existing front-cover artwork
  by default.
- The `back.jpg` pipeline has its own strict no-clobber safety checks.
  Enabling `back_artwork` is not permission to replace someone's existing
  back artwork indiscriminately.
- Real multidisc layouts use guarded sidecar placement per eligible disc
  directory; the same exact-release artwork is used rather than inventing
  one image per Medium.

If you also want the approved **front** cover embedded in supported audio
tags, explicitly use:

```bash
beet nm --apply --write album:"Example Album"
```

The back `back.jpg` remains a sidecar; `--write` does not invent
a new embedded media-art tag for it or redo the CAA lookup.

## Troubleshooting

If no image is proposed, check the album's known MusicBrainz Release ID,
the CAA provider switch, the exact artwork type and existing files.
An unavailable Back image does **not** justify using an unrelated edition's
image. For safe file replacement rules, see
[Artwork configuration](../configuration/artwork.md),
[Where metadata is saved](../concepts/data-destinations.md) and
[REVIEW or BLOCKED](../troubleshooting/review-blocked.md).
