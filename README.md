# Agentic Workflow

> Unified AI Development Workflow Skill - 统一智能体工作流

## What is This?

Agentic Workflow is a **skill-based workflow system** that provides systematic approaches to handling development tasks. It uses a phase-based architecture where different skills handle different aspects of the development lifecycle.

**Current Version**: 5.10.0

## Current Capabilities (v5.10.0)

This section describes what actually works **today** via the scripts layer.

### Phase Skills (Layer 1 - Skill Specs)

| Phase | Status | Description |
|-------|--------|-------------|
| ROUTER | ✅ Stable | Keyword-based routing |
| OFFICE-HOURS | ✅ Stable | Product consultation |
| EXPLORING | ✅ Stable | Socratic deep exploration |
| RESEARCH | ✅ Stable | Web search + findings artifact output |
| THINKING | ✅ Stable | Expert reasoning |
| PLANNING | ✅ Stable | Task breakdown with plan artifact |
| EXECUTING | ✅ Stable | TDD-driven implementation |
| REVIEWING | ✅ Stable | Code review + review artifact output |
| DEBUGGING | ✅ Stable | 5-step systematic debugging |
| REFINING | ✅ Stable | Feedback loop iteration |
| COMPLETE | ✅ Stable | Finalization + completion_summary artifact |

### Runtime Layer (Layer 2 - Execution Engine)

The actual executable surface:

| Script | Status | Purpose |
|--------|--------|---------|
| `scripts/router.py` | ✅ Stable | Route user input to phase |
| `scripts/workflow_engine.py` | ✅ Stable | Phase orchestration, state transitions |
| `scripts/unified_state.py` | ✅ Stable | Unified state management (single source of truth) |
| `scripts/task_decomposer.py` | ✅ Stable | Task decomposition with IDs |
| `scripts/trajectory_logger.py` | ✅ Stable | Trajectory persistence + resume |
| `scripts/memory_ops.py` | ✅ Stable | SESSION-STATE.md operations |
| `scripts/task_tracker.py` | ✅ Stable | Task progress tracking |
| `scripts/parallel_executor.py` | 🔬 Experimental | Parallel Band execution |
| `scripts/agent_spawner.py` | 🔬 Experimental | Multi-agent orchestration |
| `scripts/semantic_router.py` | 🔬 Experimental | Semantic similarity routing |
| `scripts/execution_loop.py` | 🔬 Experimental | Execution loop patterns |
| `scripts/evaluator.py` | 🔬 Experimental | Generator-Evaluator pattern |
| `scripts/context_manager.py` | 🔬 Experimental | Context reset + checkpoints |

### State Files

| File | Status | Description |
|------|--------|-------------|
| `.workflow_state.json` | ✅ Primary | Unified state (schema validated, contains trigger_type) |
| `.artifacts.json` | ✅ Active | Artifact registry (progress, plan, session, tracker) |
| `SESSION-STATE.md` | ✅ Active | Session state (markdown) |
| `progress.md` | ✅ Active | Phase progress (markdown) |
| `task_plan.md` | ✅ Active | Task breakdown (markdown) |

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

### Parallel Execution Bands (NEW)

```bash
# List all bands
python3 scripts/parallel_executor.py --op list-bands

# Execute a specific band (Band 1: RESEARCH||THINKING)
python3 scripts/parallel_executor.py --op execute-band --band 1

# Execute full workflow with band scheduling
python3 scripts/parallel_executor.py --op execute-workflow --phases ROUTER RESEARCH THINKING PLANNING EXECUTING COMPLETE
```

### Multi-Agent Orchestration (NEW)

```bash
# List available agents
python3 scripts/agent_spawner.py --op list

# Domain-based routing
python3 scripts/agent_spawner.py --op spawn-domain --domain research --task "搜索..."

# Full orchestration with consensus
python3 scripts/agent_spawner.py --op orchestrate --task "研究并实现REST API"

# Health monitoring
python3 scripts/agent_spawner.py --op health
```

