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
| Test Coverage | `tests/test_workflow_chain.py` - router-to-plan integration tests |
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
