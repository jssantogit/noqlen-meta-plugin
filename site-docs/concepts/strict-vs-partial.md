# Strict And Partial

You will learn when ordinary changes are withheld and what explicit partial
mode can safely preserve.

## Definitions

**Strict** means one `REVIEW` or mapping blocker prevents all ordinary Noqlen
changes for that target.

**Partial** means already-safe, losslessly mapped ordinary fields may apply;
review and blocked fields remain unchanged.

Suppose a provider produces:

```text
genres -> safe proposal
styles -> safe proposal
year -> conflicts with the existing value, so REVIEW
```

The outcomes are:

```text
preview
-> shows every status and writes nothing

--apply
-> strict mode; applies nothing for that target

--apply --partial
-> applies genres and styles; preserves year
```

## Partial Is Not Force

Partial does not:

- accept a `REVIEW`;
- choose an ambiguous candidate;
- lower confidence;
- serialize or discard part of a mapping blocker;
- bypass stale-state guards;
- apply identity partially;
- apply file tags partially.

Noqlen v1 has no `--force`.

## Importer And Command Settings

For the library command, request partial explicitly:

```bash
beet nm --apply --partial album:"Example Album"
```

For importer enrichment, configuration is separate:

```yaml
noqlenmeta:
  apply: true
  apply_mode: partial
```

Importer `apply_mode` does not control `beet nm`. Importer application mutates
only the metadata selected by beets; normal later beets behavior owns database
persistence and optional file writing.

Identity repair and identity-tag synchronization are coherent all-or-blocked
workflows and never use partial mode.
