# Noqlen Meta Documentation v2 Redesign Design

## Status

Approved product direction in ChatGPT/Superpowers. This written specification is pending user review before implementation planning.

Base branch: `main` at `2813cf205deba60e336f4520c38834789de40079`.

Working branch: `docs/v2-documentation-redesign`.

Public documentation language: English only.

Target audience: a beginner who has installed beets, but may not yet understand beets configuration, queries, database-vs-file behavior, or import workflow details.

## Goal

Rebuild the public documentation experience around user goals and progressive learning while preserving a precise, code-verified technical reference.

A new user should be able to install Noqlen Meta, configure a useful starter setup, preview enrichment on an existing album, understand the result, apply changes, optionally write supported metadata to files, and then discover more advanced workflows without needing to understand Noqlen's internal architecture first.

The redesign must also eliminate stale v1-era claims and contradictions that remain in public documentation after the v2.0.0 release.

## Non-Goals

This redesign must not:

- change Noqlen Meta runtime behavior, defaults, provider semantics, commands, flags, fields, or configuration contracts;
- redesign beets itself or become a complete beets manual;
- remove precise technical documentation merely to make the site shorter;
- weaken documentation validation or CI to make a rewrite pass;
- move or retag the immutable `v2.0.0` release;
- treat existing documentation as authoritative when it conflicts with production code;
- add new configuration presets as runtime features; documented presets are examples only;
- duplicate the same complete explanation across multiple public pages.

## Documentation Principles

### User journey first

The primary documentation hierarchy answers user questions such as:

- How do I install it?
- How do I configure moods?
- How do I preview changes?
- How do I write tags to my files?
- How do I process my whole library?
- How do I repair MusicBrainz identity?

The main navigation must not require a beginner to decide whether their question is a concept, how-to guide, reference topic, or architecture topic before they can find the answer.

### Explain beets context locally

Assume beets is installed, but do not assume the reader already knows every beets concept. When Noqlen usage depends on a beets concept, explain the minimum needed in context.

Examples:

- explain what `album:"Discovery"` selects when it first appears;
- explain the difference between the beets database and audio-file tags before asking the user to choose between `--apply` and `--write`;
- explain importer-specific behavior only when the reader reaches the import workflow.

Link to beets documentation for deeper coverage rather than duplicating a complete beets manual.

### Friendly documentation and technical reference are separate layers

The primary Configuration and Commands sections teach intent, examples, and common choices.

Technical Reference documents exact public contracts: full dotted paths, types, defaults, ranges, interactions, invalid combinations, provider authority, field targets, compatibility, and safety boundaries.

Technical precision must be preserved, but it must no longer dominate the beginner path.

### Production code is the source of truth

Existing public documentation is reusable material, not an authority.

Every migrated factual claim must agree with current production behavior. If old documentation conflicts with implementation, the documentation is corrected or removed.

### One canonical home for each complete explanation

A fact may be summarized in multiple contexts, but its full explanation must have one canonical page. Other pages link to it instead of copying large sections.

This prevents the current problem of similar pages drifting into contradictory descriptions.

## Proposed Navigation

```text
Home

Start Here
├─ What is Noqlen Meta?
├─ Installation
├─ Basic Configuration
├─ Your First Preview
├─ Understanding the Results
├─ Apply Your First Changes
└─ Write Changes to Your Files

Configuration
├─ Configuration Overview
├─ Fields
├─ Providers
├─ Genres & Styles
├─ Moods
├─ Artwork
├─ BPM
├─ Lyrics & Languages
├─ AcoustID
├─ Advanced Resolution
└─ Full Configuration Example

Commands
├─ Command Overview
├─ Preview Metadata
├─ Apply Metadata
├─ Write Metadata to Files
├─ Process the Whole Library
├─ Repair MusicBrainz Identity
├─ Use AcoustID
└─ Sync Identity Tags

Recipes
├─ Enrich an Existing Library
├─ Enrich During Import
├─ Add or Replace Album Covers
├─ Analyze BPM Locally
├─ Add Lyrics and Language Metadata
├─ Repair MusicBrainz IDs
└─ Safely Update an Entire Library

Troubleshooting
├─ Common Problems
├─ Nothing Was Changed
├─ REVIEW and BLOCKED Results
├─ Provider Problems
├─ File Writing Problems
└─ AcoustID Problems

Technical Reference
├─ Configuration Reference
├─ Command-line Reference
├─ Fields Reference
├─ Providers Reference
├─ beets Interaction
└─ Compatibility

Advanced
├─ Database vs File Tags
├─ Preview, Apply and Write
├─ Strict vs Partial
├─ Provider Authority and Resolution
├─ Safety Guarantees
└─ Architecture

Project
├─ Changelog
├─ Contributing
└─ Release
```

