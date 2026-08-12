# Process the Whole Library

Scale the ordinary workflow in the same preview-first order:

```bash
beet nm --all
beet nm --all --apply
beet nm --all --apply --write
```

`--all` replaces a query and selects every eligible Album and Item for the
active mode. It grants no write permission by itself.

First test your configuration on a narrow album or artist query. Once the
results are understood, preview `--all`, inspect the output, then add only the
permissions you actually want.

A query and `--all` cannot be combined. See the
[Command-line Reference](../technical-reference/command-line.md) for exact
selection behavior.
