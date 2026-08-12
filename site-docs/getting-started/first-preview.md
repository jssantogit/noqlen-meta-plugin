# First Preview

You will preview enrichment for one existing album and then, only after review,
apply eligible ordinary metadata to the beets database.

## Enable A Provider

MusicBrainz enrichment is a simple first choice when beets already knows the
exact release MBID:

```yaml
noqlenmeta:
  preview: true
  providers:
    musicbrainz:
      enabled: true
```

This provider does not rematch the album. It reads the exact release selected
by beets and can contribute edition metadata.

## Preview

```bash
beet nm album:"Example Album"
```

The argument is a native beets Album query. Preview may perform provider
network requests. It does not change the beets database or audio files.

Look for these statuses:

- `KEEP`: retain the current value.
- `PROPOSE`: a safe change is available.
- `REVIEW`: evidence or an existing-value conflict needs attention.
- `BLOCKED`: the target cannot safely represent the change.

## Apply To The Database

After reviewing the exact query:

```bash
beet nm --apply album:"Example Album"
```

`--apply` changes eligible ordinary fields in the beets database and may write
an authorized verified `cover.jpg` sidecar and persist `Album.artpath`. It does
not mutate audio files without `--write`. Strict mode is the default, so one
`REVIEW` or mapping blocker prevents all ordinary Noqlen changes for that album.

If you intentionally want safe fields while preserving unresolved ones, read
[Strict and Partial](../concepts/strict-vs-partial.md) before using:

```bash
beet nm --apply --partial album:"Example Album"
```

Partial is not force. For complete syntax and invalid combinations, use the
[command reference](../technical-reference/command-line.md).
