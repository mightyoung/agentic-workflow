# Agentic Workflow Self-Improvement Program

> Scope: adapt the `autoresearch` improvement loop to this repository's real role as an agent skill and harness.
> Status: proposed
> Updated: 2026-04-01

## Purpose

This repository is not a single-objective training lab.

It is an agent harness whose job is to help an AI agent:

1. understand a task
2. analyze and plan
3. execute in phases
4. review and recover
5. loop toward a higher-quality result

The `autoresearch` project proves that an autonomous loop can work well when the system has:

- one narrow edit surface
- one fixed metric
- one cheap experiment cycle
- one simple keep-or-discard rule

This repository does **not** have those properties by default.

So the correct adaptation is:

- keep the discipline
- do not copy the shape

## What To Reuse From `autoresearch`

The following ideas should be adopted directly:

- a written experiment contract
- a small allowed mutation surface
- a baseline-first workflow
- strict keep-or-discard rules
- lightweight experiment logging
- branch/worktree isolation for autonomous trials

The following ideas should **not** be copied literally:

- one global scalar objective
- "loop forever" behavior
- unrestricted self-modification of the harness core
- hardcoded git reset discipline as the only rollback tool

## Core Design Principles

### 1. The Harness Must Stay More Stable Than The Tasks It Runs

The harness is not the product being built by the agent.
It is the substrate that lets the agent build products.

This means self-improvement must be more conservative than ordinary feature work.

### 2. File-Based State Is A Feature

Project-local Markdown and JSON are intentionally kept because they are highly readable by LLMs.

The goal is not to replace them with a database.
The goal is to make them safer:

- atomic writes
- file locks on critical state
- stable schemas
- easy recovery after interruption

### 3. Improvement Must Be Bounded

Unlike `autoresearch`, this repository should not run an unbounded "never stop" loop by default.

Harness self-improvement should run in bounded sessions:

- fixed number of experiments, or
- fixed wall-clock budget, or
- until a defined acceptance target is reached

### 4. Multi-Dimensional Evaluation Beats One Score

There is no single `val_bpb` for this repository.

A good self-improvement run must satisfy a gate bundle:

- tests
- schema validity
- workflow smoke checks
- quality gate behavior
- trajectory/resume behavior
- artifact integrity

## Runtime Protection Model

Self-improvement should treat the codebase as three zones.

### Zone A: Protected Core

Changes here are allowed only with explicit justification and full validation.

Files:

- `scripts/workflow_engine.py`
- `scripts/unified_state.py`
- `scripts/state_schema.py`
- `scripts/quality_gate.py`
- `scripts/safe_io.py`
- `scripts/trajectory_logger.py`

Rules:

- prefer minimal edits
- one hypothesis per run
- must pass full core validation bundle
- if degraded, always rollback

### Zone B: Guided Mutable Surface

This is the preferred self-improvement zone.

Files:

- `scripts/router.py`
- `scripts/task_decomposer.py`
- `scripts/task_tracker.py`
- `scripts/search_adapter.py`
- `scripts/memory_ops.py`
- `skills/*/skill.md`
- `README.md`
- `SKILL.md`

Typical improvements:

- routing heuristics
- plan quality
- review/research output quality
- state prompts and instructions
- documentation truthfulness

### Zone C: Experimental Surface

This is where exploratory capability work should happen first.

Files:

- `scripts/experimental/*`
- `docs/roadmap/*`

Rules:

- safe to iterate faster
- not part of the main runtime until promoted
- promotion requires explicit acceptance

## Self-Improvement Run Contract

Each autonomous improvement run should work inside a dedicated branch or worktree.

Recommended branch pattern:

- `self-improve/<date>-<topic>`

Recommended worktree pattern:

- isolated temp worktree per run

Every run must record:

- hypothesis
- files changed
- checks executed
- hard-gate result
- soft observations
- keep or discard decision

## Required Baseline Before Any Mutation

Before editing anything, the agent must establish a baseline.

