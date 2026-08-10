# Noqlen Meta v2 Genre Foundation Design

Status: user-approved architecture supplement for the v2 Foundation.

This document extends the approved Noqlen Meta v2 enrichment design with a dedicated genre-classification foundation. It exists because genre behaves differently from scalar or provider-owned metadata: multiple sources can contribute complementary evidence, community tags contain substantial noise, Discogs intentionally separates broad genres from specific styles, and a useful zero-config experience must not depend on the external beets LastGenre plugin or its packaged vocabulary.

The implementation remains part of the v2 Foundation only where it establishes durable domain, taxonomy, resolution, configuration, and test boundaries. Online provider behavior that actually produces the new evidence remains Semantic Enrichment work.

## Objective

Noqlen Meta should classify musical genres more accurately than a simple single-provider or Last.fm-tag workflow while remaining predictable, dependency-light, and independently usable as one beets plugin.

The genre system must:

- work without enabling or installing beets LastGenre;
- use a Noqlen-owned packaged genre vocabulary at runtime;
- produce one final genre by default;
- support a configurable number of final genres without automatically inserting broad parent categories;
- allow recognized Discogs styles to contribute genre evidence while preserving those values in `styles`;
- combine corroborating evidence from multiple providers instead of selecting one provider tuple atomically;
- prefer trustworthy track-level evidence over release/album evidence, and release/album evidence over artist evidence;
- keep provider collection separate from genre classification and persistence;
- remain deterministic and explainable.

## Non-goals

- Do not require LastGenre or copy its runtime vocabulary.
- Do not download or refresh the genre taxonomy during ordinary plugin execution.
- Do not build or maintain a full genre-family tree such as `Metal -> Death Metal -> Technical Death Metal`.
- Do not add broad parents automatically merely because a specific genre is selected.
- Do not expose arbitrary provider weights and tuning knobs as public configuration in the first v2 cut.
- Do not treat moods, artist origin descriptors, social/community labels, eras, platforms, or artist names as genres.
- Do not create a fake `noqlen-genre` provider in the provider registry.
- Do not implement the MusicBrainz `inc=genres`, new Last.fm collection flow, or other online evidence adapters in this Foundation supplement.

## 1. Canonical result semantics

`genres` remains a canonical multivalued metadata field, but the default user-facing result contains one value.

```yaml
genres:
  num_genres: 1
  promote_styles: true
```

`fields.genres` remains the ordinary field enable/disable switch. The separate `genres` section only configures classification behavior and never enables collection on its own.

`num_genres` controls the maximum number of selected genre labels. The accepted range is `1..10`.

Examples:

```text
num_genres: 1
-> Technical Death Metal
```

```text
num_genres: 3
-> Technical Death Metal
-> Death Metal
-> Progressive Metal
```

The resolver must not append `Metal`, `Rock`, `Pop`, or any other parent merely because a selected genre belongs to that musical family. Additional genres appear only when independently supported by eligible evidence and ranked within `num_genres`.

## 2. Packaged Noqlen taxonomy

Noqlen Meta owns the runtime taxonomy used to answer whether a normalized label is a recognized musical genre.

The taxonomy is packaged with the plugin. Its base vocabulary is a reviewed snapshot derived from the public MusicBrainz genre vocabulary, supplemented only by small Noqlen-owned normalization data.

Conceptually:

```text
beetsplug/noqlenmeta/genre_taxonomy/
├── genres.txt
├── aliases.py
└── classifier.py

scripts/
└── update_genre_taxonomy.py
```

The exact internal paths may follow repository conventions, but the responsibilities are fixed:

- `genres.txt`: deterministic packaged snapshot of recognized canonical genre names;
- aliases: common alternate spellings, abbreviations, punctuation forms, and capitalization variants mapped to canonical names;
- classifier: pure runtime classification against the packaged vocabulary;
- update script: development/release helper that fetches the upstream MusicBrainz vocabulary, normalizes/sorts it, and produces a reviewable diff.

Ordinary plugin execution must never require the taxonomy update script or a network request to classify a label.

A taxonomy snapshot identifier must be retained internally for debugging and reproducibility, using a date, content hash, or equivalent immutable identifier. It is not a normal end-user tuning option.

