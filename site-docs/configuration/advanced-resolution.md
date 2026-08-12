# Advanced Resolution

Most users do not need manual resolution configuration. Built-in authority,
confidence, and preservation defaults are designed for normal use.

`authority` changes provider order for a named field. It does not enable the
provider or add a capability:

```yaml
resolution:
  authority:
    genres: [musicbrainz, discogs, lastfm, itunes]
```

`min_confidence` can require stronger evidence:

```yaml
resolution:
  min_confidence:
    genres: 0.85
```

`preserve_existing` defaults true. Setting it false allows qualified evidence
to replace a conflicting current value, but it grants no write permission and
does not bypass review, mapping, or identity rules.

Exact accepted provider/field names and validation rules are in the
[Configuration Reference](../technical-reference/configuration.md#resolution-controls).
