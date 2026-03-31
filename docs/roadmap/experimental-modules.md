# Experimental Modules

This directory contains documentation for experimental features that are not yet integrated into the main runtime.

## Purpose

These modules represent ambitious extensions to the core workflow system. They are kept here to:
- Allow experimentation without affecting stable code
- Provide a clear boundary between production and research code
- Enable easy removal if a module doesn't prove useful

## Module Inventory

| Module | Purpose | Integration Status | Notes |
|--------|---------|-------------------|-------|
| `semantic_router.py` | Embedding-based phase routing | Not integrated | Falls back to keyword routing |
| `execution_loop.py` | ReAct/Plan-and-Execute patterns | Not integrated | Design reference only |
| `parallel_executor.py` | Parallel Band execution | Not integrated | High complexity |
| `agent_spawner.py` | Multi-agent orchestration | Not integrated | Based on ruflo patterns |
| `evaluator.py` | Generator-Evaluator pattern | Not integrated | Based on Anthropic harness |
| `context_manager.py` | Context checkpoint/handoff | Not integrated | Based on Anthropic harness |

## Decision Criteria for Promotion

A module should be promoted from experimental to stable when:

1. **Integration**: It is called by `workflow_engine.py` in the main execution path
2. **Testing**: It has dedicated tests with >80% coverage
3. **Documentation**: Entry command, state artifact, and test coverage are documented
4. **Stability**: No known critical bugs, handles edge cases gracefully
5. **User Need**: Clear use case that core modules cannot fulfill

## Review Cadence

Experimental modules should be reviewed quarterly (every 3 months) to:
- Remove modules that proved unsuccessful
- Promote successful modules to stable
- Update documentation

## Path Forward

To promote an experimental module:

1. Ensure it works standalone with CLI interface
2. Write integration tests
3. Update `workflow_engine.py` to call it in the main path
4. Update README.md capability tables
5. Remove "(experimental)" designation