### Alias behavior

Aliases normalize representation; they do not invent genre identity.

Examples include concepts such as:

```text
kpop -> K-pop
K-Pop -> K-pop
rnb -> R&B
r&b -> R&B
dnb -> canonical taxonomy representation of Drum and Bass
```

The packaged taxonomy determines the canonical label. Noqlen-specific aliases point to that canonical identity instead of creating parallel spellings.

## 3. Semantic classification boundary

Raw provider labels pass through one reusable semantic-classification boundary before they can become genre evidence.

```text
raw provider label
       ↓
Unicode/whitespace normalization
       ↓
alias normalization
       ↓
semantic/noise classification
       ↓
packaged genre taxonomy lookup
       ↓
GenreEvidence or discard/non-genre classification
```

The classifier must distinguish at least:

- recognized genre;
- mood descriptor;
- origin/geographic descriptor;
- non-genre descriptor;
- known noise;
- unknown.

Known noise includes categories demonstrated by the Noqlen Forge experience, such as years/decades, personal/favorite tags, platform names, same-as-artist labels, obvious related-artist contamination, Last.fm meta tags, generic terms such as `song`/`track`, and noisy personal phrases.

The Foundation does not need to solve all future mood/origin classification, but its genre boundary must be designed so those labels are not accidentally persisted as genres and can later be routed to dedicated semantic systems.

## 4. Broad categories and specificity

Noqlen Meta does not maintain a complete hierarchical genre ontology.

Instead, it owns a deliberately small set of broad categories used only as a ranking signal. Typical examples include `Pop`, `Rock`, `Metal`, `Electronic`, `Hip Hop`, `R&B`, `Jazz`, `Blues`, `Classical`, `Country`, `Folk`, `Reggae`, and `Latin`.

A recognized genre not listed as broad is treated as specific for ranking purposes.

This allows a defensible comparison such as:

```text
Discogs genre: Rock
Discogs style: Progressive Rock
```

where `Progressive Rock` may outrank `Rock` without requiring Noqlen to encode or infer the complete ancestry of Progressive Rock.

Specificity must never be guessed from string suffixes such as `metal`, `rock`, or `pop`.

## 5. Genre evidence domain

Providers do not directly decide the final `genres` tuple. They contribute normalized evidence.

Conceptually:

```python
@dataclass(frozen=True, slots=True)
class GenreEvidence:
    genre: str
    provider: str
    scope: ProviderScope
    kind: GenreEvidenceKind
    confidence: float
    source_id: str
    source_url: str | None = None
    weight: int | None = None
```

The exact type names may adapt to existing domain conventions, but the semantic fields are required.

`GenreEvidenceKind` contains at least:

```text
GENRE
PROMOTED_STYLE
COMMUNITY_TAG
```

Evidence contains facts about its provenance. It does not contain a fabricated final score, specificity score, or authority points.

`weight` is optional provider-native evidence such as a Last.fm tag count/weight. It must not be repurposed as a universal Noqlen score.

## 6. Discogs style promotion

Discogs preserves its own field semantics:

```text
genres -> Discogs broad genre values
styles -> Discogs style values
```

When `genres.promote_styles` is true, a Discogs style that the Noqlen taxonomy recognizes as a musical genre also emits `GenreEvidence(kind=PROMOTED_STYLE)`.

For example:

```text
Discogs genre = Rock
Discogs style = Technical Death Metal
```

may produce genre evidence for both `Rock` and `Technical Death Metal`, while persistent `styles` still includes `Technical Death Metal`.

This is not considered harmful duplication: `styles` preserves source classification, while `genres` represents Noqlen's resolved navigation/classification result.

A style that is not recognized as a genre must not be promoted merely because Discogs labels it a style.

## 7. Genre resolver

Genre resolution is a dedicated pure component rather than special-case branches embedded throughout `resolve_metadata()`.

Conceptually:

```python
resolve_genres(
    evidence: Sequence[GenreEvidence],
    *,
    num_genres: int,
) -> tuple[str, ...]
```

The resolver has no network access, database access, file writes, or provider object dependencies.

