# Audit MusicBrainz Identity

You will audit a complete album or standalone Item and optionally repair four
MusicBrainz database fields without changing files.

Preview with a native Item query:

```bash
beet nm --identity title:"Example Track"
```

Matching one album track expands to the complete Album. A matching standalone
Item remains a singleton target. The MusicBrainz identity source may perform
network lookups; ordinary enrichment providers are not used.

Review the verdict, score, margin, track assignment, and repair readiness. A
weak, ambiguous, incomplete, malformed, or stale result is blocked.

Only after review, request database repair:

```bash
beet nm --identity --apply title:"Example Track"
```

The repair changes only release, release-group, recording, and release-track
MBID columns. It does not read or write media tags. There is no partial or
force identity mode.

Importer identity is separately controlled:

```yaml
noqlenmeta:
  identity:
    enabled: true
    preview: true
    apply: false
```

`providers.musicbrainz.enabled` does not control this identity source.
