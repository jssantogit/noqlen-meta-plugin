# Noqlen Meta

Noqlen Meta is a beets plugin for multi-provider metadata enrichment and
MusicBrainz identity tools. beets remains the matcher and library manager:
Noqlen enriches releases and tracks that beets has already selected, and it
offers separate workflows to audit MusicBrainz identity and synchronize four
confirmed MusicBrainz IDs to audio-file tags.

Noqlen previews by default. Database changes require `--apply`; specialized
identity-tag file replacement requires `--identity-tags --write`. There is no
`--force` option.

## Capabilities

- Enrich selected releases from Discogs, MusicBrainz, Last.fm, and iTunes.
- Add selected-track plain lyrics from LRCLIB during import.
- Preview or apply ordinary enrichment to albums already in a beets library.
- Audit and repair release, release-group, recording, and release-track MBIDs.
- Synchronize those four coherent database MBIDs to supported audio files.
- Keep provider lookup, database application, and file writing separately
  authorized.

Noqlen does not rematch ordinary enrichment targets. It does not call
Navidrome APIs; Navidrome is a possible consumer of resulting file tags.

## Documentation

The complete manual is prepared for
[Read the Docs](https://noqlen-meta-plugin.readthedocs.io/). Until the owner
imports the project there, browse the public source in
[`site-docs/`](https://github.com/jssantogit/noqlen-meta-plugin/tree/main/site-docs).

Start with:

- [Installation](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/getting-started/installation.md)
- [First safe preview](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/getting-started/first-preview.md)
- [Command reference](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/reference/commands.md)
- [Configuration reference](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/reference/configuration.md)
- [Troubleshooting](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/troubleshooting/index.md)

## Installation

Install Noqlen Meta in the same Python environment as beets:

```bash
pip install beets-noqlenmeta
```

Discogs search needs the optional client:

```bash
pip install "beets-noqlenmeta[discogs]"
```

Enable the plugin in the beets `config.yaml`:

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  preview: true
```

Run `beet config -p` to print the configuration path. beets chooses the normal
platform-specific configuration directory; do not assume the same path on
Linux, macOS, and Windows.

Verify that the plugin loaded:

```bash
beet help noqlenmeta
```

The command is `beet noqlenmeta`; `beet nm` is the preferred alias.

## First Preview

Enable at least one provider before ordinary enrichment. For example,
MusicBrainz enrichment uses the exact release MBID already known by beets:

```yaml
noqlenmeta:
  providers:
    musicbrainz:
      enabled: true
```

Preview one existing album:

```bash
beet nm album:"Example Album"
```

The command may use the network, but preview does not change the beets database
or audio files. Review `KEEP`, `PROPOSE`, `REVIEW`, and `BLOCKED` results before
continuing.

## Apply To The Database

After reviewing the same query, explicitly apply ordinary safe changes:

```bash
beet nm --apply album:"Example Album"
```

This changes ordinary metadata in the beets database only. It does not write
audio-file tags. Strict mode is the default: one review or mapping blocker
withholds every ordinary Noqlen change for that album.

Partial mode is explicit:

```bash
beet nm --apply --partial album:"Example Album"
```

Partial mode can store already-safe ordinary fields while leaving blocked or
review fields unchanged. Partial is not force: it never accepts ambiguity,
lowers confidence, bypasses stale-state checks, or applies identity/file work
partially.

## Commands And Write Boundaries

| Command | Purpose | Network | Database | Audio files |
| --- | --- | --- | --- | --- |
| `beet nm QUERY` | Ordinary preview | Enabled providers | No | No |
| `beet nm --apply QUERY` | Ordinary application | Enabled providers | Ordinary album metadata | No |
| `beet nm --identity QUERY` | Identity audit | MusicBrainz | No | No |
| `beet nm --identity --apply QUERY` | Identity repair | MusicBrainz | Four MBID columns | No |
| `beet nm --identity-tags QUERY` | Identity-tag preview | No | No | No |
| `beet nm --identity-tags --write QUERY` | Four-MBID synchronization | No | Operational `mtime` only | Four MBID tags |
| `beet write QUERY` | Native beets tag sync | No | Operational state | Generic beets fields |

The importer has another boundary: Noqlen may update the metadata selected by
beets, then beets performs its normal persistence and optional tag write.
`import.write`, native `beet write`, and Noqlen `--identity-tags --write` are
different controls. See [How Noqlen interacts with
beets](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/reference/beets-interaction.md).

## Providers

All providers are disabled by default.

| Provider | Current scope | Current contribution |
| --- | --- | --- |
| Discogs | Releases | Genres, styles, labels, catalog numbers, barcodes, country, year, media, format descriptions |
| MusicBrainz enrichment | Releases with an exact release MBID | Labels, catalog numbers, barcode, country, year, media |
| Last.fm | Releases | Filtered album genres |
| iTunes | Releases | Album genre and release year |
| LRCLIB | Importer-selected tracks | Plain lyrics; synchronized lyrics preview as blocked |
| MusicBrainz identity source | Separate identity modes | Four MusicBrainz identity fields |

Discogs direct-ID lookup can work without credentials; search requires the
optional client and generally a token. Set the token in the
`NOQLENMETA_DISCOGS_TOKEN` environment variable rather than committing it.

## Fields And Formats

Ordinary release fields include genres, styles, labels, catalog numbers,
barcodes, country, year, media, and format descriptions. Mood, lyrics,
synchronized lyrics, and cover settings are present for explicit capability
control, but a field is usable only where an enabled provider and a lossless
target mapping exist.

Noqlen v1 does not apply synchronized lyrics or cover art. Existing-library
ordinary enrichment is album-only. Importer plain-lyrics enrichment applies to
selected tracks only.

Identity-tag round trips are tested with:

- FLAC
- MP3
- M4A/MP4
- Ogg Vorbis
- Opus

The identity-tag filesystem workflow requires proven no-atime, no-follow, and
same-directory atomic-replacement guarantees. Unsupported operating systems,
filesystems, or files block before replacement. This narrower limitation does
not imply that ordinary database enrichment is Linux-only.

## beets And Navidrome

The beets database is information managed privately by beets. Audio-file tags
are metadata stored inside media files. Navidrome normally scans those files;
it does not normally read the private beets database.

Therefore `beet nm --apply` alone does not update what Navidrome sees. Use
native `beet write` for generic beets database-to-file synchronization, or use
`beet nm --identity-tags --write` only for the specialized four-MBID workflow.
Then let Navidrome rescan according to its own configuration.

## Compatibility

- Python 3.10 through 3.14 (`>=3.10,<3.15`) are supported and covered by the
  release CI matrix. Version 1.0.0 does not claim Python 3.15 support.
- beets 2.12 or later within the 2.x series is required.
- Ordinary enrichment and database identity operations are Python/beets based.
- Identity-tag replacement is supported only where its filesystem guarantees
  can be proven at runtime.
- Navidrome compatibility describes a file-tag workflow, not a direct API
  integration.

See the [compatibility reference](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/reference/compatibility.md) for the
tested matrix and limitations.

## Project

- [Changelog](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/CONTRIBUTING.md)
- [Security](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/SECURITY.md)
- [Release status and owner gates](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/RELEASE_CHECKLIST.md)
- [Issue tracker](https://github.com/jssantogit/noqlen-meta-plugin/issues)

Version `1.0.0` is a prepared release candidate. Publication remains gated on
public repository confirmation, Read the Docs setup, PyPI ownership and
trusted-publisher setup, and creation of the release tag.

## License

Noqlen Meta is distributed under the [MIT License](LICENSE).

Copyright © 2026 João Pedro Rosa dos Santos.
