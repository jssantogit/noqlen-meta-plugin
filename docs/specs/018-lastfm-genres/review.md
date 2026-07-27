# Review - Conservative Last.fm Genre Enrichment

## Review focus

- Confirm no raw Last.fm tag can bypass weight and packaged-vocabulary filtering.
- Confirm only genres are declared/emitted and styles/mood cannot invoke the adapter.
- Confirm the API key cannot appear in provenance, logs, previews, exceptions, fixtures, or docs.
- Confirm request identity, `autocorrect=0`, pacing, cache lifetime, and response bounds.
- Confirm default/custom authority behavior without resolver changes.
- Confirm importer and CLI reuse existing planning/application paths with no file-write change.

## Status

Implementation review is pending after validation and push.
