# File Writing Problems

## Database Changed, Files Did Not

Ordinary `--apply` updates approved database metadata and may write verified
`cover.jpg` sidecars plus `Album.artpath`. Audio files remain unchanged unless
`--write` is added:

```bash
beet nm --apply --write album:"Discovery"
```

Adding `--write` never triggers another provider call or analyzer pass.

## A Field Was Not Writable

Only losslessly supported prepared fields can be synchronized. Synchronized
lyrics have no delivered writable target. Fractional BPM may block where a
format cannot round-trip it unless configured rounding produced the canonical
value first.

## Cover Sidecar vs Embedded Art

`--apply` may write verified `cover.jpg` sidecars. Audio-file embedding requires
ordinary `--apply --write` or the corresponding enabled importer write path.

## File or Filesystem Blocked

Check permissions, regular-file status, supported media mapping, source
stability, and the required replacement guarantees. Identity-tag mode has a
narrower no-atime/no-follow filesystem contract than ordinary database work.

Native `beet write`, importer `import.write`, and identity-tag `--write` remain
separate controls. See [beets Interaction](../technical-reference/beets-interaction.md).
