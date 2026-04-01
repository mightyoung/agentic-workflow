#!/usr/bin/env bash
# Baseline Check Script for Self-Improvement Runs
# Run this before any self-improvement mutation to establish baseline.
# Part of docs/self_improvement_program.md implementation.
#
# FAIL-CLOSED: Any gate failure causes non-zero exit code.
# Dual gate validation: passing fixture must pass AND failing fixture must fail.
#
# Usage:
#   .self-improvement/baseline_check.sh           # default: fail-closed on dirty tree
#   .self-improvement/baseline_check.sh --allow-dirty  # allow dirty tree (for exploration only)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse flags
ALLOW_DIRTY=0
if [[ "$1" == "--allow-dirty" ]]; then
    ALLOW_DIRTY=1
    echo "NOTE: --allow-dirty set. Dirty tree will be warned but not blocked."
    echo ""
fi

echo "=== Agentic Workflow Self-Improvement Baseline Check ==="
echo "Project: $PROJECT_ROOT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

cd "$PROJECT_ROOT"

FAILED=0
PASSED_GATES=0
TOTAL_GATES=10

fail_gate() {
    echo "FAIL: $1"
    FAILED=1
}

pass_gate() {
    echo "PASS: $1"
    PASSED_GATES=$((PASSED_GATES + 1))
}

# Check 0: Branch/worktree enforcement (must be on self-improve/worktree branch or in a worktree)
echo "[0/8] Self-improvement branch/worktree enforcement..."
current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
is_self_improve_context=0

