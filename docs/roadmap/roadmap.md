# Agentic Workflow Roadmap

This directory contains planned features and capabilities.

## Phase 1: Foundation (Completed v5.11.0)

### Completed
- [x] Basic workflow engine (`scripts/workflow_engine.py`)
- [x] State management (`scripts/unified_state.py`) - 统一状态，单一真相来源
- [x] Task decomposition (`scripts/task_decomposer.py`)
- [x] Trajectory logging (`scripts/trajectory_logger.py`) - with resume support
- [x] Router with keyword matching (`scripts/router.py`)
- [x] Status markers on all skill specs
- [x] README cleanup and restructuring
- [x] End-to-end business chain tests
- [x] Quality gate integration with fail-closed strategy
- [x] Real web search for RESEARCH phase (DuckDuckGo/Exa)
- [x] Task-directed REVIEWING (owned_files > file_changes > workdir_scan)
- [x] CI/CD integration (GitHub Actions + pre-commit)
- [x] Project restructuring (experimental/, utils/, tools/ directories)

## Phase 2: Control Plane (Planned)

### Planned Features

#### Multi-Agent Spawning
- [ ] 12 subagent definitions exist in `agents/` but actual spawning not integrated
- [ ] Need: `scripts/agent_spawner.py` to coordinate subagent lifecycle

#### Parallel Execution Orchestration
- [ ] Design exists in `skills/_shared/parallel-execution.md`
- [ ] Need: Actual orchestration in workflow_engine.py
- [ ] Need: Band-aware phase scheduling

#### Semantic Router (L3)
- [ ] Current: keyword-based routing in `router.py`
- [ ] Planned: complexity assessment + semantic understanding
- [ ] Need: `scripts/semantic_router.py` integration (in experimental/)

### Dependencies
- Phase 2 requires Phase 1 complete

## Phase 3: Intelligence (Future)

### Planned Features

#### Trajectory-based Learning
- [x] `./trajectories/` directory for persistence (done)
- [ ] Pattern detection from past runs
- [ ] Experience store integration (`scripts/experience_store.py`)

#### Auto Task Decomposition with LLM
- [ ] Current: keyword-based decomposition in `task_decomposer.py`
- [ ] Planned: LLM-powered task breakdown with dependency graph
- [ ] Need: Integration with planning phase

#### WAL (Write-Ahead Log) Auto-commit
- [ ] Design: automatic commit on phase completion
- [ ] Need: `scripts/wal_scanner.py` integration with git hooks

### Dependencies
- Phase 3 requires Phase 2 complete

## Known Limitations

| Limitation | Description | Workaround |
|------------|-------------|------------|
| No semantic routing | Router is keyword-based, not semantic | Use explicit phase triggers |
| No trajectory resume | Cannot resume from interrupted workflow | Restart from beginning |
| No multi-agent orchestration | Subagents defined but not coordinated | Manual agent spawning |
| No parallel phase execution | Bands designed but not implemented | Sequential execution |
| State in markdown files | SESSION-STATE.md, progress.md are fragile | Use `.workflow_state.json` |

## Architecture Layers

```
Layer 1: Skill Specs (skills/*.md)
├── Status markers added (implemented | planned | deprecated)
└── Describes WHAT to do, not HOW

Layer 2: Workflow Runtime (scripts/*.py)
├── Current: workflow_engine.py, router.py, state management
├── Experimental: agent_spawner.py, parallel_executor.py, semantic_router.py
└── Describes HOW to execute

Runtime Surface:
├── scripts/router.py - lightweight routing
├── scripts/workflow_engine.py - phase orchestration
├── scripts/unified_state.py - state management
├── scripts/task_decomposer.py - task breakdown
├── scripts/trajectory_logger.py - trajectory persistence
├── scripts/memory_ops.py - SESSION-STATE.md operations
├── scripts/quality_gate.py - quality enforcement
├── scripts/search_adapter.py - web search with metadata validation
└── scripts/experimental/ - experimental features (semantic_router, parallel_executor, etc.)
```
