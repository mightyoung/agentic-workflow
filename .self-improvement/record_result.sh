#!/usr/bin/env bash
# Record a self-improvement run result to the results ledger.
# Uses Python fcntl for concurrent-safe appends (cross-platform).
#
# Usage:
#   record_result.sh --run-id <id> --hypothesis <text> --files <paths> \
#       --checks <summary> --status <keep|discard|rollback|stabilization> \
#       [--benchmark-evidence <ref>] [--notes <text>]
#
#   Shorthand:
#   record_result.sh <hypothesis> <files> <status> [notes]
#
# Examples:
#   record_result.sh "improve routing heuristics" "scripts/router.py" "keep" "routing +5%"
#   record_result.sh --run-id 20260401-01 --hypothesis "tighten REVIEWING" \
#       --files "scripts/workflow_engine.py" --checks "10/10 gates" --status keep \
#       --benchmark-evidence "tests/bench/ab_experiment_results/ab_experiment_20260408_223414.json" \
#       --notes "review targeting improved"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEDGER="$SCRIPT_DIR/results.tsv"
HELPER="$SCRIPT_DIR/_record_helper.py"

usage() {
    echo "Usage: record_result.sh [--run-id <id>] --hypothesis <text> --files <paths>"
    echo "       --checks <summary> --status <keep|discard|rollback|stabilization>"
    echo "       [--benchmark-evidence <ref>] [--notes <text>]"
    echo ""
    echo "   Shorthand: record_result.sh <hypothesis> <files> <status> [notes]"
    echo ""
    echo "Statuses: keep | discard | rollback | stabilization"
    exit 1
}

# Parse args
RUN_ID=""
HYPOTHESIS=""
FILES=""
CHECKS=""
STATUS=""
BENCHMARK_EVIDENCE=""
NOTES=""

if [[ "$#" -eq 0 ]]; then
    usage
fi

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    usage
fi

if [[ "$1" == "--"* ]]; then
    # Long-form args
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
            --run-id)
                RUN_ID="$2"; shift 2;;
            --hypothesis)
                HYPOTHESIS="$2"; shift 2;;
            --files)
                FILES="$2"; shift 2;;
            --checks)
                CHECKS="$2"; shift 2;;
            --status)
                STATUS="$2"; shift 2;;
            --benchmark-evidence)
                BENCHMARK_EVIDENCE="$2"; shift 2;;
            --notes)
                NOTES="$2"; shift 2;;
            --*)
                echo "Unknown option: $1"; usage;;
            *)
                echo "Unexpected arg: $1"; usage;;
        esac
    done
else
    # Shorthand: hypothesis files status [notes]
    if [[ "$#" -lt 3 ]]; then
        usage
    fi
    HYPOTHESIS="$1"
    FILES="$2"
    STATUS="$3"
    NOTES="${4:-}"
fi

# Validate required
if [[ -z "$HYPOTHESIS" ]]; then
    echo "Error: hypothesis is required"; usage
fi
if [[ -z "$FILES" ]]; then
    echo "Error: files is required"; usage
fi
if [[ -z "$STATUS" ]]; then
    echo "Error: status is required"; usage
fi

VALID_STATUSES="keep discard rollback stabilization in_progress"
if [[ ! " $VALID_STATUSES " =~ " $STATUS " ]]; then
    echo "Error: status must be one of: $VALID_STATUSES"
    usage
fi

# Generate run_id if not provided
if [[ -z "$RUN_ID" ]]; then
    RUN_ID="run-$(date -u +%Y%m%dT%H%M%S)"
fi

# Use Python helper for locked TSV append (cross-platform fcntl)
python3 - "$LEDGER" "$RUN_ID" "$HYPOTHESIS" "$FILES" "${CHECKS:-passed}" "$STATUS" "$BENCHMARK_EVIDENCE" "$NOTES" << 'PYEOF'
import sys
import fcntl
import os

ledger_path = sys.argv[1]
run_id = sys.argv[2]
hypothesis = sys.argv[3]
files = sys.argv[4]
checks = sys.argv[5]
status = sys.argv[6]
benchmark_evidence = sys.argv[7]
notes = sys.argv[8]

# TSV-safe cleaning: replace tabs and newlines with spaces
def tsv_clean(value):
    return ' '.join(value.replace('\t', ' ').replace('\n', ' ').split())

hypothesis = tsv_clean(hypothesis)
files = tsv_clean(files)
checks = tsv_clean(checks)
notes = tsv_clean(notes)
benchmark_evidence = tsv_clean(benchmark_evidence)

if benchmark_evidence:
    notes = f"benchmark_evidence={benchmark_evidence}" + (f" | {notes}" if notes else "")

lock_path = ledger_path + '.lock'

# Ensure ledger exists with proper header
header_line = "run_id\thypothesis\tfiles_changed\tchecks_passed\tstatus\tnotes"
if not os.path.exists(ledger_path):
    with open(ledger_path, 'w') as f:
        f.write(header_line + '\n')

# Lock and append
with open(lock_path, 'w') as lock_f:
    fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)  # exclusive lock
    try:
        with open(ledger_path, 'a') as f:
            row = '\t'.join([run_id, hypothesis, files, checks, status, notes])
            f.write(row + '\n')
    finally:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
        os.remove(lock_path)

print(f"Recorded: {run_id} | {status} | {hypothesis}", file=sys.stdout)
print(f"Ledger: {ledger_path}", file=sys.stdout)
PYEOF
