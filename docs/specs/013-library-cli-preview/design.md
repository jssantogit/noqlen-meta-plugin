# Design - Library CLI Preview Boundary

## Flow

```text
library Album
  -> ReleaseEnrichmentContext + canonical current values
  -> shared provider/resolver/ChangePlan helper
  -> LibraryTargetPlan
  -> sanitized preview only
```

One `Subcommand("noqlenmeta", aliases=["nm"])` owns both names. The handler validates query intent,
builds one policy, queries `Library.albums()` using native beets semantics, and plans each album
independently. Provider failures remain isolated; internal contract and mapping errors propagate.

`LibraryTargetPlan` reuses `BeetsTargetShape` as representation vocabulary but has its own explicit
persistent Album field map. Multi-value canonical data maps only to `genres`; singular fields require
exactly one tuple value. `media`, `format_descriptions`, and future unmapped valid fields are blockers.
No application function is reachable from the command path.
