# Nothing Was Changed

Check these causes in order.

## 1. Is the Field Enabled?

Inspect your effective configuration:

```bash
beet config noqlenmeta.fields
```

Enable the relevant field, such as `fields.moods` or `fields.lyrics`, then
preview again.

## 2. Is a Suitable Source Enabled and Usable?

Check the matching provider block with `beet config noqlenmeta.providers`.
Artwork needs Cover Art Archive; lyrics need LRCLIB; local BPM needs both the
`[audio]` extra and `local_analysis.bpm.enabled`.

## 3. Is There Enough Identity or Evidence?

MusicBrainz semantic lookups require exact known IDs. CAA needs album identity.
Providers may legitimately return no defensible result.

## 4. Is an Existing Value Preserved?

Most fields preserve existing values by default. Artwork also preserves an
existing sidecar or embedded image unless `replace_existing` is true.

## 5. Was the Result REVIEW or BLOCKED?

Read [REVIEW and BLOCKED Results](review-blocked.md). These statuses are not
silent no-ops and should not be bypassed.

## 6. Did the Query Select the Intended Music?

Repeat a narrow query such as:

```bash
beet nm album:"Discovery"
```

Confirm the same native beets query with `beet ls` when needed. See
[Preview Metadata](../commands/preview.md).
