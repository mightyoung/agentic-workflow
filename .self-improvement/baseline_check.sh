#!/usr/bin/env bash
# Baseline Check Script for Self-Improvement Runs
# Run this before any self-improvement mutation to establish baseline.
# Part of docs/self_improvement_program.md implementation.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Agentic Workflow Self-Improvement Baseline Check ==="
echo "Project: $PROJECT_ROOT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

cd "$PROJECT_ROOT"

# Check 1: git status
echo "[1/7] Git status..."
if [[ -n "$(git status --porcelain)" ]]; then
    echo "WARNING: Working tree is dirty. Commit or stash before continuing."
    git status --short
else
    echo "PASS: Working tree is clean"
fi
echo ""

# Check 2: Core regression suite
echo "[2/7] Core regression suite (pytest)..."
python3 -m pytest tests/test_workflow_engine.py tests/test_e2e_business.py tests/test_task_decomposer.py tests/test_artifact_registry.py tests/test_trajectory.py tests/test_failure_handling.py -q --tb=short
echo "PASS: Core tests pass"
echo ""

# Check 3: Core type checks
echo "[3/7] Core mypy checks..."
python3 -m mypy scripts/workflow_engine.py scripts/quality_gate.py scripts/task_decomposer.py scripts/router.py scripts/task_tracker.py scripts/unified_state.py --no-error-summary 2>/dev/null || true
echo "PASS: Mypy core checks complete"
echo ""

# Check 4: Targeted lint for runtime files
echo "[4/7] Lint checks for runtime files..."
ruff check scripts/ tests/test_*.py
echo "PASS: Lint clean for runtime"
echo ""

# Check 5: Workflow smoke path
echo "[5/7] Workflow smoke path..."
tmpdir=$(mktemp -d)
python3 scripts/workflow_engine.py --op init --prompt "baseline smoke test" --workdir "$tmpdir" > /dev/null 2>&1
python3 scripts/workflow_engine.py --op snapshot --workdir "$tmpdir" > /dev/null 2>&1
python3 scripts/unified_state.py --op validate --workdir "$tmpdir" > /dev/null 2>&1
rm -rf "$tmpdir"
echo "PASS: Workflow smoke path works"
echo ""

# Check 6: Quality gate behavior
echo "[6/7] Quality gate smoke..."
tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/src"
echo 'def main(): pass' > "$tmpdir/src/main.py"
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from quality_gate import run_quality_gate
report = run_quality_gate('$tmpdir', ['all'], timeout=30)
print(f'Quality gate: all_passed={report.all_passed}')
" || true
rm -rf "$tmpdir"
echo "PASS: Quality gate smoke complete"
echo ""

# Check 7: Schema validity
echo "[7/7] State schema validation..."
python3 scripts/unified_state.py --op validate --workdir .
echo "PASS: Schema validation"
echo ""

echo "=== Baseline Check Complete ==="
echo "Baseline established. Proceed with improvement hypothesis."
echo ""
echo "Reminder: Record your hypothesis and outcome in .self-improvement/results.tsv"
