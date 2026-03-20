# Agentic Workflow

> Unified AI Development Workflow - Fusion of 10+ World-Class Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/agentic-workflow)](https://github.com/mightyoung/agentic-workflow)
[![Version](https://img.shields.io/badge/Version-4.9-blue.svg)](SKILL.md)

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

Agentic Workflow is a **unified AI development workflow skill** that combines the essence of 10+ world-class skills into a single, powerful framework (v4.9). It provides a systematic approach to handling complex development tasks, from thinking and planning to execution and debugging.

### Core Philosophy

**Don't ask "What do you think?" — ask "Who knows this best? What would they say?"**

This principle, inspired by the best-minds approach, ensures we always leverage expert-level thinking rather than generic responses.

---

## v4.9 New Features

### 1. Self-Evolution Mechanisms

| Feature | Description | Status |
|---------|-------------|--------|
| **Self-Reflection Log** | Structured reflection template in COMPLETE phase | New |
| **3x Confirmation Rule** | WAL pattern promotion after 3 corrections | New |
| **Decision Point** | Human-in-loop for self-correction | Implemented |

### 2. Self-Evolution Loop

```
Detection → Decision Point → Human Approval → Evolution
     ↑                                        ↓
     ←←←←←←←← (Pattern Learning) ←←←←←←←←←←
```

### 3. WAL Protocol (Write-Ahead Logging)

Memory trigger detection for user corrections, preferences, and decisions:

| Type | Example | Action |
|------|---------|--------|
| Correction | "是X，不是Y" | Update SESSION-STATE |
| Preference | "我喜欢X" | Record preference |
| Decision | "用X方案" | Save decision |
| Value | Numbers, URLs, IDs | Store exact value |

### 4. Three-Layer Memory Architecture

```
SESSION-STATE.md     → Working memory (current session)
memory/YYYY-MM-DD.md → Daily logs (optional)
MEMORY.md           → Long-term memory (optional)
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

## Testing Status (v4.9)

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
| 3x Confirmation | v4.9 - WAL Pattern Promotion |

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

### PUA激励 (Pressure Escalation)

When failing, automatically triggers:
- Exhaust 3 approaches
- Do first, ask later
- Proactive delivery

---

## License

MIT License - See [LICENSE](LICENSE) file.
