# Handoff

## State

Block 007 adds Apple's public iTunes Search API as the second production provider. Discogs and iTunes
are independently gated and failure-isolated, then all successful candidates enter one existing Field
Authority resolver pass. The selected import state remains unchanged.

## Completed

- `ITunesProvider` supports positive `itunes.collection` lookup, UPC lookup, and one bounded album
  search against a validated two-letter storefront.
- Artist/title and useful year checks conservatively select one collection; ambiguity emits nothing.
- iTunes emits only tuple-shaped genres and integer year with collection ID/public URL provenance.
- Store-facing country, lookup barcode, copyright, artwork, and previews do not become candidates.
- Configuration adds disabled `providers.itunes` with storefront `us`; Discogs remains disabled too.
- Provider contribution checks prevent unnecessary I/O, including iTunes when only styles is enabled.
- Discogs and iTunes failures are isolated while successful candidates continue to one resolver pass.
- Existing authority chains are unchanged: Discogs genres beat higher-confidence iTunes genres, and
  iTunes wins when the higher-authority candidate is absent.
- Preview branding renders `iTunes`; `AlbumInfo`, choice, match, and items remain unchanged.

## Important decisions

- The integration remains explicit for two providers; no dynamic provider registry was introduced.
- Provider-local confidence determines eligibility but cannot outrank per-field authority.
- iTunes HTTP uses only the standard library with fixed safe errors and bounded response handling.
- Resolution creates preview decisions only and never writes.

## Deferred

- Metadata change plans/application, provenance persistence, and field-specific merge policy.
- `beet noqlenmeta` and preferred `beet nm` alias.
- Confidence calibration, artwork, previews, lyrics, and additional provider adapters.

## Recommended next block

Review Block 007 independently before selecting another scoped block. Do not assume metadata writes,
another provider, artwork, lyrics, or CLI work is next.
