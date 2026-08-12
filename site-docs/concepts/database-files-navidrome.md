# Database, Files, And Navidrome

You will learn why a successful database apply may not immediately appear in a
music server.

## Three Different Places

```text
beets database
-> information managed internally by beets

audio-file tags
-> metadata stored inside FLAC, MP3, M4A, Ogg, or Opus files

Navidrome
-> a server that normally scans audio files, not the private beets database
```

Noqlen ordinary library application changes the first layer:

```bash
beet nm --apply album:"Example Album"
```

That command does not write tags. To synchronize generic beets database
metadata to files, first preview native beets behavior, then write when ready:

```bash
beet write -p album:"Example Album"
beet write album:"Example Album"
```

The specialized four-MBID workflow is different:

```bash
beet nm --identity-tags album:"Example Album"
beet nm --identity-tags --write album:"Example Album"
```

After file tags change, Navidrome must rescan according to its own behavior.
Noqlen does not call Navidrome APIs, configure scans, or guarantee when caches
refresh. Use the [whole-library recipe](../recipes/whole-library.md) for the
complete sequence.
