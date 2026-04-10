#!/usr/bin/env bash
# Self-Improvement Runner - Unified entry point for self-improvement runs
#
# Usage:
#   self_improve.sh --hypothesis <text> [--zone B] [--allow-dirty]
#   BENCHMARK_EVIDENCE=<ref> self_improve.sh --hypothesis <text>
#
# This script:
#   1. Creates a dedicated self-improve branch (or validates current context)
#   2. Runs the baseline check
#   3. Records the run in the ledger
#
# Requirements:
#   - Must be run from the git repo root
#   - Git must be available

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LEDGER="$SCRIPT_DIR/results.tsv"
RECORD_HELPER="$SCRIPT_DIR/record_result.sh"
BENCHMARK_EVIDENCE="${BENCHMARK_EVIDENCE:-}"
SKILL_PROPOSAL=""

usage() {
    echo "Self-Improvement Runner"
    echo ""
    echo "Usage: $0 --hypothesis <text> [--zone B|A|C] [--allow-dirty]"
    echo ""
    echo "Options:"
    echo "  --hypothesis <text>  What this improvement run tries to achieve (required)"
    echo "  --zone <A|B|C>       Which zone to target (default: B - Guided Mutable Surface)"
    echo "  --allow-dirty        Allow dirty tree (only for exploratory work)"
    echo "  BENCHMARK_EVIDENCE   Optional benchmark report path/reference to attach"
    echo "  --help, -h           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --hypothesis 'improve routing heuristics for complex tasks'"
    echo "  $0 --hypothesis 'add new phase skill' --zone A"
    exit 0
}

# Parse args
HYPOTHESIS=""
ZONE="B"
ALLOW_DIRTY=0

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --hypothesis)
            HYPOTHESIS="$2"; shift 2;;
        --zone)
            ZONE="$2"; shift 2;;
        --allow-dirty)
            ALLOW_DIRTY=1; shift;;
        --help|-h)
            usage;;
        *)
            echo "Unknown option: $1"; usage;;
    esac
done

if [[ -z "$HYPOTHESIS" ]]; then
    echo "Error: --hypothesis is required"
    usage
fi

BENCHMARK_ARGS=()
if [[ -n "$BENCHMARK_EVIDENCE" ]]; then
    BENCHMARK_ARGS+=(--benchmark-evidence "$BENCHMARK_EVIDENCE")
fi

cd "$PROJECT_ROOT"

echo "=== Self-Improvement Runner ==="
echo "Hypothesis: $HYPOTHESIS"
echo "Target Zone: $ZONE"
echo ""

# Step 1: Determine run context (existing branch or new branch)
current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
run_id="run-$(date -u +%Y%m%dT%H%M%S)"
new_branch=""
is_new_branch=0

# Check if we should create a new branch
if [[ "$current_branch" == "main" ]] || [[ "$current_branch" == "main" ]] && [[ $ALLOW_DIRTY -eq 0 ]]; then
    # We're on main - create a self-improve branch
    slug=$(echo "$HYPOTHESIS" | sed 's/[^a-zA-Z0-9]/_/g' | cut -c1-30)
    new_branch="self-improve/$(date +%Y%m%d)-${slug}"
    echo "[1/4] Creating self-improvement branch: $new_branch"
    git checkout -b "$new_branch" > /dev/null 2>&1
    is_new_branch=1
    echo "  Created branch: $new_branch"
elif [[ "$current_branch" == self-improve/* ]] || [[ "$current_branch" == self-improvement/* ]] || [[ "$current_branch" == worktree/* ]]; then
    echo "[1/4] Already on self-improvement branch: $current_branch"
    new_branch="$current_branch"
else
    echo "[1/4] WARNING: Running on '$current_branch' - creating self-improve branch anyway"
    slug=$(echo "$HYPOTHESIS" | sed 's/[^a-zA-Z0-9]/_/g' | cut -c1-30)
    new_branch="self-improve/$(date +%Y%m%d)-${slug}"
    git checkout -b "$new_branch" > /dev/null 2>&1
    is_new_branch=1
    echo "  Created branch: $new_branch"
fi
echo ""

# Step 2: Run baseline check
echo "[2/4] Running baseline check..."
baseline_args="--allow-dirty"
if [[ $ALLOW_DIRTY -eq 0 ]]; then
    baseline_args=""
fi
if bash "$SCRIPT_DIR/baseline_check.sh" $baseline_args > /tmp/baseline_run.log 2>&1; then
    baseline_result="PASS"
    echo "  Baseline: PASS"
else
    baseline_result="FAIL"
    echo "  Baseline: FAIL"
    echo "  See /tmp/baseline_run.log for details"
fi
echo ""

# Step 3: Determine status
if [[ "$baseline_result" == "FAIL" ]]; then
    status="discard"
    echo "[3/4] Baseline failed - marking as discard"
    echo "[4/4] Recording result..."

    "$RECORD_HELPER" \
        --run-id "$run_id" \
        --hypothesis "$HYPOTHESIS" \
        --files "baseline check failed" \
        --checks "0/10 gates passed" \
        --status "$status" \
        "${BENCHMARK_ARGS[@]}" \
        --notes "Baseline failed before any changes - context not ready"

    echo ""
    echo "=== Result: DISCARD ==="
    echo "Baseline check failed. Fix the issues before making improvements."
    echo "See /tmp/baseline_run.log for details."
    exit 1
fi

echo "[3/4] Baseline passed - ready for improvement"
echo ""
echo "=== Baseline PASSED - Ready for improvement ==="
echo ""
if [[ -n "$BENCHMARK_EVIDENCE" ]]; then
    echo "[3/4] Generating skill evolution proposal from benchmark evidence..."
    SKILL_PROPOSAL=$(python3 "$PROJECT_ROOT/scripts/skill_evolution.py" --benchmark "$BENCHMARK_EVIDENCE" --output-dir "$PROJECT_ROOT/knowledge/skill_proposals")
    echo "  Proposal: $SKILL_PROPOSAL"
    echo ""
fi

echo "Run ID: $run_id"
echo "Branch: $new_branch"
echo ""
echo "Next steps:"
echo "  1. Make your Zone $ZONE changes"
echo "  2. Run: .self-improvement/baseline_check.sh $baseline_args"
echo "  3. If gates pass: .self-improvement/record_result.sh \\"
echo "       --run-id $run_id \\"
echo "       --hypothesis '$HYPOTHESIS' \\"
echo "       --files '<your changed files>' \\"
echo "       --checks '10/10 gates' \\"
echo "       --status keep \\"
echo "       --notes '<your notes>'"
echo ""

# Step 4: Pre-record the run start in ledger
echo "[4/4] Recording run start..."
files_placeholder="(no changes yet)"
notes_text="Zone $ZONE improvement - branch: $new_branch"
if [[ -n "$BENCHMARK_EVIDENCE" ]]; then
    notes_text="benchmark_evidence=$BENCHMARK_EVIDENCE | ${notes_text}"
fi
if [[ -n "$SKILL_PROPOSAL" ]]; then
    notes_text="skill_proposal=$SKILL_PROPOSAL | ${notes_text}"
fi
"$RECORD_HELPER" \
    --run-id "$run_id" \
    --hypothesis "$HYPOTHESIS" \
    --files "$files_placeholder" \
    --checks "10/10 baseline gates passed" \
    --status "in_progress" \
    "${BENCHMARK_ARGS[@]}" \
    --notes "$notes_text"

echo ""
echo "Run initialized: $run_id"
echo "Branch: $new_branch"
