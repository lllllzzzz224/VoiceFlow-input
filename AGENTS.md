# Engineering Agent Rules

This project follows the `vibe-project-bootstrap` workflow.

## 0. Planner / Controller Mode

If this conversation is the planner, controller, strategy, review, or brainstorming window:

- do not write code;
- do not create files;
- do not edit files;
- do not delete files;
- only provide direction, task breakdown, prompts, review, and process design.

Only modify files after the user explicitly says: start writing, generate files, implement, apply, execute, or similar.

## 1. Required Read Order

Before code changes, read:

1. `project/docs/PROJECT_CONTEXT.md`
2. `project/docs/DECISIONS.md`
3. `project/docs/ARCHITECTURE.md`
4. `project/docs/TODOS.md`
5. `project/docs/API_CONTRACTS.md`
6. `project/docs/STATE_MATRIX.md`
7. `project/docs/ACCEPTANCE_CASES.md`
8. `project/docs/OPEN_SOURCE_COMPLIANCE.md`

If Agent or AI behavior is involved, also read:

1. `project/docs/AGENT_REUSABLE_PATTERN.md`

If a file does not exist, say so. Do not pretend to have read it.

## 2. Core Rules

- Read before write.
- Plan before coding.
- Minimal diff.
- Preserve existing style.
- Backend contract first.
- State matrix first.
- Verify before done.
- Update docs after accepted feature work.
- Do not introduce dependencies without a recorded decision.
- Do not mark incomplete or unverified work as done.
- Do not copy third-party source, README text, demo UI or repository structure from reference projects.

## 3. Competition Rules

- Keep continuous PR and commit history during the 72h window.
- Each PR must do one thing.
- Each PR description must include feature description, implementation idea and test method.
- Main branch must remain runnable after merge.
- README must include startup instructions, dependencies, demo video link and original work scope.
- README must distinguish direct dependencies from reference-only projects.
- Do not submit code with commit timestamps outside the selected batch window.
- Do not import all code only on the final day.

## 4. Contract Rules

- Backend schema is source of truth.
- Frontend types must align to backend schema.
- Agent outputs must align to backend schema if AI is used.
- New fields can be appended.
- Frozen fields cannot be renamed or removed without versioning.
- Error responses must keep a stable shape.

## 5. State Rules

- `success=false` outranks confidence.
- Missing source-of-truth values cannot be shown as reliable results.
- `confidence=null` is not reliable.
- `fallback_required=true` must show review/fallback state.
- `needs_user_input` must guide the user to provide missing input.
- Provider failure must not crash the page.
- Debug fields must not drive normal user UI.

## 6. Git Rules

- Small changes.
- Clear commit scope.
- No broad refactors.
- Do not revert user changes without approval.
- Do not mix unrelated work.
- Do not amend commits unless explicitly asked.

## 7. Default Output Format

Use this structure unless the task is tiny:

### Current Understanding
### Problem Analysis
### Change Plan
### Implementation
### Test Method
### Risk Notes
