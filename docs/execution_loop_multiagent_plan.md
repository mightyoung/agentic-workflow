# Execution Loop and Multi-Agent Orchestration Plan

> Purpose: adapt long-running harness and multi-agent best practices to this repository's real role as an agent skill + harness.
> Updated: 2026-04-01

## Scope

This document focuses on two questions:

1. How should the stable runtime execute complex, stepwise tasks without drifting?
2. How should multi-agent orchestration be introduced without overwhelming the current harness?

It is based on:

- Anthropic's long-running harness design patterns
- Ruflo's swarm orchestration ideas
- graph/checkpoint style best practices from durable agent runtimes

The goal is not to copy any external system literally.
The goal is to borrow the load-bearing parts and keep this harness small, explicit, and debuggable.

## Design Principles

### 1. Execution Must Be Explicit

Prompt-only loops are too implicit for long tasks.

The runtime should make these things explicit:

- current objective
- current contract
- current frontier of executable tasks
- current owner(s)
- current verification state
- current checkpoint / handoff state

### 2. Parallelism Must Follow Ownership

Parallelism should not start from "how many agents can we spawn?"
It should start from:

- dependency graph
- `owned_files`
- verification boundaries
- artifact merge cost

If two tasks touch the same files or require the same artifact, default to serial.

### 3. Evaluation Must Be Separate From Generation

For complex tasks, the agent that builds should not be the final judge.

The stable runtime should separate:

- planner / coordinator
- executor / worker
- evaluator / reviewer

This does not require a giant swarm.
It requires a clean contract and a skeptical evaluation step.

### 4. Checkpoints Must Be Conditional, Not Constant

Checkpointing is useful when:

- the task is long-running
- the trajectory becomes large
- the phase is about to switch
- a worker fails repeatedly
- a run is about to be resumed in a fresh context

Checkpointing should not be a default tax on every short task.

### 5. Stable Runtime Must Stay Smaller Than Experimental Runtime

The stable runtime should absorb only the minimum load-bearing mechanisms:

- task contract
- bounded execution loop
- evaluator gate
- checkpoint/handoff
- small-team orchestration

Not:

- giant swarm topologies
- heavy consensus everywhere
- reinforcement learning loops
- 100+ agent catalogs

## What To Borrow

### From Anthropic

- planner -> generator -> evaluator separation
- explicit contract before execution
- structured handoff/checkpoint artifacts
- evaluator thresholds that can reject a round
- periodic simplification: remove scaffolding that is no longer load-bearing

### From Ruflo

- domain-based routing
- queen/worker style hierarchy as the default topology
- agent registry with health / availability
- task orchestration based on dependency and capability
- explicit degraded/fallback modes

### From Graph-Based Runtimes

- explicit state machine
- frontier-based scheduling
- checkpointable state
- bounded loops with retry / interrupt / resume

## What Not To Borrow

### Do Not Copy From Anthropic Literally

- expensive always-on evaluator loops for every task
- heavyweight multi-hour build harness as the default mode
- context reset as a universal requirement

### Do Not Copy From Ruflo Literally

- massive agent catalogs
- Raft / BFT / gossip consensus in stable runtime
- always-on learning loops
- generalized swarm complexity before the stable loop is proven

## Proposed Stable Execution Loop

### New Runtime State Machine

```text
ROUTER
  -> PLANNING
  -> CONTRACTING
  -> FRONTIER_SELECT
  -> ASSIGN
  -> EXECUTING
  -> EVALUATING
  -> {REPLAN | DEBUGGING | CHECKPOINT | COMPLETE}
```

### Phase Semantics

- `PLANNING`
  - produce or refine `task_plan.md`
  - ensure tasks have `id`, `dependencies`, `owned_files`, `verification`, `acceptance`

- `CONTRACTING`
  - generate the execution contract for the next frontier
  - define "what exactly is done" before code is written

- `FRONTIER_SELECT`
  - choose all tasks whose dependencies are satisfied
  - split them into serial-safe and parallel-safe sets

- `ASSIGN`
  - map each frontier task to one worker role
  - ensure no file ownership conflicts

- `EXECUTING`
  - perform bounded task execution
  - track file changes, decisions, and produced artifacts

- `EVALUATING`
  - run quality gate
  - run task-specific evaluator checks
  - either accept, request revision, or reroute to debugging/replan

