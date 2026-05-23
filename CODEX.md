# Codex Project Rules

Use this file at the root of a project that is managed by `vibe-project-bootstrap`.

## Required Read Order

Before code changes, read:

1. `project/docs/PROJECT_CONTEXT.md`
2. `project/docs/DECISIONS.md`
3. `project/docs/ARCHITECTURE.md`
4. `project/docs/TODOS.md`
5. `project/docs/API_CONTRACTS.md`
6. `project/docs/STATE_MATRIX.md`
7. `project/docs/ACCEPTANCE_CASES.md`
8. `project/docs/OPEN_SOURCE_COMPLIANCE.md`

For Agent or AI work, also read:

1. `project/docs/AGENT_REUSABLE_PATTERN.md`

## Core Rules

- Read before write.
- Plan before coding.
- Prefer minimal diffs.
- Preserve existing style.
- Backend contract is source of truth.
- Follow the state matrix.
- Do not hide failed states.
- Do not show debug fields to normal users.
- Do not introduce dependencies without a decision.
- Update docs after a small feature is implemented and accepted.
- Use reference projects through documented dependency APIs or original adapter code; do not copy third-party source or README text.

## 72h Delivery Rules

- Use small, focused PRs.
- Keep commit history continuous during the valid batch window.
- Keep main branch runnable after merge.
- Document dependency usage and original work scope in README.
- Place the demo video link in a visible README section.
- Keep direct dependencies, optional providers and reference-only projects clearly separated.

## Context Layers

Work within this instruction stack:

```text
system/developer instructions
  -> CODEX.md
  -> skills
  -> project/docs
  -> current task
  -> code context
```

Project docs are the project truth layer. Do not ignore them when implementing task-level prompts.

## Planner Mode

If this is a planning/controller discussion, do not write files or code until the user explicitly asks you to generate or apply changes.
