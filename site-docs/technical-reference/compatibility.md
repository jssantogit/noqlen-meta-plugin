# Compatibility

You will distinguish general plugin support from the narrower identity-tag
filesystem workflow.

## Python

Python 3.10 through 3.14 are supported and covered by release CI. Package
metadata declares `Requires-Python >=3.10,<3.15`. Python 3.15 is not claimed by
Noqlen Meta; supporting a future Python release requires a new package
release after compatibility is tested.

## beets

The declared and tested range is `beets>=2.12,<3`:

| Boundary | Release validation |
| --- | --- |
| Minimum | beets 2.12 |
| Latest compatible | newest available beets below 3 |

The focused compatibility jobs install these boundaries explicitly. Noqlen
uses beets plugin discovery, importer selected metadata, native query APIs,
database models, and MediaFile mappings; it does not patch beets.

## Operating Systems And Filesystems

Ordinary preview and database identity operations are Python/beets-based.
Ordinary `--apply` may write verified artwork sidecars, and ordinary
`--apply --write` may perform verified supported audio-file synchronization.

The identity-tag filesystem workflow is supported only on platforms where
its required no-atime/no-follow and atomic replacement guarantees can be
proven. It relies on `O_NOATIME`, `O_NOFOLLOW`, same-directory candidate and
backup files, atomic `os.replace`, regular single-link source files, and safe
metadata preservation. Unsupported operating systems, permissions, files, or
filesystems block before writing. Windows and macOS identity-tag support is not
claimed.

Preview can identify an unsupported source, but only a real `--write`
candidate round trip proves write capability for that file.

## Media Formats

Real synthetic-media round trips are covered for:

| Format | Tested container/extension |
| --- | --- |
| FLAC | `.flac` |
| MP3 | `.mp3` |
| M4A/MP4 audio | `.m4a` |
| Ogg Vorbis | `.ogg` |
| Opus | `.opus` |

This is not a claim that every MediaFile codec or container can use the safe
identity-tag workflow.

## Navidrome

Navidrome compatibility is an indirect workflow: beets database change, then
appropriate file-tag synchronization, then a Navidrome rescan. Noqlen does not
call Navidrome, certify a Navidrome version, or control its cache/scan timing.


## V3 regression coverage and limitations

V3 release CI tested reopening an existing V2-typed beets library,
preserving native/typed multivalues, and extending the Item schema without
destroying earlier values. The audio-proxy `--apply --write` path is tested
against synthetic FLAC, MP3, M4A, Ogg and Opus fixtures, asserting **byte-for-byte
unchanged audio files** when the only new data belongs to the beets database.

These tests do not prove every codec, filesystem, community plugin combination
or real-world catalog quality. Human-labelled perceptual validity is not claimed
for RMS Energy or rhythmic Danceability. Disc-surface artwork is deferred.
