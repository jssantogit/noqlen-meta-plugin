# Sync Identity Tags

Preview the specialized coherent four-MBID file synchronization:

```bash
beet nm --identity-tags QUERY
```

Authorize verified file replacement with:

```bash
beet nm --identity-tags --write QUERY
```

This mode performs no provider lookup. It compares four coherent database MBIDs
with supported media-file tags, verifies a candidate and filesystem safety
guarantees, replaces eligible files, and updates only operational Item `mtime`
in the database.

It is not ordinary `--apply --write` and is not an alias for native
`beet write`. Use it only for release, release-group, recording, and
release-track MBID tags.
