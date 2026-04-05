#!/usr/bin/env bash
# observe.sh — PreToolUse hook: record AI tool usage patterns
#
# Claude Code calls this before every tool invocation.
# Input: JSON via stdin with shape {"tool_name": "...", "tool_input": {...}}
# Output: must exit 0 to allow the tool call to proceed.
#
# Writes one JSON-line per call to .observations.jsonl for later
# pattern extraction by evaluate-session.sh (Stop hook).

set -euo pipefail

WORKDIR="${PWD}"
OBS_FILE="${WORKDIR}/.observations.jsonl"
MAX_OBS=2000   # rolling window — older entries are trimmed by evaluate-session.sh

# Read the hook event from stdin (may be empty in test runs)
INPUT="$(cat 2>/dev/null || true)"

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Extract tool_name safely (python3 is always available in Claude Code)
TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name','unknown'))" \
  2>/dev/null || echo "unknown")"

# Append observation (fire-and-forget — never block the tool call)
printf '{"timestamp":"%s","tool":"%s","type":"pre_tool_use"}\n' \
  "$TIMESTAMP" "$TOOL_NAME" >> "$OBS_FILE" 2>/dev/null || true

# Trim file if it grows beyond MAX_OBS lines (prevent unbounded growth)
if [ -f "$OBS_FILE" ]; then
    LINE_COUNT="$(wc -l < "$OBS_FILE" 2>/dev/null || echo 0)"
    if [ "$LINE_COUNT" -gt "$MAX_OBS" ]; then
        tail -"$MAX_OBS" "$OBS_FILE" > "${OBS_FILE}.tmp" \
          && mv "${OBS_FILE}.tmp" "$OBS_FILE" 2>/dev/null || true
    fi
fi

# Always allow (must exit 0 for PreToolUse)
exit 0
