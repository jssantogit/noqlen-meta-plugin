# Compatibility

You will distinguish general plugin support from the narrower identity-tag
filesystem workflow.

## Python

Python 3.10 through 3.14 are supported and covered by release CI. Package
metadata declares `Requires-Python >=3.10,<3.15`. Python 3.15 is not claimed by
Noqlen Meta 2.0.0; supporting a future Python release requires a new package
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
