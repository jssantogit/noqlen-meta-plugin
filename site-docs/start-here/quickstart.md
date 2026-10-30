# Quickstart: preview one album

**Goal:** install Noqlen, run a safe preview, and know what your first
enrichment would change. No API keys or optional audio dependencies are
required for this path.

**Before you begin:** beets is installed, you have imported at least one
album into its library, and you can run `beet` in a terminal.
If your library is empty, [import music with beets](https://beets.readthedocs.io/en/stable/guides/main.html)
first. Noqlen doesn't select albums on behalf of beets.

## 1. Install the plugin

For a regular pip/virtualenv beets setup, use the **same Python environment**:

```bash
python -m pip install beets-noqlenmeta
beet config -p
```

!!! tip "Do you use uv tool or pipx?"
    An unrelated `pip install` will not inject Noqlen into beets' isolated
    tool environment. Follow the
    [uv tool or pipx installation instructions](installation.md) instead,
    then return here after `beet nm --help` works.

The second command shows the location of your existing beets configuration
file. Open it and **add** `noqlenmeta` to the existing plugin list:

```yaml
plugins:
  - noqlenmeta
```

If you already use other beets plugins, keep them in the same list. Don't
create a second `plugins:` key or replace your entire config with this
two-line example.

## 2. Check the installation

```bash
beet nm --help
beet ls -a
```

The first command should display Noqlen's command options. The second
lists albums already imported into beets. Choose one album title from the
list. A network connection is needed when querying online metadata providers.

## 3. Preview the album

```bash
beet nm album:"Discovery"
```

`Discovery` is **only an example**; use your own album title.
The `album:"..."` part is a normal beets query.

The preview may contact enabled sources, but it **does not alter** your
beets database, audio files or sidecars.

## 4. Interpret the result

Noqlen uses four field-level statuses:

- **KEEP** — an existing value is retained.
- **PROPOSE** — a candidate is eligible for consideration; check it.
- **REVIEW** — the evidence needs investigation; don't force it.
- **BLOCKED** — a safety or storage rule prevents a change.

**Important:** `PROPOSE` does **not** guarantee application. In the default
**strict** mode, one `REVIEW` or mapping `BLOCKED` for the same target
can withhold **all** ordinary changes, including unrelated proposed fields.

Read the `application`, `mapping blockers` and `resolution review`
lines, not just field-level statuses. For a worked terminal example,
follow [Read your first preview](reading-preview.md).

A run may legitimately have **no proposals**. Noqlen needs recognized IDs,
a suitable provider, and usable evidence. This is not automatically an error.
See [Nothing was changed](../troubleshooting/nothing-changed.md).

## 5. Apply only after reviewing

If the preview contains changes you want **and no unresolved blocker or
review that would withhold the target**, authorize database application:

```bash
beet nm --apply album:"Discovery"
```

This can also write approved, verified **sidecar** files when enabled, such as
`cover.jpg`. It does **not** write ordinary metadata into the audio files.

If you additionally want supported prepared metadata written to audio tags,
use the explicit combination:

```bash
beet nm --apply --write album:"Discovery"
```

**Do not use `--all` as your first trial.** Start with one album, inspect the
result, and back up valuable files before broad changes.

## 6. Pick your next feature

You have completed the beginner workflow. Now choose a concrete goal:

- [Add artwork](../recipes/artwork.md)
- [Add lyrics, including `.lrc` sidecars](../recipes/lyrics-synced.md)
- [Add Recording/Work credits](../recipes/recording-credits.md)
- [Calculate local BPM, Key or audio proxies](../recipes/audio-analysis.md)
- [Use configuration profiles](../recipes/configuration-profiles.md)

Not sure how the options fit? Read
[the three configuration switches](../concepts/mental-model.md)
and [where changes are stored](../concepts/data-destinations.md).

!!! tip "Already using beets"
    Noqlen has conservative defaults. You do **not** need to turn on every
    field, provider or analyzer to get started. The full defaults file is
    intended for reference, not as a starter config.
