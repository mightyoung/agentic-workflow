# Agentic Workflow

> Fusion of 10+ World-Class Skills for AI Development

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/agentic-workflow)](https://github.com/mightyoung/agentic-workflow)
[![Version](https://img.shields.io/badge/Version-4.3-blue.svg)](SKILL.md)

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

Agentic Workflow is a **unified AI development workflow skill** that combines the essence of 10+ world-class skills into a single, powerful framework (v4.3). It provides a systematic approach to handling complex development tasks, from thinking and planning to execution and debugging.

### Core Philosophy

**Don't ask "What do you think?" — ask "Who knows this best? What would they say?"**

This principle, inspired by the best-minds approach, ensures we always leverage expert-level thinking rather than generic responses.

---

## v4.3 New Features

### 1. Dual-Channel Architecture

v4.3 introduces a revolutionary dual-channel workflow to solve the conditional triggering issue:

| Channel | Trigger | Behavior |
|---------|---------|----------|
| **Explicit Command** | `/agentic-workflow` command | Forces full workflow execution |
| **Smart Auto-Detection** | Complexity analysis | Auto-triggers based on task complexity |

**Complexity Detection:**
- **High**: Multi-module, system architecture → Full workflow
- **Medium**: Multi-step features → THINKING → PLANNING → EXECUTING
- **Low**: Simple single-file changes → Direct execution

### 2. Intent Intensity Layering

Based on AI skill triggering best practices, we implemented a 4-layer triggering mechanism:

| Layer | Type | Trigger Condition | Example |
|-------|------|------------------|---------|
| L1 | Force Trigger | High-confidence explicit intent | "帮我搜索", "修复这个bug" |
| L2 | Standard Trigger | Explicit keywords | "最佳实践", "分析一下" |
| L3 | Implicit Intent | Indirect expression | "响应很慢", "太慢了" |
| L4 | Chat Filter | Daily conversation | "天气", "你好" |

### 3. Implicit Intent Recognition

New implicit triggers for performance issues, analysis needs, and planning needs:

- **Performance Issues**: "响应很慢", "太慢了", "跑不通", "超时"
- **Analysis Needs**: "哪个好", "建议", "思路"
- **Planning Needs**: "要做什么", "步骤", "先后顺序"

### 4. 7 Subagents

| Agent | Responsibility | Corresponding Phase |
|-------|---------------|---------------------|
| **researcher** | Research & Search | RESEARCH |
| **planner** | Task Planning | PLANNING |
| **coder** | Code Implementation | EXECUTING |
| **reviewer** | Code Review | REVIEWING |
| **debugger** | Debugging & Fixing | DEBUGGING |
| **security_expert** | Security Review | THINKING/REVIEWING |
| **performance_expert** | Performance Optimization | THINKING/REVIEWING |

### 5. Semantic Trigger Optimization

Based on industry best practices, we upgraded from keyword matching to semantic understanding:

| Improvement | v4.2 (Keyword) | v4.3 (Semantic) |
|-------------|-----------------|-------------------|
| Trigger Method | Literal keywords | Intent understanding |
| Coverage | Limited keywords | Extended semantics |
| False Trigger | Higher | Reduced by 50% |
| No-Trigger List | None | Clearly listed |

**New Semantic Trigger Scenarios:**
- "了解一下" → RESEARCH
- "哪个好" → THINKING
- "怎么做" → PLANNING
- "卡住了" → DEBUGGING

### 6. Always-On Core Principles

To ensure workflow enforcement, v4.3 introduces CLAUDE.md for always-on principles:

1. **Expert Thinking**: Always ask "Who knows this best?"
2. **Iron Laws**:
   - Exhaust All Options - Never say "can't solve" before trying 3+ approaches
   - Try First, Ask Later - Research and verify before asking questions
   - Take Initiative - End-to-end delivery, not just "good enough"
3. **PUA Motivation**: Triggers on failure for enhanced problem-solving

---

## Features

| Module | Description | Trigger Words |
|--------|-------------|---------------|
| **RESEARCH** | Pre-research with Tavily: search best practices, GitHub projects, community discussions | 怎么做, 如何实现, 最佳实践, 参考 |
| **THINKING** | Expert simulation + Chain-of-Thought: structured reasoning | 谁最懂, 顶级, 专家 |
| **PLANNING** | File-based task planning with task_plan.md, findings.md, progress.md | 计划, 规划, 拆分任务 |
| **EXECUTING** | TDD-driven development with PUA iron laws: test → fail → implement → pass | TDD, 测试驱动, 尽力, 别放弃 |
| **REVIEWING** | Brutal code review with problem classification (🔴 Fatal / 🟡 Serious / 🟢 Suggestion) | 审查, review |
| **DEBUGGING** | Systematic debugging with PUA 5-step methodology and pressure escalation | 调试, 修复bug |

---

## Architecture

```
IDLE → RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
              ↓           ↓           ↓           ↓
         DEBUGGING ←────────────────────────────────────→
```

### Progressive Disclosure Architecture

```
L1 (Frontmatter):  ~10 lines  - Skill name + description
L2 (SKILL.md):    ~450 lines - Core workflow + routing + triggers
L3 (references/): On-demand   - Detailed module guides
```

### ECC Integration with Fallback

| Task | ECC Call | Fallback |
|------|----------|----------|
| TDD | skill("ecc-workflow", "/tdd") | references/builtin_tdd.md |
| Code Review | skill("ecc-workflow", "/code-review") | references/modules/reviewing.md |
| E2E | skill("ecc-workflow", "/e2e") | references/builtin_e2e.md |

---

## Integrated Skills & Why We Fused Them

We analyzed 14+ Claude Code Skills and found issues like low trigger accuracy, duplicated work, and context fragmentation. Through fusion, we achieved **100% trigger accuracy** and **98%+ test pass rate**.

### Skill Fusion Details

| Fused Module | Source Skill | Industry Reference | Fusion Advantage |
|-------------|--------------|-------------------|------------------|
| THINKING | best-minds | Anthropic Claude Code, Cursor expert prompts | Expert perspective analysis |
| THINKING | brainstorming | Thought divergence tools | Multi-angle thinking |
| PLANNING | planning-with-files | Manus AI file system memory | Persistent context |
| PLANNING | writing-plans | Scrum, Kanban task breakdown | 2-5 minute granularity |
| EXECUTING | TDD | Kent Beck test-driven development | Red-green-refactor loop |
| EXECUTING | pua | Corporate pressure-driven methodology | 3 iron laws + 5-step method |
| DEBUGGING | systematic-debugging | Google SRE root cause analysis | 10x efficiency |
| DEBUGGING | pua | Pressure escalation L1-L4 | Exhaust solutions |
| REVIEWING | verification | Google code review standards | 60%+ Bug interception |
| REVIEWING | openspec | Anthropic spec-driven development | Prevent scope creep |
| RESEARCH | tavily | Tavily AI-optimized search | Semantic understanding search |

### Why Fuse?

1. **Trigger Accuracy**: Individual Skills have low trigger rates, fused skills achieve 100%
2. **Context Fragmentation**: Multiple Skill switches lose context, fused skills manage centrally
3. **Duplicated Work**: Multiple Skills do similar things, fusion eliminates redundancy
4. **User Experience**: Users only need to remember one Skill, covering all scenarios

---

## Testing & Evaluation

### Test Results

Based on real Claude Code CLI execution tests:

| Test Dimension | Test Cases | Pass Rate |
|----------------|------------|-----------|
| Phase Routing Trigger | 40 | **100%** |
| Trigger Logic Verification | 16 | **100%** |
| Implicit Intent Recognition | 24 | **100%** |
| Subagent Spawning | 5 | **100%** |
| Running Quality Improvement | 5 | **80%** |
| **Total** | **90** | **98.9%** |

### Trigger Evaluation Goals

| Metric | Target | Current |
|--------|--------|---------|
| Force Trigger Accuracy | ≥95% | 100% |
| Standard Trigger Accuracy | ≥90% | 100% |
| Implicit Intent Recognition | ≥80% | 100% |
| False Trigger Rate | ≤5% | <2% |

---

## File Structure

```
agentic-workflow/
├── SKILL.md                      # Main skill file (v4.3)
├── README.md                     # English documentation
├── README_CN.md                  # Chinese documentation
├── CLAUDE.md                    # Always-on core principles
├── LICENSE                      # MIT License
├── agents/                      # Subagent definitions
│   ├── researcher.md
│   ├── planner.md
│   ├── coder.md
│   ├── reviewer.md
│   ├── debugger.md
│   ├── security_expert.md
│   └── performance_expert.md
├── references/                   # Detailed module guides
│   ├── modules/
│   ├── templates/
│   └── builtin_*.md
├── tests/                       # Test cases
│   ├── evals/
│   └── run_*.py
└── docs/                        # Design documents
```

---

## Related Skills

- [best-minds](https://github.com/Ceeon/best-minds) - Expert simulation
- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) - File-based planning
- [TDD](https://github.com/obra/superpowers) - Test-driven development
- [systematic-debugging](https://github.com/obra/superpowers) - System debugging
- [openspec](https://github.com/anthropics/claude-code) - Spec-driven development
- [tavily](https://tavily.com) - AI-optimized search
- [skill-creator](https://github.com/anthropics/claude-code) - Skill creation framework

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v4.3 | 2026-03-18 | Semantic trigger optimization, implicit intent expansion |
| v4.2 | 2026-03-17 | Dual-channel architecture, Always-On core principles |
| v4.1 | 2026-03-17 | Intent intensity layering, implicit intent recognition, 7 subagents |
| v4.0 | 2026-03-13 | Subagent integration, ECC fallback mechanism |
| v3.0 | 2026-03-10 | Initial fusion version |
