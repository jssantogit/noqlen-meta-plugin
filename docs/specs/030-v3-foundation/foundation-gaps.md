# V3 Foundation Gaps

## Scope

This document audits, without changing, `domain.py`, `providers/specs.py`,
`providers/base.py`, `resolver.py`, `field_types.py`, `beets_mapping.py`,
`track_mapping.py`, `changeplan.py`, `provider_cache.py`, and
`configuration.py`. Recommendations are the minimum foundation work proposed
for Wave 0B; domain feature implementation remains in later waves.

## Current strengths to preserve

- Providers normalize evidence and never write.
- Resolution is pure and precedes ChangePlan/application.
- Provider enablement, field enablement, capability and authority are separate
  gates.
- Provider-local confidence does not override field authority.
- Genre, semantic, identity, AcoustID, artwork and audio already demonstrate
  that one conflict algorithm is not appropriate for every domain.
- ChangePlan preserves proposals, reviews, keeps and skips without acquiring
  authority.
- Command caches distinguish definitive miss from transient failure.

## Required answers

### 1. Can current `MetadataValue` represent V3 without structural loss?

No. It is `str | int | float | bool | tuple[str, ...]`. It can preserve current
scalars and string lists but cannot represent:

- partial dates without sentinel components;
- explicit unknown for tri-state values in a type-safe way;
- multiple typed identifiers tied to Recording or Work;
- structured credits with person, role, instrument, scope and entity;
- ordered artist-credit nodes and join phrases;
- localized title records with language/script/type;
- normalized version plus source description;
- typed artwork/assets and medium association;
- audio method/version/confidence state.

**0B recommendation:** introduce a closed canonical value vocabulary for the
foundation primitives needed by Wave 1 and extension points for later domain
records. Do not use arbitrary dictionaries or JSON strings. At minimum freeze
`PartialDate`, explicit enum/unknown semantics, identifier collections, and an
evidence envelope that can later carry typed credit/title/asset values.

### 2. Does `MetadataCandidate` need more entity/scope/provenance?

Yes. It currently has field, value, provider, confidence, source ID and URL.
That cannot prevent a release producer from being applied to a Recording or
distinguish Work language from lyric-provider language.

**0B recommendation:** replace or generalize it as evidence carrying:

- canonical field/concept;
- typed value;
- exact subject entity type and canonical/local identity;
- asserted source scope;
- provider/source reference;
- acquisition/match provenance required by that field;
- provider-local quality, when meaningful.

Cardinality and conflict kind should come from the field contract, not be
repeated ad hoc on every candidate. Provenance/confidence remain internal and
must not become file tags.

### 3. Does `ProviderScope` need new scopes?

The current Release/Track/Artist organization is insufficient as an evidence
scope for V3, but blindly adding every MusicBrainz entity to provider invocation
would overcomplicate orchestration.

**0B recommendation:** separate two concepts:

- **acquisition/target domain:** release, track, artist, artwork, identity, etc.;
- **asserted entity scope:** Release, Release Group, Medium, Recording, Work,
  Artist, and relationship scope.

Work and Recording must be first-class evidence subjects because cardinality
and inheritance depend on them. They need not become independent public CLI
mutation scopes or generic provider classes. Keep supporting Area internal to
semantic geography unless a stable V3 field needs it.

### 4. Is `ProviderSpec.supported_fields` sufficient?

No. A flat field set plus one scope cannot express:

- field availability by entity/scope;
- primary/secondary/fallback/corroboration/ineligible roles;
- identity preconditions and direct-ID versus search acquisition;
- cardinality/quality requirements;
- acquisition cost/includes and response reuse;
- asset versus ordinary metadata boundaries.

**0B recommendation:** keep `ProviderSpec` as static adapter identity, but make
capabilities structured records keyed by field contract and asserted scope.
Capability declares what an adapter can emit and its acquisition prerequisites;
the authority matrix separately declares whether that evidence is eligible and
for what role. Do not put dynamic confidence or resolver behavior in the spec.

### 5. Is the authority tuple sufficient?

No. It works for the current exclusive scalar resolver, but position alone
cannot express corroboration-only or explicit ineligibility, and conflates
secondary authority with fallback acquisition. V3 also needs role by scope.

**0B recommendation:** use explicit roles:

- `primary`
- `secondary`
- `fallback`
- `corroboration-only`
- `ineligible`

Keep provider-local quality thresholds. Define acquisition order independently
where needed: a secondary source may be cheap corroboration, while a fallback
must not be called after resolution. Absence from a matrix is ineligible by
default. Preserve V2 ordered authority configuration as a compatibility overlay
for fields whose old scalar semantics remain unchanged.

### 6. How should specialized resolvers be preserved?

Do not create a universal resolver. Introduce a small dispatcher by field
contract/conflict kind:

- exclusive scalar/enum/partial-date resolver;
- compatible multivalue union resolver;
- existing genre/semantic taxonomic resolver;
- structured credit/relationship resolver in Wave 2;
- lyrics representation resolver in Wave 3;
- artwork asset resolver in Wave 4;
- audio resolver in Wave 5;
- identity and AcoustID remain entirely separate authority domains.