### Semantic Routing (NEW)

```bash
# Semantic routing with similarity matching
python3 scripts/semantic_router.py --text "帮我搜索微服务最佳实践"

# Show all phase scores
python3 scripts/semantic_router.py --text "帮我搜索微服务最佳实践" --scores --verbose

# Router with semantic fallback
python3 scripts/router.py --semantic "帮我搜索微服务最佳实践"
```

### Execution Loop (NEW)

```bash
# Iterative mode (ReAct): Thought -> Action -> Observation
python3 scripts/execution_loop.py --task "实现REST API" --mode iterative

# Plan-and-Execute mode: Plan first, then execute
python3 scripts/execution_loop.py --task "实现REST API" --mode plan_and_execute

# Reflexion mode: Self-reflection with improvement
python3 scripts/execution_loop.py --task "实现REST API" --mode reflexion

# Adaptive mode: Auto-select based on task complexity
python3 scripts/execution_loop.py --task "实现REST API" --mode adaptive
```

### Generator-Evaluator Pattern (NEW)

借鉴 Anthropic Harness Design 最佳实践：

```bash
# 评估输出
python3 scripts/evaluator.py --output output.json --threshold 0.7

# 协商 Sprint Contract
python3 scripts/evaluator.py --negotiate --task-description "实现REST API"
```

**核心组件：**
- `SprintContract`: Generator 和 Evaluator 之间的预协商协议
- `WorkflowEvaluator`: 基于 Grading Rubrics 的严格评估
- `ContractNegotiator`: 自动协商成功标准

### Context Manager (NEW)

借鉴 Anthropic Harness Design 最佳实践：

```bash
# 检查是否需要重置上下文
python3 scripts/context_manager.py --op check --trajectory trajectory.json --context context.txt

# 创建检查点
python3 scripts/context_manager.py --op checkpoint --phase EXECUTING --session-id xxx --trajectory trajectory.json --context context.txt

# 列出所有检查点
python3 scripts/context_manager.py --op list

# 重置并恢复
python3 scripts/context_manager.py --op reset --checkpoint-id cp_xxx --next-phase EXECUTING
```

**核心功能：**
- `ContextCheckpoint`: 上下文检查点数据结构
- `HandoffDocument`: 交接文档 (Markdown 格式)
- `ContextManager`: 检查点创建、保存、恢复

### Plan-Driven Execution (NEW)

任务计划现在支持可执行格式：

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
├── semantic_router.py 🔬 - semantic routing (experimental)
├── execution_loop.py 🔬 - execution loops (experimental)
├── parallel_executor.py 🔬 - parallel execution (experimental)
├── agent_spawner.py 🔬 - multi-agent (experimental)
├── evaluator.py 🔬 - Generator-Evaluator (experimental)
└── context_manager.py 🔬 - context management (experimental)
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
- `task_plan.md` -> type: plan
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
# Core workflow tests (69 tests - includes failure handling)
python3 -m pytest tests/test_workflow_engine.py tests/test_e2e_business.py tests/test_workflow_chain.py tests/test_task_decomposer.py tests/test_artifact_registry.py tests/test_trajectory.py tests/test_failure_handling.py -q

# Task decomposition tests (14 tests)
python3 -m pytest tests/test_task_decomposer.py -v

# Artifact registry tests (11 tests)
python3 -m pytest tests/test_artifact_registry.py -v

# Trajectory tests (18 tests)
python3 -m pytest tests/test_trajectory.py -v

# Failure handling tests (9 tests)
python3 -m pytest tests/test_failure_handling.py -v

# Validate unified state
python3 scripts/unified_state.py --op=validate --workdir .
```

## Historical Versions

For v4.x through v5.x history, benchmarks, and detailed comparisons, see:
- [docs/history/v5-history.md](docs/history/v5-history.md)

## License

MIT
