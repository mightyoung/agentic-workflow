# Archived Experimental References

This document is a historical archive of design experiments that are no longer
part of the runtime. The authoritative runtime is `scripts/workflow_engine.py`.

## Purpose

These modules are preserved only so readers can understand what was tried
before the repository converged on a single runtime.

## Module Inventory

| Module | Purpose | Status | Notes |
|--------|---------|--------|-------|
| `semantic_router.py` | Embedding-based phase routing | Archived reference | Historical design only |
| `execution_loop.py` | ReAct/Plan-and-Execute patterns | Archived reference | Historical design only |
| `parallel_executor.py` | Parallel Band execution | Archived reference | Historical design only |
| `agent_spawner.py` | Multi-agent orchestration | Archived reference | Historical design only |
| `evaluator.py` | Generator-Evaluator pattern | Archived reference | Historical design only |
| `context_manager.py` | Context checkpoint/handoff | Archived reference | Historical design only |

## Archival Rule

Do not use this archive as a source of active implementation guidance. New
capabilities belong in the stable runtime or its shared helpers, not in the
archived modules listed above.
