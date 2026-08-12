# Configuration Overview

Noqlen Meta configuration lives under one `noqlenmeta` block in your beets
configuration file:

```yaml
noqlenmeta:
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

- `fields` chooses which metadata categories Noqlen may handle.
- `providers` chooses metadata sources and their prerequisites.
- `genres`, `moods`, `artwork`, and `bpm` tune their named features.
- `local_analysis` controls optional analysis of your own audio.
- `acoustid` controls the separate existing-library evidence workflow.
- `resolution` customizes authority, confidence, and preservation. Most users
  should leave it alone.

Start with [Fields](fields.md) and [Providers](providers.md). For every exact
path and default, use the [Configuration Reference](../technical-reference/configuration.md).
