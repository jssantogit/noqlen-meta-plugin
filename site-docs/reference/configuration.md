# Configuration Reference

You will find every public Noqlen Meta YAML key, its default, users, effects,
and write authority. The canonical complete example is
[`full-config.yaml`](../examples/full-config.yaml).

All paths below are relative to the beets configuration root and begin with
`noqlenmeta`.

## Importer Controls

### `noqlenmeta.preview`

- Type: boolean. Default: `true`. Accepted: `true`, `false`.
- Used by: importer ordinary release and selected-track enrichment only.
- Effect: renders importer ordinary plans when work is eligible.
- Grants writes: no.
- Interaction: independent of `noqlenmeta.apply`; neither setting controls the library command.
- Example: `preview: true`.

### `noqlenmeta.apply`

- Type: boolean. Default: `false`. Accepted: `true`, `false`.
- Used by: importer ordinary release and selected-track enrichment only.
- Effect: permits guarded mutation of metadata already selected by beets.
- Grants writes: selected importer metadata only; not direct database or file writes.
- Interaction: final persistence and tag writing remain normal beets importer behavior.
- Example: `apply: true`.

### `noqlenmeta.apply_mode`

- Type: string. Default: `strict`. Accepted: `strict`, `partial`.
- Used by: importer ordinary enrichment only.
- Effect: classifies selected release/track ordinary metadata application.
- Grants writes: no; `noqlenmeta.apply: true` is still required.
- Does not affect: `beet nm --apply`, identity, or identity-tag modes.
- Example: `apply_mode: partial`.

The value is normalized for surrounding whitespace and case when importer
application is enabled. Invalid values stop application.

## Importer Identity Controls

| Path | Type | Default | Used by | Effect and interaction |
| --- | --- | --- | --- | --- |
| `noqlenmeta.identity.enabled` | boolean | `false` | Identity importer | Master gate for identity audit; separate from enrichment provider settings. |
| `noqlenmeta.identity.preview` | boolean | `true` | Identity importer | Renders identity audit when enabled; grants no writes. |
| `noqlenmeta.identity.apply` | boolean | `false` | Identity importer | Permits coherent selected-metadata repair; requires `identity.enabled: true`. |

Accepted values are `true` or `false`. These keys do not control the library
`--identity` command. Identity importer repair mutates selected `AlbumInfo` and
`TrackInfo` only; beets owns later persistence and file behavior.

`providers.musicbrainz.enabled` neither enables nor disables identity audit.

```yaml
identity:
  enabled: true
  preview: true
  apply: false
```

## AcoustID Controls

AcoustID is recording-identity evidence for existing-library workflows. It is
not an importer metadata provider. All settings are validated before target,
backend, credential, or network work.

| Path | Type | Default | Effect |
| --- | --- | --- | --- |
| `noqlenmeta.acoustid.enabled` | boolean | `false` | Enables optional AcoustID evidence in `--identity`; standalone `--acoustid` is explicit authority. |
| `noqlenmeta.acoustid.reuse_existing` | boolean | `true` | Reuses a valid stored fingerprint; a stored AcoustID ID is not fresh evidence. |
| `noqlenmeta.acoustid.compute_missing` | boolean | `false` | Permits standalone missing-fingerprint calculation; never permits it in `--identity`. |
| `noqlenmeta.acoustid.lookup` | boolean | `true` | Permits lookup when valid fingerprint material exists. |
| `noqlenmeta.acoustid.use_for_identity` | boolean | `true` | Allows decisive evidence to filter MusicBrainz candidates when AcoustID is enabled. |
| `noqlenmeta.acoustid.min_score` | finite number | `0.90` | Inclusive AcoustID result threshold from `0.0` through `1.0`. |
| `noqlenmeta.acoustid.min_margin` | finite number | `0.05` | Inclusive unique-recording margin from `0.0` through `1.0`. |
| `noqlenmeta.acoustid.max_results` | integer | `5` | Retains from `1` through `20` result groups. |
| `noqlenmeta.acoustid.max_recordings_per_result` | integer | `10` | Retains from `1` through `50` recording MBIDs per result. |
| `noqlenmeta.acoustid.timeout_seconds` | finite number | `15.0` | Backend/request timeout from `1.0` through `60.0` seconds. |
| `noqlenmeta.acoustid.requests_per_second` | finite number | `3.0` | Positive process-local ceiling, at most `3.0`. |
| `noqlenmeta.acoustid.cache_entries` | integer | `256` | Process-local lookup cache size from `0` through `4096`. |
| `noqlenmeta.acoustid.fpcalc` | non-empty string | `fpcalc` | Executable used only for authorized calculation. |

