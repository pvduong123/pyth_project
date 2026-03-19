# AI Agents For This Repo

This directory contains prompt templates for running specialized AI agents on this FastAPI codebase.

## Agents

- `spec-agent.md`: Turns a rough request into a complete implementation-ready spec through focused clarification.
- `code-agent.md`: Implements features and fixes bugs.
- `review-agent.md`: Reviews code changes and reports risks or defects.
- `test-agent.md`: Adds and updates unit tests and integration tests.

## Recommended Flow

1. Run `Spec Agent` when the request is still incomplete, rough, or ambiguous.
2. Run `Code Agent` on the approved spec or specific bugfix.
3. Run `Review Agent` on the resulting diff.
4. Run `Test Agent` on the same diff and on any review findings that require coverage.
5. Run verification commands locally:

```bash
ruff check .
pytest -q
```

You can also use the orchestration script:

```bash
./scripts/run_agents.sh "Describe the feature or bugfix here"
```

Useful variants:

```bash
./scripts/run_agents.sh --parallel "Describe the feature or bugfix here"
./scripts/run_agents.sh --only spec "Clarify the new billing workflow"
./scripts/run_agents.sh --only review "Review the current working tree"
./scripts/run_agents.sh --only test "Write tests for the current working tree"
./scripts/run_agents.sh --verify-cmd "pytest tests/test_password_reset.py -q" "Harden password reset flow"
```

The script will:

- snapshot the repo before the run
- execute `Spec Agent`
- execute `Code Agent`
- review only the changes introduced during that run
- execute `Test Agent`
- optionally run `Review Agent` and `Test Agent` in parallel after the code stage
- optionally run `ruff check .` and `pytest -q`
- save prompts, outputs, diffs, and verification logs under `.agent-runs/`

In `all` mode, `Code Agent` receives the `Spec Agent` output as run context.

## Collaboration Rules

- Keep production code ownership with `Code Agent`.
- Keep review-only ownership with `Review Agent`.
- Keep test file ownership with `Test Agent`.
- Avoid having multiple agents edit the same production file at the same time.
- When possible, give each agent the task, expected output, and file scope up front.

## Suggested Inputs

Use prompts like these when dispatching work:

- `Spec Agent`: "Clarify this rough request and turn it into a complete spec with acceptance criteria, assumptions, and open questions."
- `Code Agent`: "Implement X without broad refactors. Follow the repository architecture and summarize changed files."
- `Review Agent`: "Review the diff for bugs, regressions, edge cases, and missing validation. Report findings only."
- `Test Agent`: "Write unit and integration tests for the new behavior. Prefer minimal fixtures and summarize uncovered risks."

## Repo Context

This project uses:

- FastAPI app entrypoint at `app/main.py`
- Layered architecture under `app/domain`, `app/application`, `app/infrastructure`, and `app/presentation`
- Tests under `tests/`
- PostgreSQL and Alembic for persistence and migrations

If a task touches routes, validate both API behavior and template-facing web flows when relevant.
