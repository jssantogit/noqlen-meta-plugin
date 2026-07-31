# Synchronize Identity Tags

You will synchronize four coherent MusicBrainz IDs from the beets database to
supported audio files without contacting a provider.

First audit and, if needed, repair database identity:

```bash
beet nm --identity album:"Example Album"
beet nm --identity --apply album:"Example Album"
```

Then preview the file workflow:

```bash
beet nm --identity-tags album:"Example Album"
```

Preview reads the database and existing tags but creates no candidate or
backup. It does not claim per-file write capability; that can be proven only
by a real candidate round trip during `--write`.

When every target is coherent and the platform limitations are acceptable:

```bash
beet nm --identity-tags --write album:"Example Album"
```

No provider or network call occurs. Exactly `mb_albumid`,
`mb_releasegroupid`, `mb_trackid`, and `mb_releasetrackid` are synchronized.
Unrelated readable writable tags must remain unchanged. The database changes
only for each successful Item's operational `mtime`.

Writes use same-directory candidates and backups, atomic replacement, and
post-replacement verification. Atomicity is per file, not command-wide;
earlier files may remain committed if a later file fails. Unsupported files or
filesystems block before replacement. See [advanced safety](../advanced/safety.md).
