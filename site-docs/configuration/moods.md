# Moods

Mood enrichment uses controlled canonical labels from supported MusicBrainz and
Last.fm evidence.

```yaml
fields:
  moods: true

moods:
  max_moods: 1
```

`fields.moods` permits mood enrichment. `moods.max_moods` is the maximum number
of independently supported canonical moods retained. The default is one.

To retain up to three supported moods:

```yaml
moods:
  max_moods: 3
```

Noqlen may return fewer than the maximum. It never invents or pads moods to
reach the limit. Accepted values are integers from 1 through 10.

Enable a contributing semantic provider as described in [Providers](providers.md).
There is no implemented local mood-analysis backend. Exact defaults are in the
[Configuration Reference](../technical-reference/configuration.md).
