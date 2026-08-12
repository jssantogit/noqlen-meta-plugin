# Your First Preview

Preview the teaching album:

```bash
beet nm album:"Discovery"
```

`album:"Discovery"` is a beets query. It selects music whose `album` field
matches `Discovery`. Replace that value with an album in your own library.

The command may contact enabled providers, but preview is non-mutating: it does
not change the beets database, artwork sidecars, or audio files.

Read the output before adding any permission flag. Continue with
[Understanding the Results](understanding-results.md).
