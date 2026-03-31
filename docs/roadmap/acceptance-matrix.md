# Acceptance Matrix

This document tracks the verification criteria for each capability in the agentic-workflow system.

## Verification Criteria

Each capability must answer three questions:
1. **Entry Command**: How to invoke this capability
2. **State Artifact**: What files/state it produces
3. **Test Coverage**: How it is tested

---

## ✅ Stable Capabilities

### 1. Keyword Routing

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/router.py "用户输入"` |
| State Artifact | None (in-memory routing) |
| Test Coverage | `tests/test_router.py` - routing logic tests |
| Verification | Assert correct phase selection for various inputs |

### 2. Unified State Management

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/workflow_engine.py --op init --prompt "..."` |
| State Artifact | `.workflow_state.json` |
| Test Coverage | `tests/test_e2e_business.py`, `tests/test_workflow_engine.py` |
| Verification | Schema validation, state transitions, file persistence |

### 3. Workflow Engine

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/workflow_engine.py --op [init/advance/snapshot]` |
| State Artifact | `.workflow_state.json`, `progress.md` |
| Test Coverage | `tests/test_workflow_engine.py` - 8 tests |
| Verification | Phase transitions, state updates, artifact creation |

### 4. Task Decomposition

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/task_decomposer.py --prompt "..."` |
| State Artifact | Tasks returned in memory (not persisted) |
| Test Coverage | `tests/test_task_decomposer.py` if exists |
| Verification | Task IDs unique, priorities assigned correctly |

### 5. Trajectory Logging

| Criterion | Details |
|----------|---------|
| Entry Command | Automatic via `workflow_engine.py --op init` |
| State Artifact | `trajectories/{date}/{session_id}/trajectory.json` |
| Test Coverage | `tests/test_e2e_business.py::TestTrajectoryPersistence` |
| Verification | Phase transitions logged, resume works |

### 6. Session State

| Criterion | Details |
|----------|---------|
| Entry Command | Automatic via `workflow_engine.py --op init` |
| State Artifact | `SESSION-STATE.md` |
| Test Coverage | Implicit via workflow tests |
| Verification | Task info and resume point updated |

### 7. Task Tracking

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/task_tracker.py --op create --task-id T001` |
| State Artifact | `.task_tracker.json` |
| Test Coverage | Implicit via workflow tests |
| Verification | Task creation, status updates, quality gates |

---

## 🔬 Experimental Capabilities

### 8. Semantic Routing

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/semantic_router.py --text "..." --scores` |
| State Artifact | None (in-memory) |
| Test Coverage | `tests/test_semantic_router.py` if exists |
| Status | Not integrated into main routing |

### 9. Execution Loop

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/execution_loop.py --task "..." --mode iterative` |
| State Artifact | In-memory state during execution |
| Test Coverage | `tests/test_execution_loop.py` if exists |
| Status | Design reference, not production-ready |

### 10. Parallel Execution

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/parallel_executor.py --op execute-band --band 1` |
| State Artifact | None |
| Test Coverage | `tests/test_parallel_executor.py` if exists |
| Status | High complexity, not integrated |

### 11. Multi-Agent Orchestration

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/agent_spawner.py --op orchestrate --task "..."` |
| State Artifact | Agent registry state |
| Test Coverage | `tests/test_agent_spawner.py` if exists |
| Status | Based on ruflo, complex design |

### 12. Generator-Evaluator

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/evaluator.py --negotiate --task-description "..."` |
| State Artifact | Sprint contracts (in-memory) |
| Test Coverage | `tests/test_evaluator.py` if exists |
| Status | Based on Anthropic harness design |

### 13. Context Manager

| Criterion | Details |
|----------|---------|
| Entry Command | `python3 scripts/context_manager.py --op checkpoint --phase ...` |
| State Artifact | `.checkpoints/` directory |
| Test Coverage | `tests/test_context_manager.py` if exists |
| Status | Based on Anthropic harness design |

---

## Verification Checklist

For each capability before marking as stable:

- [ ] **Entry Command**: CLI interface works as documented
- [ ] **State Artifact**: Correct file created/updated on disk
- [ ] **Test Coverage**: At least one test exercising the capability
- [ ] **Integration**: No manual intervention required to use
- [ ] **Error Handling**: Graceful handling of invalid inputs

## Test Commands

```bash
# Run all stable capability tests
python3 -m pytest tests/test_workflow_engine.py tests/test_e2e_business.py -v

# Run specific capability tests
python3 -m pytest tests/test_workflow_engine.py -v

# Run with coverage
python3 -m pytest tests/ --cov=scripts --cov-report=term-missing
```
