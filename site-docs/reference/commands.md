# Command Reference

You will find the exact command modes, selection behavior, effects, and invalid
combinations.

```text
beet noqlenmeta [OPTIONS] [QUERY]
beet nm [OPTIONS] [QUERY]
```

## Mode Matrix

| Invocation | Network | beets database | Audio files |
| --- | --- | --- | --- |
| `beet nm QUERY` | Enabled enrichment providers | No | No |
| `beet nm --apply QUERY` | Enabled enrichment providers | Ordinary metadata and verified artwork `artpath` | Verified `cover.jpg`; no audio-file mutation |
| `beet nm --apply --partial QUERY` | Enabled enrichment providers | Safe ordinary fields | No |
| `beet nm --apply --write QUERY` | Same prepared provider/analysis work | Ordinary metadata, artwork, and operational `mtime` | Supported metadata/BPM tags plus prepared cover embedding |
| `beet nm --identity QUERY` | MusicBrainz identity source | No | No |
| `beet nm --identity --apply QUERY` | MusicBrainz identity source | Four MBID columns | No |
| `beet nm --acoustid QUERY` | Configured AcoustID lookup | No | No |
| `beet nm --acoustid --apply QUERY` | Configured AcoustID lookup | AcoustID columns | No |
| `beet nm --identity-tags QUERY` | No | No | No |
| `beet nm --identity-tags --write QUERY` | No | Operational `mtime` only | Four MBID tags |

## Query Semantics

Ordinary mode evaluates the same native beets query against Albums and Items,
independently skipping a scope when no enabled provider can contribute:

```bash
beet nm album:"Example Album"
```

`--identity`, `--acoustid`, and `--identity-tags` use a native beets **Item
query**. Matching one track expands to its complete Album, while a standalone
singleton Item is supported as one target:

```bash
beet nm --identity title:"Example Track"
```

Multiple query terms use normal beets semantics. Shell quoting keeps spaces in
one argument; it is not part of the query language.

## `--all`

- Type: boolean flag; default off.
- Query: replaces a query; query plus `--all` is invalid.
- Ordinary selection: every Album and Item for contributing scopes.
- Identity/tag selection: every complete Album and standalone Item once.
- Network: follows the selected mode.
- Database/files: grants no write permission by itself.
- Valid with: every mode, including its apply/write permission.
- Common block: incomplete target identity in identity-tag mode.

```bash
beet nm --identity --all
```

## `--apply`

- Type: boolean flag; default off.
- Query: required unless `--all` is used.
- Ordinary mode: strict database application; provider network enabled.
- Identity mode: coherent four-MBID database repair; MusicBrainz network enabled.
- File effect: verified `cover.jpg` sidecars may be written; audio files remain unchanged unless `--write` is also present.
- Valid with: ordinary mode, `--partial`, `--write`, `--identity`, or `--acoustid`.
- Invalid with: `--identity-tags`.
- Common block: ordinary `REVIEW`/mapping blocker, or identity ambiguity.

```bash
beet nm --apply album:"Example Album"
```

## `--partial`

- Type: boolean flag; default off.
- Mode: ordinary metadata only.
- Query: required unless `--all` is used.
- Network: enabled ordinary providers.
- Database: applies only safe, losslessly mapped ordinary fields.
- Files: unchanged unless `--write` is also present; unsupported fields remain explicit blockers.
- Valid combination: `--apply --partial`.
- Invalid without `--apply` and invalid with either identity mode.
- Common block: no safe mapped fields remain after withholding unresolved ones.

```bash
beet nm --apply --partial album:"Example Album"
```

Partial is not force and never relaxes review, confidence, mapping, stale,
identity, or file guards.

## `--identity`