`Concepts` and `How-to Guides` cease to be top-level public navigation categories. Useful material from them is migrated into Start Here, Recipes, Advanced, Troubleshooting, or Technical Reference according to purpose.

## Start Here: Continuous Beginner Journey

Start Here is deliberately linear and uses one continuous existing-library example. The onboarding should feel like one short tutorial rather than a set of independent reference pages.

A representative query is:

```bash
beet nm album:"Discovery"
```

The exact album is only a teaching target; it is not a product dependency.

### 1. What is Noqlen Meta?

Explain in plain language:

- Noqlen Meta enriches music managed by beets;
- examples include genres, styles, moods, artwork, BPM, lyrics/languages, and identity-related metadata;
- preview is non-mutating by default;
- Noqlen Meta complements beets rather than replacing it.

Do not introduce internal types, resolution objects, authority internals, or mapping structures here.

### 2. Installation

Teach the shortest successful setup:

```bash
pip install beets-noqlenmeta
beet config -p
```

Then enable the plugin:

```yaml
plugins:
  - noqlenmeta
```

Verify installation with:

```bash
beet nm --help
```

Advanced environment details such as `BEETSDIR`, alternate config files, plugin discovery internals, and unusual installation layouts belong in Troubleshooting or Technical Reference unless required for the common path.

### 3. Basic Configuration

Introduce a small, genuinely useful configuration and explain the mental model of major blocks.

Example:

```yaml
noqlenmeta:
  providers:
    musicbrainz:
      enabled: true
    coverartarchive:
      enabled: true

  fields:
    genres: true
    styles: true
    moods: true
    cover: true

  genres:
    num_genres: 1

  moods:
    max_moods: 1
```

Explain:

- providers are sources of metadata;
- fields are metadata categories Noqlen may enrich;
- feature-specific blocks such as `genres` and `moods` fine-tune behavior.

Do not teach the entire configuration contract during onboarding.

### 4. Your First Preview

Run:

```bash
beet nm album:"Discovery"
```

Explain that `album:"Discovery"` is a beets query selecting the album whose album field matches that value. The user should not need prior knowledge of the entire beets query language.

Preview remains the default and changes nothing.

### 5. Understanding the Results

Explain the statuses only after the reader has seen them:

- `KEEP`: the current value is retained;
- `PROPOSE`: Noqlen found a value considered safe enough to propose, but has not changed anything yet;
- `REVIEW`: useful evidence exists, but automatic confidence/safety is insufficient;
- `BLOCKED`: a safety, identity, mapping, or contract requirement prevented the change.

The beginner explanation should describe operational meaning first. Exact status semantics may link to Technical Reference or Advanced.

### 6. Apply Your First Changes

Teach:

```bash
beet nm --apply album:"Discovery"
```

Explain that `--apply` authorizes approved ordinary enrichment to be committed to the beets library, while preserving the v2 artwork exception: authorized artwork sidecars and `Album.artpath` may also be updated without audio-file mutation.

This page introduces the difference between the beets database and tags stored in audio files.

### 7. Write Changes to Your Files

Teach:

```bash
beet nm --apply --write album:"Discovery"
```

Explain that `--apply` authorizes the prepared enrichment application and `--write` additionally synchronizes supported prepared metadata to audio files. Adding `--write` must not be described as triggering a second provider lookup or new analysis pass.

At the end of Start Here, the reader should understand this central model:

```text
configure
    ↓
preview
    ↓
review
    ↓
apply
    ↓
write, when wanted
```

The final page offers two clear next paths:

- customize behavior in Configuration;
- learn importer use in Recipes → Enrich During Import.

## Configuration Design

Configuration is divided into short topic pages rather than one beginner-facing mega-reference.

Each page follows the same editorial order:

1. what the feature does;
2. minimal useful YAML;
3. plain-language explanation;
4. default behavior;
5. useful alternatives;
6. important interactions with related settings;
7. link to Technical Reference for exact contract details.

Avoid leading with full dotted paths, internal targets, or implementation-oriented terminology.

### Configuration Overview

Present the major shape without dumping every leaf setting:

```yaml
noqlenmeta:
  fields:
    ...
  providers:
    ...
  genres:
    ...
  moods:
    ...
  artwork:
    ...
  bpm:
    ...
  local_analysis:
    ...
  acoustid:
    ...
  resolution:
    ...
```

Explain each block in one or two sentences.

`resolution` is explicitly introduced as advanced; most users should not need to configure it manually.

