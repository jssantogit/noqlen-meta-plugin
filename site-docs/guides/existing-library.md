# Enrich An Existing Library

You will preview and apply ordinary release metadata for albums already stored
in beets without changing audio files.

Enable at least one release provider. Then preview an Album query:

```bash
beet nm album:"Example Album"
```

Ordinary mode selects Albums only. It does not enrich standalone singleton
Items and never calls the track-only LRCLIB provider.

After reviewing all statuses, apply strict changes:

```bash
beet nm --apply album:"Example Album"
```

If one review or mapping blocker should not withhold other safe ordinary
fields, use explicit partial mode:

```bash
beet nm --apply --partial album:"Example Album"
```

Application updates mapped Album fields and uses normal beets inheritance for
database Items. It does not call `Item.write()`, move files, or update cover
art. Use [native beets write](../reference/beets-interaction.md#2-native-beet-write)
separately if generic file tags should follow database metadata.
