# Agentic Workflow Roadmap

This directory contains planned features and capabilities.

## Phase 1: Foundation (Completed v6.3.0)

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

## Current Boundaries

| Boundary | Description | Practical Guidance |
|----------|-------------|--------------------|
| Semantic routing is helper-only | Primary routing is still keyword-based; middleware may enrich the input portrait but does not replace router.py | Use explicit phase triggers when intent is ambiguous |
| Parallel execution is scheduling-only | Frontier can produce parallel-safe groups, but execution is still coordinated through the single authoritative runtime | Treat parallel groups as orchestration hints, not concurrent workers |
| Markdown state is compatibility-sidecar | `SESSION-STATE.md` and `progress.md` remain for compatibility, but `.workflow_state.json` is the authoritative state | Prefer `.workflow_state.json` for automation and validation |
| Experimental modules are archived | `scripts/experimental/` is reference-only and not part of the runtime | Do not route new work into archived modules |

## Architecture Layers

```
Layer 1: Skill Specs (skills/*.md)
├── Status markers added (implemented | planned | deprecated)
└── Describes WHAT to do, not HOW

Layer 2: Workflow Runtime (scripts/*.py)
├── Current: workflow_engine.py, router.py, state management
├── Shared helpers: middleware.py, runtime_profile.py
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
└── scripts/experimental/ - archived design references only
```
