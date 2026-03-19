#!/usr/bin/env bash

set -euo pipefail

DEFAULT_VERIFY_COMMANDS=(
  "ruff check ."
  "pytest -q"
)

EXCLUDE_PATTERNS=(
  ".git"
  ".venv"
  ".agent-runs"
  ".pytest_cache"
  ".mypy_cache"
  ".ruff_cache"
  "__pycache__"
  ".DS_Store"
)

usage() {
  cat <<'EOF'
Usage:
  ./scripts/run_agents.sh [options] "task description"

Options:
  --model MODEL              Override the Codex model
  --only MODE                Run only one stage: all, code, review, test
  --parallel                 Run Review Agent and Test Agent in parallel after Code Agent
  --no-verify                Skip local verification commands
  --verify-cmd COMMAND       Add a custom verification command (repeatable)
  -h, --help                 Show this help

Examples:
  ./scripts/run_agents.sh "Add audit logging for password reset"
  ./scripts/run_agents.sh --model gpt-5.2 "Fix billing page validation"
  ./scripts/run_agents.sh --only review "Review the current working tree"
  ./scripts/run_agents.sh --parallel "Improve reset password error handling"
  ./scripts/run_agents.sh --verify-cmd "pytest tests/test_password_reset.py -q" "Harden auth flows"

Modes:
  all     Run Code Agent, then Review Agent and Test Agent, then verification
  code    Run only Code Agent, then optional verification
  review  Run only Review Agent on the current working tree changes
  test    Run only Test Agent on the current working tree changes

Outputs:
  .agent-runs/<timestamp>/

Notes:
  - Nested Codex runs use an isolated runtime under .agent-home/.codex by default.
  - The script will copy ~/.codex/auth.json into that runtime if needed.
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
  local -a cmd

  cmd=(
    codex exec
    --full-auto
    --color never
    -C "$ROOT"
    -o "$output_file"
  )

  if [[ -n "$MODEL" ]]; then
    cmd+=(-m "$MODEL")
  fi

  (
    export HOME="$AGENT_HOME_ROOT"
    export CODEX_HOME="$AGENT_CODEX_HOME"
    export XDG_CONFIG_HOME="$AGENT_XDG_CONFIG_HOME"
    "${cmd[@]}" - < "$prompt_file"
  )
}

prepare_codex_runtime() {
  local source_auth="${HOME}/.codex/auth.json"

  mkdir -p \
    "$AGENT_HOME_ROOT" \
    "$AGENT_CODEX_HOME" \
    "$AGENT_XDG_CONFIG_HOME" \
    "$AGENT_CODEX_HOME/memories" \
    "$AGENT_CODEX_HOME/sessions" \
    "$AGENT_CODEX_HOME/shell_snapshots" \
    "$AGENT_CODEX_HOME/tmp"

  if [[ -f "$source_auth" ]]; then
    cp "$source_auth" "$AGENT_CODEX_HOME/auth.json"
  fi

  cat > "$AGENT_CODEX_HOME/config.toml" <<EOF
model = "${MODEL:-gpt-5.4}"
model_reasoning_effort = "medium"
suppress_unstable_features_warning = true

[features]
default_mode_request_user_input = false
multi_agent = false
EOF
}

build_rsync_args() {
  local mode="$1"
  local pattern
  for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    printf '%s\0%s\0' "$mode" "$pattern"
  done
}

snapshot_repo() {
  local -a rsync_excludes
  mkdir -p "$BASELINE_DIR"
  while IFS= read -r -d '' item; do
    rsync_excludes+=("$item")
  done < <(build_rsync_args --exclude)

  rsync -a --delete "${rsync_excludes[@]}" "$ROOT/" "$BASELINE_DIR/"
}

collect_run_changes() {
  local name="$1"
  local changes_file="$RUN_DIR/${name}.changed-files.txt"
  local diff_file="$RUN_DIR/${name}.diff"
  local rsync_file="$RUN_DIR/${name}.rsync.txt"
  local -a rsync_excludes
  local -a diff_excludes
  local diff_status

  while IFS= read -r -d '' item; do
    rsync_excludes+=("$item")
  done < <(build_rsync_args --exclude)

  while IFS= read -r -d '' item; do
    diff_excludes+=("$item")
  done < <(build_rsync_args -x)

  rsync -ani --delete "${rsync_excludes[@]}" "$BASELINE_DIR/" "$ROOT/" > "$rsync_file"
  awk 'NF >= 2 {print $2}' "$rsync_file" | sed '/\/$/d' | sort -u > "$changes_file"

  set +e
  diff -ruN "${diff_excludes[@]}" "$BASELINE_DIR" "$ROOT" > "$diff_file"
  diff_status=$?
  set -e

  if [[ $diff_status -gt 1 ]]; then
    echo "Failed to collect diff for $name" >&2
    exit 1
  fi
}

