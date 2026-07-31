# How Noqlen Interacts With beets

You will distinguish three similarly named write concepts and understand which
import decisions allow Noqlen to run.

## 1. `import.write` And Import `-w`/`-W`

This setting belongs to the beets importer. In beets 2.12, `import.write`
defaults to enabled; import `-w` enables and `-W` disables the final importer
tag write.

Noqlen importer enrichment can mutate the selected `AlbumInfo` and
`TrackInfo`. beets later applies that selected metadata, persists import state,
and performs its normal single write when enabled. Noqlen does not duplicate
the importer file write.

| Noqlen importer `apply` | beets `import.write` | Outcome |
| ---: | ---: | --- |
| false | false | Preview only; no Noqlen mutation; no beets tag write. |
| false | true | beets writes its selected metadata without Noqlen proposals. |
| true | false | Noqlen modifies selected metadata; beets persists import state but does not write file tags. |
| true | true | One normal beets write includes the applied Noqlen metadata. |

The beets importer also decides what metadata is selected:

- **Apply** accepts a proposed match; Noqlen can run.
- **Skip** does not import that task; Noqlen does not run.
- **Use as-is** imports existing metadata without applying a candidate; Noqlen does not run.
- **Abort** stops the session; Noqlen does not run for an unselected task.
- Duplicate choices run Noqlen only when the resulting task has the selected
  `Action.APPLY` decision.
- Quiet import normally falls back to skip when no automatic choice is
  accepted, so Noqlen does not run for that skipped task.

The exact boundary is: importer enrichment and identity run only for a
selected `Action.APPLY` task. Noqlen does not reinterpret beets decisions.

## 2. Native `beet write`

This is generic beets database-to-file synchronization:

```bash
beet write -p album:"Example Album"
beet write album:"Example Album"
beet write -f album:"Example Album"
```

`-p`/`--pretend` previews without writing. By default, beets compares database
media fields with disk and writes changed selections. `-f`/`--force` asks
beets to write even when it considers tags current, which can also run native
write-hook behavior.

Native write may handle many beets-supported metadata fields. It does not
bypass Noqlen resolver, identity, or safety rules. In particular, `beet write
-f` does not:

- accept a Noqlen `REVIEW`;
- lower confidence or override `preserve_existing`;
- repair ambiguous identity;
- bypass coherent-database checks or stale guards;
- bypass identity-tag candidate verification.

Noqlen v1 has no `--force`.

## 3. `beet nm --identity-tags --write`

This is specialized Noqlen four-MBID synchronization:

```bash
beet nm --identity-tags album:"Example Album"
beet nm --identity-tags --write album:"Example Album"
```

It performs no provider/network lookup, requires coherent database identity,
updates only four MBID tags, verifies a same-directory candidate and backup
workflow, and updates only operational Item `mtime` in the database. It is not
a replacement for generic `beet write`.

## Native Queries

Noqlen passes query terms to beets. Bare terms use normal text matching,
`field:value` restricts a field, multiple terms use AND, and range/regex/exact
forms remain native beets behavior. Ordinary mode asks beets for Albums;
identity modes ask for Items and then expand matching album Items to complete
Albums. See the [command reference](commands.md#query-semantics).
