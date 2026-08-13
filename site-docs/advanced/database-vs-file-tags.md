# Database vs File Tags

Wave 1 keeps plural ISRCs, ISWCs, and Work IDs queryable in the Item database. File writing expands known release/original date components and supports release type/status plus exactly one ISRC or Work ID. Multiple ISRCs/Works, ISWC, recording date, edition, and separate secondary release types are blocked for file sync. Under partial mode, those blockers do not prevent safe database application.

Noqlen can affect three distinct places:

```text
beets database -> information managed by beets
audio-file tags -> metadata inside FLAC, MP3, M4A, Ogg, or Opus files
artwork sidecars -> cover.jpg files referenced by Album.artpath
```

Ordinary `--apply` commits approved metadata to the beets database. It may also
write verified `cover.jpg` sidecars and persist their canonical
`Album.artpath`; a sidecar is not an audio-file mutation.

Ordinary `--apply --write` additionally synchronizes supported prepared tags to
audio files and may embed the already prepared cover. Native `beet write` is
generic beets database-to-file synchronization. Identity-tag mode is a separate
four-MBID replacement workflow.

External scanners such as Navidrome normally observe audio files and sidecars,
not the private beets database. They may need their own rescan after changes.
Noqlen does not call their APIs or control their caches.
