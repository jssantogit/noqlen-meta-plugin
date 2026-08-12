# Safely Update an Entire Library

First validate your configuration with a narrow query. Then preview every
eligible target:

```bash
beet nm --all
```

Inspect provider warnings and all `REVIEW` or `BLOCKED` results. When the
prepared work is acceptable, apply database and authorized artwork changes:

```bash
beet nm --all --apply
```

Synchronize supported prepared tags only when wanted:

```bash
beet nm --all --apply --write
```

`--all` grants no mutation authority by itself, and `--write` does not expand
collection or analysis.

After file writes, external library scanners such as Navidrome may need their
own rescan. Noqlen does not call a Navidrome API or control its cache and scan
timing.