collect_workspace_changes() {
  local name="$1"
  local changes_file="$RUN_DIR/${name}.changed-files.txt"
  local diff_file="$RUN_DIR/${name}.diff"
  local untracked_file="$RUN_DIR/${name}.untracked-files.txt"

  git -C "$ROOT" status --short --untracked-files=all > "$changes_file" || true
  git -C "$ROOT" diff --binary HEAD > "$diff_file" || true
  git -C "$ROOT" ls-files --others --exclude-standard > "$untracked_file" || true
}

write_summary() {
  local summary_file="$RUN_DIR/summary.txt"

  {
    echo "Run directory: $RUN_DIR"
    echo "Task: $TASK"
    echo "Mode: $RUN_MODE"
    echo "Model: ${MODEL:-default}"
    echo "Parallel review/test: $PARALLEL_REVIEW_TEST"
    echo "Verification enabled: $RUN_VERIFY"
    echo "Agent home root: $AGENT_HOME_ROOT"
    echo "Agent CODEX_HOME: $AGENT_CODEX_HOME"
  } > "$summary_file"
}

write_verify_commands() {
  local verify_file="$RUN_DIR/verification/commands.txt"

  mkdir -p "$RUN_DIR/verification"
  printf '%s\n' "${VERIFY_COMMANDS[@]}" > "$verify_file"
}

run_verification() {
  local verify_dir="$RUN_DIR/verification"
  local index=1
  local safe_name
  local command_file
  local output_file
  local exitcode_file
  local command
  local status

  mkdir -p "$verify_dir"
  write_verify_commands

  for command in "${VERIFY_COMMANDS[@]}"; do
    safe_name="$(printf '%02d' "$index")"
    command_file="$verify_dir/${safe_name}.command.txt"
    output_file="$verify_dir/${safe_name}.output.txt"
    exitcode_file="$verify_dir/${safe_name}.exitcode"

    printf '%s\n' "$command" > "$command_file"

    set +e
    (
      cd "$ROOT"
      bash -lc "$command"
    ) > "$output_file" 2>&1
    status=$?
    set -e

    printf '%s\n' "$status" > "$exitcode_file"
    index=$((index + 1))
  done
}

write_code_prompt() {
  local prompt_file="$1"

  cat > "$prompt_file" <<EOF
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
}

