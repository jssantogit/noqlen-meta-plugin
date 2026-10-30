# Read your first preview — using the real CLI format

**Goal:** decide whether a Noqlen enrichment is safe to apply, even when one
field is proposed but another needs review or cannot be saved.

The illustrative excerpts below explain the **terminal** output shape; they
are **not** a transcript of an actual album run.

Start with an album already imported into beets:

```bash
beet nm album:"Example Album"
```

Replace the title with one from `beet ls -a`. The preview may contact
providers but leaves the database, audio files and sidecars unchanged.
A preview **does not** commit changes.

## 1. Read the summary *before* the fields

A typical library-album preview starts with a summary like this:

```text
Noqlen Meta / library target preview:

  album: Example Artist - Example Album
  application: disabled (preview only)
  file tags: unchanged
  planned changes: 2
  losslessly mapped: 1
  mapping blockers: 1
  resolution review: 0
  unchanged: 0
  skipped: 0
  mapping complete: no
```

!!! note "Example, not output captured from your music"
    The artist, album and counts above are **illustrative**. The field names,
    status lines and format follow Noqlen's real Album renderer. Your run
    may contain other numbers, messages and provider evidence.

The important lines:

- **`application: disabled (preview only)`** — your library was not changed.
- **`planned changes`** — candidate changes identified; not a count of
  values that are guaranteed to be saved.
- **`losslessly mapped`** — changes that have safe storage targets.
- **`mapping blockers`** — proposed values that cannot safely use the
  selected target, or another mapping restriction.
- **`resolution review`** — unresolved/conflicting evidence that needs
  investigation.
- **`file tags: unchanged`** — this run did not modify embedded audio tags.

Do not equate `planned changes: 2` with "two values were written".

## 2. Read the decision for each field

Further down the output, you can encounter:

| Status | Meaning | What to do |
| --- | --- | --- |
| **KEEP** | A current value is retained | No action |
| **PROPOSE** | Evidence supports a candidate value | Check source, current/proposed value and target |
| **REVIEW** | Evidence or conflict is unresolved | Investigate; do not treat it as approval |
| **BLOCKED** | A safety/storage condition prevents the change | Resolve the cause, if possible |

For a mapped proposal, the real CLI uses labels such as:

```text
  genres
    PROPOSE
    target: genres
    proposed: Rock
    source: Discogs
    confidence: 0.94
```

This is a **shortened illustrative excerpt** following the real renderer;
the live output also includes a reason and can include evidence provenance.
The value, provider and confidence are examples, not measurements from
your library.

## 3. Critical: PROPOSE is not the same as APPLIED

**Strict** is the default mode. For a selected target, **one** ordinary
`REVIEW` or mapping `BLOCKED` can cause **all** ordinary Noqlen changes
for that target to be withheld, even if another field shows `PROPOSE`.

Example: genre is `PROPOSE`, but a different field has no safe mapping.
With ordinary strict `--apply`, Noqlen can report:

```text
  application mode: strict
  application: blocked
  mapping blockers: 1
```

In that case, **no ordinary database changes for that target were committed**.
This is intentional preservation, not a silent failure. Check the actual
`application` line in the output to learn what happened.

When you want to correct the problem, first narrow the selected fields,
fix source evidence or identify a supported storage target; then preview
again.

For experienced users who explicitly choose independent safe fields,
`--apply --partial` can apply **only** safely mapped ordinary values
while leaving reviewed or blocked fields alone:

```bash
beet nm --apply --partial album:"Example Album"
```

!!! warning "Partial is not a force switch"
    Partial does **not** accept a `REVIEW` field, invent a mapping,
    bypass stale-state checks, relax identity requirements or partially
    synchronize media-file tags. Noqlen has **no force mode**. Prefer
    resolving the blockers before broad changes.

See [Strict versus Partial](../advanced/strict-vs-partial.md) for the
exact authorized boundary.

## 4. Three outcomes after applying

| `application` summary | Meaning |
| --- | --- |
| `stored in library database (... fields)` | Eligible ordinary changes were persisted |
| `blocked` | Strict mode withheld ordinary changes for that target |
| `partially stored in library database (... fields)` | Explicit partial mode committed only independent eligible fields |

**If a preview is read-only**, use the same album query with explicit
`--apply` permission **only once you're satisfied with the planned
changes and any blockers**:

```bash
beet nm --apply album:"Example Album"
```

This can update beets' database and authorized `cover.jpg`, `back.jpg`
or `.lrc` sidecars when their respective options and guards permit it.
Ordinary embedded MP3/FLAC tags remain unchanged unless you separately
request:

```bash
beet nm --apply --write album:"Example Album"
```

`--write` is not a way around a blocked proposal, and database-only
fields such as Energy and Danceability never gain invented media tags.

## 5. If there were no useful proposals

Check, in order:

1. Does the query match music in your beets library? Try `beet ls -a`.
2. Is the field enabled? Inspect `beet config noqlenmeta.fields`.
3. Does an enabled provider or local analyzer support that field?
4. Does the album/track have the required identifiers and evidence?
5. Is there already a value Noqlen must preserve?

Next steps: [Nothing changed](../troubleshooting/nothing-changed.md),
[REVIEW and BLOCKED](../troubleshooting/review-blocked.md),
[configuration mental model](../concepts/mental-model.md),
or [choose a small profile](../recipes/configuration-profiles.md).
