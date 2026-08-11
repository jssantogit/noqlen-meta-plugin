# Noqlen Meta

Noqlen Meta is a beets plugin for multi-provider metadata enrichment and
MusicBrainz identity tools. beets remains the matcher and library manager:
Noqlen enriches releases and tracks that beets has already selected, and it
offers separate workflows to audit MusicBrainz identity, use AcoustID as
recording-level identity evidence, and synchronize four confirmed MusicBrainz
IDs to audio-file tags.

Noqlen previews by default. Ordinary database and approved artwork-sidecar
changes require `--apply`; audio-file mutation requires `--write`. Specialized
identity-tag file replacement requires `--identity-tags --write`. There is no
`--force` option.

The repository is preparing Noqlen Meta `2.0.0`. The currently published
PyPI/GitHub release remains `1.0.0` until the v2 release workflow is explicitly
executed after merge to `main`.

## Capabilities

- Enrich releases, tracks, and artists with semantic genres, styles, moods,
  languages, and geography from Discogs, MusicBrainz, Last.fm, and iTunes.
- Add selected-track plain lyrics from LRCLIB during import.
- Preview or apply ordinary enrichment to albums already in a beets library.
- Synchronize supported ordinary metadata to files through a verified
  `--apply --write` workflow.
- Select and apply verified Cover Art Archive album artwork, including
  deterministic `cover.jpg` sidecars and optional embedding.
- Analyze local BPM with optional lazy Librosa support from the `[audio]` extra.
- Audit and repair release, release-group, recording, and release-track MBIDs.
- Use decisive AcoustID recording evidence to filter incompatible MusicBrainz
  identity candidates without changing structural scores or thresholds.
- Preview or apply standalone existing-library AcoustID evidence, including
  explicit calculation of missing fingerprints when requested.
- Synchronize four coherent database MBIDs to supported audio files.
- Keep provider lookup, database application, fingerprint calculation, and file
  writing separately authorized.

Noqlen does not rematch ordinary enrichment targets. It does not call
Navidrome APIs; Navidrome is a possible consumer of resulting file tags.

## Documentation

