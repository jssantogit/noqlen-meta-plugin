# Block 025 Review

## Checklist

- Identity execution and write permission are separate from enrichment and provider configuration.
- Only already accepted album/singleton matches are audited; Noqlen does not influence selection.
- Effective identity mirrors normal beets application and `from_scratch` behavior.
- Block 024 owns assignment, score, selection, ambiguity, and four-field comparison.
- Preview is deterministic and omits paths, queries, opaque keys, and raw malformed values.
- Album preview collapses repeated canonical IDs, labels distinct IDs `multiple/conflict`, and labels
  mixed-marker state `mixed/missing` without exposing internal joined or marker values.
- Ambiguous preview assignment counts come from the top-ranked evaluation while the verdict remains
  ambiguous and no repair plan is produced.
- Ambiguous and non-repair-ready audits cannot produce or apply identity changes.
- Canonical plans map only exact selected `AlbumInfo`/`TrackInfo` identity fields.
- Repair revalidates plan and context, then applies one atomic set with rollback and cache handling.
- No direct Item, Album, database, tag, or file write occurs.
- Library identity/tag sync remain absent, AcoustID remains excluded, and 026/027/028/STOP is frozen.

## Outcome

Block 025 importer identity preview/repair is integrated. Block 026 library identity audit/repair is
next. Focused preview/plugin validation passes 48 tests, the identity suite passes 166 tests, and the
full offline suite passes 966 tests with 5 opt-in live tests skipped. Ruff, repository contamination,
and diff-whitespace checks pass.
