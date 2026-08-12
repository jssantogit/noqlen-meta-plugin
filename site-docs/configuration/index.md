# Configuration Overview

Noqlen Meta configuration lives under one `noqlenmeta` block in your beets
configuration file.

Most existing-library users can start with **fields** and **providers**. The
other sections let you tune individual features or importer behavior when you
need them.

## The full shape

```yaml
noqlenmeta:
  preview: true
  apply: false
  apply_mode: strict

  identity:
    enabled: false
    preview: true
    apply: false

  fields:
    ...
  providers:
    ...
  genres:
    ...
  moods:
    ...
  artwork:
    ...
  bpm:
    ...
  local_analysis:
    ...
  acoustid:
    ...
  resolution:
    ...
```

You do **not** need to configure every section. Noqlen already has conservative
defaults.

## Importer controls

The first settings apply to Noqlen while beets is importing music. They do not
control the `beet nm` library command.

- `preview: true` shows ordinary importer enrichment without authorizing a
  Noqlen metadata mutation. This is the default.
- `apply: false` means importer proposals are not applied by Noqlen. Set it to
  `true` only when you want approved proposals added to the metadata selected by
  beets.
- `apply_mode: strict` requires the selected ordinary enrichment work to be
  safely applicable as a whole. `partial` may keep independently safe fields
  while withholding blockers; **partial is not force**.
- `identity` is a separate importer MusicBrainz identity audit. Its `enabled`,
  `preview`, and `apply` switches do not enable ordinary enrichment and are
  independent of `providers.musicbrainz.enabled`.

If you only use Noqlen on an existing library, you can leave these importer
settings at their defaults and use the command flags documented under
[Commands](../commands/index.md).

## Feature blocks

- `fields` chooses which metadata categories Noqlen may handle.
- `providers` chooses metadata sources and their prerequisites.
- `genres` controls genre count and style promotion.
- `moods` controls the maximum number of supported moods retained.
- `artwork` controls Cover Art Archive image size and replacement policy.
- `bpm` controls BPM persistence, recalculation, rounding, and octave handling.
- `local_analysis` controls optional analysis of your own audio. Local BPM is
  implemented; the reserved local mood switch currently has no analysis model.
- `acoustid` controls the separate existing-library fingerprint/evidence
  workflow and its optional use during identity audit.
- `resolution` customizes provider authority, confidence, and existing-value
  preservation. Most users should leave it alone.

Start with [Fields](fields.md) and [Providers](providers.md), then open the page
for the feature you want to customize. For every exact path, type, range, and
default, use the [Configuration Reference](../technical-reference/configuration.md).
