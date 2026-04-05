#!/usr/bin/env bash
# evaluate-session.sh — Stop hook: extract patterns from session observations
#
# Claude Code calls this once when a session ends (stop_reason = end_turn / tool_use_limit / etc.).
# Input: JSON via stdin with shape {"stop_reason": "...", "usage": {...}}
# Output: exit 0 always (Stop hooks cannot block session teardown).
#
# What it does:
#   1. Reads .observations.jsonl accumulated by observe.sh during this session
#   2. Computes tool-usage summary for the session
#   3. Writes a structured experience entry to memory_longterm.py
#   4. Rotates .observations.jsonl to keep only last 1000 lines

set -euo pipefail

WORKDIR="${PWD}"
OBS_FILE="${WORKDIR}/.observations.jsonl"
MEMORY_SCRIPT="${WORKDIR}/scripts/memory_longterm.py"

# Guard: nothing to do if observation file or memory script is absent
[ -f "$OBS_FILE" ]      || exit 0
[ -f "$MEMORY_SCRIPT" ] || exit 0

# ------------------------------------------------------------------
# 1. Count tool usage for this session (last 500 lines = ~1 session)
# ------------------------------------------------------------------
TOOL_SUMMARY="$(python3 - <<'PYEOF'
import json, sys, os, collections

obs_file = os.path.join(os.environ.get("PWD", "."), ".observations.jsonl")
try:
    tools: list[str] = []
    with open(obs_file, encoding="utf-8") as f:
        lines = f.readlines()
    # Only the most recent 500 observations belong to this session
    for line in lines[-500:]:
        try:
            d = json.loads(line)
            tools.append(d.get("tool", "unknown"))
        except Exception:
            pass
    counts = collections.Counter(tools)
    top = counts.most_common(5)
    if top:
        print(", ".join(f"{t}:{c}" for t, c in top))
except Exception:
    pass
PYEOF
2>/dev/null || true)"

# ------------------------------------------------------------------
# 2. Write session summary to long-term memory (confidence = 0.4
#    because it is automatically inferred, not manually curated)
# ------------------------------------------------------------------
if [ -n "$TOOL_SUMMARY" ]; then
    python3 "$MEMORY_SCRIPT" \
      --op add-experience \
      --exp "Session tool-usage pattern: ${TOOL_SUMMARY}" \
      --confidence 0.4 \
      --scope global \
      2>/dev/null || true
fi

# ------------------------------------------------------------------
# 3. Rotate .observations.jsonl — keep last 1000 lines
# ------------------------------------------------------------------
if [ -f "$OBS_FILE" ]; then
    tail -1000 "$OBS_FILE" > "${OBS_FILE}.tmp" \
      && mv "${OBS_FILE}.tmp" "$OBS_FILE" 2>/dev/null || true
fi

exit 0
