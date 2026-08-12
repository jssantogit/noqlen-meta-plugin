# Enrich an Existing Library

## 1. Choose Fields and Providers

```yaml
noqlenmeta:
  fields:
    genres: true
    styles: true
    moods: true
  providers:
    musicbrainz:
      enabled: true
```

## 2. Preview One Album

```bash
beet nm album:"Discovery"
```

Inspect every `KEEP`, `PROPOSE`, `REVIEW`, and `BLOCKED` result.

## 3. Apply and Optionally Write

```bash
beet nm --apply album:"Discovery"
beet nm --apply --write album:"Discovery"
```

Use the second command only when supported prepared metadata should also reach
audio files. Adding `--write` does not repeat provider or analyzer work.

Ordinary library mode supports eligible Albums and standalone singleton Items.
Track providers such as LRCLIB can contribute to Items when enabled; album-only
features such as covers remain album-only.

## 4. Scale Up

Move to a broader artist query or preview `beet nm --all`. Follow the same
preview, inspect, apply, optional-write progression.