- `CHECKPOINT`
  - write handoff artifact only when thresholds or state transitions justify it

### Execution Policy

Introduce a simple policy enum:

- `DIRECT`
  - single agent, no frontier scheduler
  - for small tasks

- `SERIAL_PLAN`
  - one task at a time
  - default for most engineering work

- `FRONTIER_PARALLEL`
  - execute only dependency-free, ownership-safe frontier tasks in parallel
  - stable mode for medium complexity

- `TEAM_SWARM`
  - reserved for experimental mode

The router or planner should select this policy based on:

- task count
- dependency width
- `owned_files` conflicts
- expected artifact merge cost

## Proposed Task Contract

Add a stable contract artifact for the next execution slice.

Suggested file:

- `.contract.json`

Suggested fields:

```json
{
  "contract_id": "ctr_20260401_01",
  "phase": "EXECUTING",
  "tasks": ["TASK-003", "TASK-004"],
  "goal": "Implement auth API and session middleware",
  "owned_files": ["auth.py", "session.py"],
  "verification": [
    "pytest tests/test_auth.py -q",
    "python3 -m py_compile auth.py session.py"
  ],
  "acceptance": [
    "login returns session cookie",
    "logout invalidates session"
  ],
  "rejection_threshold": "any_verification_failure",
  "created_by": "planner",
  "approved_by": "evaluator"
}
```

### Why This Matters

Today the runtime has `task_plan.md`, but not a strong execution contract consumed by both executor and reviewer.

This contract closes that gap:

- executor knows exactly what to build now
- reviewer knows exactly what to check now
- complete gate can validate against a concrete artifact

## Proposed Evaluator Integration

Do not promote the entire experimental evaluator into stable runtime.

Promote a thin version:

- stable evaluator path is only for:
  - P0/P1 tasks
  - tasks with code changes
  - tasks that failed gate once
  - tasks explicitly marked `require_review`

### Stable Evaluator Responsibilities

- check contract compliance
- check quality gate result
- inspect produced artifacts
- emit:
  - `pass`
  - `need_revision`
  - `fail`

### Stable Evaluator Outputs

Suggested artifact:

- `evaluation_<session>.md`

Suggested metadata:

- `contract_id`
- `tasks`
- `files_reviewed`
- `criteria_failed`
- `revision_required`

## Proposed Checkpoint / Handoff Integration

Do not turn checkpointing into a default phase.

Instead, trigger it when:

- trajectory step count exceeds threshold
- task frontier is exhausted and a new frontier is about to start
- evaluator sends the run to debugging
- a resume boundary is intentionally created

Suggested stable artifacts:

- `.checkpoints/<checkpoint_id>.json`
- `handoff_<checkpoint_id>.md`

### Minimum Stable Checkpoint Contents

- current phase
- completed tasks
- pending frontier
- key decisions
- current artifacts
- next recommended action

This is enough to resume coherently without pulling the full experimental context system into mainline.

## Proposed Multi-Agent Topology

### Stable Topology: Lead + Small Worker Set

Use one coordinator plus a small set of typed workers:

- `planner`
- `researcher`
- `coder`
- `reviewer`
- `debugger`

The coordinator should remain thin:

- select frontier
- assign tasks
- enforce ownership rules
- collect artifacts
- decide revise / debug / complete

This is enough for the stable runtime.

### Experimental Topology: Queen / Workers

Keep these ideas in `experimental/` for now:

- strategic queen
- tactical queen
- adaptive queen
- consensus across multiple reviewers
- peer mesh communication

These are valuable experiments, but too heavy for stable by default.

## Proposed Assignment Rules

### Worker Selection

Select worker by domain:

- `RESEARCH` -> researcher
- `EXECUTING` -> coder
- `REVIEWING` -> reviewer
- `DEBUGGING` -> debugger

### Parallel Safety Rules

Tasks may run in parallel only if all of the following are true:

- dependencies satisfied
- no overlap in `owned_files`
- no shared contract artifact to mutate
- no shared migration/schema touch
- no same target deployment/config surface

Otherwise:

- serialize them
- or split the contract into separate rounds

## Proposed Agent Registry

Promote only a minimal registry into stable runtime.

Suggested file:

- `.team_registry.json`

Suggested fields:

```json
{
  "workers": [
    {
      "worker_id": "reviewer-01",
      "role": "reviewer",
      "state": "idle",
      "current_task": null,
      "lease_expires_at": null,
      "error_count": 0
    }
  ]
}
```

