# BPM

BPM has two separate decisions: **may Noqlen handle BPM?** and **may Noqlen
calculate it from the audio file?**

## Enable the BPM field

```yaml
fields:
  bpm: true
```

This permits BPM enrichment and synchronization. It does not start audio
analysis. The field is enabled by default.

## Enable local calculation

Install the optional audio dependency:

```bash
pip install "beets-noqlenmeta[audio]"
```

Then opt in:

```yaml
local_analysis:
  bpm:
    enabled: true
    analysis_mode: full
    window_seconds: 90
```

Librosa is the only current local BPM backend. There is no external BPM
provider.

### Local-analysis options

| Setting | Default | What it does |
| --- | ---: | --- |
| `enabled` | `false` | Allows Noqlen to calculate BPM locally when analysis is needed. |
| `analysis_mode` | `full` | `full` analyzes the track; `window` analyzes one centered window. |
| `window_seconds` | `90` | Length of the centered analysis window when `analysis_mode: window` is used. |

Example for a centered 60-second window:

```yaml
local_analysis:
  bpm:
    enabled: true
    analysis_mode: window
    window_seconds: 60
```

## Control how BPM is stored

```yaml
bpm:
  round: false
  recalculate_existing: false
  octave_normalization: false
  octave_range:
    min: 70
    max: 180
```

| Setting | Default | What it does |
| --- | ---: | --- |
| `round` | `false` | Rounds the canonical BPM before persistence. Useful when a target format cannot preserve a fractional BPM. |
| `recalculate_existing` | `false` | When `false`, an existing BPM is preserved and normally avoids analysis. Set `true` only when you intentionally want it recalculated. |
| `octave_normalization` | `false` | Allows multiplication or division by powers of two to move BPM into the configured range. |
| `octave_range.min` | `70` | Lower bound used when octave normalization is enabled. |
| `octave_range.max` | `180` | Upper bound used when octave normalization is enabled; it must be greater than `min`. |

For example, to normalize octave-equivalent estimates into 70–180 BPM while
still preserving existing values:

```yaml
bpm:
  recalculate_existing: false
  octave_normalization: true
  octave_range:
    min: 70
    max: 180
```

## Preview, apply, and write

Local analysis happens while Noqlen prepares enrichment evidence, not because
`--write` was added. Preview lets you inspect the prepared BPM first. `--apply`
can persist the approved database value, and `--apply --write` can additionally
synchronize that already-prepared BPM to supported audio tags.

See the [Configuration Reference](../technical-reference/configuration.md#artwork-and-bpm)
for exact validation rules.
