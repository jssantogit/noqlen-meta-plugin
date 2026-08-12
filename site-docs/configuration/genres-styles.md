# Genres & Styles

Genres are classified labels; styles preserve ordered source style or subgenre
detail as a lossless multivalued field.

```yaml
fields:
  genres: true
  styles: true
genres:
  num_genres: 1
  promote_styles: true
```

The default keeps at most one independently supported genre. Set `num_genres`
from 1 through 10 when you want more supported results. Noqlen does not add
broad parent genres just to reach the limit.

With `promote_styles: true`, a Discogs style recognized by Noqlen's packaged
taxonomy may also participate in genre resolution. The value remains in
`styles`, so promotion does not discard the original style meaning.

Provider enablement, confidence, and existing-value preservation still apply.
See the [Configuration Reference](../technical-reference/configuration.md#genre-classification)
for the exact contract.
