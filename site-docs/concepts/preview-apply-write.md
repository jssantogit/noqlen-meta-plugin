# Preview, Apply, And Write

You will choose the permission that matches the intended target.

## Preview

Preview is the default for every library mode:

```bash
beet nm album:"Example Album"
beet nm --identity album:"Example Album"
beet nm --identity-tags album:"Example Album"
```

Provider enrichment and identity audit can use the network. Identity-tag mode
does not. Preview writes neither ordinary database metadata nor file tags.

## Apply

`--apply` grants ordinary database and approved artwork-sidecar permission:

```bash
beet nm --apply album:"Example Album"
beet nm --identity --apply album:"Example Album"
```

The first applies ordinary album metadata; verified `cover.jpg` sidecars may be
written and their canonical paths persisted as `Album.artpath`. Audio files
remain unchanged unless `--write` is also present. The second command repairs
only four MusicBrainz identity columns and writes no files.

## Write

Ordinary file synchronization requires both permissions:

```bash
beet nm --apply --write album:"Example Album"
```

Provider collection and analysis are completed before application. Adding
`--write` never triggers another provider call or analyzer run. The command
performs global preflight, writes a verified candidate copy, reopens and verifies
the result, then replaces the source safely. Unsupported lossless mappings block
before database mutation in strict mode.

Identity-tag synchronization remains a separate mode:

```bash
beet nm --identity-tags --write album:"Example Album"
```

It authorizes verified replacement of eligible files to synchronize four MBID
tags. The database changes only for operational `mtime` bookkeeping.

Native `beet write` is a fourth concept: it is generic beets database-to-file
synchronization. Importer `import.write` is a fifth control owned by the beets
import lifecycle. See [beets interaction](../technical-reference/beets-interaction.md).
