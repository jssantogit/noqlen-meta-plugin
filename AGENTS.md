# AGENTS

This repository follows the Noqlen Playbook.

## Before editing

- Read `docs/context/current.md` and `docs/context/handoff.md`.
- Read the active spec and any relevant ADR.
- Work only on the requested block.
- Declare Tool Mode when optional tooling affects the block.
- Use the smallest context level that is safe for the task.

## Scope discipline

- Respect allowed and forbidden files.
- Do not perform broad rewrites or opportunistic refactors.
- Keep product implementation, audit, release, and environment bootstrap as separate blocks unless explicitly requested otherwise.
- Stop if the block requires forbidden files, destructive actions, unclear requirements, or a scope-changing validation failure.

## Integration policy

- Use the real-first, fixture-backed policy in `docs/development/integration-policy.md`.
- Implement production adapters directly rather than building parallel fake implementations first.
- Keep network I/O behind narrow boundaries.
- Prefer sanitized real-response fixtures for deterministic tests.
- Keep live network tests opt-in and excluded from the default test run.
- Mock only failure conditions that are impractical or unsafe to reproduce live.
- Never use a real music library in automated tests.

## Safety and repository hygiene

- Never expose or commit secrets, credentials, personal paths, private data, lyrics, fingerprints, or real music-library paths.
- Do not commit active local agent or tool configuration.
- Do not create or commit `opencode.json`, `.opencode/`, `.serena/`, `.mcp/`, `.claude/`, `.cursor/`, `.windsurf/`, or `RTK.md` unless a future explicit and sanitized policy changes this rule.
- Do not perform destructive file or metadata writes without explicit scope and review.

## Validation

- Validate before claiming a block is complete.
- Run the focused tests for the changed behavior and the repository hygiene check.
- Report touched files, commands run, validation results, residual risks, and whether the block is complete.
- If validation cannot run, state why and report the residual risk.

## Git rules

- Do not use `git add .`.
- Stage intended files explicitly.
- Do not force push.
- Do not rewrite history unless explicitly requested.