- Type: boolean mode flag; default off.
- Query: native Item query required unless `--all` is used.
- Selection: complete Albums plus standalone Items.
- Network: MusicBrainz identity source, plus optional configured AcoustID lookup.
- Database: preview is read-only; `--apply` repairs four MBID columns.
- Files: never read or written for tags.
- Valid with: `--apply` or `--all`.
- Invalid with: `--identity-tags`, `--acoustid`, `--partial`, or `--write`.
- Common block: candidate evidence is ambiguous, weak, incomplete, or stale.

```bash
beet nm --identity --apply album:"Example Album"
```

Importer `identity.*` settings and `providers.musicbrainz.enabled` do not
authorize or disable this command mode.

## `--acoustid`

- Type: boolean mode flag; default off.
- Query: native Item query required unless `--all` is used.
- Selection: complete Albums plus standalone Items.
- Network: bounded AcoustID lookup when enabled and fingerprint material exists.
- Database: preview is read-only; `--apply` changes only `acoustid_id` and `acoustid_fingerprint`.
- Files: never written.
- Valid with: `--fingerprint-missing`, `--apply`, or `--all`.
- Invalid with: `--identity`, `--identity-tags`, `--write`, or `--partial`.

```bash
beet nm --acoustid title:"Example Track"
```

The explicit standalone mode is authorized even when
`noqlenmeta.acoustid.enabled` is false. Preview is the default.

## `--fingerprint-missing`

- Type: boolean permission flag; default off.
- Mode: requires `--acoustid`.
- Effect: permits local fingerprint calculation for selected Items lacking a valid stored fingerprint.
- Database: grants no write permission; `--apply` remains required.
- Files: read for fingerprint calculation but never written.

`--identity` never calculates a missing fingerprint, including when
`noqlenmeta.acoustid.compute_missing` is true.

## `--identity-tags`

- Type: boolean mode flag; default off.
- Query: native Item query required unless `--all` is used.
- Selection: complete Albums plus standalone Items.
- Network: none.
- Database: preview none; write updates operational Item `mtime` only.
- Files: preview reads tags; `--write` synchronizes four MBID tags.
- Valid with: `--write` or `--all`.
- Invalid with: `--identity`, `--apply`, or `--partial`.
- Common block: incoherent database identity or unsupported filesystem/file.

```bash
beet nm --identity-tags album:"Example Album"
```

## `--write`

- Type: boolean permission flag; default off.
- Mode: ordinary metadata requires `--apply`; legacy identity synchronization requires `--identity-tags`.
- Query: required unless `--all` is used.
- Network/analysis: does not enable or expand CAA lookup, image selection, or Librosa work.
- Database: ordinary changes come from `--apply`; successful file replacement also updates Item `mtime`.
- Files: verified replacement using only the already prepared plan, including BPM tags and one primary front image; legacy identity mode still writes exactly four MBID tags.
- Invalid without: either ordinary `--apply` or `--identity-tags`.
- Common block: candidate round trip or required filesystem guarantee fails.

```bash
beet nm --apply --write album:"Example Album"
```

## Invalid Combinations

| Invalid input | Result |
| --- | --- |
| `--partial` without `--apply` | `--partial requires --apply` |
| ordinary `--write` without `--apply` | `--write requires --apply for ordinary metadata` |
| `--identity --identity-tags` | modes are mutually exclusive |
| `--acoustid --identity` | AcoustID and identity are mutually exclusive |
| `--acoustid --identity-tags` | AcoustID and identity tags are mutually exclusive |
| `--acoustid --write` | AcoustID cannot use file-write authority |
| `--acoustid --partial` | AcoustID has no partial mode |
| `--fingerprint-missing` without `--acoustid` | fingerprint permission requires AcoustID mode |
| `--identity-tags --apply` | identity tags cannot use apply |
| `--identity-tags --partial` | identity tags cannot use partial |
| `--identity --partial` | identity cannot use partial |
| `--identity --write` | identity file sync requires `--identity-tags --write` instead |
| query plus `--all` | choose query or all, not both |
| no query and no `--all` | mode-specific query requirement |

Invalid combinations fail before provider, library-selection, or file work.
Noqlen has no `--force`.
