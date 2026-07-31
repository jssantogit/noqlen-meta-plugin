# Architecture

You will see how provider data becomes an explicit, target-aware plan without
mixing network access and writes.

```text
providers
-> normalized candidates
-> per-field authority and resolution
-> canonical change plan
-> beets-specific target mapping
-> explicit application boundary
```

Provider adapters declare release or track scope and current field capability.
Orchestration calls an adapter only when provider enablement, field enablement,
authority, and capability intersect. Candidates retain structured values,
source, confidence, and provenance.

The resolver compares candidates with current canonical values. It produces
`KEEP`, `PROPOSE`, `REVIEW`, or skipped decisions without knowing a beets
target. A `ChangePlan` collects these decisions but cannot write.

Target mapping then asks whether the selected beets object can represent each
proposal losslessly. Release importer, selected-track importer, persistent
Album, identity database, and identity-tag file targets use separate mappings.
A mapping blocker is not converted into a resolver review or flattened value.

Application is the final explicit boundary. Importer application mutates only
selected metadata objects; ordinary library application stores mapped Albums;
identity database repair uses fixed columns; identity-tag application uses the
candidate/backup replacement workflow. This separation keeps a provider or
resolver from acquiring write authority.