The generic metadata resolver remains responsible for ordinary provider-owned values such as year, country, labels, barcodes, styles, and lyrics. Once the specialized genre path is active, raw provider `genres` tuples must not also be independently resolved by `resolve_metadata()`. Genre evidence is aggregated first and produces the one canonical resolved `genres` value/decision that proceeds into ordinary change planning, database application, and file synchronization.

This keeps the generic resolver free of K-pop aliases, Last.fm noise rules, Discogs style semantics, and provider-specific genre logic while avoiding two competing genre decisions for the same target.

The genre resolver itself is not a provider and must not appear in `ProviderRegistry` or `providers:` configuration.

## 8. Deterministic ranking rules

Genre resolution uses discrete evidence rules rather than a tunable universal numeric score.

The ranking process is:

1. **Semantic validity** — discard labels that are not eligible recognized genres after normalization/classification.
2. **Evidence eligibility** — discard evidence below the reliability threshold appropriate to its kind/provider semantics.
3. **Scope preference among reliable evidence** — prefer `TRACK` over `RELEASE`/album, and release/album over `ARTIST`.
4. **Independent-provider corroboration** — prefer genres confirmed by more distinct providers.
5. **Evidence-kind strength** — use the semantic quality of direct genre evidence, recognized promoted style evidence, and community-tag evidence as a deterministic tie-break signal.
6. **Specificity** — prefer a recognized specific genre over a broad category when the specific evidence is sufficiently reliable.
7. **Provider-native signal** — use native weight/count only where it exists and only as a late tie-breaker among comparable evidence.
8. **Stable canonical order** — resolve otherwise equivalent cases deterministically by canonical representation.

There is intentionally no exposed arithmetic rule such as `MusicBrainz=40 + Discogs=30 + Last.fm=17`.

### Scope does not rescue weak evidence

`Track > Release > Artist` applies only after evidence is eligible.

A weak track-level community tag must not automatically defeat strong corroborated release evidence simply because it is attached to the track. Reliability filtering happens before scope preference.

### Provider independence

Consensus counts distinct providers, not raw evidence records.

Three MusicBrainz observations at track, release-group, and artist scopes remain one provider for corroboration purposes. Likewise, Discogs genre and Discogs promoted style do not count as two independent sources.

## 9. Track, release, and artist behavior

When trustworthy evidence exists at multiple scopes, the most specific musical target wins:

```text
Track > Release/Album > Artist
```

This intentionally permits tracks from one album to resolve to different genres.

Example:

```text
Artist evidence: K-pop
Album evidence:  K-pop
Track evidence:  Drum and Bass

result for that track -> Drum and Bass
```

Release/album or artist evidence remains useful fallback when track evidence is absent or not sufficiently reliable.

The Foundation must preserve the scope in `GenreEvidence`; Semantic Enrichment later decides which MusicBrainz/Last.fm/etc. endpoints contribute evidence at each scope.

## 10. Last.fm independence

The Foundation must remove the current Last.fm provider's runtime lookup of `beetsplug.lastgenre` and its packaged `genres.txt`. Even before the richer Semantic Enrichment collection strategy exists, any current Last.fm genre normalization retained in the Foundation must classify against the packaged Noqlen taxonomy instead.

The Noqlen taxonomy becomes the sole runtime genre-vocabulary dependency.

The better filtering ideas already proven in Noqlen Forge should be retained conceptually:

- normalize common aliases such as K-pop/R&B variants;
- remove years, decades, personal tags, platforms, meta tags, generic labels, obvious artists, and noisy phrases;
- keep semantic categories separate rather than treating every popular Last.fm tag as a genre.

Semantic Enrichment will replace or extend the current album-only Last.fm evidence collection with the appropriate track/release/artist fallback strategy. Only that online collection expansion is deferred; LastGenre vocabulary dependence is not deferred.

## 11. MusicBrainz zero-config direction

MusicBrainz remains the zero-credential semantic backbone.

The Foundation must allow MusicBrainz genre evidence at release, track, and artist scopes, but the actual `inc=genres` API integration is Semantic Enrichment work.

Once implemented, the expected zero-config behavior is:

```text
Noqlen Meta installed
MusicBrainz enabled by default
no API key
       ↓
MusicBrainz genre evidence
       ↓
Noqlen packaged taxonomy + GenreResolver
       ↓
genres
```