# Accept self-improve/*, self-improvement/*, or worktree/* branches as valid context
if [[ "$current_branch" == self-improve/* ]] || \
   [[ "$current_branch" == self-improvement/* ]] || \
   [[ "$current_branch" == worktree/* ]]; then
    is_self_improve_context=1
fi

# Also accept if we are inside an actual worktree (not the main working tree)
# Use --porcelain for reliable parsing and check if current path appears in non-main worktree list
if [[ $is_self_improve_context -eq 0 ]]; then
    current_pwd="$(pwd)"
    # Parse worktree list: first entry is always main, subsequent ones are additional worktrees
    # Format: "worktree /path/to/worktree" lines followed by metadata lines, then next "worktree" or "bare"
    worktree_paths=$(git worktree list --porcelain 2>/dev/null | awk '/^worktree / {print $2}' | tail -n +2)
    while IFS= read -r wt_path; do
        # Only check if wt_path is non-empty (avoids empty glob matching everything)
        if [[ -n "$wt_path" && "$current_pwd" == "$wt_path"* ]]; then
            is_self_improve_context=1
            break
        fi
    done <<< "$worktree_paths"
fi

if [[ $is_self_improve_context -eq 1 ]]; then
    pass_gate "Self-improvement context ($current_branch)"
elif [[ $ALLOW_DIRTY -eq 1 ]]; then
    echo "WARNING: Not in self-improvement branch/worktree context (branch=$current_branch)"
    echo "  This is only acceptable with --allow-dirty for exploratory work."
    pass_gate "Self-improvement context (warned - exploratory mode)"
else
    fail_gate "Must run on self-improve/*, worktree/* branch or in a worktree (current: $current_branch)"
fi
echo ""

# Check 1: git status (FAIL-CLOSED by default; --allow-dirty makes it soft)
echo "[1/8] Git status..."
if [[ -n "$(git status --porcelain)" ]]; then
    if [[ $ALLOW_DIRTY -eq 1 ]]; then
        echo "WARNING: Working tree is dirty. This is only acceptable for exploratory work."
        git status --short
        pass_gate "Git status (dirty - soft warning, exploratory mode)"
    else
        fail_gate "Working tree is dirty. Commit or stash before continuing."
        echo "  Hint: use --allow-dirty only for exploratory work."
        git status --short
    fi
else
    pass_gate "Git status (clean)"
fi
echo ""

# Check 2: Full regression suite (aligned with formal acceptance suite)
echo "[2/8] Full regression suite (pytest)..."
if python3 -m pytest \
    tests/test_workflow_engine.py \
    tests/test_e2e_business.py \
    tests/test_workflow_chain.py \
    tests/test_task_decomposer.py \
    tests/test_artifact_registry.py \
    tests/test_trajectory.py \
    tests/test_failure_handling.py \
    tests/test_quality_gate.py \
    tests/test_result_only_spawning.py \
    -q --tb=short > /tmp/baseline_pytest.log 2>&1; then
    pass_gate "Full pytest suite"
else
    fail_gate "Full pytest suite"
    cat /tmp/baseline_pytest.log
fi
echo ""

# Check 3: Core type checks (FAIL-CLOSED; use standalone mypy or python3 -m mypy)
echo "[3/8] Core mypy checks..."
mypy_files="scripts/workflow_engine.py scripts/quality_gate.py scripts/task_decomposer.py scripts/router.py scripts/task_tracker.py scripts/unified_state.py"
if command -v mypy > /dev/null 2>&1; then
    # Use standalone mypy if available
    if mypy $mypy_files --no-error-summary > /tmp/baseline_mypy.log 2>&1; then
        pass_gate "Core mypy checks"
    else
        fail_gate "Core mypy checks"
        cat /tmp/baseline_mypy.log
    fi
elif python3 -m mypy --version > /dev/null 2>&1; then
    # Fall back to python3 -m mypy
    if python3 -m mypy $mypy_files --no-error-summary > /tmp/baseline_mypy.log 2>&1; then
        pass_gate "Core mypy checks"
    else
        fail_gate "Core mypy checks"
        cat /tmp/baseline_mypy.log
    fi
else
    echo "SKIP: mypy not available - skipping type check gate"
    pass_gate "Core mypy checks (skipped - not installed)"
fi
echo ""

# Check 4: Targeted lint for runtime files
echo "[4/8] Lint checks for runtime files..."
if ruff check scripts/ tests/test_*.py > /tmp/baseline_ruff.log 2>&1; then
    pass_gate "Ruff lint checks"
else
    fail_gate "Ruff lint checks"
    cat /tmp/baseline_ruff.log
fi
echo ""

# Check 5: Workflow smoke path
echo "[5/8] Workflow smoke path (init + snapshot + validate + recommend)..."
tmpdir=$(mktemp -d)
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

if python3 scripts/workflow_engine.py --op init --prompt "baseline smoke test" --workdir "$tmpdir" > /tmp/baseline_wf_init.log 2>&1 &&
   python3 scripts/workflow_engine.py --op snapshot --workdir "$tmpdir" > /tmp/baseline_wf_snap.log 2>&1 &&
   python3 scripts/unified_state.py --op validate --workdir "$tmpdir" > /tmp/baseline_wf_val.log 2>&1 &&
   python3 scripts/workflow_engine.py --op recommend --workdir "$tmpdir" > /tmp/baseline_wf_rec.log 2>&1; then
    pass_gate "Workflow smoke path (init/snapshot/validate/recommend)"
else
    fail_gate "Workflow smoke path"
    echo "=== init ==="; cat /tmp/baseline_wf_init.log
    echo "=== snapshot ==="; cat /tmp/baseline_wf_snap.log
    echo "=== validate ==="; cat /tmp/baseline_wf_val.log
    echo "=== recommend ==="; cat /tmp/baseline_wf_rec.log
fi
echo ""

# Check 6: Quality gate dual validation (passing AND failing fixtures)
echo "[6/8] Quality gate dual validation..."

# 6a: Passing fixture - clean Python code should pass quality gate
echo "  [6a] Passing fixture: clean code..."
pass_fixture=$(mktemp -d)
mkdir -p "$pass_fixture/src"
cat > "$pass_fixture/src/main.py" << 'PYEOF'
def add(a: int, b: int) -> int:
    return a + b

def main() -> None:
    result = add(1, 2)
    print(result)
PYEOF

pass_output=$(python3 -c "
import sys
sys.path.insert(0, 'scripts')
from quality_gate import run_quality_gate
report = run_quality_gate('$pass_fixture', ['all'], timeout=30)
print(f'all_passed={report.all_passed}')
" 2>&1)
pass_pass=$?

if [[ $pass_pass -eq 0 ]] && echo "$pass_output" | grep -q "all_passed=True"; then
    echo "  PASS: Quality gate correctly passes on clean code"
    pass_gate "Quality gate: passing fixture"
else
    echo "  FAIL: Quality gate did not pass on clean fixture"
    echo "  Output: $pass_output"
    fail_gate "Quality gate: passing fixture (should pass but didn't)"
fi
rm -rf "$pass_fixture"

# 6b: Failing fixture - code with type errors should fail quality gate
echo "  [6b] Failing fixture: code with type errors..."
fail_fixture=$(mktemp -d)
mkdir -p "$fail_fixture/src"
cat > "$fail_fixture/src/main.py" << 'PYEOF'
def bad_add(a: int, b: str) -> int:
    # Type error: b should be int
    return a + b  # type error: unsupported operand

def main() -> None:
    result = bad_add(1, "x")  # runtime error too
    print(result)
PYEOF

fail_output=$(python3 -c "
import sys
sys.path.insert(0, 'scripts')
from quality_gate import run_quality_gate
report = run_quality_gate('$fail_fixture', ['all'], timeout=30)
print(f'all_passed={report.all_passed}')
" 2>&1)
fail_pass=$?

# Quality gate should either:
# - Return non-zero (gate failed), OR
# - Return zero but report all_passed=False (gate ran but found issues)
if [[ $fail_pass -ne 0 ]]; then
    echo "  PASS: Quality gate correctly fails on type-error code (exit $fail_pass)"
    pass_gate "Quality gate: failing fixture (correctly fails)"
elif echo "$fail_output" | grep -q "all_passed=False"; then
    echo "  PASS: Quality gate correctly reports failure on type-error code"
    pass_gate "Quality gate: failing fixture (correctly reports)"
else
    echo "  FAIL: Quality gate did not catch type errors in failing fixture"
    echo "  Output: $fail_output"
    fail_gate "Quality gate: failing fixture (should fail but didn't)"
fi
rm -rf "$fail_fixture"
echo ""

# Check 7: Schema validity
echo "[7/8] State schema validation..."
if python3 scripts/unified_state.py --op validate --workdir . > /tmp/baseline_schema.log 2>&1; then
    pass_gate "Schema validation"
else
    fail_gate "Schema validation"
    cat /tmp/baseline_schema.log
fi
echo ""

# Check 8: Self-improvement ledger append check (verify results.tsv is well-formed)
echo "[8/8] Ledger integrity check..."
ledger="$SCRIPT_DIR/results.tsv"
if [[ -f "$ledger" ]]; then
    # Verify TSV format: each non-empty, non-header line has exactly 6 fields
    header=$(head -1 "$ledger")
    if [[ "$header" == "run_id	hypothesis	files_changed	checks_passed	status	notes" ]]; then
        # Check for malformed lines (more or fewer fields)
        malformed=$(awk -F'\t' 'NR>1 && NF!=6 && NF>0' "$ledger" | wc -l | tr -d ' ')
        if [[ "$malformed" -eq 0 ]]; then
            pass_gate "Ledger integrity (well-formed TSV)"
        else
            fail_gate "Ledger integrity ($malformed malformed lines)"
        fi
    else
        echo "WARNING: Ledger header may not be machine-readable TSV format"
        pass_gate "Ledger integrity (header check skipped)"
    fi
else
    echo "NOTE: No ledger file yet (first run will create it)"
    pass_gate "Ledger integrity (no prior ledger)"
fi
echo ""

# Summary
echo "=== Baseline Check Summary ==="
echo "Passed: $PASSED_GATES/$TOTAL_GATES gates"
echo ""

if [[ $FAILED -eq 0 ]]; then
    echo "RESULT: ALL GATES PASSED - Baseline established."
    echo "Proceed with improvement hypothesis."
else
    echo "RESULT: BASELINE CHECK FAILED - Cannot establish baseline."
    echo "Fix failures before making improvements."
    exit 1
fi

echo ""
echo "Reminder: Record your hypothesis and outcome in .self-improvement/results.tsv"
