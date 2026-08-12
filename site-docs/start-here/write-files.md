# Write Changes to Your Files

To apply the same prepared enrichment and synchronize supported metadata to
audio files, run:

```bash
beet nm --apply --write album:"Discovery"
```

`--apply` authorizes prepared ordinary enrichment. `--write` additionally
authorizes verified synchronization of supported prepared metadata and, when
available, embedding of the already prepared cover image.

Adding `--write` never triggers another provider call or analyzer pass. It does
not change which evidence was collected; it changes only the permitted mutation
surface for the existing plan.

The central workflow is:

```text
configure -> preview -> review -> apply -> write, when wanted
```

Next, customize behavior in **Configuration**, or learn the secondary importer
path in **Recipes -> Enrich During Import** once that section is introduced.
For exact boundaries now, use [Preview, Apply, and Write](../concepts/preview-apply-write.md).