The AcoustID client key is available exclusively through
`NOQLENMETA_ACOUSTID_API_KEY`; there is no credential setting in YAML.

## Field Controls

Every field key is boolean, accepts `true` or `false`, grants no write
permission, and is used only where a provider scope and lossless target mapping
exist. Enabling a field does not guarantee an enabled provider can supply it.

| Path | Default | Importer use | Ordinary library use | Important interaction |
| --- | ---: | --- | --- | --- |
| `noqlenmeta.fields.genres` | `true` | Release | Album | Discogs, Last.fm, iTunes; list mapping. |
| `noqlenmeta.fields.styles` | `true` | Release | Album | Discogs; typed plural storage is lossless and legacy `style` is a read fallback. |
| `noqlenmeta.fields.labels` | `true` | Release | Album | Discogs/MusicBrainz; multiple values can block singular targets. |
| `noqlenmeta.fields.catalog_numbers` | `true` | Release | Album | Discogs/MusicBrainz; multiple values can block. |
| `noqlenmeta.fields.barcodes` | `true` | Release | Album | Discogs/MusicBrainz; multiple values can block. |
| `noqlenmeta.fields.country` | `true` | Release | Album | Discogs/MusicBrainz; iTunes storefront is not release country. |
| `noqlenmeta.fields.year` | `true` | Release | Album | MusicBrainz, Discogs, iTunes. |
| `noqlenmeta.fields.media` | `true` | Release | Preview/block | Importer target exists; persistent Album target does not. |
| `noqlenmeta.fields.format_descriptions` | `true` | Preview/block | Preview/block | Discogs can supply it; v1 has no lossless ordinary target. |
| `noqlenmeta.fields.moods` | `true` | Typed track target | Typed Item target | Semantic mood providers/normalization are deferred. |
| `noqlenmeta.fields.bpm` | `true` | Numeric track target | Built-in Item target | Foundation adds no provider or local analyzer. |
| `noqlenmeta.fields.lyrics_languages` | `true` | Typed track target | Typed Item target | MusicBrainz Work lookup is deferred. |
| `noqlenmeta.fields.artist_countries` | `true` | Typed release/track targets | Typed Album/Item targets | Artist API lookup is deferred. |
| `noqlenmeta.fields.artist_areas` | `false` | Typed release/track targets | Typed Album/Item targets | Artist API lookup is deferred. |
| `noqlenmeta.fields.artist_languages` | `true` | Typed release/track targets | Typed Album/Item targets | Semantic derivation is deferred. |
| `noqlenmeta.fields.lyrics` | `false` | Selected tracks | Items | LRCLIB plain lyrics use shared import/library resolution. |
| `noqlenmeta.fields.synced_lyrics` | `false` | Preview/block | Preview/block | No lossless synchronized-lyrics target is delivered. |
| `noqlenmeta.fields.cover` | `true` | None currently | None currently | CAA/download/embed are deferred. |

Example:

```yaml
fields:
  genres: true
  lyrics: false
```

Field settings do not control identity importer, identity library, or
identity-tag commands, whose four fields are fixed.

## Provider Controls

