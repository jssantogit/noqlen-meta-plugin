# Install Noqlen Meta alongside beets

Noqlen Meta is a **beets plugin**, not a separate music player. You need
beets installed first, and Noqlen must be installed in the **same environment**
where the `beet` command runs. A common cause of `unknown command 'nm'` is
installing the two into different Python environments.

If you have never installed beets, first follow
[beets' official getting-started guide](https://beets.readthedocs.io/en/stable/guides/main.html),
then return here. The beets import process has its own file-copying and tag
options; make a backup before importing existing music.

## 1. Pick how you installed beets

=== "Python pip / virtual environment"

    If beets was installed with `pip`, activate the **same virtual
    environment** or interpreter you use to run `beet`.

    ```bash
    python -m pip install beets-noqlenmeta
    ```

    If that interpreter differs from the one running `beet`, this install
    will not make the plugin visible. Avoid mixing system Python, a virtual
    environment and isolated app tools.

=== "uv tool"

    If beets is an isolated tool installed with `uv tool`, install the
    plugin **inside beets' tool environment**, not via unrelated `pip`:

    ```bash
    uv tool install --with beets-noqlenmeta beets
    ```

    If beets is already installed as a uv tool and its environment needs
    replacing, you can use `uv tool install --force --with beets-noqlenmeta
    beets`. **Include any previous beets extras and `--with` dependencies**
    when recreating that environment, so other plugins are not omitted.

    Official reference:
    [uv tool dependencies](https://docs.astral.sh/uv/concepts/tools/#including-additional-dependencies).

=== "pipx"

    If you installed beets using `pipx install beets`, inject Noqlen into
    that **existing pipx environment**:

    ```bash
    pipx inject beets beets-noqlenmeta
    ```

    To inspect the injected package, run `pipx list --include-injected`.
    Official reference:
    [pipx inject](https://pipx.pypa.io/latest/how-to/inject-packages.html).

!!! tip "Optional audio analysis or Discogs"
    Install `beets-noqlenmeta[audio]` in the **same environment** if you
    want Librosa-based local BPM, Key, Energy or Danceability. Likewise,
    `beets-noqlenmeta[discogs]` provides the optional Discogs client.
    For example, use `pipx inject beets "beets-noqlenmeta[audio]"`
    for a pipx-managed beets installation. Keep any previously enabled
    extras when updating your installation.

## 2. Enable the plugin in the beets configuration

Find the file beets actually reads:

```bash
beet config -p
```

Edit that **existing** `config.yaml`, adding the plugin to the **single**
`plugins:` list:

```yaml
plugins:
  - noqlenmeta
```

Keep the rest of your beets configuration and other installed plugins.
If a `plugins:` list exists, append `noqlenmeta` to it instead of creating
a second `plugins:` key.

## 3. Confirm that the command is available

```bash
beet nm --help
```

You should see command options for Noqlen. `beet noqlenmeta` is the full
command name, while `beet nm` is the short alias.

If the command is not found, check these **in order**:

1. Does `beet` work at all? If not, fix the underlying beets installation.
2. Did you install Noqlen into the same environment that owns `beet`?
   Review the pip / uv tool / pipx tabs above.
3. Did you enable `noqlenmeta` in the correct file from `beet config -p`?
4. Did you accidentally create two `plugins:` keys? Keep only one list.
5. Does the effective plugin list appear under `beet config plugins`?

For general setup problems, open [Troubleshooting](../troubleshooting/index.md)
or check the exact [compatibility contract](../technical-reference/compatibility.md).

Next: [Quickstart one album](quickstart.md), or
[choose a small configuration profile](../recipes/configuration-profiles.md).
