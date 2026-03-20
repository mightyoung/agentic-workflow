# Agentic Workflow

> Unified AI Development Workflow - Fusion of 10+ World-Class Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/agentic-workflow)](https://github.com/mightyoung/agentic-workflow)
[![Version](https://img.shields.io/badge/Version-4.13-blue.svg)](SKILL.md)

---

## Quick Skill Reference

| Module | Source Skills | Industry Best Practice | Core Value |
|--------|--------------|---------------------|-------------|
| **RESEARCH** | tavily, planning-with-files | AI-optimized search + file persistence | Decision based on evidence |
| **THINKING** | best-minds | Expert-level thinking simulation | Avoid generic responses |
| **PLANNING** | writing-plans, planning-with-files | Agile task breakdown + file memory | Measurable progress |
| **EXECUTING** | TDD, pua | Test-driven + pressure escalation | Code correctness guaranteed |
| **REVIEWING** | verification, openspec | Graded review + spec-driven | 60%+ Bug interception |
| **DEBUGGING** | systematic-debugging, pua | 5-step methodology + 7 checks | 10x debugging efficiency |

---

## What is Agentic Workflow?

Agentic Workflow is a **unified AI development workflow skill** that combines the essence of 10+ world-class skills into a single, powerful framework (v4.13). It provides a systematic approach to handling complex development tasks, from thinking and planning to execution and debugging.

### Core Philosophy

**Don't ask "What do you think?" — ask "Who knows this best? What would they say?"**

This principle, inspired by the best-minds approach, ensures we always leverage expert-level thinking rather than generic responses.

---

## v4.13 New Features

### 1. YAGNI Check (v4.13)

> **Core Principle**: Don't implement features that aren't needed yet.

| Question | If Yes | Correct Action |
|----------|--------|----------------|
| Did user explicitly require this? | ❌ Not needed now | Delete it |
| Is this in the user story? | ❌ No | Delete it |
| Will tests fail if removed? | ❌ No | Delete it |
| Is this "just in case"? | ✅ Over-engineering | Delete it |

### 2. Frequent Commit Rules (v4.13)

> **Core Principle**: Commit after every meaningful independent unit of work.

| When Complete | Must Commit |
|--------------|-------------|
| One function/method | ✅ |
| One test case | ✅ |
| One small feature module | ✅ |
| Bug fix | ✅ |
| Refactoring (behavior unchanged) | ✅ |
| Documentation update | ✅ |

---

## v4.12 New Features

### 1. HARD-GATE Design Gate

> **Core Principle**: No implementation until design is approved by user.

```
<HARD-GATE>
Before any implementation:
- ❌ Write any code
- ❌ Set up project structure
- ❌ Execute any implementation action
- ❌ Call implementation skills

Must complete:
- ✅ Understand what user truly wants
- ✅ Propose 2-3 options with trade-off analysis
- ✅ Get segmented approval from user
- ✅ Write design to documentation
```

### 2. Red Flags - Anti-Self-Rationalization

> **Core Principle**: If there's even 1% chance a skill applies, you must invoke it.

| When You Think | Actual Meaning | Correct Action |
|----------------|----------------|----------------|
| "This is a simple issue" | Issue = task, check skill | STOP, check skill |
| "I need to learn more first" | Skill check before context | Call skill first |
| "Quick look at the file" | File lacks conversational context | Call skill first |

### 3. Segmented Design Confirmation

Complex designs are presented in sections with incremental approval:

| Project Type | Design Length | Confirmation Rhythm |
|--------------|---------------|-------------------|
| Simple (single file) | A few sentences | 1 confirmation |
| Medium (2-3 files) | 100-200 words per section | Confirm per section |
| Complex (multi-system) | 200-300 words per section | Confirm per section |

---

## v4.11 New Features: Idle Detection & Result Tracking

### Idle Detection

When user returns after 30+ minutes of inactivity:

1. **Detect**: Read timestamp from SESSION-STATE.md
2. **判断**: If last_active > 30 minutes, show recovery card
3. **恢复**: Continue from breakpoint or start new task

### Result Tracking (JSONL)

Task execution history in append-only JSONL format:

```json
{"timestamp": "2026-03-20T10:45:00", "task_id": "T001", "status": "success", "duration_seconds": 300}
```

---

## v4.9 Self-Evolution Mechanisms

### Self-Reflection Log

Structured reflection in COMPLETE phase:

```markdown
## Self-Reflection Log

### Task
[Task description]

### Execution Result
- Status: success/partial/failed
- Key Decisions: [what was decided]

### Observations
- What was discovered: [observations during execution]
- Unexpected issues: [unanticipated problems]

### Lessons
- How to improve next time: [specific improvements]
- Pattern recognition: [recurring patterns]

### WAL Pattern Promotion Check
- Similar corrections: N
- Needs promotion: [Yes/No]
```

### 3x Confirmation Rule

When same pattern corrected 3+ times, trigger promotion:

```
Detected 3 similar corrections: "User prefers X over Y"
Confirm this as permanent rule?
  [1] Confirm and add to PATTERNS.md
  [2] Ignore temporarily
  [3] View history
```

---

## v4.8 Budget Control & Quality Gate

### Budget Control (Informational)

| Command | Function |
|---------|----------|
| `task_tracker.py --op=start` | Start task timer |
| `task_tracker.py --op=budget` | Check budget status |

> Note: Budget tracking is informational only, does not truncate tasks.

### Quality Gate

Automated verification before task completion:

| Gate | Tool | Purpose |
|------|------|---------|
| typecheck | tsc/pyright/mypy | Type safety |
| lint | eslint/flake8 | Code style |
| test | jest/pytest | Functionality |

---

## Architecture

### State Machine

```
IDLE → RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
              ↓           ↓           ↓           ↓
         DEBUGGING ←────────────────────────────────────→
```

### Routing Logic (4 Layers)

| Layer | Type | Description |
|-------|------|-------------|
| L0 | Negative Filter | DO NOT TRIGGER (chitchat) |
| L1 | Explicit Command | Force trigger (/agentic-workflow) |
| L2 | Smart Detection | Keyword matching |
| L3 | Semantic (Optional) | Indirect expression |

---

## Quick Start

### Explicit Command (Force Full Workflow)

```
/agentic-workflow 帮我开发一个电商系统
```

### Auto-Detection

| Complexity | Behavior |
|------------|----------|
| High (multi-module) | Full workflow |
| Medium (multi-step) | THINKING → PLANNING → EXECUTING |
| Low (single file) | Direct execution |

---

## Scripts

| Script | Platform | Purpose |
|--------|----------|---------|
| `wal_scanner.py` | Cross-platform | WAL trigger detection |
| `task_tracker.py` | Cross-platform | Budget control + quality gate |
| `quality_gate.py` | Cross-platform | Automated verification |
| `memory_ops.py` | Cross-platform | SESSION-STATE operations |
| `memory_daily.py` | Cross-platform | Daily log management |
| `memory_longterm.py` | Cross-platform | Long-term memory |

**Windows Batch Scripts** (scripts/win/):
- `init_session.bat`, `check_env.bat`, `quick_review.bat`, etc.

---

## Testing Status (v4.13)

| Component | Status |
|-----------|--------|
| Trigger Routing | 100% (40/40) |
| Bash Scripts | 100% (8/8) |
| Python Scripts | 100% |
| Windows Scripts | 100% (5/5) |
| Subagent Architecture | 100% (7/7) |
| Memory System | Layer 1/2/3 Implemented |
| Quality Gate | P0 - typecheck/lint/test |
| Budget Control | P1 - start/budget/quality-gate |
| Self-Correction | P2 - Decision Point Pattern |
| HARD-GATE | v4.12 - Design Gate |
| Red Flags | v4.12 - Anti-Self-Rationalization |
| Segmented Design | v4.12 - Incremental Confirmation |
| YAGNI Check | v4.13 - Prevent Over-Engineering |
| Frequent Commit | v4.13 - Commit After Each Unit |

---

## File Structure

```
agentic-workflow/
├── SKILL.md                    # Main skill definition
├── README.md / README_CN.md    # Documentation
├── .gitignore                  # Git ignore rules
├── agentic-workflow.lock       # Version lock file
├── references/
│   ├── modules/                # Workflow modules
│   │   ├── executing.md
│   │   ├── thinking.md
│   │   ├── debugging.md
│   │   └── reviewing.md
│   ├── templates/              # File templates
│   │   ├── task_plan.md
│   │   └── session_state.md
│   ├── memory_integration.md   # Memory system
│   └── builtin_tdd.md          # Built-in TDD
├── scripts/
│   ├── wal_scanner.py         # WAL trigger scanner
│   ├── task_tracker.py         # Task budget control
│   ├── quality_gate.py         # Quality verification
│   ├── memory_ops.py           # Memory operations
│   ├── memory_daily.py         # Daily logs
│   ├── memory_longterm.py      # Long-term memory
│   └── win/                   # Windows batch scripts
└── agents/                     # Subagent definitions
```

---

## Core Principles

### Iron Rules

1. **Exhaustion Rule** - Never say "can't solve" before trying 3 approaches
2. **Do-First Rule** - Search, read source, verify before asking
3. **Proactive Rule** - End-to-end delivery, not "just enough"

### PUA Pressure Escalation

When failing, automatically triggers:
- Exhaust 3 approaches
- Do first, ask later
- Proactive delivery

---

## License

MIT License - See [LICENSE](LICENSE) file.
