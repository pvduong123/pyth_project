# AI Agents For This Repo

This directory contains prompt templates for running three specialized AI agents on this FastAPI codebase.

## Agents

- `code-agent.md`: Implements features and fixes bugs.
- `review-agent.md`: Reviews code changes and reports risks or defects.
- `test-agent.md`: Adds and updates unit tests and integration tests.

## Recommended Flow

1. Run `Code Agent` on a specific feature or bugfix.
2. Run `Review Agent` on the resulting diff.
3. Run `Test Agent` on the same diff and on any review findings that require coverage.
4. Run verification commands locally:

```bash
ruff check .
pytest -q
```

You can also use the orchestration script:

```bash
./scripts/run_agents.sh "Describe the feature or bugfix here"
```

The script will:

- snapshot the repo before the run
- execute `Code Agent`
- review only the changes introduced during that run
- execute `Test Agent`
- optionally run `ruff check .` and `pytest -q`
- save prompts, outputs, diffs, and verification logs under `.agent-runs/`

## Collaboration Rules

- Keep production code ownership with `Code Agent`.
- Keep review-only ownership with `Review Agent`.
- Keep test file ownership with `Test Agent`.
- Avoid having multiple agents edit the same production file at the same time.
- When possible, give each agent the task, expected output, and file scope up front.

## Suggested Inputs

Use prompts like these when dispatching work:

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
