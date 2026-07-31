# Installation

You will install Noqlen Meta beside beets, enable it, and verify that beets can
load the command.

## Required Steps

Install the package in the same Python environment that provides `beet`:

```bash
pip install beets-noqlenmeta
```

Discogs search requires the optional Discogs client:

```bash
pip install "beets-noqlenmeta[discogs]"
```

Find the active beets configuration file:

```bash
beet config -p
```

beets normally uses a platform-specific user configuration directory. Linux,
macOS, and Windows use different defaults, and `BEETSDIR` or `beet -c` can
change the effective configuration. `beet config -p` is safer than assuming a
path. `beet config -e` can open the file in your configured editor.

Enable the plugin:

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  preview: true
```

If you list plugins explicitly, include any other beets plugins you still use,
including `musicbrainz` when it should provide normal beets matches.

Verify discovery through beets' real help flow:

```bash
beet help noqlenmeta
beet nm --help
```

The distribution name is `beets-noqlenmeta`, the plugin identifier is
`noqlenmeta`, the command is `beet noqlenmeta`, and `beet nm` is its preferred
alias. No console script is installed because beets discovers
`beetsplug.noqlenmeta` directly.

## Next Step

Enable one provider and run the [first preview](first-preview.md).
