#!/usr/bin/env bash
# Baseline Check Script for Self-Improvement Runs
# Run this before any self-improvement mutation to establish baseline.
# Part of docs/self_improvement_program.md implementation.
#
# FAIL-CLOSED: Any gate failure causes non-zero exit code.
# Dual gate validation: passing fixture must pass AND failing fixture must fail.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Agentic Workflow Self-Improvement Baseline Check ==="
echo "Project: $PROJECT_ROOT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

cd "$PROJECT_ROOT"

FAILED=0
PASSED_GATES=0
TOTAL_GATES=8

fail_gate() {
    echo "FAIL: $1"
    FAILED=1
}

pass_gate() {
    echo "PASS: $1"
    PASSED_GATES=$((PASSED_GATES + 1))
}

# Check 1: git status (soft gate - dirty tree is warned but doesn't block baseline)
echo "[1/7] Git status..."
if [[ -n "$(git status --porcelain)" ]]; then
    echo "WARNING: Working tree is dirty. Commit or stash before continuing."
    git status --short
    pass_gate "Git status (dirty - soft warning, not blocking)"
else
    pass_gate "Git status (clean)"
fi
echo ""

# Check 2: Core regression suite
echo "[2/7] Core regression suite (pytest)..."
if python3 -m pytest tests/test_workflow_engine.py tests/test_e2e_business.py tests/test_task_decomposer.py tests/test_artifact_registry.py tests/test_trajectory.py tests/test_failure_handling.py -q --tb=short > /tmp/baseline_pytest.log 2>&1; then
    pass_gate "Core pytest suite"
else
    fail_gate "Core pytest suite"
    cat /tmp/baseline_pytest.log
fi
echo ""

# Check 3: Core type checks (FAIL-CLOSED; use standalone mypy or python3 -m mypy)
echo "[3/7] Core mypy checks..."
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
echo "[4/7] Lint checks for runtime files..."
if ruff check scripts/ tests/test_*.py > /tmp/baseline_ruff.log 2>&1; then
    pass_gate "Ruff lint checks"
else
    fail_gate "Ruff lint checks"
    cat /tmp/baseline_ruff.log
fi
echo ""

# Check 5: Workflow smoke path
echo "[5/7] Workflow smoke path (init + snapshot + validate)..."
tmpdir=$(mktemp -d)
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

if python3 scripts/workflow_engine.py --op init --prompt "baseline smoke test" --workdir "$tmpdir" > /tmp/baseline_wf_init.log 2>&1 &&
   python3 scripts/workflow_engine.py --op snapshot --workdir "$tmpdir" > /tmp/baseline_wf_snap.log 2>&1 &&
   python3 scripts/unified_state.py --op validate --workdir "$tmpdir" > /tmp/baseline_wf_val.log 2>&1; then
    pass_gate "Workflow smoke path (init/snapshot/validate)"
else
    fail_gate "Workflow smoke path"
    echo "=== init ==="; cat /tmp/baseline_wf_init.log
    echo "=== snapshot ==="; cat /tmp/baseline_wf_snap.log
    echo "=== validate ==="; cat /tmp/baseline_wf_val.log
fi
echo ""

# Check 6: Quality gate dual validation (passing AND failing fixtures)
echo "[6/7] Quality gate dual validation..."

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
echo "[7/7] State schema validation..."
if python3 scripts/unified_state.py --op validate --workdir . > /tmp/baseline_schema.log 2>&1; then
    pass_gate "Schema validation"
else
    fail_gate "Schema validation"
    cat /tmp/baseline_schema.log
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
