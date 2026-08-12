# Write Metadata to Files

Combine both ordinary permissions:

```bash
beet nm --apply --write QUERY
```

The command applies the same prepared ordinary plan and additionally performs
verified synchronization of supported metadata and BPM tags. It may embed the
already prepared primary cover when the artwork plan permits it.

Adding `--write` never triggers another provider call or analyzer pass. It does
not expand CAA selection, Librosa work, fields, evidence, or target selection.

Native `beet write`, importer `import.write`, and
`beet nm --identity-tags --write` are separate controls. See
[beets Interaction](../technical-reference/beets-interaction.md).
