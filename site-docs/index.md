# Noqlen Meta

Noqlen Meta adds multi-provider metadata enrichment and MusicBrainz identity
tools to beets. You will learn how to preview changes safely, apply selected
changes to the beets database, and choose the correct file-tag workflow.

beets remains responsible for matching music and managing the library. Noqlen
does not rematch ordinary enrichment targets. It enriches releases and tracks
that beets has already selected, or separately audits their MusicBrainz IDs.

## Why Use It?

- Combine narrow metadata contributions from Discogs, MusicBrainz, Last.fm,
  iTunes, and LRCLIB.
- Review conflicts and target limitations before changing anything.
- Repair four MusicBrainz identity fields only when evidence is complete and
  unambiguous.
- Synchronize those four confirmed database fields to supported media files
  through a separate, verified workflow.

## Try It Safely

Install and enable the plugin, enable one provider, then preview an existing
album:

```bash
beet nm album:"Example Album"
```

Preview can contact enabled providers but writes neither the database nor
audio files. Continue with [Getting Started](getting-started/index.md), or use
the [command reference](reference/commands.md) when you already know beets.

## Where To Go

- [Getting Started](getting-started/index.md): install through first apply.
- [Concepts](concepts/index.md): understand databases, tags, modes, and status.
- [How-to guides](guides/index.md): complete one practical workflow.
- [Reference](reference/index.md): exact flags, configuration, providers, and fields.
- [Troubleshooting](troubleshooting/index.md): resolve a blocked or surprising result.
- [Advanced safety](advanced/safety.md): inspect write guarantees and limitations.

The canonical public documentation is live at
[https://noqlen-meta-plugin.readthedocs.io/](https://noqlen-meta-plugin.readthedocs.io/).
The public `latest` build has passed. A versioned `v1.0.0` documentation build
will not exist until the release tag is created and built.

## License And Repository Status

Noqlen Meta is MIT licensed. The repository's root
[`LICENSE`](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/LICENSE)
is the canonical license text.

The GitHub repository is public and public access has been confirmed. The
package has not been published to PyPI. The license choice does not imply
endorsement by beets, MusicBrainz, Discogs, Navidrome, Last.fm, Apple, LRCLIB,
or any provider.