### Fields

Begin with a realistic example:

```yaml
fields:
  genres: true
  styles: true
  moods: true
  bpm: true
  lyrics: false
  cover: true
```

Explain that fields control which kinds of metadata Noqlen may handle, then group them conceptually where useful: release/album, track, artist, and artwork metadata.

The exact storage targets and typed field contracts remain in Technical Reference.

### Providers

The page should answer why a user would enable each provider, not start with a provider capability matrix.

Examples:

- MusicBrainz: strong default source; no API key required;
- Cover Art Archive: album artwork; no API key required;
- Discogs: genres, styles, labels, and release information; document credentials/dependency requirements;
- LRCLIB: lyrics-oriented source; show the related field settings together with provider enablement;
- other production providers: document their practical value and prerequisites consistently.

Important provider/field relationships must be shown together rather than as disconnected configuration fragments.

### Genres & Styles

Explain the relationship between genre enrichment, style enrichment, `num_genres`, and style promotion using concrete examples before exact contract details.

### Moods

Begin with:

```yaml
fields:
  moods: true

moods:
  max_moods: 1
```

Explain `fields.moods` as permission to enrich moods and `moods.max_moods` as the maximum number of independently supported canonical moods retained.

Example:

```yaml
moods:
  max_moods: 3
```

Plain-language contract: Noqlen may keep up to three supported moods; it does not invent or pad values to reach the limit.

### Artwork

Teach the common combination of `fields.cover`, Cover Art Archive enablement, artwork size, and `replace_existing`. Explain `cover.jpg`, `Album.artpath`, multidisc behavior, and optional embedding at the level appropriate to the page, with exact write contracts linked to Technical Reference.

### BPM

Explicitly distinguish:

```yaml
fields:
  bpm: true
```

from:

```yaml
local_analysis:
  bpm:
    enabled: true
```

The former permits BPM as an enrichment field; the latter allows local calculation from audio files. Document the `[audio]` extra and current local backend without implying that an external BPM provider exists.

### Lyrics & Languages

Explain plain lyrics, synced lyrics where applicable, lyrics-language metadata, and artist language/country/area behavior according to production v2. Correct all stale v1 wording that says these semantic fields are deferred or unavailable.

### AcoustID

Teach AcoustID as an existing-library identity/evidence workflow, not as ordinary semantic enrichment. Keep its enablement, fingerprint reuse/computation, lookup, thresholds, and relationship to `--identity` understandable, while exact constraints remain in Technical Reference.

Do not imply that Noqlen replaces native beets/chroma importer acoustic matching or submission.

### Advanced Resolution

Begin with a clear statement that most users do not need manual resolution configuration.

Teach `authority`, `min_confidence`, and `preserve_existing` through concrete scenarios first. Exact field paths and validation rules remain in Technical Reference.

### Full Configuration Example

Retain a complete config that exactly matches production defaults, but label it clearly:

> This is a reference example, not a recommended starter configuration.

Comments may be added where they improve readability, provided the machine-validated YAML remains an exact representation of production defaults.

## Commands Design

The main Commands area is organized by user objective, not by a flat list of flags.

### Command Overview

Use a goal-to-command map such as:

```text
See what Noqlen would change
→ beet nm QUERY

Save approved changes
→ beet nm --apply QUERY

Also synchronize supported tags to files
→ beet nm --apply --write QUERY

Process the whole library
→ beet nm --all

Repair MusicBrainz identity
→ beet nm --identity QUERY

Use acoustic fingerprints/evidence
→ beet nm --acoustid QUERY
```

Exact option parsing, valid/invalid combinations, and mode matrices remain in Technical Reference.

### Preview Metadata

Teach normal `beet nm QUERY` behavior and targeted query examples. Preview is the recommended first step for any new configuration or broad library operation.

### Apply Metadata

Teach `--apply` with the exact v2 permission boundary: ordinary database changes plus authorized artwork sidecar/`Album.artpath` behavior, but no audio-file mutation.

### Write Metadata to Files

Teach `--apply --write`, supported prepared metadata synchronization, and the rule that `--write` does not expand provider or analyzer work.

### Process the Whole Library

Teach preview-first scaling:

```bash
beet nm --all
beet nm --all --apply
beet nm --all --apply --write
```

Recommend testing a narrow album/artist query first without portraying the plugin as unsafe.

### Identity, AcoustID, and Identity Tags

Keep MusicBrainz identity audit/repair, AcoustID evidence, and identity-tag synchronization as distinct goals with their separate mutation authorities. Do not imply that `providers.musicbrainz.enabled` controls identity audit.

## Recipes Design

