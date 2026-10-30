# Glossary: Noqlen and beets vocabulary

Use this page when a term appears before you know what it means.

| Term | Meaning here |
| --- | --- |
| **beets** | The library manager that imports, matches and stores your music. Noqlen is its plugin. |
| **Album** | A release or album entity in the beets library database. |
| **Item** | One audio track stored in the beets library. |
| **Recording** | The MusicBrainz identity of a particular recorded performance. |
| **Work** | The underlying musical composition, which may have several Recordings. |
| **Release** | A specific edition of an album; distinct from its Release Group. |
| **Release Group** | MusicBrainz's grouping of related editions of the same album. |
| **Provider** | An online source such as MusicBrainz, LRCLIB, Discogs or Cover Art Archive. |
| **Field** | A kind of metadata that may be enriched, e.g. `genres` or `lyrics`. |
| **Local analysis** | Optional audio processing from your own files, e.g. BPM or Key. |
| **Preview** | A read-only proposal; it may use network sources but doesn't change the library or files. |
| **`KEEP`** | Existing value is retained. |
| **`PROPOSE`** | Noqlen has a candidate worth considering. |
| **`REVIEW`** | Ambiguous or insufficient evidence requires investigation. |
| **`BLOCKED`** | Safety, mapping or compatibility rule prevents a change. |
| **Sidecar** | A separate file next to audio (e.g. `cover.jpg` or `.lrc`). |
| **Media tag** | Metadata stored inside an MP3, FLAC or other supported audio file. |
| **MBID** | A MusicBrainz identifier for a Release, Release Group, Recording, track or Work. |
| **Typed field** | A value stored with an explicit data type in beets or plugin-owned storage. |
| **No-clobber** | A safety policy that doesn't overwrite an existing sidecar without approved conditions. |
| **Proxy metric** | A documented signal measurement; not necessarily a validated perceptual score. |

An identity ID, a track title, and a provider search suggestion are **not**
equivalent evidence. Noqlen deliberately abstains when it cannot show an
unambiguous, safe result.

For more details, see the
[configuration mental model](mental-model.md) and
[provider authority](../advanced/provider-authority-resolution.md).
