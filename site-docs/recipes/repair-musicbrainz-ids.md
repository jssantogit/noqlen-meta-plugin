# Repair MusicBrainz IDs

Identity repair is separate from ordinary enrichment. Preview first:

```bash
beet nm --identity album:"Discovery"
```

The audit evaluates release, release-group, recording, and release-track IDs as
one coherent assignment. It blocks ambiguity, incomplete evidence, and stale
targets.

Apply a complete approved repair with:

```bash
beet nm --identity --apply album:"Discovery"
```

`providers.musicbrainz.enabled` neither enables nor disables this identity
source. Identity mode has no partial or force mode and does not write file tags.
Use [Sync Identity Tags](../commands/identity-tags.md) afterward only when the
four coherent database IDs should be synchronized to supported files.