Recipes solve complete user tasks and intentionally combine configuration plus commands when needed. They are not a second technical reference.

Required recipes:

### Enrich an Existing Library

Choose providers and fields, preview one album, inspect results, apply, optionally write files, then scale to a larger query or the whole library.

### Enrich During Import

This is the secondary onboarding path. Explain importer integration only after the ordinary existing-library workflow is understood. Correct stale claims about singleton items and v1-only limitations.

### Add or Replace Album Covers

Show the relevant cover field, provider, and artwork settings together. Explain `replace_existing`, sidecar behavior, and when embedding can occur.

### Analyze BPM Locally

Show `[audio]` installation, the related field plus local-analysis configuration, and a real command. Keep current v2 preservation/recalculation semantics accurate.

### Add Lyrics and Language Metadata

Show the exact field/provider combinations needed for current v2 plain lyrics and semantic language metadata.

### Repair MusicBrainz IDs

Teach the identity workflow independently from ordinary semantic enrichment.

### Safely Update an Entire Library

Show the recommended preview → inspect → apply → optional write progression for broad queries.

Additional small goal-oriented configuration examples may be included inside these pages, such as metadata without lyrics or BPM-only analysis, but they must not introduce runtime presets.

## Troubleshooting Design

Troubleshooting is organized by user-visible symptom.

### Common Problems

Provide a compact diagnostic starting point and link to more specific symptom pages.

### Nothing Was Changed

Diagnose in practical order:

1. whether the relevant field is enabled;
2. whether an appropriate provider/source is enabled and usable;
3. whether sufficient identity/evidence exists;
4. whether existing-value preservation prevents replacement;
5. whether the result was `REVIEW` or `BLOCKED`;
6. whether the beets query actually selected the intended items.

Each diagnosis should include a concrete command or config check where possible.

### REVIEW and BLOCKED Results

Explain operational meaning first, then common causes and next steps. Link to exact status contracts rather than duplicating them.

### Provider Problems

Troubleshoot credentials, dependencies, identity prerequisites, network behavior, and provider scope by practical symptom.

### File Writing Problems

Troubleshoot database-vs-file expectations, `--write`, supported tag synchronization, artwork sidecars/embedding, file permissions, and relevant beets interactions.

### AcoustID Problems

Troubleshoot fingerprint reuse, `fpcalc`, optional fingerprint computation, API credentials where required, thresholds, and identity filtering behavior.

## Technical Reference

Technical Reference remains precise and comprehensive.

It must contain:

- all public CLI options;
- all public configuration leaf paths;
- types, defaults, ranges, and validation constraints;
- valid and invalid option combinations;
- provider capability and prerequisite matrices where useful;
- exact field targets and storage behavior;
- beets interaction contracts;
- supported Python/beets compatibility;
- safety and mutation boundaries where exact wording is required.

Technical Reference pages should start with a pointer back to Configuration or Commands for users looking for setup instructions and examples.

The current technical material is preserved only where accurate. Stale v1 statements are rewritten or removed.

## Advanced

Advanced is conceptual, not a duplicate reference.

It explains how and why the system behaves:

- Database vs File Tags;
- Preview, Apply and Write;
- Strict vs Partial;
- Provider Authority and Resolution;
- Safety Guarantees;
- Architecture.

`Concepts` material that remains useful should migrate here when it explains mental models rather than task steps.

## Home Page

The home page becomes a product entry point rather than a release-status dashboard.

It should quickly answer:

- what Noqlen Meta is;
- what kinds of metadata it can enrich;
- whether it is safe to try;
- where a new user should start.

Primary call to action: Start Here / Get Started.

Secondary call to action: Configuration.

GitHub, PyPI, license, release, and project information remain accessible but must not dominate the first screen or core explanation.

## Known Stale or Contradictory Areas to Correct

The migration must explicitly audit and fix known v2 contradictions, including at least:

- Field Reference statements that moods, lyrics languages, artist languages, artist countries, and artist areas are unavailable/deferred when current v2 supports them;
- Existing Library guidance that ordinary mode selects Albums only, does not enrich singleton Items, and never performs current v2 verified write behavior;
- old wording that ordinary `--apply` is always database-only, ignoring authorized artwork sidecar/`Album.artpath` writes;
- import-enrichment wording that still labels shipped capabilities as v1 mapping blockers or deferred behavior;
- stale release/version/homepage language inherited by immutable `v2.0.0` documentation sources;
- any documentation that conflates semantic MusicBrainz provider enablement with the separate identity audit workflow;
- any wording that implies `--write` triggers a new provider/analyzer pass;
- any implication that Noqlen owns importer acoustic matching/submission instead of native beets/chroma.

