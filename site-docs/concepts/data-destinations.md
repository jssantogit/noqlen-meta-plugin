# Where does my metadata go?

Noqlen can enrich more information than every audio tag format can store.
That's why **database changes, separate sidecar files, and audio-file tags
are not interchangeable**.

| Destination | What it is | When it can change |
| --- | --- | --- |
| **beets library** | Database containing your Albums, Items and plugin-owned structured data | Authorized `--apply`, or selected importer application |
| **Sidecar** | Separate `cover.jpg`, `back.jpg` or `.lrc` file beside the media | A verified, supported sidecar plan during authorized `--apply`; guards prevent unsafe overwrites |
| **Audio tags** | Metadata embedded in FLAC, MP3, M4A, Ogg or Opus | Supported ordinary fields via explicit `--apply --write`, or normal beets importer writing |
| **External player** | Navidrome or another library scanner | Only after the relevant files/sidecars change and the player rescans |

## An album artwork example

An approved front cover may create `cover.jpg` during ordinary `--apply`
without changing the audio bytes. With `--apply --write`, Noqlen may also
embed that *already selected* cover when supported.

An exact-release back image may create `back.jpg` when the opt-in is on.
It is **not** individual CD/Medium surface artwork. Existing back sidecars
are protected.

## A lyrics example

Plain lyrics can have a supported ordinary metadata target. Synchronized
lyrics use a separately verified `.lrc` sidecar in the existing-library
workflow; enabling them does not promise an embedded SYLT tag.

## A local audio example

- BPM has a native database value and supported ordinary file-tag mappings.
- Key uses native beets `initial_key` when evidence is sufficient and
  a safe supported write mapping is available.
- Energy, Danceability and method IDs are **database-only**; an audio file
  will not receive proprietary or speculative tags for them.
- Structured title aliases, instrument credits and many multi-value fields
  remain queryable in database storage only.

## What each CLI mode authorizes

```text
beet nm QUERY                Preview; no ordinary mutations
beet nm --apply QUERY        Database + verified authorized sidecars
beet nm --apply --write QUERY Database + sidecars + supported audio tags
```

`--write` is not a way to override safety checks; it does not trigger new
provider lookup or audio analysis. Native `beet write`, importer
`import.write`, and Noqlen's separate `--identity-tags --write`
are distinct paths.

If a value is database-only, `--write` will **not** manufacture a corresponding
audio tag. To make values visible in an external player, confirm that player
supports their chosen file tags or sidecars; a beets database value alone is
not visible to it.

See [Preview, Apply and Write](../advanced/preview-apply-write.md)
for exact technical boundaries.