write_review_prompt() {
  local prompt_file="$1"
  local changes_file="$2"
  local diff_file="$3"
  local scope_note="$4"

  cat > "$prompt_file" <<EOF
$(cat "$AGENTS_DIR/review-agent.md")

## Review Task

$TASK

## Scope

$scope_note

- Repository root: \`$ROOT\`
- Changed files list: \`$changes_file\`
- Scoped diff: \`$diff_file\`

## Changed Files

\`\`\`text
$(cat "$changes_file")
\`\`\`

Return findings only.
EOF
}

write_test_prompt() {
  local prompt_file="$1"
  local changes_file="$2"
  local diff_file="$3"
  local scope_note="$4"
  local review_reference="$5"

  cat > "$prompt_file" <<EOF
$(cat "$AGENTS_DIR/test-agent.md")

## Test Task

$TASK

## Scope

$scope_note

- Repository root: \`$ROOT\`
- Changed files list: \`$changes_file\`
- Scoped diff: \`$diff_file\`
$review_reference

## Changed Files

\`\`\`text
$(cat "$changes_file")
\`\`\`

If feasible, run the most relevant test commands after updating tests.
EOF
}

run_code_stage() {
  CODE_PROMPT="$RUN_DIR/01-code-agent.prompt.md"
  CODE_OUTPUT="$RUN_DIR/01-code-agent.output.md"

  write_code_prompt "$CODE_PROMPT"

  echo "==> Running Code Agent"
  run_codex_exec "$CODE_PROMPT" "$CODE_OUTPUT"
  collect_run_changes "02-after-code"
}

run_review_stage_from_run() {
  REVIEW_PROMPT="$RUN_DIR/03-review-agent.prompt.md"
  REVIEW_OUTPUT="$RUN_DIR/03-review-agent.output.md"

  write_review_prompt \
    "$REVIEW_PROMPT" \
    "$RUN_DIR/02-after-code.changed-files.txt" \
    "$RUN_DIR/02-after-code.diff" \
    "Review only the changes introduced during this run since the baseline snapshot. Ignore any edits that existed before this run."

  echo "==> Running Review Agent"
  run_codex_exec "$REVIEW_PROMPT" "$REVIEW_OUTPUT"
}

run_test_stage_from_run() {
  TEST_PROMPT="$RUN_DIR/04-test-agent.prompt.md"
  TEST_OUTPUT="$RUN_DIR/04-test-agent.output.md"
  local review_reference=""

  if [[ -n "${REVIEW_OUTPUT:-}" && -f "${REVIEW_OUTPUT:-}" ]]; then
    review_reference="- Review Agent findings: \`$REVIEW_OUTPUT\`"
  fi

  write_test_prompt \
    "$TEST_PROMPT" \
    "$RUN_DIR/02-after-code.changed-files.txt" \
    "$RUN_DIR/02-after-code.diff" \
    "Write or update tests for the changes introduced during this run since the baseline snapshot. Focus on useful automated coverage." \
    "$review_reference"

  echo "==> Running Test Agent"
  run_codex_exec "$TEST_PROMPT" "$TEST_OUTPUT"
}

run_review_stage_from_workspace() {
  REVIEW_PROMPT="$RUN_DIR/01-review-agent.prompt.md"
  REVIEW_OUTPUT="$RUN_DIR/01-review-agent.output.md"

  collect_workspace_changes "00-workspace"
  write_review_prompt \
    "$REVIEW_PROMPT" \
    "$RUN_DIR/00-workspace.changed-files.txt" \
    "$RUN_DIR/00-workspace.diff" \
    "Review the current working tree changes. Inspect the working tree directly for untracked files listed in git status."

  echo "==> Running Review Agent"
  run_codex_exec "$REVIEW_PROMPT" "$REVIEW_OUTPUT"
}

run_test_stage_from_workspace() {
  TEST_PROMPT="$RUN_DIR/01-test-agent.prompt.md"
  TEST_OUTPUT="$RUN_DIR/01-test-agent.output.md"

  collect_workspace_changes "00-workspace"
  write_test_prompt \
    "$TEST_PROMPT" \
    "$RUN_DIR/00-workspace.changed-files.txt" \
    "$RUN_DIR/00-workspace.diff" \
    "Write or update tests for the current working tree changes. Inspect the working tree directly for untracked files listed in git status." \
    ""

  echo "==> Running Test Agent"
  run_codex_exec "$TEST_PROMPT" "$TEST_OUTPUT"
}

MODEL=""
RUN_MODE="all"
RUN_VERIFY=1
PARALLEL_REVIEW_TEST=0
VERIFY_COMMANDS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="${2:-}"
      shift 2
      ;;
    --only)
      RUN_MODE="${2:-}"
      shift 2
      ;;
    --parallel)
      PARALLEL_REVIEW_TEST=1
      shift
      ;;
    --no-verify)
      RUN_VERIFY=0
      shift
      ;;
    --verify-cmd)
      VERIFY_COMMANDS+=("${2:-}")
      shift 2
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

case "$RUN_MODE" in
  all|code|review|test)
    ;;
  *)
    echo "Invalid mode for --only: $RUN_MODE" >&2
    exit 1
    ;;
esac

if [[ ${#VERIFY_COMMANDS[@]} -eq 0 ]]; then
  VERIFY_COMMANDS=("${DEFAULT_VERIFY_COMMANDS[@]}")
fi

TASK="$*"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTS_DIR="$ROOT/agents"
RUNS_DIR="${AGENT_RUNS_DIR:-$ROOT/.agent-runs}"
AGENT_HOME_ROOT="${AGENT_HOME_ROOT:-$ROOT/.agent-home}"
AGENT_CODEX_HOME="${AGENT_CODEX_HOME:-$AGENT_HOME_ROOT/.codex}"
AGENT_XDG_CONFIG_HOME="${AGENT_XDG_CONFIG_HOME:-$AGENT_HOME_ROOT/.config}"
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
prepare_codex_runtime
write_summary

echo "Run directory: $RUN_DIR"
echo "Task: $TASK"
echo "Mode: $RUN_MODE"

git -C "$ROOT" status --short > "$RUN_DIR/git-status-before.txt" || true
git -C "$ROOT" diff > "$RUN_DIR/git-diff-before.patch" || true

case "$RUN_MODE" in
  all)
    snapshot_repo
    run_code_stage

    if [[ "$PARALLEL_REVIEW_TEST" -eq 1 ]]; then
      run_review_stage_from_run &
      review_pid=$!
      run_test_stage_from_run &
      test_pid=$!
      wait "$review_pid"
      wait "$test_pid"
    else
      run_review_stage_from_run
      run_test_stage_from_run
    fi

    collect_run_changes "05-after-test"
    ;;
  code)
    snapshot_repo
    run_code_stage
    collect_run_changes "05-after-test"
    ;;
  review)
    run_review_stage_from_workspace
    ;;
  test)
    run_test_stage_from_workspace
    ;;
esac

git -C "$ROOT" status --short > "$RUN_DIR/git-status-after.txt" || true
git -C "$ROOT" diff > "$RUN_DIR/git-diff-after.patch" || true

if [[ "$RUN_VERIFY" -eq 1 ]]; then
  echo "==> Running local verification"
  run_verification
fi

echo
echo "Workflow complete."
echo "Artifacts:"
if [[ -n "${CODE_OUTPUT:-}" ]]; then
  echo "  Code Agent output:   $CODE_OUTPUT"
fi
if [[ -n "${REVIEW_OUTPUT:-}" ]]; then
  echo "  Review Agent output: $REVIEW_OUTPUT"
fi
if [[ -n "${TEST_OUTPUT:-}" ]]; then
  echo "  Test Agent output:   $TEST_OUTPUT"
fi
if [[ -f "$RUN_DIR/05-after-test.diff" ]]; then
  echo "  Final diff:          $RUN_DIR/05-after-test.diff"
fi
if [[ "$RUN_VERIFY" -eq 1 ]]; then
  echo "  Verification logs:   $RUN_DIR/verification"
fi
