#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/run_agents.sh [--model MODEL] [--no-verify] "task description"

Examples:
  ./scripts/run_agents.sh "Add audit logging for password reset"
  ./scripts/run_agents.sh --model gpt-5.2 "Fix billing page validation"

What it does:
  1. Snapshots the repo baseline for this run
  2. Runs Code Agent with the requested task
  3. Builds a diff of changes introduced during this run only
  4. Runs Review Agent on that scoped diff
  5. Runs Test Agent using the same scoped diff and review findings
  6. Optionally runs ruff and pytest locally

Outputs:
  .agent-runs/<timestamp>/
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

run_codex_exec() {
  local prompt_file="$1"
  local output_file="$2"

  if [[ -n "${MODEL}" ]]; then
    codex exec --full-auto -C "$ROOT" -m "$MODEL" -o "$output_file" - < "$prompt_file"
  else
    codex exec --full-auto -C "$ROOT" -o "$output_file" - < "$prompt_file"
  fi
}

snapshot_repo() {
  mkdir -p "$BASELINE_DIR"
  rsync -a \
    --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '.agent-runs' \
    --exclude '.pytest_cache' \
    --exclude '.mypy_cache' \
    --exclude '.ruff_cache' \
    --exclude '__pycache__' \
    --exclude '.DS_Store' \
    "$ROOT/" "$BASELINE_DIR/"
}

collect_run_changes() {
  local name="$1"
  local changes_file="$RUN_DIR/${name}.changed-files.txt"
  local diff_file="$RUN_DIR/${name}.diff"
  local rsync_file="$RUN_DIR/${name}.rsync.txt"

  rsync -ani \
    --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '.agent-runs' \
    --exclude '.pytest_cache' \
    --exclude '.mypy_cache' \
    --exclude '.ruff_cache' \
    --exclude '__pycache__' \
    --exclude '.DS_Store' \
    "$BASELINE_DIR/" "$ROOT/" > "$rsync_file"

  awk 'NF >= 2 {print $2}' "$rsync_file" | sed '/\/$/d' | sort -u > "$changes_file"

  set +e
  diff -ruN \
    -x '.git' \
    -x '.venv' \
    -x '.agent-runs' \
    -x '.pytest_cache' \
    -x '.mypy_cache' \
    -x '.ruff_cache' \
    -x '__pycache__' \
    -x '.DS_Store' \
    "$BASELINE_DIR" "$ROOT" > "$diff_file"
  local diff_status=$?
  set -e

  if [[ $diff_status -gt 1 ]]; then
    echo "Failed to collect diff for $name" >&2
    exit 1
  fi
}

run_verification() {
  local verify_dir="$RUN_DIR/verification"
  mkdir -p "$verify_dir"

  if command -v ruff >/dev/null 2>&1; then
    set +e
    ruff check . > "$verify_dir/ruff.txt" 2>&1
    echo $? > "$verify_dir/ruff.exitcode"
    set -e
  else
    echo "ruff not found" > "$verify_dir/ruff.txt"
    echo 127 > "$verify_dir/ruff.exitcode"
  fi

  if command -v pytest >/dev/null 2>&1; then
    set +e
    pytest -q > "$verify_dir/pytest.txt" 2>&1
    echo $? > "$verify_dir/pytest.exitcode"
    set -e
  else
    echo "pytest not found" > "$verify_dir/pytest.txt"
    echo 127 > "$verify_dir/pytest.exitcode"
  fi
}

MODEL=""
RUN_VERIFY=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="${2:-}"
      shift 2
      ;;
    --no-verify)
      RUN_VERIFY=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -eq 0 ]]; then
  usage >&2
  exit 1
fi

TASK="$*"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTS_DIR="$ROOT/agents"
RUNS_DIR="${AGENT_RUNS_DIR:-$ROOT/.agent-runs}"
STAMP="$(date +"%Y%m%d-%H%M%S")"
RUN_DIR="$RUNS_DIR/$STAMP"
BASELINE_DIR="$RUN_DIR/baseline"

require_cmd codex
require_cmd rsync
require_cmd git

for file in \
  "$AGENTS_DIR/code-agent.md" \
  "$AGENTS_DIR/review-agent.md" \
  "$AGENTS_DIR/test-agent.md"
