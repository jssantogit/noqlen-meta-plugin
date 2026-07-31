# Update A Navidrome-Scanned Library

You will move an intended change through the beets database, file tags, and a
later Navidrome rescan. Noqlen does not call a Navidrome API.

## Ordinary Metadata

Preview and apply the database change:

```bash
beet nm album:"Example Album"
beet nm --apply album:"Example Album"
```

At this point files are unchanged. Preview native beets synchronization:

```bash
beet write -p album:"Example Album"
```

When the generic tag changes are acceptable:

```bash
beet write album:"Example Album"
```

## MusicBrainz Identity Only

For the specialized four-MBID path, use:

```bash
beet nm --identity-tags album:"Example Album"
beet nm --identity-tags --write album:"Example Album"
```

Do not normally run both native `beet write` and identity-tag write for the
same purpose. Native write is generic; Noqlen identity-tag write is narrowly
verified and requires coherent database identity.

Finally, allow or request a Navidrome rescan using Navidrome's own documented
administration. Results can be delayed by scan schedules or caches. Noqlen does
not verify Navidrome behavior.
