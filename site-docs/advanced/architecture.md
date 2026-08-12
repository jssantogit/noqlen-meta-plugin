# Architecture

Noqlen separates evidence collection from mutation:

```text
providers and optional local analysis
-> normalized release, track, artist, artwork, and tempo evidence
-> per-field authority and resolution
-> canonical target-aware plans
-> beets database, selected importer metadata, artwork, or file mapping
-> explicit application boundary
```

Provider adapters declare release, track, or artist scope and current field
capability. Orchestration calls a source only when enablement, requested fields,
authority, capability, and available identity intersect.

Resolution compares structured candidates with canonical current values and
produces explicit outcomes without acquiring write authority. Target mapping
then asks whether an importer release/track, persistent Album/Item, artwork
target, or supported media file can represent a proposal losslessly.

Application is the final explicit boundary. Importer application mutates only
metadata selected by beets. Ordinary library application handles eligible
Albums and singleton Items. Artwork and BPM use dedicated preparation and
verification. Identity database repair, AcoustID persistence, ordinary file
sync, and identity-tag replacement retain separate application units.
