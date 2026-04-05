#!/usr/bin/env bash
# evaluate-session.sh — Stop hook: extract patterns from session observations
#
# Claude Code calls this once when a session ends (stop_reason = end_turn / tool_use_limit / etc.).
# Input: JSON via stdin with shape {"stop_reason": "...", "usage": {...}}
# Output: exit 0 always (Stop hooks cannot block session teardown).
#
# P1 upgrade (MAGMA Slow Path):
#   1. Tool-usage summary   → confidence=0.4 global experience (same as before)
#   2. Structural patterns  → analyse which tool sequences correlate with success/failure
#                             and write higher-confidence structured experiences
#   3. Graph index rebuild  → trigger build-graph-indexes if new Reflexion entries added
#   4. Rotate observations  → keep last 1000 lines

set -euo pipefail

WORKDIR="${PWD}"
OBS_FILE="${WORKDIR}/.observations.jsonl"
MEMORY_SCRIPT="${WORKDIR}/scripts/memory_longterm.py"

# Guard: nothing to do if observation file or memory script is absent
[ -f "$OBS_FILE" ]      || exit 0
[ -f "$MEMORY_SCRIPT" ] || exit 0

# ------------------------------------------------------------------
# 1. Tool-usage summary (fast path — same as before)
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

if [ -n "$TOOL_SUMMARY" ]; then
    python3 "$MEMORY_SCRIPT" \
      --op add-experience \
      --exp "Session tool-usage pattern: ${TOOL_SUMMARY}" \
      --confidence 0.4 \
      --scope global \
      2>/dev/null || true
fi

# ------------------------------------------------------------------
# 2. Structural pattern extraction (slow path — P1 upgrade)
#    Detect: heavy Edit+Bash combos suggest implementation sessions;
#    heavy Read combos suggest research sessions.
#    Write a scoped project experience with confidence=0.5.
# ------------------------------------------------------------------
SESSION_PATTERN="$(python3 - <<'PYEOF'
import json, os, collections

obs_file = os.path.join(os.environ.get("PWD", "."), ".observations.jsonl")
try:
    tools: list[str] = []
    with open(obs_file, encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[-500:]:
        try:
            d = json.loads(line)
            tools.append(d.get("tool", "unknown"))
        except Exception:
            pass

    total = len(tools)
    if total < 5:
        raise SystemExit(0)

    counts = collections.Counter(tools)
    edit_pct  = counts.get("Edit",  0) / total
    bash_pct  = counts.get("Bash",  0) / total
    read_pct  = counts.get("Read",  0) / total
    write_pct = counts.get("Write", 0) / total
    grep_pct  = counts.get("Grep",  0) / total

    # Classify session intent from dominant tool pattern
    if edit_pct + bash_pct > 0.55:
        pattern = f"Implementation session: Edit={edit_pct:.0%} Bash={bash_pct:.0%} total={total}"
    elif read_pct + grep_pct > 0.55:
        pattern = f"Research session: Read={read_pct:.0%} Grep={grep_pct:.0%} total={total}"
    elif write_pct > 0.20:
        pattern = f"Creation session: Write={write_pct:.0%} total={total}"
    else:
        pattern = f"Mixed session: top={counts.most_common(3)} total={total}"

    print(pattern)
except SystemExit:
    pass
except Exception:
    pass
PYEOF
2>/dev/null || true)"

if [ -n "$SESSION_PATTERN" ]; then
    python3 "$MEMORY_SCRIPT" \
      --op add-experience \
      --exp "Trigger:session_end Signal:${SESSION_PATTERN}" \
      --confidence 0.5 \
      --scope project \
      2>/dev/null || true
fi

# ------------------------------------------------------------------
# 3. Rebuild graph indexes (if .memory_index.jsonl was updated this session)
#    Only rebuild if the index file is newer than the causal index
# ------------------------------------------------------------------
INDEX_FILE="${WORKDIR}/.memory_index.jsonl"
CAUSAL_FILE="${WORKDIR}/.memory_causal_index.json"

if [ -f "$INDEX_FILE" ]; then
    SHOULD_REBUILD=false
    if [ ! -f "$CAUSAL_FILE" ]; then
        SHOULD_REBUILD=true
    elif [ "$INDEX_FILE" -nt "$CAUSAL_FILE" ]; then
        SHOULD_REBUILD=true
    fi

    if [ "$SHOULD_REBUILD" = "true" ]; then
        python3 "$MEMORY_SCRIPT" \
          --op build-graph-indexes \
          2>/dev/null || true
    fi
fi

# ------------------------------------------------------------------
# 4. Rotate .observations.jsonl — keep last 1000 lines
# ------------------------------------------------------------------
if [ -f "$OBS_FILE" ]; then
    tail -1000 "$OBS_FILE" > "${OBS_FILE}.tmp" \
      && mv "${OBS_FILE}.tmp" "$OBS_FILE" 2>/dev/null || true
fi

exit 0
