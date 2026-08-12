# Apply Metadata

After reviewing the same query, authorize ordinary application:

```bash
beet nm --apply QUERY
```

`--apply` commits approved ordinary metadata to the beets database. Verified
`cover.jpg` sidecars may be written and their canonical path saved as
`Album.artpath`; this is the authorized artwork exception.

Audio files remain unchanged unless `--write` is also present. Strict mode is
the default. Optional `--partial` may retain independently safe ordinary work,
but partial is not force and does not bypass confidence, mapping, stale-state,
or identity rules.

Continue to [Write Metadata to Files](write-files.md) when supported tags should
also be synchronized.
