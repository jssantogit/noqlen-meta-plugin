# Apply Your First Changes

Run the same query with explicit application authority:

```bash
beet nm --apply album:"Discovery"
```

`--apply` commits approved ordinary enrichment to the beets database. The beets
database is the library information managed by beets; audio-file tags are
metadata stored inside files such as FLAC or MP3.

Ordinary apply does not mutate audio files. It may write an authorized verified
`cover.jpg` artwork sidecar and save its canonical path as `Album.artpath`.

Strict mode is the default, so unresolved ordinary work can withhold the target
rather than silently accepting an unsafe value. Continue with
[Write Changes to Your Files](write-files.md) only if supported tags should also
change.
