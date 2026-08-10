# AGENTS

This repository follows Noqlen Playbook V2.2. The playbook is the canonical
workflow; this file keeps only Noqlen Meta-specific invariants.

## Work discipline

- Inspect the task-relevant code, tests, documentation, and current repository
  state before editing.
- Read `docs/context/`, specs, and ADRs when they are relevant to the change;
  they are not mandatory preambles for routine work.
- Make the smallest complete and coherent change that satisfies the request.
- Do not perform unrelated rewrites or opportunistic refactors.
- Respect explicit user scope and repository boundaries.
- Do the workflow; do not narrate `Inspect -> Implement -> Verify -> Review`,
  Tool Mode, context levels, inactive escalations, or process metadata merely
  to prove compliance.
- Default to one capable agent. Delegate or parallelize only when independent
  execution, context isolation, shorter feedback cycles, or independent
  scrutiny clearly outweigh coordination cost.
- Keep one coordinator responsible for integrating delegated work and
  verifying the combined result.
- When the same correction or failure recurs, choose the lightest durable fix
  that addresses the cause instead of expanding future prompts.

## Integration policy

- Follow `docs/development/integration-policy.md` for external metadata
  services.
- Implement production adapters directly behind narrow network/process
  boundaries rather than building parallel fake implementations first.
- Prefer small sanitized real-response fixtures when they provide durable
  regression value.
- Keep live network checks opt-in and outside the default test run.
- Do not invent an abstraction only so a fake can exist.

## Verification

- Validate changed behavior before claiming completion.
- Use focused tests first and broaden validation when the blast radius warrants
  it.
- When cheap and relevant, observe the actual outcome as well: run the affected
  CLI path with safe synthetic input, build the documentation, inspect a
  generated artifact, or exercise another user-visible boundary.
- Review the final diff for scope drift, accidental changes, and residual risk.
- If validation cannot run, report why and what remains unverified.
- Agent statements such as "implemented" or "fixed" are not verification
  evidence by themselves.

## Safety and repository hygiene

- Never expose or commit secrets, credentials, personal paths, private data,
  lyrics, fingerprints, or real music-library data.
- User-authorized local/private data may be inspected transiently when the task
  requires it; automated tests must use synthetic or sanitized data.
- Do not commit active local agent/tool configuration or generated agent state.
- Do not create or commit `opencode.json`, `.opencode/`, `.serena/`, `.mcp/`,
  `.claude/`, `.cursor/`, `.windsurf/`, or `RTK.md` unless an explicit,
  sanitized repository task requires it.
- For high-impact real-state mutation that has not already been authorized,
  require explicit apply intent. Do not ask for the same authorization twice.
- Do not merge, publish, deploy, tag, release, force push, or rewrite history
  unless explicitly requested.
- Treat third-party skills, plugins, MCP servers, and agent packages as
  software trust dependencies: minimize privileges and review them on adoption
  or material change.

## Architecture and testing

- Follow existing boundaries unless changing them is part of the request.
- Isolate external or nondeterministic dependencies during verification when
  direct use would be unsafe, impractical, flaky, expensive, or dependent on
  private state.
- Use isolated workspaces for concurrent writers when interference is possible;
  read-only parallel investigation does not require a worktree by default.
- Use ADRs only for architectural decisions that are meaningfully hard to
  reverse or important to future consumers.
- Diff size or task duration alone does not require a formal plan, audit,
  delegation, stage split, or branch isolation.

## Git rules

- Stage intended files explicitly; do not use `git add .` as a shortcut.
- Do not force push or rewrite history unless explicitly requested.
