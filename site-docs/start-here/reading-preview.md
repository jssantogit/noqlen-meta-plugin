# Read your first preview

**Goal:** understand what Noqlen is telling you *before* giving it
permission to change your library or files.

Run a preview for an album already in your beets library:

```bash
beet nm album:"Example Album"
```

Replace the title with one from `beet ls -a`. This command may contact
online sources, but **preview is read-only** for the library and audio files.
You do not need `--apply` or `--write` to inspect proposals.

## Four outcomes in plain language

| Status | What it tells you | What you should do |
| --- | --- | --- |
| **KEEP** | The existing value should remain | Nothing; this is normal |
| **PROPOSE** | Noqlen has an eligible candidate | Compare the current and proposed values |
| **REVIEW** | Evidence is ambiguous or not strong enough to accept automatically | Check identities/sources; don't force it |
| **BLOCKED** | A safety, storage or compatibility condition prevents the change | Read the reason, then correct the cause if possible |

## A worked example (illustrative, not literal terminal output)

The following table is **illustrative**: it shows how you should interpret
possible field decisions. It is **not** copied from an actual command run,
does not imply that your chosen album has those tags, and does not promise the
terminal will use this exact layout.

| Example field | Possible result | Interpretation |
| --- | --- | --- |
| Genre | **PROPOSE** | A source-backed genre is available; inspect before applying |
| Existing album date | **KEEP** | The current valid date can be preserved |
| Language from an ambiguous Work | **REVIEW** | Evidence doesn't justify a confident automatic change |
| Multi-valued credit with no safe target | **BLOCKED** | Noqlen will not throw away values to fit a scalar tag |

A real preview may produce only `KEEP` outcomes, no eligible candidates,
or a different combination of statuses. That is **not automatically an error**.
Some features are off by default and providers cannot fill missing evidence
by guessing.

## Decide your next step

**If you see PROPOSE:** check whether the music selected by the query and
the candidate values are the ones you intended. When ready, run the same
selection with application permission:

```bash
beet nm --apply album:"Example Album"
```

This may change the beets database **and** authorized verified sidecars
such as `cover.jpg`; it does not write regular tags inside MP3/FLAC.

**If you also want supported embedded audio tags**, use:

```bash
beet nm --apply --write album:"Example Album"
```

This adds a separate file-tag permission; it does not rerun online searches
or bypass field safety. It also does not create speculative tags for
database-only V3 fields.

**If you see REVIEW or BLOCKED:** **Do not** treat `--apply` or
`--partial` as a force switch. Noqlen has no force mode.
[Understand REVIEW and BLOCKED](../troubleshooting/review-blocked.md),
then preview again after correcting the underlying issue.

**If nothing useful changes**, check these in order:

1. Does the [query select the intended album](../troubleshooting/nothing-changed.md)?
2. Is the desired [field enabled](../configuration/fields.md)?
3. Is a suitable [provider or local analyzer](../concepts/mental-model.md)
   enabled?
4. Is there a verified MusicBrainz identity or defensible source evidence?
5. Is an existing value intentionally protected from replacement?

## What does "apply" change exactly?

```text
beet nm QUERY                    -> Preview only
beet nm --apply QUERY            -> Database + authorized sidecars
beet nm --apply --write QUERY    -> Above + supported embedded audio tags
```

For the complete contract, see
[Where metadata goes](../concepts/data-destinations.md) and
[Preview, Apply and Write](../advanced/preview-apply-write.md).

When you're comfortable interpreting previews,
[choose a configuration profile](../recipes/configuration-profiles.md)
or [combine features](../recipes/combine-features.md).
