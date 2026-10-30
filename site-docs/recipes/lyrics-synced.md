# Add plain and synchronized lyrics

**Goal:** retrieve available lyrics for one track and, when the source
provides them, create an accompanying `.lrc` file without overwriting
an existing one.

**Needs:** beets with a known track and internet access. LRCLIB requires
no API key. `synced_lyrics` and `lyrics` are separate switches.

## Configure both the field and source

In your existing beets `config.yaml`, merge this block under your **single**
`noqlenmeta:` section:

```yaml
noqlenmeta:
  fields:
    lyrics: true
    synced_lyrics: true
  providers:
    lrclib:
      enabled: true
```

The [copyable profile](../examples/lyrics-config.yaml) includes the beets
plugin-list entry. Preserve the other fields and providers you already use.

## Preview one track

```bash
beet nm title:"Example Track"
```

Replace `Example Track` with a title in your library. The preview may fetch
lyrics but does **not** create, replace or embed files.

If the result is safe, apply it:

```bash
beet nm --apply title:"Example Track"
```

Depending on the available evidence, ordinary lyrics can be stored in
supported metadata, while synchronized lyrics can create a guarded `.lrc`
file alongside the actual audio Item in the existing-library workflow.

**Important:** no sidecar is guaranteed for every track. The provider must
supply synchronized timestamps and Noqlen must verify a safe, absent
destination. If a sidecar exists or the data conflicts, it is preserved or
sent for review. This is **not** embedded SYLT support.

## Common problems

| Symptom | What to check |
| --- | --- |
| No lyrics proposed | Track identifiers, LRCLIB coverage, network connection |
| Plain text but no `.lrc` | Source might have plain lyrics only |
| REVIEW or BLOCKED | Existing sidecar, uncertain match, path or write restrictions |
| Lyrics in database but absent in player | The player might need embedded tags or a rescan |

See [Lyrics & Languages](../configuration/lyrics-languages.md),
[Data destinations](../concepts/data-destinations.md), and
[Provider troubleshooting](../troubleshooting/providers.md).
