# Requirements — Project Foundation

## Goal

Create a minimal, trustworthy foundation for developing Noqlen Meta as an external beets plugin using the Noqlen Playbook.

## User/problem

The project needs to move quickly with Codex under a constrained usage budget. Heavy duplicate fake implementations and broad up-front architecture would waste development cycles, but skipping boundaries, deterministic tests, and repository hygiene would reduce confidence.

## Functional requirements

- The repository must be installable as a Python project.
- beets must be declared as the host/runtime dependency.
- A minimal `noqlenmeta` beets plugin package must exist without implementing enrichment behavior.
- The repository must document the Noqlen block workflow and agent boundaries.
- Provider development must follow the real-first, fixture-backed policy.
- Baseline lint, tests, and contamination checks must be defined.
- The project direction and current handoff must be discoverable from the repository.

## Non-goals

- Implementing any provider.
- Defining the complete metadata schema.
- Implementing resolver or field-authority behavior.
- Hooking into the beets importer.
- Writing tags or modifying music files.
- Publishing a package or release.

## Risks

- Over-designing contracts before the first vertical provider slice.
- Accidentally coupling domain logic to one provider.
- Treating live network checks as the normal test suite.
- Leaking local configuration or user-library data into fixtures.

## Acceptance criteria

- A clean environment can install the project in editable mode.
- `NoqlenMetaPlugin` is a `BeetsPlugin` subclass.
- Default tests require no network and no real music library.
- CI runs lint, tests, and repository contamination checks.
- Context, handoff, integration policy, and architecture decision are present.