do
  if [[ ! -f "$file" ]]; then
    echo "Missing agent prompt file: $file" >&2
    exit 1
  fi
done

mkdir -p "$RUN_DIR"

echo "Run directory: $RUN_DIR"
echo "Task: $TASK"

git -C "$ROOT" status --short > "$RUN_DIR/git-status-before.txt" || true
git -C "$ROOT" diff > "$RUN_DIR/git-diff-before.patch" || true
snapshot_repo

CODE_PROMPT="$RUN_DIR/01-code-agent.prompt.md"
CODE_OUTPUT="$RUN_DIR/01-code-agent.output.md"
cat > "$CODE_PROMPT" <<EOF
$(cat "$AGENTS_DIR/code-agent.md")

## Assigned Task

$TASK

## Run Context

- Repository root: \`$ROOT\`
- Baseline snapshot for this run: \`$BASELINE_DIR\`
- Only implement the requested task
- Keep changes focused and repo-consistent
- Leave a clean handoff for Review Agent and Test Agent
EOF

echo "==> Running Code Agent"
run_codex_exec "$CODE_PROMPT" "$CODE_OUTPUT"

collect_run_changes "02-after-code"

REVIEW_PROMPT="$RUN_DIR/03-review-agent.prompt.md"
REVIEW_OUTPUT="$RUN_DIR/03-review-agent.output.md"
cat > "$REVIEW_PROMPT" <<EOF
$(cat "$AGENTS_DIR/review-agent.md")

## Review Task

$TASK

## Scope

Review only the changes introduced during this run since the baseline snapshot.
Ignore any edits that existed before this run.

- Baseline snapshot: \`$BASELINE_DIR\`
- Changed files list: \`$RUN_DIR/02-after-code.changed-files.txt\`
- Scoped diff for this run: \`$RUN_DIR/02-after-code.diff\`
- Code Agent output: \`$CODE_OUTPUT\`

## Changed Files

\`\`\`text
$(cat "$RUN_DIR/02-after-code.changed-files.txt")
\`\`\`

Return findings only.
EOF

echo "==> Running Review Agent"
run_codex_exec "$REVIEW_PROMPT" "$REVIEW_OUTPUT"

TEST_PROMPT="$RUN_DIR/04-test-agent.prompt.md"
TEST_OUTPUT="$RUN_DIR/04-test-agent.output.md"
cat > "$TEST_PROMPT" <<EOF
$(cat "$AGENTS_DIR/test-agent.md")

## Test Task

$TASK

## Scope

Write or update tests for the changes introduced during this run since the baseline snapshot.
Use the review findings as extra guidance, but focus on shipping useful automated coverage.

- Baseline snapshot: \`$BASELINE_DIR\`
- Changed files list: \`$RUN_DIR/02-after-code.changed-files.txt\`
- Scoped diff for this run: \`$RUN_DIR/02-after-code.diff\`
- Code Agent output: \`$CODE_OUTPUT\`
- Review Agent findings: \`$REVIEW_OUTPUT\`

## Changed Files

\`\`\`text
$(cat "$RUN_DIR/02-after-code.changed-files.txt")
\`\`\`

If feasible, run the most relevant test commands after updating tests.
EOF

echo "==> Running Test Agent"
run_codex_exec "$TEST_PROMPT" "$TEST_OUTPUT"

collect_run_changes "05-after-test"

git -C "$ROOT" status --short > "$RUN_DIR/git-status-after.txt" || true
git -C "$ROOT" diff > "$RUN_DIR/git-diff-after.patch" || true

if [[ "$RUN_VERIFY" -eq 1 ]]; then
  echo "==> Running local verification"
  (
    cd "$ROOT"
    run_verification
  )
fi

echo
echo "Workflow complete."
echo "Artifacts:"
echo "  Code Agent output:   $CODE_OUTPUT"
echo "  Review Agent output: $REVIEW_OUTPUT"
echo "  Test Agent output:   $TEST_OUTPUT"
echo "  Final diff:          $RUN_DIR/05-after-test.diff"
if [[ "$RUN_VERIFY" -eq 1 ]]; then
  echo "  Verification logs:   $RUN_DIR/verification"
fi
