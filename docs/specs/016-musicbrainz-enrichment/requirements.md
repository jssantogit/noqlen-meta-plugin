# Requirements - Anchored MusicBrainz Release Enrichment

- Add disabled-by-default MusicBrainz configuration without credentials.
- Accept only validated canonical `musicbrainz.release` UUIDs already carried by selected
  `AlbumInfo` or persistent `Album` context.
- Perform one direct beets `MusicBrainzAPI.get_release` lookup with explicit `labels` and `media`
  includes; never search or fuzzy-match.
- Emit only labels, catalog numbers, barcodes, country, exact release year, and media.
- Preserve structured multi-values, provenance, response identity integrity, and fail-open external
  service handling.
- Activate existing capability gating and Field Authority without changing mapping or write policy.
- Keep default tests offline with one opt-in public-release smoke test.
