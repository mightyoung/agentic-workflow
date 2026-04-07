# Agentic Workflow

> Unified AI Development Workflow Skill - 统一智能体工作流

## What is This?

Agentic Workflow is a **skill-based workflow system** that provides systematic approaches to handling development tasks. It uses a phase-based architecture where different skills handle different aspects of the development lifecycle.

**Current Version**: 5.13.0

## Current Capabilities (v5.13.0)

This section describes what actually works **today** via the scripts layer.

### Phase Skills (Layer 1 - Skill Specs)

| Phase | Runtime | Output | Description |
|-------|---------|--------|-------------|
| ROUTER | ✅ | — | Keyword-based routing |
| OFFICE-HOURS | ✅ | — | Product consultation |
| EXPLORING | ✅ | — | Socratic deep exploration |
| RESEARCH | ✅ | .research/findings/findings_{session}.md | Web search → findings report (also writes .research/findings/findings_latest.md) |
| THINKING | ✅ | — | Expert reasoning |
| PLANNING | ✅ | .specs/<feat>/spec.md → plan.md → tasks.md → .contract.json | Task breakdown with spec-kit chain |
| EXECUTING | ✅ | — | TDD-driven implementation |
| REVIEWING | ✅ | .reviews/review/review_{session}.md | Real code analysis when files present (also writes .reviews/review/review_latest.md) |
| DEBUGGING | ✅ | — | 5-step systematic debugging |
| REFINING | ✅ | — | Feedback loop iteration |
| COMPLETE | ✅ | completion_summary_{session}.md | Finalization with aggregated summary |

**Status Key:**
- ✅ = Stable and tested
- 🔬 Review = Output is generated; review recommended before production use

### Runtime Layer (Layer 2 - Execution Engine)

The actual executable surface:

| Script | Status | Purpose |
|--------|--------|---------|
| `scripts/router.py` | ✅ Stable | Route user input to phase |
| `scripts/workflow_engine.py` | ✅ Stable | Phase orchestration, state transitions, frontier scheduling |
| `scripts/unified_state.py` | ✅ Stable | Unified state management (single source of truth) |
| `scripts/task_decomposer.py` | ✅ Stable | Task decomposition with IDs |
| `scripts/trajectory_logger.py` | ✅ Stable | Trajectory persistence + resume |
| `scripts/memory_ops.py` | ✅ Stable | SESSION-STATE.md operations |
| `scripts/task_tracker.py` | ✅ Stable | Task progress tracking |
| `scripts/search_adapter.py` | ✅ Stable | Web search adapter for RESEARCH (Exa/DuckDuckGo) |
| `scripts/team_agent.py` | ✅ Stable | Small-team orchestration foundations (lead + typed workers) |
| `scripts/experimental/parallel_executor.py` | 🔬 Experimental | Parallel Band execution |
| `scripts/experimental/agent_spawner.py` | 🔬 Experimental | Multi-agent orchestration (heavyweight) |
| `scripts/experimental/semantic_router.py` | 🔬 Experimental | Semantic similarity routing |
| `scripts/experimental/execution_loop.py` | 🔬 Experimental | Execution loop patterns |
| `scripts/experimental/evaluator.py` | 🔬 Experimental | Generator-Evaluator pattern |
| `scripts/experimental/context_manager.py` | 🔬 Experimental | Context reset patterns |

### State Files

| File | Status | Description |
|------|--------|-------------|
| `.workflow_state.json` | ✅ Primary | Unified state (schema validated, contains trigger_type) |
| `.artifacts.json` | ✅ Active | Artifact registry (progress, plan, session, tracker) |
| `SESSION-STATE.md` | ✅ Active | Session state (markdown) |
| `progress.md` | ✅ Active | Phase progress (markdown) |
| `task_plan.md` | 🔄 Legacy | Compatibility projection only; new planning uses `.specs/<feature>/...` |

## Quickstart

### Basic Workflow