All may share evidence envelopes, semantic outcomes, diagnostics and ChangePlan
interfaces. They should not share one hidden ranking algorithm.

### 7. How can registry duplication be avoided?

Today field names/types/capabilities/authority/target mappings are repeated
across configuration, `field_types`, provider specs, resolver defaults and
mapping files.

**0B recommendation:** add one immutable **field contract registry** containing
only intrinsic field facts:

- canonical name and V2 aliases;
- domain/entity/scope;
- canonical type and cardinality;
- conflict/resolver kind;
- default enablement;
- native/flexible/asset/internal target class.

Derive validation and registry completeness tests from it. Provider capability
and authority remain separate matrices referencing registered field IDs.
Target adapters remain separate because importer AlbumInfo/TrackInfo, library
models, MediaFile and sidecars have different operational contracts. Avoid a
single giant declarative registry containing executable provider and writer
logic.

### 8. Minimum changes needed in Wave 0B before Wave 1

1. Freeze field IDs, entity/scope vocabulary, cardinality, and canonical
   `PartialDate`/enum/multivalue primitives for Wave 1 fields.
2. Add the richer evidence envelope with match/acquisition provenance.
3. Add explicit authority roles and a testable field x scope x provider matrix.
4. Add structured provider capabilities and identity prerequisites.
5. Add field-contract registry and completeness/consistency validation against
   capabilities, authority and target mappings.
6. Define semantic ACCEPTED/REVIEW/BLOCKED/no-evidence/unavailable outcomes
   without breaking current preview/apply safety.
7. Define internal provenance persistence boundary and cache-key version
   dimensions; implementation can remain command-scoped until a later wave
   needs persistent cache.
8. Freeze V2 alias/config migration behavior before adding public V3 keys.

These are schema and policy foundations. Wave 0B should not add providers or
implement catalog fields itself.

### 9. What may wait for its domain wave?

- Complete MusicBrainz credit/alias/relationship parser: Wave 2.
- Credit dedupe and projection rules: Wave 2.
- LRCLIB conflict policy and `.lrc` asset implementation: Wave 3.
- Back/disc selection, multiple image preservation and image asset planner:
  Wave 4.
- Key/BPM equivalence, local analysis, methodology versions and derived bucket
  thresholds: Wave 5.
- Deezer adapter, if approved after access review: Wave 6.
- Persistent cache implementation and broad acquisition budgets: when actual
  Wave 1-6 call patterns justify them, while key/version contracts belong in
  0B.

### 10. Must a current large/tangential file be split for V3?

No broad split is justified in Wave 0B. The files named in this audit have clear
current responsibilities. `__init__.py` is large and orchestration-tangential,
but V3 does not require splitting it before schema work. Extract only when a
specific new domain integration would otherwise add another unrelated command,
hook or application path to it. Do not split resolver or configuration merely
because V3 adds fields.

## File-specific gap map

| File | Current limitation | 0B action |
| --- | --- | --- |
| `domain.py` | Flat values; candidates lack entity/scope/match provenance | Add canonical primitives and evidence envelope without migrating specialized identity domains into it. |
| `providers/specs.py` | One scope and flat fields per adapter | Structured capability records referencing field contracts; keep adapter identity simple. |
| `providers/base.py` | Release/Track/Artist protocols only | Generalize only enough for typed evidence acquisition; do not make artwork/AcoustID generic providers. |
| `resolver.py` | Ordered tuples and atomic value conflict logic | Explicit authority roles and dispatch by resolver kind; retain current scalar behavior for V2 fields. |
| `field_types.py` | V2 flexible fields only | Derive DB type registration from target contracts where safe; structured records remain internal. |
| `beets_mapping.py` | V2 release fields; singular targets block valid multiplicity | Add mappings in domain waves from audited native contracts; preserve blockers when lossy. |
| `track_mapping.py` | Plain lyrics/BPM/semantics only; synced lyrics blocked | Keep blocker until `.lrc`; later add audited native projections. |
| `changeplan.py` | Generic proposals/reviews, no asset/structured unit semantics | Preserve core; define domain plan adapters rather than bloating ChangePlan. |
| `provider_cache.py` | Command-only exact-entity cache, no methodology version | Add key/version contract; keep implementation minimal until persistent need. |
| `configuration.py` | Field/provider defaults repeated; V2 names only | Keep public V2 tree valid; derive validation/default consistency where possible. No reset or silent rename. |

## Human decisions before implementation

- Approve internal structured relationship persistence that is not a separate
  library database.
- Approve whether ISRC canonical plural receives a new typed DB projection while
  retaining native scalar `isrc` compatibility.
- Approve whether file `LANGUAGE` is explicitly defined as vocal/audio language
  for V3, with release and artist language kept separate.
- Decide whether recording date remains DB-only for 3.0 due embedded semantic
  collisions.
- Decide whether V2 private `NOQLEN_*` tags remain write-compatible indefinitely
  or become documented legacy-only projections. No automatic deletion is
  proposed.
