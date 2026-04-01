#!/usr/bin/env bash
# Record a self-improvement run result to the results ledger.
# Usage: record_result.sh --run-id <id> --hypothesis <text> --files <paths> --checks <summary> --status <keep|discard|rollback|stabilization> [--notes <text>]
# Or shorthand: record_result.sh <hypothesis> <files> <status> [notes]
#
# Examples:
#   record_result.sh "improve routing heuristics" "scripts/router.py" "keep" "routing accuracy +5%"
#   record_result.sh --run-id 20260401-01 --hypothesis "tighten REVIEWING" --files "scripts/workflow_engine.py" --checks "8/8 gates" --status keep --notes "review targeting improved"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEDGER="$SCRIPT_DIR/results.tsv"

usage() {
    echo "Usage: record_result.sh [--run-id <id>] --hypothesis <text> --files <paths> --checks <summary> --status <keep|discard|rollback|stabilization> [--notes <text>]"
    echo "   or: record_result.sh <hypothesis> <files> <status> [notes]"
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

VALID_STATUSES="keep discard rollback stabilization"
if [[ ! " $VALID_STATUSES " =~ " $STATUS " ]]; then
    echo "Error: status must be one of: $VALID_STATUSES"
    usage
fi

# Generate run_id if not provided
if [[ -z "$RUN_ID" ]]; then
    RUN_ID="run-$(date -u +%Y%m%dT%H%M%S)"
fi

# Escape tabs and newlines in fields
HYPOTHESIS_ESCAPED="${HYPOTHESIS//$'\t'/ }"
HYPOTHESIS_ESCAPED="${HYPOTHESIS_ESCAPED//$'\n'/ }"
FILES_ESCAPED="${FILES//$'\t'/ }"
CHECKS_ESCAPED="${CHECKS//$'\t'/ }"
NOTES_ESCAPED="${NOTES//$'\t'/ }"
NOTES_ESCAPED="${NOTES_ESCAPED//$'\n'/ }"

# Append TSV row
printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$RUN_ID" \
    "$HYPOTHESIS_ESCAPED" \
    "$FILES_ESCAPED" \
    "${CHECKS:-passed}" \
    "$STATUS" \
    "$NOTES_ESCAPED" >> "$LEDGER"

echo "Recorded: $RUN_ID | $STATUS | $HYPOTHESIS_ESCAPED"
echo "Ledger: $LEDGER"