Discogs, Last.fm, and iTunes improve or corroborate coverage; they are not required for the genre classifier itself to exist.

## 12. Explainability

Genre resolution must retain enough provenance to explain why a result won without exposing internal arbitrary scores.

Preview/debug output may summarize evidence such as:

```text
genres:
  proposed: Technical Death Metal
  evidence:
    - MusicBrainz release genre
    - Discogs promoted style
    - Last.fm community tag
```

Normal output should stay concise. Full evidence is diagnostic information, not mandatory verbose output on every ordinary run.

## 13. Foundation implementation boundary

The v2 Foundation PR should add only the reusable pieces required to prevent a future architectural retrofit:

- `GenreEvidence` and evidence kind;
- packaged `GenreTaxonomy`/classifier boundary;
- canonical aliases and a small broad-category set;
- deterministic pure `GenreResolver`;
- `genres.num_genres` configuration with `1` default and range `1..10`;
- `genres.promote_styles` configuration with `true` default;
- taxonomy snapshot metadata;
- development-only taxonomy update script;
- structural integration so resolved genres can flow through existing planning, database, and file-sync paths without competing generic genre resolution;
- replacement of the current Last.fm dependency on LastGenre vocabulary with the Noqlen taxonomy;
- focused deterministic tests.

The Foundation must **not** add in this supplement:

- MusicBrainz online genre collection;
- new Last.fm track/artist API behavior;
- new Discogs network behavior beyond making existing style data usable by the genre-evidence boundary;
- iTunes genre behavior changes unless needed only for evidence-shape compatibility;
- mood taxonomy implementation;
- release/version bumping.

Those belong to Semantic Enrichment after the Foundation merges.

## 14. Test expectations

Offline tests must cover at least:

- taxonomy loading without LastGenre installed/enabled;
- current Last.fm genre normalization using only the Noqlen taxonomy;
- canonical alias normalization including K-pop and R&B forms;
- representative metal subgenres including Technical Death Metal, Progressive Metal, Melodic Death Metal, and related broad-vs-specific cases;
- representative electronic genres and aliases such as Drum and Bass/DnB forms;
- rejection of known community-tag noise;
- separation of genre from mood/origin/non-genre descriptors;
- Discogs recognized-style promotion;
- no promotion for an unrecognized style;
- `promote_styles: false`;
- default `num_genres: 1`;
- multiple output values when `num_genres > 1`;
- no automatic insertion of broad parents;
- reliable Track > Release/Album > Artist behavior;
- weak track evidence failing to defeat strong release evidence;
- distinct-provider consensus counting providers rather than evidence rows;
- duplicate evidence collapse and stable ordering;
- deterministic identical output for identical inputs;
- no duplicate genre decision from the generic resolver once the specialized path is active;
- compatibility with ordinary database/file-sync genre handling already established in the Foundation.

## 15. Migration and compatibility

Existing `genres` database/file behavior remains the canonical persistence target. This supplement changes how future semantic evidence is resolved, not the field name or the explicit `--apply` / `--write` authority model.

Existing user genre values remain protected by the ordinary `preserve_existing` policy unless explicitly configured otherwise. The genre resolver does not silently rewrite already-present conflicting metadata merely because a more specific candidate exists.

The LastGenre plugin may coexist in a user's beets installation, but Noqlen Meta must neither require it nor read its vocabulary for genre classification.

## 16. Success criteria

The Genre Foundation is complete when:

- Noqlen Meta owns a deterministic packaged genre vocabulary;
- runtime classification has no dependency on LastGenre;
- genre evidence can preserve provider, scope, kind, confidence, and native weight;
- recognized Discogs styles can contribute genre evidence without losing `styles`;
- genre resolution can combine independent providers and select one result by default;
- `num_genres` changes only the number of independently supported winners, never implicit parents;
- Track > Release/Album > Artist works only after evidence reliability is established;
- the generic metadata resolver remains free of provider-specific genre classification logic and does not make a competing raw-genre decision;
- all Foundation behavior is deterministic and offline-testable;
- Semantic Enrichment can later add MusicBrainz, Last.fm, Discogs, and iTunes evidence producers without changing these contracts.
