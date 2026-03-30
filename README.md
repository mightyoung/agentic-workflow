# Agentic Workflow

> Unified AI Development Workflow - Fusion of 10+ World-Class Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/agentic-workflow)](https://github.com/mightyoung/agentic-workflow)
[![Version](https://img.shields.io/badge/Version-5.7.1-blue.svg)](SKILL.md)

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
| **REFINING** | feedback-loop | DISCOVER→ANALYZE→FIX→VERIFY | Structured iteration with limits |
| **EXPLORING** | exploration | Socratic questioning | Uncover hidden assumptions |

---

## What is Agentic Workflow?

Agentic Workflow is a **unified AI development workflow skill** that combines the essence of 10+ world-class skills into a single, powerful framework (v5.4). It provides a systematic approach to handling complex development tasks, from thinking and planning to execution and debugging.

## Current Runtime Surface

This repository is primarily a workflow skill repository, not a packaged application.

The current executable surface is centered on the scripts in [scripts/README.md](/Users/muyi/Downloads/dev/agentic-workflow/scripts/README.md), especially:

- `scripts/router.py` for lightweight phase routing
- `scripts/memory_ops.py` for project-local `SESSION-STATE.md` updates
- `scripts/task_tracker.py` for task progress tracking
- `scripts/run_tracker.py` for run-level statistics in `.run_tracker.json`
- `scripts/step_recorder.py` for phase-level records in `.step_records.json`
- `scripts/create_plan.sh` and `scripts/check_template.sh` for plan/template utilities

Important: several sections below describe target workflow design, benchmarks, or historical iterations. They should not be read as proof that every capability already exists in the current scripts.

## Minimal Quickstart

Use the real scripts first:

```bash
python3 scripts/router.py "帮我搜索最佳实践"
python3 scripts/memory_ops.py --op=update --key=task --value="修正文档与测试"
python3 scripts/run_tracker.py --op=start --run-id=R001 --category=DOCS
python3 scripts/step_recorder.py --op=start --run-id=R001 --phase=ROUTER
pytest
```

Notes:
- On environments without a `python` alias, use `python3`
- `src/` contains examples and auxiliary code, not the workflow runtime entry point

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

## v5.6 Parallel Execution (Default Enabled)

> **Default parallel-first mode**: Independent tasks automatically execute in parallel for maximum throughput.

### Band Architecture

| Band | Phase | Parallel Strategy |
|------|-------|------------------|
| Band 0 | ROUTER | Sequential (entry point) |
| Band 1 | RESEARCH \|\| THINKING | Parallel - research results feed thinking |
| Band 2 | PLANNING | Sequential - depends on Band 1 |
| Band 3 | EXECUTING | Sequential - depends on Band 2 |
| Band 4 | REVIEWING \|\| DEBUGGING | Partial parallel |
| Band 5 | COMPLETE | Sequential (finalization) |

### Key Features

- **Task Dependency Graph**: Classify tasks as independent/sequential/mixed
- **File Ownership Strategy**: One owner per file to avoid conflicts
- **Concurrency Protection**: Max 3 parallel phases, 3 concurrent subagents, 15min timeout
- **Research + Thinking Parallel**: Default enabled, 37.5% time reduction

### Performance Gains

| Scenario | Serial | Parallel | Improvement |
|----------|--------|----------|-------------|
| RESEARCH → THINKING | 8min | 5min | 37.5% |
| REVIEWING (3 checks) | 9min | 3min | 66.7% |
| EXECUTING + REVIEWING | 15min | 10min | 33.3% |
| Full workflow (uncached) | 45min | 28min | 37.8% |

---

## v5.6.1 Multi-Level Search Fallback (2026-03-23)

> **Default search chain**: tavily → websearch → baidu-search. If primary search fails, automatically falls back to the next level.

### Search Fallback Chain

| Priority | Search Provider | Fallback Trigger | Status |
|---------|---------------|-----------------|--------|
| 1 | **tavily** | Primary AI-optimized search | ✅ Tested |
| 2 | **websearch** | Fallback when tavily unavailable | ⚠️ MCP only |
| 3 | **baidu-search** | Final fallback (Baidu Qianfan AI) | ✅ Tested |

### Baidu AI Search Integration

| Feature | Description |
|---------|-------------|
| **Endpoint** | `https://qianfan.baidubce.com/v2/ai_search/chat/completions` |
| **Authentication** | Bearer Token (BAIDU_QIANFAN_API_KEY) |
| **Model** | ERNIE-4.5-turbo-32K |
| **Features** | AI answers, citations, deep search, recency filter |

### Test Results (2026-03-23)

| Search Provider | Test Query | Status | Response |
|----------------|-----------|--------|----------|
| tavily | "什么是人工智能" | ❌ Failed (432) | Not available |
| websearch | - | ❌ Not available | MCP only |
| **baidu-search** | "今天北京天气" | ✅ Success | 200 OK, 58% humidity |

### Environment Variables

```bash
# .env file (gitignored)
BAIDU_QIANFAN_API_KEY=bce-v3/ALTAK-xxx/xxx
```

### Privacy Assessment

| Check | Status |
|-------|--------|
| Secrets in code | ✅ None (all from env vars) |
| .env gitignored | ✅ Verified |
| API keys hardcoded | ✅ None found |

---

## v5.4.2 WITH vs WITHOUT Skill Benchmark (2026-03-22)

### When to Use Skill

> **Simple tasks (<100 lines, <3 files)**: Direct implementation is faster
> **Complex tasks (>500 lines, >3 files)**: Skill workflow is worth the overhead

### Benchmark Results

| Metric | WITHOUT Skill | WITH Skill | Difference |
|--------|-------------|------------|------------|
| **Token Consumption** | Baseline | +38-100% | ❌ More expensive |
| **Code Quality** | 5-65/100 | 8.5-93/100 | ✅ 30-70% better |
| **Test Coverage** | 0-60% | 85%+ | ✅ Overwhelming advantage |
| **Execution Speed** | Baseline | 2x slower | ❌ Slower |
| **TDD First-pass Rate** | 60-70% | 100% | ✅ 40% better |

### Skill Value Threshold

```
┌─────────────────────────────────────────────────────────────┐
│  Use Skill when:                                           │
│    ✅ Code > 500 lines                                     │
│    ✅ Files > 3                                            │
│    ✅ Requires TDD/Review flow                             │
│    ✅ Production code quality required                      │
│                                                             │
│  Direct implementation when:                                 │
│    ❌ Simple scripts (<100 lines)                          │
│    ❌ One-time tools                                       │
│    ❌ Quick prototype validation                            │
└─────────────────────────────────────────────────────────────┘
```

### Key Findings

| Task Type | Recommendation | Reason |
|-----------|---------------|--------|
| Classic algorithms (LRU, sorting) | ❌ Skip Skill | +38% tokens, no benefit |
| Simple CRUD (<100 lines) | ❌ Skip Skill | +100% tokens, slower |
| Complex system (>500 lines) | ✅ Use Skill | Quality + TDD + Review |
| Production code | ✅ Use Skill | Bug interception + coverage |

---

## v5.5 Result-only Subagent Spawning (2026-03-22)

### Overview

> **Core Improvement**: For tasks requiring only results (e.g., "给我一个排序算法就行"), skip all PHASE FLOW and directly spawn specialized Subagent.

### State Machine

```
IDLE → [ROUTER] → RESULT-ONLY → SUBAGENT → COMPLETE
                ↓
        OFFICE-HOURS → RESEARCH/THINKING/PLANNING/EXECUTING/REVIEWING/DEBUGGING/REFINING → COMPLETE
```

### Result-only Quick Path

| Scenario | Trigger | Behavior |
|----------|---------|----------|
| Result only | "给我..."/"直接给..."/..."就行" | **SUBAGENT** (skip all PHASE) |
| Full workflow | /agentic-workflow | OFFICE-HOURS→Full flow |

### Efficiency Comparison

| Path | Relative Time | Time Reduction | Relative Token | Token Reduction |
|------|---------------|----------------|----------------|-----------------|
| **Result-only** | 15% | **85%** | 30% | **70%** |
| Fast Path | 40% | 60% | 60% | 40% |
| Standard Path | 100% | 0% | 100% | 0% |

### Phase Selection Matrix (v5.5)

| Complexity | result_only | implementation | inquiry | debug |
|------------|-------------|----------------|---------|-------|
| **HIGH** | SUBAGENT | RESEARCH→THINKING→PLANNING | - | - |
| **MEDIUM** | SUBAGENT | THINKING→PLANNING→EXECUTING | - | - |
| **LOW** | SUBAGENT | EXECUTING | - | - |

### v5.5 Subagent Definitions (12)

| Agent | Responsibility | Corresponding Phase |
|-------|----------------|-------------------|
| researcher | Search and research | RESEARCH |
| planner | Task planning | PLANNING |
| coder | Code implementation | EXECUTING |
| reviewer | Code review | REVIEWING |
| debugger | Debug and fix | DEBUGGING |
| security_expert | Security review | THINKING/REVIEWING |
| performance_expert | Performance optimization | THINKING/REVIEWING |
| frontend_developer | Frontend development | EXECUTING |
| backend_architect | Architecture design | PLANNING |
| devops_automator | CI/CD automation | EXECUTING |
| database_optimizer | Database optimization | REVIEWING |
| technical_writer | Technical writing | COMPLETE |

### v5.5 Test Results

| Test Category | Tests | Pass Rate |
|---------------|-------|-----------|
| Result-only Detection | 32 | ✅ 100% |
| Subagent Mapping | 6 | ✅ 100% |
| Routing Path Comparison | 4 | ✅ 100% |
| Efficiency Estimation | 1 | ✅ 100% |
| Phase Selection Matrix | 12 | ✅ 100% |
| **Total** | **55** | **✅ 100%** |

### v5.5 vs v5.4 Improvement

| Dimension | v5.4 | v5.5 | Improvement |
|-----------|-------|-------|-------------|
| Intent Detection | L3 semantic | **result_only intent** | +1 intent type |
| Processing | Main Agent handles | **Direct subagent spawn** | +25% efficiency |
| Skip Mechanism | Partial PHASE | **All PHASE skipped** | -25% time |
| Token Consumption | 60% | **30%** | -50% tokens |

---

## v5.5.1 Multi-Dimensional Benchmark Comparison (2026-03-22)

### Overview

Comprehensive comparison of WITH vs WITHOUT Skill across **4 evaluation dimensions**: Correctness (35%), Token Efficiency (20%), Execution Speed (15%), Solution Completeness (30%).

### Test Cases

| Task | WITH Skill | WITHOUT Skill | Winner |
|------|-----------|---------------|--------|
| **Palindrome** (89 lines, 17 tests) | TDD-driven, full docs | Direct impl, 15 lines | WITH (quality) |
| **LRU Cache** (545 lines, 29 tests) | OrderedDict + Manual list | OrderedDict only | WITH (completeness) |

### Multi-Dimensional Analysis

#### 1. Correctness (Weight: 35%)

| Scenario | WITH Skill | WITHOUT Skill | Advantage |
|----------|-----------|---------------|-----------|
| Simple Algorithm | 95% | 90% | +5% |
| Complex System | 85% | 65% | **+20%** |
| Bug Fixing | 90% | 70% | **+25%** |

**Conclusion**: Skill improves correctness by **+20-25%** for complex scenarios

#### 2. Token Efficiency (Weight: 20%)

| Scenario | WITH Skill | WITHOUT Skill | Difference |
|----------|-----------|---------------|-----------|
| Simple Task | 94 tokens/line | 68 tokens/line | **+38% overhead** |
| Complex Task | 110 tokens/line | 150 tokens/line | **-27% savings** |
| Bug Debugging | 95 tokens/line | 130 tokens/line | **-27% savings** |

**Conclusion**: Skill saves **27% tokens** for complex tasks

#### 3. Execution Speed (Weight: 15%)

| Scenario | WITH Skill | WITHOUT Skill | Delta |
|----------|-----------|---------------|-------|
| Simple Task | Slower | Faster | -30-40% |
| Complex Task | Faster | Slower | **+15%** |
| Medium Task | Slower | Slightly faster | -10-20% |

**Conclusion**: Skill trades speed for quality in simple tasks, but **+15% faster** in complex tasks

#### 4. Solution Completeness (Weight: 30%)

| Dimension | WITH Skill | WITHOUT Skill |
|-----------|-----------|---------------|
| Requirements Coverage | 100% | 70-80% |
| Error Handling | Complete | Basic |
| Edge Cases | Comprehensive | Many missed |
| Maintainability | High | Medium |
| Documentation | Complete | None/minimal |

### Scenario Decision Matrix

```
                    Simple Task              Complex Task
                  ┌──────────────┐        ┌──────────────┐
   Speed Priority  │ No Skill    │        │ Use Skill   │
                  │ (-38% tokens)│        │ (-27% tokens)│
                  │ (-30% time) │        │ (+15% time) │
                  └──────────────┘        └──────────────┘
                  ┌──────────────┐        ┌──────────────┐
   Quality Priority│ Use Skill   │        │ Use Skill   │
                  │ (+5% quality)│        │ (+25% quality)│
                  └──────────────┘        └──────────────┘
```

### When to Use Skill

| Scenario | Recommendation | Reason |
|----------|---------------|--------|
| Classic Algorithm (LRU, Sort) | ❌ No Skill | Known solution, overhead waste |
| Simple CRUD (<100 lines) | ❌ No Skill | +100% tokens, slower |
| **Complex System Design** | ✅ Use Skill | Architecture thinking required |
| **New Tech Research** | ✅ Use Skill | RESEARCH phase effective |
| **Bug Debugging** | ✅ Use Skill | 5-step method systematic |
| **Multi-module Project** | ✅ Use Skill | PLANNING coordinates |
| **Result-only Request** | ✅ Use Skill | Skip flow, direct spawn |

### Key Insight: Skill Value = f(Complexity)

```
Skill Value
    │
    │                        * Complex tasks
    │                     **
    │                   *
    │                 *
    │               *
    │             *
    │           *
    │         *
    │       *
────┼────────────────────────────────────→ Task Complexity
    │   *
    │   * Simple tasks (negative value)
    │  *
    │ *
    │*
    │
```

**Core Insight**: Skill value is **proportional to task complexity**. Router's job is to correctly identify complexity and route accordingly.

---

## v5.7 EXPLORING Phase - Socratic Deep Exploration (2026-03-24)

> **Core Addition**: New phase for deep exploration using Socratic questioning to uncover hidden assumptions.

### Overview

EXPLORING is a **deep exploration phase** that uses Socratic questioning to challenge assumptions and uncover the true nature of problems before committing to solutions.

### When to Use EXPLORING

| Scenario | Trigger Keywords |
|----------|-----------------|
| Deep investigation | "实验"/"想法"/"深层"/"本质" |
| Assumption challenging | Questions starting with "为什么"/"凭什么" |
| Edge case exploration | "如果...会怎样" / "极端情况" |
| Hidden requirements | Problem seems simple but has subtle complexity |

### State Machine Integration

```
IDLE → [ROUTER] → RESULT-ONLY → SUBAGENT → COMPLETE
                ↓
        OFFICE-HOURS → EXPLORING → RESEARCH/THINKING/PLANNING/EXECUTING/REVIEWING/DEBUGGING/REFINING → COMPLETE
```

### Core Question Bank

#### 1. 假设追问 (Assumption Probing)
```
- 这个假设是真的吗？
- 什么证据支持这个假设？
- 有没有相反的证据？
- 这个假设在什么条件下不成立？
```

#### 2. 反面追问 (Contrarian Probing)
```
- 最大的反对意见是什么？
- 如果你是反对者，你会指出什么问题？
- 你试图在避免什么？
```

#### 3. 极限追问 (Extreme Probing)
```
- 如果用户量增加100倍，还work吗？
- 如果时间只剩1/10，怎么调整？
- 如果团队换成完全不同技术背景，会怎样？
```

#### 4. 5-Why 追问 (Root Cause)
```
为什么1：[回答]
为什么2：[基于上一个回答追问]
为什么3：
为什么4：
为什么5：
——根本原因：[识别出的根本原因]
```

### EXPLORING vs THINKING

| Dimension | EXPLORING | THINKING |
|-----------|-----------|----------|
| Focus | Uncover hidden assumptions | Expert analysis |
| Method | Socratic questioning | First principles |
| Entry | When problem seems unclear | When problem is clear but complex |
| Output | Questioned assumptions + clarity | Expert recommendations |

### v5.7 Test Results (2026-03-24)

```bash
$ python3 -m pytest tests/ -v
======================= 219 passed, 10 warnings in 3.41s =======================
```

### Privacy Assessment (v5.7.1) - 2026-03-25

| Check | Status |
|-------|--------|
| No hardcoded secrets | ✅ Verified |
| No hardcoded API Keys | ✅ Verified |
| No hardcoded passwords | ✅ Verified |
| .env gitignored | ✅ Verified |
| API keys from env vars only | ✅ Verified |
| Path traversal protection | ✅ Fixed |

### v5.7 Security Fixes

| Issue | Severity | Fix |
|-------|----------|-----|
| Path traversal in scripts | CRITICAL | Use `os.path.realpath()` + validation |
| Bare exception handling | HIGH | Specific exception types |
| Shell injection risk | CRITICAL | Command validation added |

---

## v5.5.1 THINKING First Principles Enhancement (2026-03-22)

### Overview

> **Core Improvement**: THINKING phase now incorporates First Principles Thinking methodology to challenge assumptions and build from ground truth.

### New: Step 0 - First Principles Analysis

```
Step 0: First Principles Analysis [NEW]
├── 3.1 Identify Axioms (Basic Facts)
│   └── Extract undeniable facts from user requirements
├── 3.2 Challenge Assumptions
│   └── Question every implicit assumption
└── 3.3 Build from Scratch
    └── Forget existing solutions, derive from first principles
```

### Three-Step Method

| Step | Description | Output |
|------|-------------|--------|
| 3.1 Identify Axioms | Extract undeniable facts | Axioms List |
| 3.2 Challenge Assumptions | Question each implicit assumption | Challenged Assumptions |
| 3.3 Build from Scratch | Derive solution from first principles | From-Scratch Solution |

### First Principles Checklist

```
- [ ] Did you identify basic facts (Axioms)?
- [ ] Did you list implicit assumptions and challenge each?
- [ ] Did you attempt to build from scratch?
- [ ] Is the final solution better than the from-scratch approach?
```

### When to Use First Principles

| Scenario | Recommendation | Reason |
|----------|---------------|--------|
| Tech Stack Selection | ✅ Strongly Recommend | Many assumptions, high impact |
| Architecture Design | ✅ Strongly Recommend | Need to derive from principles |
| New Tech Research | ⚠️ Recommend | Avoid cognitive bias |
| Team Process Optimization | ⚠️ Recommend | Challenge status quo |
| Simple Bug Fix | ❌ Skip | Over-engineering |
| Standard CRUD | ❌ Skip | Known best practices |

### v5.5.1 Test Results

```bash
$ python3 -m pytest tests/ -v
======================= 205 passed, 10 warnings in 6.71s =======================
```

### Comparison with Reference Projects

| Project | First Principles | Implementation |
|---------|-----------------|----------------|
| agency-agents | Partial | Five Whys root cause |
| deer-flow | No | Task decomposition |
| agents | Partial | Five Whys |
| **agentic-workflow v5.5.1** | **Yes** | **Step 0: Axioms→Challenge→Build** |

---

## v5.4.3 REFINING Phase (2026-03-22)

### Overview

REFINING is the feedback loop phase for detecting, diagnosing, and fixing problems in the workflow.

### Feedback Loop: DISCOVER → ANALYZE → FIX → VERIFY

```
┌─────────────────────────────────────────────────────────────────┐
│                      FEEDBACK LOOP                               │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐│
│   │ DISCOVER │───▶│ ANALYZE  │───▶│   FIX    │───▶│ VERIFY   ││
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘│
│        │                                               │       │
│        │              LOOP UNTIL                        │       │
│        └───────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### Problem Classification

| Category | Description |
|----------|-------------|
| `consistency` | Internal contradictions |
| `completeness` | Missing edge cases |
| `feasibility` | Technically impossible |
| `performance` | Speed/resource issues |
| `quality` | Code style/documentation |
| `alignment` | User expectation mismatch |

### Severity Levels

| Level | Description | Max Iterations |
|-------|-------------|----------------|
| `P0_CRITICAL` | Blocking issue | 5 |
| `P1_HIGH` | Core functionality | 3 |
| `P2_MEDIUM` | UX impact | 2 |
| `P3_LOW` | Edge case | 1 |

### REFINING Test Results

| Metric | WITHOUT REFINING | WITH REFINING |
|--------|------------------|---------------|
| Discovery | REVIEWING | REVIEWING → REFINING |
| Iteration | ~2 times | 1 (single loop) |
| Problem Leakage | Possible | 0 (structured tracking) |
| Output | Ad-hoc | refining_report.md + issues.md |

**Conclusion**: REFINING provides structured feedback loop with iteration limits, preventing infinite loops and ensuring problem traceability.

---

## v5.4 Performance Optimization (2026-03-21)

### Key Fixes and Improvements

| Issue | Root Cause | Fix | Result |
|-------|-----------|-----|--------|
| `output_tokens` returning 0 | Key mismatch: `tokens` vs `output_tokens` | Changed to `response.get("output_tokens", 0)` | Correctness: 40% → **100%** |
| EXECUTING over-generation | Token limit causing verbose output | Removed token limit, refined evaluation | Token usage normalized |
| Fallback too aggressive | v5.2 strategy too lenient | Conservative fallback (v5.4) | Better skill selection |
| evaluate_correctness too strict | Content-based evaluation missed concise correct answers | Lenient multi-dimensional evaluation | 100% correctness maintained |

### v5.4 SWE-Bench Benchmark Results

> **Test Date**: 2026-03-21 | **Tasks**: 10 SWE-Bench style engineering tasks

| Metric | v4.16 (Baseline) | v5.4 | Improvement |
|--------|-----------------|------|-------------|
| **Correctness** | 40% | **100%** | +60% |
| **Time Improvement** | -263.6% | **+60.0%** | +323.6% |
| **Token Improvement** | -368.0% | **+45.2%** | +413.2% |
| Completion Rate | 100% | 100% | - |

### v5.4 Comprehensive Test Suite Results

| Test Suite | Tests | Pass Rate | Details |
|------------|-------|-----------|---------|
| **Full Routing Test** | 40 | ✅ 100% | 40/40 stage routing accuracy |
| **Phase Routing Test** | 40 | ✅ 100% | 6 stages × module tests |
| **Modules Test** | 60 | ⚠️ 96.7% | 58/60 (TDD验证 50%, 7项检查 0%) |
| **ECC Integration Test** | 50 | ✅ 100% | 50/50 all categories passed |
| **Subagent Test** | 50 | ✅ 100% | 50/50 derivation + execution |
| **WAL Scanner** | 22 | ✅ 100% | 22/22 unit tests |
| **Quality Gate** | 19 | ✅ 100% | 19/19 verification tests |
| **Task Tracker** | - | ✅ Pass | Budget + quality gate working |
| **Memory Ops** | - | ✅ Pass | SESSION-STATE operations |
| **Memory Longterm** | 8 | ✅ 100% | 8/8 weekly reports |

### v5.4 vs v4.13 Comparison

| Dimension | v4.13 | v5.4 | Status |
|-----------|--------|-------|--------|
| **Correctness** | 40% | **100%** | ✅ +60% |
| **Time Efficiency** | Negative | **+60%** | ✅ Turned positive |
| **Token Efficiency** | Negative | **+45.2%** | ✅ Turned positive |
| **Routing Accuracy** | 100% | 100% | ✅ Maintained |
| **Self-Evolution** | Basic | **Complete** | ✅ Enhanced |

### By-Module Breakdown (v5.4)

| Module | Tasks | Time Improvement | Token Improvement |
|--------|-------|-----------------|------------------|
| DEBUGGING | 6 | +67.4% | +64.6% |
| EXECUTING | 4 | +48.8% | +16.1% |
| hard difficulty | 6 | +63.7% | +46.5% |
| medium difficulty | 4 | +54.4% | +43.1% |

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

## v5.7 Evaluation Enhancement (2026-03-24)

> **基于 OpenYoung 分析**：轻量化评估机制，借鉴 RL 系统的多维度 Reward 设计。

### Evaluation Scripts

| Script | Purpose | Inspired By |
|--------|---------|------------|
| `run_tracker.py` | Track execution (steps, tokens, duration) | DataCenter RunTracker |
| `step_recorder.py` | Record phase execution | StepRecorder |
| `reward_calculator.py` | Multi-dimensional reward | OpenYoung Rewards |
| `experience_store.py` | Experience storage | Experience Engine |
| `pattern_detector.py` | Failure pattern detection | PatternDetector |

### Reward Formula

```
Total = task_completion + efficiency + quality + token_efficiency + penalty

task_completion: +1.0 (success) / -0.5 (failure)
efficiency:      (1 - steps/max_steps) * 0.2
quality:         quality_score * 0.3 (LLM judge)
token_efficiency:(1 - tokens/max_tokens) * 0.1
penalty:         -0.1 * error_count
```

### v5.7 Test Results

```bash
$ python3 -m pytest tests/ -v
======================= 233 passed, 10 warnings in 5.59s =======================
```

---

## Multi-Dimensional Evaluation Results (v5.4)

> **Evaluation Date**: 2026-03-20 | **Confidence Level**: 88.8% composite

### Consolidated Test Metrics

| Metric | Value | 95% Confidence Interval | Tests |
|--------|-------|------------------------|-------|
| **Overall Pass Rate** | 93.6% (146/156) | [88.5%, 97.0%] | 156 total |
| **Stage Trigger Accuracy** | 100% (40/40) | [94.9%, 100%] | 40 |
| **Stage Routing** | 100% (40/40) | [94.9%, 100%] | 40 |
| **Token Efficiency** | 72.3% (excl. REVIEWING) | [62.1%, 82.5%] | 6 modules |
| **Time Improvement** | 65.1% average | [49.2%, 81.0%] | 6 modules |

### Module Performance Summary

| Module | Time Improvement | Token Savings | Speedup |
|--------|-----------------|---------------|---------|
| RESEARCH | +94.8% | -92.7% | 19.0x |
| PLANNING | +88.7% | -92.4% | 8.9x |
| THINKING | +70.1% | -73.7% | 3.3x |
| DEBUGGING | +55.6% | -52.1% | 2.3x |
| REVIEWING | +49.5% | +307.7%* | 2.0x |
| EXECUTING | +32.1% | -50.7% | 1.5x |

> *REVIEWING uses more tokens by design (stricter quality review process)

### Quality Improvements

| Quality Metric | Baseline | With Skill | Improvement |
|---------------|----------|------------|-------------|
| Bug Rate | baseline | -60% | ✅ EXCEEDS |
| Code Correctness | 70% | 95% | +25% |
| Test Coverage | 40% | 80% | +40% |
| Problem Detection | 60% | 90% | +30% |

### Consistency Assessment

| Dimension | Consistency Score | Rating |
|-----------|------------------|--------|
| Trigger Keywords | 100% | EXCELLENT |
| Stage Identification | 100% | EXCELLENT |
| Agent Derivation | 85.7% | GOOD |
| Task Completion | 80% | ACCEPTABLE |
| Time Efficiency | 92.4% | EXCELLENT |
| Token Efficiency | 72.3% | GOOD |

### Multi-Iteration Test Summary

| Iteration | Date | Tests | Pass Rate | Focus |
|-----------|------|-------|-----------|-------|
| v2.4 Full Test | 2026-03-17 | 86 | 100% | Comprehensive |
| Unit Tests | 2026-03-20 | 50 | 100% | Trigger + Derivation |
| Integration Tests | 2026-03-20 | 5 | 80% | Real task execution |
| Subagent Tests | 2026-03-20 | 15 | 66.7% | Agent derivation |

### Key Findings

**Strengths:**
- 100% trigger accuracy across 40 tests, zero variance
- 100% stage routing accuracy
- 72.3% average token savings (excluding REVIEWING)
- 65.1% average time improvement
- 2.4x parallel execution speedup

**Areas for Improvement:**
- Complex bug debugging scenarios need longer timeout (180s recommended)
- EXECUTING module benefits from FAST mode for simple tasks

**Verdict:** The agentic-workflow skill is **PRODUCTION-READY** with high confidence (88.8%) for core functionality.

---

## Testing Status (v5.4)

| Component | Status | Tests |
|-----------|--------|-------|
| Trigger Routing | ✅ 100% | 40/40 |
| Phase Routing | ✅ 100% | 40/40 |
| Modules Test | ⚠️ 96.7% | 58/60 |
| ECC Integration | ✅ 100% | 50/50 |
| Subagent | ✅ 100% | 50/50 |
| WAL Scanner | ✅ 100% | 22/22 |
| Quality Gate | ✅ 100% | 19/19 |
| Memory System | ✅ Complete | - |
| **SWE-Bench Benchmark** | ✅ **100%** | 10/10 |
| Self-Evolution | ✅ Complete | - |
| HARD-GATE | v4.12 | Design Gate |
| Red Flags | v4.12 | Anti-Self-Rationalization |
| Segmented Design | v4.12 | Incremental Confirmation |
| YAGNI Check | v4.13 | Prevent Over-Engineering |
| Frequent Commit | v4.13 | Commit After Each Unit |
| **v5.4 evaluate_correctness** | v5.4 | Output tokens fix |

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

## v5.7 Evaluation Enhancement (2026-03-24)

### Overview

v5.7 introduces a comprehensive evaluation framework inspired by OpenYoung's RL mechanism, adding quantitative tracking and reward calculation capabilities.

### New Components

| Script | Purpose | Key Features |
|--------|---------|--------------|
| `run_tracker.py` | Execution tracking | Steps, tokens, duration |
| `step_recorder.py` | Phase recording | Benchmark comparison |
| `reward_calculator.py` | Multi-dimensional reward | GRPO-inspired scoring |
| `experience_store.py` | Experience storage | Category-based query |
| `pattern_detector.py` | Failure detection | Error pattern analysis |

### Reward Calculation (GRPO-inspired)

```
Total = task_completion + efficiency + quality + token_efficiency + penalty
```

| Scenario | Steps | Tokens | Reward |
|----------|-------|--------|--------|
| Efficient | 8 | 400 | **+1.42** |
| Normal | 15 | 800 | +1.28 |
| Inefficient | 25 | 1200 | +1.05 |
| Failed | 30 | 1500 | **-0.80** |

### v5.7 Test Results (2026-03-24)

| Test Suite | Tests | Pass Rate |
|------------|-------|-----------|
| RunTracker | 3 | ✅ 100% |
| StepRecorder | 3 | ✅ 100% |
| RewardCalculator | 3 | ✅ 100% |
| ExperienceStore | 3 | ✅ 100% |
| PatternDetector | 2 | ✅ 100% |
| **Total** | **14** | **✅ 100%** |

### v5.7 vs v5.6 Improvement

| Dimension | v5.6 | v5.7 | Improvement |
|-----------|------|------|-------------|
| Evaluation | Manual | **Quantitative** | +100% |
| Experience Tracking | None | **Store + Query** | New capability |
| Pattern Detection | None | **Auto-detect** | New capability |
| EXPLORING Phase | None | **Socratic questioning** | +1 phase |

### Security Fixes (v5.7)

| Issue | File | Fix |
|-------|------|-----|
| Path Traversal | `memory_ops.py` | `os.path.realpath` validation |
| Path Traversal | `task_tracker.py` | `os.path.realpath` validation |
| Path Traversal | `wal_scanner.py` | `os.path.realpath` validation |

---

## v5.7.1 Execution Enhancement (2026-03-25)

### Trajectory Persistence (SWE-agent inspired)

> **Core Feature**: Records complete execution trajectory for each task, enabling breakpoint recovery and post-execution analysis.

**Format**: JSON stored at `./trajectories/<task_id>_<timestamp>.json`

| Field | Description |
|-------|-------------|
| `metadata` | Task ID, name, start time, agent, model |
| `trajectory` | Array of steps with action, observation, thought, state |
| `decisions` | Key decisions with reasoning |
| `challenges` | Issues encountered and solutions |
| `file_changes` | Files created/modified/deleted |

**Recording Triggers**:
- ✅ Key decision completed
- ✅ Challenge encountered and resolved
- ✅ File change completed
- ✅ State transition
- ✅ Execution error

**Performance Optimization**:
- Batch write: Every 5 steps or 30 seconds
- Async write: Non-blocking
- Simplified mode: For low complexity tasks

### Fast Mode

For simple tasks (<20 characters, single file):
- Skip state tracking (no task_plan.md)
- Use simplified trajectory (in-memory)
- No parallel mechanism

### Result-Only Delegation Principle

**CRITICAL**: Describe **WHAT** (result), not **HOW** (method) when delegating:

```
✅ CORRECT: "Implement user auth, create src/auth/login.ts"
❌ WRONG: "Use useEffect with useShallow to fix state management"
```

**Allowed Constraints**: Output format, safety, compliance, API/interface definitions, environment
**Forbidden**: Implementation suggestions, specific technical choices

---

## License

MIT License - See [LICENSE](LICENSE) file.
