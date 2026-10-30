# Enrich Recording and Work metadata

**Goal:** add evidence-backed song credits and recording details without
rewriting primary artist names or inventing missing relationships.

A **Recording** is a specific recorded performance. A **Work** is the
underlying musical composition. Composer and lyricist credits usually
belong to the Work; performers and production roles may belong to a
Recording or Release.

## Enable the desired fields

Use verified MusicBrainz IDs from your existing beets library. Merge the
following settings under the `noqlenmeta:` key:

```yaml
noqlenmeta:
  fields:
    works: true
    isrcs: true
    iswcs: true
    composers: true
    lyricists: true
    producers: true
    performers: true
    featured_artists: true
    structured_artist_credits: true
    vocal_languages: true
    instrumental: true
    alternate_titles: true
    transliterations: true
    track_version: true
  providers:
    musicbrainz:
      enabled: true
```

Most longstanding credit fields are on by default; the newer V3 fields
(`vocal_languages`, `instrumental`, titles and versions) are opt-in.
You can leave out any category you do not want. See the
[copyable profile](../examples/credits-config.yaml).

## Preview one song

```bash
beet nm title:"Example Track"
```

Inspect what is proposed and which source relationship supports it. If
you are satisfied, apply to the database:

```bash
beet nm --apply title:"Example Track"
```

Complex credits, instrumental roles, alternate titles and relationships
may be kept in **typed/plugin-owned database storage**. They are not
automatically flattened into arbitrary audio tags.

## What won't be guessed?

- A singer isn't automatically a **featured artist**.
- A Release-level producer credit isn't indiscriminately copied to every
  track.
- `vocal_languages` requires a sufficiently verified Recording-to-Work
  relationship; it does not listen to the audio.
- Missing instrumental evidence means **unknown**, not `false`.
- Multiple titles or credit values aren't silently joined or truncated.

To use explicit/clean advisories, enable `fields.explicitness: true`
and the iTunes provider separately, then preview again. The advisory
must be from an exact track match; absent advisory does not mean clean.

For limits and where values are persisted, see the
[Field Reference](../technical-reference/fields.md),
[Glossary](../concepts/glossary.md), and
[Provider authority](../advanced/provider-authority-resolution.md).