The complete manual is available on
[Read the Docs](https://noqlen-meta-plugin.readthedocs.io/). The
[`site-docs/`](https://github.com/jssantogit/noqlen-meta-plugin/tree/main/site-docs)
source is available for contributions.

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

Opt-in local BPM analysis uses the lazy audio extra:

```bash
pip install "beets-noqlenmeta[audio]"
```

No extra Python dependency is required for AcoustID lookup or stored-fingerprint
reuse. Explicit missing-fingerprint calculation uses an external `fpcalc`
executable (Chromaprint), configurable through `noqlenmeta.acoustid.fpcalc`.

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

MusicBrainz is enabled by default and uses only exact MBIDs already known by
beets; it never performs fuzzy identity search:

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

This changes ordinary metadata in the beets database and may write an authorized
verified `cover.jpg` sidecar and persist `Album.artpath`. Audio files remain
unchanged unless `--write` is also present. Strict mode is the default: one
review or mapping blocker withholds every ordinary Noqlen change for that album.

Add `--write` to the same reviewed command to synchronize supported ordinary
fields to media files through verified candidate-copy/reopen checks. Collection
and analysis are identical with or without `--write`; adding `--write` never
triggers another provider call or analyzer run.

Partial mode is explicit:

```bash
beet nm --apply --partial album:"Example Album"
```

Partial mode can store already-safe ordinary fields while leaving blocked or
review fields unchanged. Partial is not force: it never accepts ambiguity,
lowers confidence, bypasses stale-state checks, or applies identity/file work
partially.

## AcoustID Evidence

Standalone AcoustID mode operates on complete existing-library Albums and
standalone Items. Preview is the default:

```bash
beet nm --acoustid title:"Example Track"
```

A valid stored fingerprint can be reused. Missing fingerprints are calculated
only with explicit standalone authority:

```bash
beet nm --acoustid --fingerprint-missing title:"Example Track"
```

`--apply` remains a separate database permission and can change only
`acoustid_id` and `acoustid_fingerprint`. It never writes audio files.

When `acoustid.enabled` and `acoustid.use_for_identity` are enabled, the
existing-library `--identity` command may use decisive AcoustID recording
evidence to remove incompatible MusicBrainz candidates. AcoustID does not add
score, lower thresholds, or directly supply release/release-group/release-track
identity. `--identity` never calculates a missing fingerprint, even when
standalone calculation is configured.

The AcoustID API key is environment-only:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

Chromaprint is the fingerprint algorithm/tooling family; `fpcalc` is the local
Chromaprint executable used for explicit calculation; AcoustID is the recording
lookup service. Native beets `chroma` remains responsible for importer acoustic
matching and fingerprint submission. Noqlen's AcoustID feature is an
existing-library evidence workflow and does not replace `chroma`.

## Commands And Write Boundaries

| Command | Purpose | Network | Database | Audio files |
| --- | --- | --- | --- | --- |
| `beet nm QUERY` | Ordinary preview | Enabled providers | No | No |
| `beet nm --apply QUERY` | Ordinary application | Enabled providers | Ordinary metadata and artwork path | No audio mutation; verified `cover.jpg` may change |
| `beet nm --apply --write QUERY` | Ordinary DB + file application | Enabled providers | Ordinary metadata | Supported verified tags |
| `beet nm --identity QUERY` | Identity audit | MusicBrainz + optional AcoustID lookup | No | No |
| `beet nm --identity --apply QUERY` | Identity repair | MusicBrainz + optional AcoustID lookup | Four MBID columns | No |
| `beet nm --acoustid QUERY` | AcoustID preview | Configured AcoustID lookup | No | No |
| `beet nm --acoustid --apply QUERY` | AcoustID database application | Configured AcoustID lookup | Two AcoustID columns | No |
| `beet nm --identity-tags QUERY` | Identity-tag preview | No | No | No |
| `beet nm --identity-tags --write QUERY` | Four-MBID synchronization | No | Operational `mtime` only | Four MBID tags |
| `beet write QUERY` | Native beets tag sync | No | Operational state | Generic beets fields |

The importer has another boundary: Noqlen may update the metadata selected by
beets, then beets performs its normal persistence and optional tag write.
`import.write`, native `beet write`, and Noqlen `--identity-tags --write` are
different controls. See [How Noqlen interacts with
beets](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/reference/beets-interaction.md).

## Providers

MusicBrainz is the zero-credential provider enabled by default. Discogs and
Last.fm are opt-in. AcoustID remains a separate recording-evidence subsystem.

| Provider/source | Current scope | Current contribution |
| --- | --- | --- |
| Discogs | Releases, opt-in | Structured genres/styles plus release metadata; styles remain ordered and authoritative |
| MusicBrainz enrichment | Exact Release/Recording/Artist/Work MBIDs | Genres, moods, Work language codes, artist areas/countries, and release metadata |
| Last.fm | Track -> Release -> Artist, opt-in | Classified genre/style/mood community tags only while requested fields remain unresolved |
| iTunes | Releases | Album genre and release year |
| LRCLIB | Importer-selected tracks | Plain lyrics; synchronized lyrics preview as blocked |
| Cover Art Archive | Exact album Releases | Approved main-front artwork, with Release Group fallback only after definitive absence |
| Local Librosa analysis | User audio, opt-in `[audio]` extra | BPM only; no external BPM provider |
| MusicBrainz identity source | Separate identity modes | Four MusicBrainz identity fields |
| AcoustID evidence | Existing-library identity/standalone mode | Recording compatibility evidence and two AcoustID database fields |

Discogs direct-ID lookup can work without credentials; search requires the
optional client and generally a token. Set the token in the
`NOQLENMETA_DISCOGS_TOKEN` environment variable rather than committing it.

## Fields And Formats

Semantic fields include genres, styles, moods, lyrics languages, contextual
artist languages, artist countries, and artist areas. Language values use
three-letter codes such as `eng`, `kor`, and `jpn`. `artist_languages` is
derived only from Works reached by tracks in the current target; it is not a
whole-career crawl. Artist geography uses MusicBrainz area structure and is
never guessed from names, language, release country, script, or place strings.

Verified semantic file mappings are available for `styles`, `moods`,
`lyrics_languages`, `artist_languages`, `artist_countries`, and `artist_areas`
on FLAC, MP3, M4A/MP4, Ogg Vorbis, and Opus. Album artwork uses exact approved
CAA fronts, deterministic `cover.jpg` sidecars, and optional verified embedding.
Local BPM analysis is disabled by default, preserves existing BPM unless
recalculation is requested, and imports Librosa only when analysis runs.
Synchronized lyrics and local ML mood analysis remain outside this phase.

Identity-tag round trips are tested with:

- FLAC
- MP3
- M4A/MP4
- Ogg Vorbis
- Opus

The identity-tag filesystem workflow requires proven no-atime, no-follow, and
same-directory atomic-replacement guarantees. Unsupported operating systems,
filesystems, or files block before replacement. This narrower limitation does
not imply that ordinary or AcoustID database workflows are Linux-only.

## beets And Navidrome

The beets database is information managed privately by beets. Audio-file tags
are metadata stored inside media files. Navidrome normally scans those files;
it does not normally read the private beets database.

Therefore `beet nm --apply` alone does not synchronize audio tags, although an
authorized artwork sidecar may become visible to Navidrome after a rescan.
Use `beet nm --apply --write` for supported ordinary metadata/BPM tags and
prepared cover embedding, native `beet write` for generic beets
database-to-file synchronization, or `beet nm --identity-tags --write` only for
the specialized four-MBID workflow. Then let Navidrome rescan according to its
own configuration. AcoustID `--apply` remains database-only.

## Compatibility

- Python 3.10 through 3.14 (`>=3.10,<3.15`) are supported and covered by the
  release CI matrix. Version 1.0.0 does not claim Python 3.15 support.
- beets 2.12 or later within the 2.x series is required.
- Ordinary enrichment, AcoustID, and database identity operations are
  Python/beets based.
- Explicit AcoustID fingerprint calculation additionally requires a compatible
  `fpcalc` executable; stored-fingerprint reuse and lookup do not.
- Identity-tag replacement is supported only where its filesystem guarantees
  can be proven at runtime.
- Navidrome compatibility describes a file-tag workflow, not a direct API
  integration.

See the [compatibility reference](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/reference/compatibility.md) for the
tested matrix and limitations.

## Project

- [PyPI](https://pypi.org/project/beets-noqlenmeta/)
- [GitHub releases](https://github.com/jssantogit/noqlen-meta-plugin/releases)
- [Changelog](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/CONTRIBUTING.md)
- [Security](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/SECURITY.md)
- [Release status and owner gates](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/RELEASE_CHECKLIST.md)
- [Issue tracker](https://github.com/jssantogit/noqlen-meta-plugin/issues)

Version `1.0.0` was published on PyPI and released on GitHub on 2026-08-02.
Versioned documentation is available through the Read the Docs `stable` and
`v1.0.0` versions.

## License

Noqlen Meta is distributed under the [MIT License](LICENSE).

Copyright © 2026 João Pedro Rosa dos Santos.