```bash
# Route a request
python3 scripts/router.py "帮我搜索最佳实践"

# Initialize workflow
python3 scripts/workflow_engine.py --op=init --prompt "实现REST API" --workdir .

# Get current state
python3 scripts/workflow_engine.py --op=snapshot --workdir .

# Validate state
python3 scripts/unified_state.py --op=validate --workdir .

# Advance to next phase
python3 scripts/workflow_engine.py --op=advance --phase=EXECUTING --workdir .

# Recommend next phases
python3 scripts/workflow_engine.py --op=recommend --workdir .
```

`snapshot` 现在会返回下一阶段的上下文提示：

- `memory_hints`: relevant long-term memory summaries
- `memory_query`: the search query used for retrieval
- `memory_intent`: `plan` / `review` / `debug` / `auto`

### Unified State Management (NEW)

```bash
# Initialize with unified state
python3 scripts/unified_state.py --op=init --prompt "your task" --workdir .

# Validate schema
python3 scripts/unified_state.py --op=validate --workdir .

# Get snapshot
python3 scripts/unified_state.py --op=snapshot --workdir .

# List trajectories
python3 scripts/unified_state.py --op=list-trajectories --workdir .
```

### Task Decomposition (NEW)

```bash
# Decompose task into structured tasks
python3 scripts/task_decomposer.py --prompt "实现用户认证模块：注册、登录、登出"
```

### Plan-Driven Execution (spec-kit chain)

规划现在以 spec/plan/tasks/contract 为主：

```bash
# 验证任务计划（检查循环依赖等）
python3 scripts/workflow_engine.py --op validate-plan --workdir .

# 更新任务状态
python3 scripts/workflow_engine.py --op update-task --task-id TASK-001 --status in_progress --workdir .

# 记录决策到 trajectory
python3 scripts/workflow_engine.py --op log-decision --decision "选择方案A" --reason "更简单的实现" --workdir .

# 记录文件变更到 trajectory
python3 scripts/workflow_engine.py --op log-file --path auth.py --action create --workdir .

# 完成工作流
python3 scripts/workflow_engine.py --op complete --workdir .
```

**任务计划字段：**
- `id`: 任务唯一标识 (TASK-001)
- `title`: 任务标题
- `status`: backlog | in_progress | completed | blocked
- `priority`: P0 | P1 | P2 | P3
- `dependencies`: 依赖的任务ID列表
- `owned_files`: 任务拥有的文件
- `verification`: 验证方法
- `acceptance`: 验收标准

## Architecture

```
Layer 1: Skill Specs (skills/*.md)
└── Phase definitions with status markers

Layer 2: Workflow Runtime (scripts/*.py)
├── router.py ✅ - entry routing
├── workflow_engine.py ✅ - phase orchestration
├── unified_state.py ✅ - unified state management (single source)
├── task_decomposer.py ✅ - task breakdown
├── trajectory_logger.py ✅ - trajectory + resume
├── memory_ops.py ✅ - session state operations
├── task_tracker.py ✅ - task tracking
└── experimental/
    ├── semantic_router.py 🔬 - semantic routing
    ├── execution_loop.py 🔬 - execution loops
    ├── parallel_executor.py 🔬 - parallel execution
    ├── agent_spawner.py 🔬 - multi-agent
    ├── evaluator.py 🔬 - Generator-Evaluator
    └── context_manager.py 🔬 - context management
```

## Current Capabilities (What Works)

### ✅ Stable (Core Runtime)
- Phase routing (keyword-based)
- Workflow initialization and state management
- Unified state schema with validation
- Task decomposition with unique IDs
- Trajectory logging and resume
- Session state management
- Task progress tracking

### 🔬 Experimental (Not Yet in Main Runtime)
- Semantic routing (embedding-based)
- Execution loop patterns (ReAct/Plan-and-Execute/Reflexion)
- Parallel execution bands
- Multi-agent orchestration
- Generator-Evaluator pattern
- Context manager

### Experimental Features (🔬 Not in Main Runtime)

