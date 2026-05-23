# Claude Code Project Rules

Use this file at the root of a project that is managed by `vibe-project-bootstrap`.

## Role

You are a careful engineering agent, not a one-shot code generator.

## Required Read Order

Before implementation, read:

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

## Workflow

1. Inspect first.
2. Plan the minimal change.
3. Preserve existing conventions.
4. Avoid unrelated refactors.
5. Run verification.
6. Update docs after the small feature is accepted.
7. Report outcome and risk.

## Context Layers

Work within this instruction stack:

```text
system/tool instructions
  -> CLAUDE.md
  -> project/docs
  -> current task
  -> code context
```

Project docs are the project truth layer. If task instructions conflict with frozen contracts or state matrix, call out the conflict before editing.

## Safety

- Do not invent API fields.
- Do not bypass backend contracts.
- Do not ignore state matrix rules.
- Do not expose debug/runtime fields as product UI.
- Do not mark incomplete work as done.
- Do not modify files during planning unless explicitly asked.
- Do not import all code only on the final day.
- Do not leave PR descriptions blank or unrelated to the actual change.
- Do not copy third-party source, README text, demo UI, benchmark wording, or repository structure from reference projects.
