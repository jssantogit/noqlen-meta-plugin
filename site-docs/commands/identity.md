# Repair MusicBrainz Identity

Audit the coherent release, release-group, recording, and release-track IDs:

```bash
beet nm --identity QUERY
```

Preview changes nothing. Apply a complete, unambiguous repair with:

```bash
beet nm --identity --apply QUERY
```

Identity mode has its own MusicBrainz source, scoring, completeness, and stale
guards. `providers.musicbrainz.enabled` neither enables nor disables identity
audit. Identity repair writes four database columns and does not use ordinary
field switches, partial mode, or ordinary `--write`.

For file-tag synchronization after coherent database identity exists, use the
separate [Identity Tags](identity-tags.md) workflow.