Every `enabled` key is boolean, accepts `true`/`false`, and grants no write
permission. Release providers are used by importer release
enrichment and ordinary library mode. LRCLIB is used only for selected importer
tracks and existing-library Items. No provider key controls identity-tag mode.

| Path | Type | Default | Effect and dependencies |
| --- | --- | --- | --- |
| `noqlenmeta.providers.discogs.enabled` | boolean | `false` | Enables release collection when field authority intersects Discogs capability; search needs the optional Discogs dependency. |
| `noqlenmeta.providers.discogs.user_token` | string | empty | Optional Discogs token; redacted; a non-empty `NOQLENMETA_DISCOGS_TOKEN` environment value takes precedence. |
| `noqlenmeta.providers.musicbrainz.enabled` | boolean | `true` | Enables safe zero-credential exact-release-MBID enrichment only; does not control identity audit. |
| `noqlenmeta.providers.lastfm.enabled` | boolean | `false` | Enables filtered album genres; uses the API key current beets shares with plugins. |
| `noqlenmeta.providers.itunes.enabled` | boolean | `false` | Enables album genres/year from the public search API. |
| `noqlenmeta.providers.itunes.storefront` | string | `us` | Two ASCII letters such as `us`, `gb`, or `jp`; normalized lowercase when iTunes is used. |
| `noqlenmeta.providers.lrclib.enabled` | boolean | `false` | Enables exact-signature selected-track lookup; no API key. |

## Local Analysis Structure

- `noqlenmeta.local_analysis.bpm.enabled`: boolean, default `true`.
- `noqlenmeta.local_analysis.bpm.mode`: string, currently `fallback`.
- `noqlenmeta.local_analysis.mood.enabled`: boolean, default `false`.

These are validated Foundation settings. They do not run analysis in this
change: no BPM backend, `[audio]` dependency, or local mood model is included
yet. `--write` never activates analysis.

Token example without a secret value:

```yaml
providers:
  discogs:
    enabled: true
    user_token: ""
```

Prefer setting `NOQLENMETA_DISCOGS_TOKEN` in the process environment. Never
commit a real token. Direct Discogs release-ID lookup does not require a token;
search generally does.

## Resolution Controls

These three mapping settings are used by importer ordinary enrichment and the
ordinary library command. They are not used by either identity mode and grant
no write permission.

### `noqlenmeta.resolution.authority`

- Type: mapping from field name to a non-empty ordered list of current provider names.
- Default: `{}` (all fields use built-in authority).
- Accepted providers: `discogs`, `musicbrainz`, `lastfm`, `itunes`, `lrclib`.
- Effect: replaces the built-in provider order for each named field.
- Validation: field/provider names must be known and unique after normalization.
- Interaction: does not enable providers or add capabilities.

```yaml
authority:
  genres: [discogs, lastfm, itunes]
```

### `noqlenmeta.resolution.min_confidence`

- Type: mapping from field name to finite number.
- Default: `{}`; built-in threshold is `0.8` for each field.
- Accepted range: inclusive `0.0` through `1.0`; booleans are invalid.
- Effect: candidates below the field threshold are ineligible.
- Grants writes: no.

```yaml
min_confidence:
  genres: 0.85
```

### `noqlenmeta.resolution.preserve_existing`

- Type: mapping from field name to boolean.
- Default: `{}`; built-in behavior is `true` for each field.
- Accepted: `true`, `false`.
- Effect: when false, a qualified candidate may replace a conflicting current value without `REVIEW`.
- Grants writes: no; importer still needs `apply: true`, and the library command still needs `--apply`.

```yaml
preserve_existing:
  year: false
```

## Complete Examples

- [`minimal-config.yaml`](../examples/minimal-config.yaml) is the safe starting point.
- [`full-config.yaml`](../examples/full-config.yaml) contains every public key exactly once with valid values.

The full example is illustrative, not a recommendation to enable every
provider or field. AcoustID has no audio-file write authority. Ordinary file
replacement requires `--apply --write`; legacy `--identity-tags --write`
authority remains unchanged.
