# Provider Authority and Resolution

Three conditions intersect before a provider can contribute:

1. the field is enabled;
2. the provider is enabled and supports the target scope and field;
3. the provider appears in field authority and meets confidence.

Authority is preference order, not a contest for the largest numeric
confidence. After candidates meet the field threshold, the highest-authority
eligible source wins.

An authority override replaces the built-in order for that field. It does not
enable providers, add capabilities, or grant writes. `preserve_existing: false`
can turn a qualified existing-value conflict into a proposal, but still grants
no mutation authority.

MusicBrainz semantic enrichment under `providers.musicbrainz.enabled` is
separate from MusicBrainz identity audit. Configure examples in
[Advanced Resolution](../configuration/advanced-resolution.md); exact paths are
in the [Configuration Reference](../technical-reference/configuration.md).