Required baseline checks:

1. current git branch and clean/dirty state
2. core regression suite
3. core type checks
4. targeted lint checks for runtime files
5. workflow smoke path:
   - `init`
   - `snapshot`
   - `validate`
   - `recommend`
6. quality gate smoke:
   - passing fixture must pass
   - failing fixture must fail

If the baseline is already broken, the run changes from "improvement" to "stabilization".

## Required Validation Bundle

### Hard Gates

A change must be discarded if any of the following fail:

- core pytest suite regresses
- schema validation fails
- quality gate behavior regresses
- state file becomes unreadable or malformed
- trajectory/resume path regresses
- core command-line entrypoints stop working

### Soft Signals

These do not automatically fail a run, but they affect keep/discard judgment:

- output quality improvement
- smaller or clearer diffs
- lower context noise
- fewer touched files
- better artifact metadata
- better review/research specificity

## Recommended Experiment Ledger

Use a lightweight machine-readable ledger similar to `autoresearch/results.tsv`.

Recommended file:

- `.self-improvement/results.tsv`

Recommended columns:

```tsv
run_id	hypothesis	files_changed	checks_passed	status	notes
```

Where:

- `run_id`: short timestamp or branch-local id
- `hypothesis`: what this run tries to improve
- `files_changed`: semicolon-separated paths
- `checks_passed`: summary of the gate bundle
- `status`: `keep`, `discard`, `rollback`, `stabilization`
- `notes`: important result or regression detail

The ledger should remain simple enough for an LLM to read directly.

## Improvement Loop

This is the adapted loop for this repository.

1. Establish baseline.
2. Pick exactly one improvement hypothesis.
3. Limit edits to one zone unless there is a clear dependency.
4. Prefer Guided Mutable Surface before touching Protected Core.
5. Run the required validation bundle.
6. Record the outcome in the ledger.
7. Keep only if hard gates pass and the change is directionally better.
8. Roll back immediately if the run worsens reliability or truthfulness.

## Good Hypothesis Examples

- Improve `REVIEWING` by preferring `owned_files` before repository scan fallback.
- Make `RESEARCH` metadata more explicit and easier to audit.
- Expand `safe_io` coverage to one missing runtime write path.
- Tighten `quality_gate` behavior for code tasks.
- Reduce route ambiguity for a known prompt family.

## Bad Hypothesis Examples

- Rewrite the entire harness architecture in one run.
- Modify router, state schema, trajectory logic, and review output together.
- Add a new multi-agent system directly into the stable runtime.
- Keep iterating indefinitely without a stop condition.

## Promotion Rules

A change can move from experimental to stable only if:

1. it is already isolated in `scripts/experimental/`
2. it has a clear runtime purpose
3. it has dedicated tests
4. it does not regress core checks
5. README and SKILL describe it truthfully

## Immediate Repository Priorities

The next self-improvement cycles should focus on reliability before feature expansion.

### P0

- make `quality_gate` fail closed for code-task completion
- expand safe write coverage to all critical state and trajectory writes
- add file locks for the highest-value shared state files
- reduce core runtime lint debt

### P1

- make `REVIEWING` more change-targeted
- make `RESEARCH` source metadata stricter and easier to audit
- tighten plan verification so empty verification cannot silently pass
- strengthen E2E assertions around metadata truth

### P2

- improve default findings/review content density
- simplify trajectory resume summaries
- continue lowering experimental/runtime context noise

## Non-Goals

This program does **not** propose:

- a database migration
- full plugin infrastructure right now
- infinite autonomous self-improvement
- unrestricted edits to the harness core

## Acceptance Criteria For This Program

This self-improvement program is successfully adopted when:

1. self-improvement runs use a written contract instead of free-form repo-wide edits
2. every autonomous improvement run has a baseline and a recorded outcome
3. core runtime changes are kept or discarded by explicit gates
4. protected core and experimental surfaces are treated differently
5. the harness becomes more reliable without becoming harder for an LLM to inspect
