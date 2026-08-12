# Provider Problems

## Credentials and Dependencies

- Discogs search needs the optional Discogs client and generally
  `NOQLENMETA_DISCOGS_TOKEN`; direct release-ID lookup can work without a token.
- Last.fm uses beets' shared API key rather than a Noqlen token setting.
- LRCLIB, MusicBrainz enrichment, iTunes, and Cover Art Archive need no plugin
  API key.

Never put a real token in documentation, output, or a committed config file.

## Identity Prerequisites

MusicBrainz semantic enrichment follows exact existing Release, Recording,
Work, and Artist IDs. CAA needs exact album identity. Missing identity can mean
the provider is correctly unavailable rather than broken.

## Scope and Field Mismatch

Enabling a provider does not make it support every field. For example, iTunes
does not supply moods, and CAA does not supply singleton artwork. Check
[Providers](../configuration/providers.md) for practical scope.

## Network Outcomes

Timeouts, service errors, and no exact result are isolated where safe. Other
eligible providers may continue. Preview reports sanitized warnings rather than
raw provider exceptions or credentials.
