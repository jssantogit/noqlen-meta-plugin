# BPM

The field switch permits BPM handling, but it does not enable calculation:

```yaml
fields:
  bpm: true
```

To calculate missing BPM locally, install the optional dependency and opt in:

```bash
pip install "beets-noqlenmeta[audio]"
```

```yaml
local_analysis:
  bpm:
    enabled: true
    analysis_mode: full
    window_seconds: 90
```

Librosa is the only current local backend. There is no external BPM provider.
Analysis is disabled by default and existing BPM is preserved by default.

The `bpm` block can enable `recalculate_existing`, round before persistence, or
normalize by powers of two into a configured positive range. Analysis mode is
`full` or one centered `window`; `window_seconds` defaults to 90.

Adding `--write` does not start analysis. It can only synchronize an already
prepared canonical BPM. See the [Configuration Reference](../technical-reference/configuration.md#artwork-and-bpm).
