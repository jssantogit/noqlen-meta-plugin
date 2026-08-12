# Command Overview

Choose the command from your goal:

```text
See what Noqlen would change -> beet nm QUERY
Save approved changes -> beet nm --apply QUERY
Also synchronize supported tags to files -> beet nm --apply --write QUERY
Process the whole library -> beet nm --all
Repair MusicBrainz identity -> beet nm --identity QUERY
Use acoustic fingerprints/evidence -> beet nm --acoustid QUERY
```

Preview is the recommended starting point for every new configuration or broad
operation. `QUERY` uses native beets query syntax.

These pages teach common goals. For every flag, invalid combination, and exact
mode boundary, use the [Command-line Reference](../technical-reference/command-line.md).
