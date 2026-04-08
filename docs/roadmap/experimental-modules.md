# Archived Experimental References

This document is a reference archive for experimental features that were explored
outside the authoritative runtime. The main runtime is `scripts/workflow_engine.py`;
these modules are not part of the active promotion path.

## Purpose

These modules are kept here only as references to prior design experiments.
They should not be treated as a roadmap for the stable runtime.

## Module Inventory

| Module | Purpose | Status | Notes |
|--------|---------|--------|-------|
| `semantic_router.py` | Embedding-based phase routing | Archived reference | Falls back to keyword routing in the stable runtime |
| `execution_loop.py` | ReAct/Plan-and-Execute patterns | Archived reference | Design reference only |
| `parallel_executor.py` | Parallel Band execution | Archived reference | High complexity; not in the stable runtime |
| `agent_spawner.py` | Multi-agent orchestration | Archived reference | Replaced by `team_agent.py` |
| `evaluator.py` | Generator-Evaluator pattern | Archived reference | Not in the stable runtime |
| `context_manager.py` | Context checkpoint/handoff | Archived reference | Replaced by checkpoint/trajectory flow |

## Archival Rule

If a new capability is needed, implement it directly in the stable runtime or
in a shared helper that is consumed by the stable runtime. Do not revive these
modules as a parallel mainline without a concrete migration plan.
