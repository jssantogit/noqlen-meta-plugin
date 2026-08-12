# Analyze BPM Locally

Install the optional audio backend:

```bash
pip install "beets-noqlenmeta[audio]"
```

Enable both BPM handling and local calculation:

```yaml
noqlenmeta:
  fields:
    bpm: true
  local_analysis:
    bpm:
      enabled: true
      analysis_mode: full
      window_seconds: 90
```

Preview one target:

```bash
beet nm title:"Example Track"
```

Librosa is the only current local backend; there is no external BPM provider.
Existing BPM is preserved by default. Set `bpm.recalculate_existing: true` only
when recalculation is intended.

Use `--apply` to persist the prepared BPM and `--apply --write` to synchronize a
supported canonical BPM tag. `--write` never starts a new analysis pass.