> **Note:** These features are experimental and NOT integrated into the main workflow. Do not rely on them for production use.

Experimental modules are documented separately in [docs/roadmap/experimental-modules.md](docs/roadmap/experimental-modules.md), including:
- Module inventory and integration status
- Promotion criteria (what makes a module ready for stable)
- Decision criteria for removal

Available experimental modules:
- `semantic_router.py` - Embedding-based routing (design reference)
- `execution_loop.py` - ReAct/Plan-and-Execute patterns (design reference)
- `parallel_executor.py` - Parallel Band execution (high complexity)
- `agent_spawner.py` - Multi-agent orchestration (based on ruflo patterns)
- `evaluator.py` - Generator-Evaluator pattern (based on Anthropic harness)
- `context_manager.py` - Context checkpoint/handoff (based on Anthropic harness)

### P2 New Features

**Schema Migration** (`state_schema.py`):
```python
from state_schema import migrate_state, SCHEMA_VERSION

# 自动迁移到最新版本
new_state = migrate_state(old_state)
```

**Artifact Registry** (`unified_state.py`):
```bash
# 工件自动注册到 .artifacts.json
# 类型: state, trajectory, plan, findings, review, progress, session, tracker, custom
```

**已注册工件类型**:
- `progress.md` -> type: progress
- `.specs/<feature>/tasks.md` -> type: plan (canonical)
- `task_plan.md` -> type: plan (legacy compatibility projection)
- `SESSION-STATE.md` -> type: session
- `.task_tracker.json` -> type: tracker

## Roadmap (v5.8.1 - Completed)

> Note: "✅ Done" indicates the feature exists with minimum viable capability. "🔄" indicates mature/implemented.

| Feature | Status | Notes |
|---------|--------|-------|
| Schema migration mechanism | ✅ Min Viable | Basic migration framework in place |
| Artifact registry | ✅ Min Viable | Core registry working, business artifact coverage expanding |
| Plan-driven execution | ✅ Min Viable | Task status updates work, affects phase recommendations |
| Executable task plan format | ✅ Done | Task IDs, priorities, dependencies supported |
| Trajectory integration | ✅ Done | Full persistence and resume supported |
| trigger_type in WorkflowState | ✅ Done | Formal field in unified state schema |
| Phase history on init | ✅ Done | Initial phase written to history on init |
| Resume main chain fix | ✅ Done | State and trajectory sync on resume |
| Independent module tests | ✅ Done | 68+ tests in core suite |
| workflow_state.py removed | ✅ Done | unified_state.py is single source of truth |

## Two-Layer Architecture

### Layer 1: Skill Specs (`skills/`)

Each skill is a Markdown specification that describes:
- What the phase does
- Entry/exit criteria
- Core processes
- Status: `implemented | planned | deprecated`

### Layer 2: Workflow Runtime (`scripts/`)

The executable code that implements the workflow:
- State management
- Phase transitions
- Trajectory logging
- Task tracking

**Important**: If a capability is in `skills/` but not in `scripts/`, it's a **design target**, not current behavior.

## Documentation Structure

```
README.md          - This file (capabilities, quickstart)
docs/
├── roadmap/       - Planned features and limitations
│   └── roadmap.md
└── history/       - Version history
    └── v5-history.md
```

## Validation

```bash
# Full test suite (302 tests)
python3 -m pytest tests/ -q

# Core workflow tests (69 tests - includes failure handling)
python3 -m pytest tests/test_workflow_engine.py tests/test_e2e_business.py tests/test_workflow_chain.py tests/test_task_decomposer.py tests/test_artifact_registry.py tests/test_trajectory.py tests/test_failure_handling.py -q

# Quality gate tests (19 tests)
python3 -m pytest tests/test_quality_gate.py -v

# Validate unified state
python3 scripts/unified_state.py --op=validate --workdir .
```

## Historical Versions

For v4.x through v5.x history, benchmarks, and detailed comparisons, see:
- [docs/history/v5-history.md](docs/history/v5-history.md)

## License

MIT
