# Configuration basics

You do not have to enable every field or copy the full configuration file.
Start with a **goal**, then pick only the settings that support it.

## A three-part configuration

```yaml
noqlenmeta:
  fields:
    lyrics: true
  providers:
    lrclib:
      enabled: true
```

- **Fields** decide *what information* Noqlen may enrich.
- **Providers** decide *which online source* can supply it.
- **Local analysis** is a separate optional way to calculate certain values
  (e.g. BPM or Key) from the audio.

None of these settings grants write permission on its own. Run
`beet nm QUERY` for a preview, `--apply` for approved database changes
and sidecars, and `--apply --write` for supported audio tags.

See [the mental model](../concepts/mental-model.md) before using advanced
resolution or importer flags.

## Start from a profile

| Goal | Example to copy |
| --- | --- |
| Genres, styles, moods and front cover | [Starter profile](../recipes/configuration-profiles.md#profile-a-starter-library-enrichment) |
| Plain lyrics and `.lrc` files | [Lyrics profile](../recipes/configuration-profiles.md#profile-b-plain-and-synchronized-lyrics) |
| Verified MusicBrainz credits and Work details | [Credits profile](../recipes/configuration-profiles.md#profile-c-detailed-recording-and-work-credits) |
| Local BPM and Key | [Audio profile](../recipes/configuration-profiles.md#profile-d-local-audio-analysis) |

The profile examples are additive. Keep one `noqlenmeta:` mapping in your
existing beets `config.yaml`; do not duplicate sections when combining them.

## Where to go next

Browse [Fields](fields.md) and [Providers](providers.md) for user-oriented
explanations; use the separate
[Configuration Reference](../technical-reference/configuration.md) when you
need precise types, defaults and restrictions.

### Importer configuration is different

`noqlenmeta.preview`, `noqlenmeta.apply` and `apply_mode` configure
Noqlen **during beets import**. They do **not** control the standalone
`beet nm --apply` command for your existing library. The standalone
`identity` and AcoustID modes also have separate authorities.

If you don't use importer enrichment, keep those importer switches at their
conservative defaults. See [Enrich During Import](../recipes/import-enrichment.md).

### What is the full configuration file?

[Default Configuration Snapshot](full-example.md) documents every
**established default**, not every possible optional V3 field. New V3
capabilities are intentionally omitted from the default tree until you opt in.
Use the [Field Reference](../technical-reference/fields.md) for all supported
field names.
