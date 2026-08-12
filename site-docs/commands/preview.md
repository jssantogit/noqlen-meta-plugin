# Preview Metadata

Preview is the default and grants no mutation permission:

```bash
beet nm QUERY
```

Replace `QUERY` with a native beets query, for example:

```bash
beet nm album:"Discovery"
beet nm artist:"Daft Punk"
```

The first selects an album by its album field; the second narrows by artist.
Preview may contact enabled providers and run already configured analysis, but
it changes neither the database nor files.

Review `KEEP`, `PROPOSE`, `REVIEW`, and `BLOCKED` before continuing to
[Apply Metadata](apply.md).
