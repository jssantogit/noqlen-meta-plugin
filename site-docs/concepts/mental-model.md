# How Noqlen decides what to enrich

Think of Noqlen as a **careful assistant to beets**, not an automatic tag
replacer. beets selects the album/recording; Noqlen looks for additional
information and proposes changes that can be represented safely.

## Four decisions, in order

```text
1. WHAT information?       fields
2. WHERE does it come from? providers / local_analysis
3. IS the evidence safe?    identification, resolution, preservation
4. WHAT may be changed?     preview -> --apply -> optional --write
```

**1. Fields** choose metadata categories. A field set to `true` permits
considering that category, but does not guarantee a result. Example:
`fields.lyrics: true`.

**2. Sources** supply evidence. `providers.lrclib.enabled: true` permits
online lyrics lookup; `local_analysis.bpm.enabled: true` permits decoding
your own audio to estimate BPM. A field switch does **not** activate an
analyzer by itself.

**3. Evidence and safety** determine whether Noqlen keeps, proposes,
requests review or blocks a change. It can abstain if IDs are absent, providers
disagree or a value cannot be stored without losing information.

**4. Permissions** determine the result. Preview changes nothing. Application
may update beets' library database and authorized verified sidecars.
`--apply --write` may additionally synchronize supported media tags.

## One concrete example: lyrics

The *same* settings block must name both the desired field and the provider:

```yaml
noqlenmeta:
  fields:
    lyrics: true
  providers:
    lrclib:
      enabled: true
```

Then choose one track to preview:

```bash
beet nm title:"Example Track"
```

Only after inspecting a proposal should you use
`beet nm --apply title:"Example Track"`.

## One exception: V3 local audio analysis needs two opt-ins

For musical Key, the `key` field and `local_analysis.key` must **both** be
enabled; the optional `[audio]` package extra is also required.

```yaml
noqlenmeta:
  fields:
    key: true
  local_analysis:
    key:
      enabled: true
      analysis_mode: window
      window_seconds: 90
```

Energy and Danceability use `local_analysis.audio_features` similarly.
Their results are measurement proxies, not perceptual labels.

## Two workflows that must not be confused

| | Existing library (`beet nm`) | During import (beets importer) |
| --- | --- | --- |
| What is selected? | Native beets album/track query | The match chosen by beets |
| Preview control | No `--apply` flag | `noqlenmeta.preview` |
| Apply control | `--apply` CLI flag | `noqlenmeta.apply` |
| File tags | `--apply --write` where supported | Normal beets importer `import.write` controls eventual writing |
| Identity audit | Separate `--identity` mode | Separate `identity` configuration |

Enabling `providers.musicbrainz.enabled` does **not** enable identity
repair. Identity, AcoustID and ordinary enrichment have separate authorities.

See [Database vs File Tags](data-destinations.md),
[Importer recipe](../recipes/import-enrichment.md), and
[full configuration reference](../technical-reference/configuration.md).
