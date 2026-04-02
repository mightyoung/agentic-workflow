# Experimental Modules Graduation Plan

This document outlines the graduation plan for experimental modules in `scripts/experimental/`.

## Overview

Experimental modules are not imported by any production code. They exist as reference implementations or proof-of-concept code that may be graduated to production status based on demonstrated value and integration readiness.

## Graduation Priority

| Module | Lines | Value | Dependencies | Priority | Target |
|--------|-------|-------|--------------|----------|--------|
| `execution_loop.py` | 794 | ReflexionLoop, PlanExecuteEngine | P0-3 (self-correction) | **HIGH** | Sprint 4 |
| `parallel_executor.py` | 578 | Parallel execution patterns | P0-2 (multi-agent) | **HIGH** | Sprint 4 |
| `semantic_router.py` | 694 | Embedding-based routing | P2-2 (router improvement) | MEDIUM | Backlog |
| `context_manager.py` | 501 | Checkpoint/snapshot | Already integrated (checkpoint op) | LOW | Reference |
| `agent_spawner.py` | 1357 | Multi-agent coordination | P0-2 (multi-agent) | MEDIUM | Backlog |
| `evaluator.py` | 545 | Generator-Evaluator pattern | Future work | LOW | Archive |

## Graduation Criteria

A module is ready for graduation when:
1. Has clear integration point with production code
2. Has tests covering core functionality
3. No blocking TODOs or placeholder code
4. API surface is stable (no breaking changes expected)

## Module Analysis

### execution_loop.py (794 lines)

**Contains:**
- `PhaseBand` enum: Phase execution bands (PREP, CORE, POST)
- `ParallelExecutor`: Band-based parallel execution
- `BandAwareWorkflow`: Workflow with band awareness
- `ReflectionEngine`: Reflexion-style self-correction
- `PlanExecuteEngine`: Plan-and-Execute pattern
- `ExecutionLoop`: Main execution loop

**Graduation path for P0-3:**
The `ReflectionEngine` provides the self-reflection pattern needed for P0-3 (self-correction loop). The key insight is that we don't need the full ExecutionLoop - we need the error classification and retry strategy adjustment logic.

**Action:** Extract `classify_error`, retry strategy, and error history patterns into `workflow_engine.py` handle_workflow_failure().

### parallel_executor.py (578 lines)

**Contains:**
- `LoopMode` enum: AUTO, STEP, BATCH
- `StepStatus` enum: PENDING, RUNNING, DONE, FAILED
- `LoopStep`: Individual step representation
- `ReflectionEngine`: Duplicate implementation
- `PlanExecuteEngine`: Duplicate implementation

**Issue:** This file duplicates much of execution_loop.py. The `ParallelExecutor` class provides true parallel task execution.

**Graduation path for P0-2:**
The `ParallelExecutor` class can provide the parallel task execution capability needed for multi-agent team coordination.

**Action:** Deduplicate against execution_loop.py, then integrate ParallelExecutor into TeamAgent.

### semantic_router.py (694 lines)

**Contains:**
- Embedding-based semantic routing using sklearn
- Route confidence scoring
- Dynamic route learning

**Graduation path for P2-2:**
This can replace or augment the keyword-based router in `router.py`.

**Action:** Add as optional router when embeddings available.

### agent_spawner.py (1357 lines)

**Contains:**
- Queen Agent (coordinator)
- Message Bus
- Consensus mechanism
- Worker Agent pool

**Issue:** Very large, complex design. Currently unused.

**Graduation path:**
This is a heavy-weight solution. For P0-2 (multi-agent), we should focus on lightweight task spawning via subprocess/Agent tool rather than this full coordinator pattern.

**Action:** Keep as reference design, but do not prioritize graduation.

## Recommendations

1. **execution_loop.py** - HIGH priority: The ReflexionLoop pattern is valuable but the current implementation is complex. Consider extracting just the error classification and retry strategy (already done in P0-3). The band-based parallel execution is interesting but may be overkill.

2. **parallel_executor.py** - MEDIUM priority: The ParallelExecutor provides real parallel execution capability. This could be valuable for team coordination but needs significant work to integrate.

3. **semantic_router.py** - MEDIUM priority: Useful for fuzzy matching and non-keyword routing. Low risk to add as optional enhancement.

4. **context_manager.py** - LOW priority: Already has a production integration path via the `checkpoint` operation. May need cleanup but not critical.

5. **agent_spawner.py** - LOW priority: Over-engineered for current needs. Keep as reference but don't invest heavily.

6. **evaluator.py** - LOW priority: Generator-Evaluator pattern is useful but not critical path.

## Decision: Archive Low-Priority Modules

Given limited bandwidth, recommend:
- Archive `evaluator.py` (Generator-Evaluator not on critical path)
- Keep `agent_spawner.py` as reference design only
- Focus on `execution_loop.py` patterns for P0-3 and `semantic_router.py` for P2-2