### Stable Registry Needs

- worker role
- current task
- lease / timeout
- state
- recent failure count

This is enough to support:

- small-team orchestration
- failure detection
- bounded retries

It is not necessary to add:

- voting systems
- weighted consensus
- health score vectors

until the stable team loop proves insufficient.

## Proposed Message Model

Do not build a general message bus first.

Stable runtime should use file-backed envelopes scoped to the current contract:

- `.messages/<contract_id>/<worker>.jsonl`

Message types:

- `assignment`
- `status`
- `artifact_ready`
- `evaluation`
- `handoff`

This gives:

- auditability
- replayability
- low coupling

without forcing a heavy broker abstraction into the runtime too early.

## Execution Loop Algorithm

### Stable Algorithm

```text
1. Route request
2. Build / validate task plan
3. Derive next frontier from dependencies
4. Create execution contract for this frontier
5. Partition frontier into serial-safe vs parallel-safe groups
6. Assign each task to one worker role
7. Execute tasks with bounded retries
8. Record artifacts, file changes, and decisions
9. Evaluate against contract + quality gate
10. If accepted:
      - mark tasks complete
      - move to next frontier
11. If rejected:
      - revise once or twice
      - else reroute to debugging or replanning
12. Create checkpoint if threshold crossed
13. Complete only when all required tasks and gates pass
```

### Loop Guards

- max rounds per contract
- max revisions per task
- max active parallel workers
- max unresolved degraded modes
- hard stop when contract and gate conflict repeatedly

## Recommended Promotion Order

### P1 - Promote To Stable First

1. `TaskContract` artifact
2. frontier scheduler based on dependencies + `owned_files`
3. thin evaluator pass after execution
4. conditional checkpoint/handoff
5. minimal team registry

### P2 - Promote Carefully

1. domain-based worker assignment
2. file-backed contract-scoped messages
3. limited parallel execution for disjoint frontiers
4. explicit degraded review mode

### P3 - Keep Experimental

1. queen hierarchy
2. consensus modes
3. self-learning routing
4. semantic routing promotion
5. generalized swarm memory

## Concrete Changes Recommended For This Repository

### 1. Add Stable Contracting Layer

Implement:

- `workflow_engine.py --op contract`
- contract artifact generation
- evaluator consumption of contract

### 2. Replace Recommend-Only With Frontier Scheduling

Current runtime recommends phases and next tasks.
It should also derive the next executable frontier:

- `--op frontier`
- returns serial-safe tasks
- returns parallel-safe task groups
- returns blocking dependencies

### 3. Introduce Small-Team Orchestration Before Full Swarm

Promote a tiny stable orchestrator:

- one lead
- one or more workers
- explicit contracts
- explicit ownership checks

Do not promote the full `agent_spawner.py` complexity directly.

### 4. Promote Checkpoint/Handoff As Thresholded Behavior

Use the experimental context manager as the source of truth for design,
but promote only:

- checkpoint trigger logic
- handoff summary artifact
- resume path from checkpoint

### 5. Keep Ruflo-Inspired Heavy Swarm Features Experimental

Do not bring these into stable yet:

- consensus mechanisms
- health scoring vectors
- topological swarm selection
- large registry catalogs

These are valuable later, but currently exceed the proven needs of the harness.

## Acceptance Criteria

This design should be considered successfully adopted only when:

1. the stable runtime can produce and consume a task contract
2. the runtime can compute a dependency frontier, not just recommend phases
3. the runtime can execute at least one parallel-safe frontier round
4. evaluator output can reject a contract round and force revision
5. checkpoint/handoff can resume a long-running task coherently
6. multi-agent orchestration remains bounded, file-auditable, and ownership-safe

## Final Recommendation

The correct direction is:

- borrow Anthropic's contract + evaluator + handoff discipline
- borrow Ruflo's domain-based orchestration and coordinator/worker split
- reject giant-swarm complexity in the stable runtime

This repository should evolve toward:

- a contract-driven execution loop
- a frontier scheduler
- a small-team orchestrator
- a conditional checkpoint/evaluator layer

not toward:

- an always-on mega-swarm platform
- generalized consensus-heavy orchestration by default

That path gives the harness more real capability without sacrificing truthfulness,
debuggability, or controllable complexity.
