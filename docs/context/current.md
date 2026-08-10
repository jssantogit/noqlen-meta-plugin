# Current Context

This file is an optional working snapshot, not a mandatory workflow gate. Use
repository state, relevant code/tests, and durable docs as the source of truth;
refresh this file only when an ongoing body of work genuinely benefits from it.

## Project

Noqlen Meta — multi-provider metadata enrichment and MusicBrainz identity tools
for beets.

Released baseline: `1.0.0`.

Current `main` baseline before this workflow retrofit:

```text
68f32073debd87090a44212b0d203c54954e4e19
```

## Completed work

Block 029 — AcoustID recording-level identity evidence — is closed.

Product implementation was squash-merged in PR #19 as:

```text
c5eabf80bbbe0f661aaa8867a78b3ebb83f0b3e3
```

The final documentation/release-readiness closure was squash-merged in PR #20
as `68f32073...` after CI run 78 passed all repository jobs, including strict
documentation build.

The historical Block 029 contracts, ADR 0025, stage briefs, and completion
records remain useful references for that feature. They do not define a
mandatory stage structure for future work.

## Next product direction

The next intended initiative is a major Noqlen Meta v2 enrichment expansion,
rather than publishing the completed AcoustID work as a standalone 1.1.0
feature release.

Candidate v2 capabilities currently include:

- cover art;
- moods;
- BPM;
- broader/better style representation;
- track/song language;
- artist country/origin.

These are product goals, not frozen architecture. Provider authority, storage
representation, Album/Item/artist ownership, local analysis boundaries, and
write semantics still need deliberate design before implementation where those
decisions are hard to reverse.

## Workflow

Noqlen Meta now follows Noqlen Playbook V2.2:

```text
Inspect -> Implement -> Verify -> Review
```

Future work should not create stages, completion records, specs, handoffs,
Tool Mode declarations, context levels, or formal audits merely because a task
is large or long-running.

Use a durable change brief only when planning materially changes what is built,
where it belongs, or implementation order. Use an ADR only for architectural
decisions that are meaningfully hard to reverse. Split implementation when it
improves feedback, independent execution, isolation, or reviewability — not as
ceremony.

`docs/context/handoff.md` is updated only when work is interrupted, transferred,
externally blocked, or otherwise cannot be resumed safely from repository state
alone.