The implementation audit may identify additional stale pages; this list is a minimum, not a closed set.

## Migration Method

Do not delete all public documentation and rewrite blindly. Audit each existing public page and classify it as one of:

- Keep: accurate and already suitable;
- Rewrite: necessary topic, but stale or poorly oriented;
- Split: tutorial and exact reference are mixed together;
- Merge: redundant pages cover the same user question;
- Move: useful information belongs in a different section;
- Remove: obsolete, redundant, or fully replaced.

Maintain an internal migration matrix during implementation with at least:

```text
Feature/topic | Production behavior | Current docs state | Migration action | Destination
```

The matrix is an execution artifact and does not need to become public documentation.

## Validation Strategy

The existing documentation CI is retained and adapted rather than weakened.

Current useful contracts include:

- extracting public `beet nm` long options from the actual command and requiring Technical Reference coverage;
- extracting `default_config()` leaf paths and requiring Technical Reference coverage;
- requiring `site-docs/examples/full-config.yaml` to exactly equal production defaults;
- parsing all public YAML examples;
- ensuring every MkDocs navigation target exists;
- ensuring public Markdown is represented in navigation;
- strict MkDocs build validation;
- release-state checks;
- guards against internal project links, secrets, and private filesystem paths.

When reference paths move from `site-docs/reference/` to `site-docs/technical-reference/`, update `scripts/check_public_docs.py` to follow the new canonical locations without reducing its behavioral coverage.

CI should validate facts and public contracts, not lock editorial prose unnecessarily. Avoid fragile assertions that require arbitrary beginner-facing sentences to remain word-for-word identical.

The documentation job continues to run both:

```bash
python scripts/check_public_docs.py
mkdocs build --strict
```

No documentation PR is mergeable until the full repository CI is green.

## Read the Docs and Versioning Constraint

The existing `v2.0.0` tag must remain immutable.

If Read the Docs `stable` is tied to release/tag behavior such that the redesigned main documentation cannot become stable directly, publication of the redesigned stable docs must use the normal future release/version mechanism rather than moving or recreating `v2.0.0`.

Determining the exact Read the Docs alias/version update is a release/publishing follow-up after the redesign is merged and verified; it is not permission to retag an existing release.

## Execution Workflow

Planning and coordination follow the project's preferred workflow:

1. ChatGPT + Superpowers: investigate, design, specify, plan, review, and coordinate;
2. OpenCode: execute the large multi-file documentation migration when the implementation plan is approved and heavy execution is warranted;
3. ChatGPT/GitHub review: inspect diff, validate documentation against current production behavior, inspect CI, fix issues, and merge only when green.

The OpenCode phase must receive a bounded plan and migration matrix. It must not independently redesign the information architecture or reinterpret product behavior.

Avoid unnecessary intermediate contract documents. This design spec plus the approved Superpowers implementation plan are the authoritative task contract unless a concrete implementation discovery requires an explicitly documented correction.

## Acceptance Criteria

The redesign is complete when all of the following are true:

- public documentation is entirely in English;
- top-level navigation follows the approved user-oriented architecture or a clearly equivalent final structure justified during implementation;
- a beginner can follow Start Here from installation through preview, result interpretation, apply, and optional file writing using one continuous example;
- beginner docs explain necessary beets concepts in context without becoming a full beets manual;
- Configuration is split into focused, human-oriented topic pages;
- Moods clearly explains both `fields.moods` and `moods.max_moods`, including that `max_moods` is a maximum rather than a padding target;
- provider pages explain practical purpose and relevant field/provider interactions;
- Commands is organized by user objective;
- Recipes cover existing-library, import, artwork, local BPM, lyrics/languages, identity repair, and whole-library workflows;
- Troubleshooting is symptom-oriented;
- Technical Reference preserves complete public CLI/configuration coverage and exact contract detail;
- Advanced holds conceptual/internal mental models rather than blocking beginner onboarding;
- known v1/v2 contradictions are removed;
- no public page claims behavior that contradicts current production code;
- `full-config.yaml` remains machine-equal to `default_config()`;
- all public YAML examples parse;
- all public Markdown is intentionally navigable;
- `python scripts/check_public_docs.py` passes;
- `mkdocs build --strict` passes;
- the full repository CI is green;
- the redesign introduces no unintended runtime/product behavior changes.

## Implementation Gate

No documentation migration should begin from this specification alone until:

1. the user reviews and approves this written spec;
2. Superpowers `writing-plans` produces the implementation plan;
3. that plan defines the concrete audit/migration sequence and OpenCode execution handoff.
