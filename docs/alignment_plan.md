# Agentic Workflow Alignment Plan

> Scope: align documentation, scripts, and tests around the repository's real executable behavior.
> Status: proposed
> Updated: 2026-03-30

## Problem Statement

The repository currently has three partially divergent layers:

1. Design/spec layer in `SKILL.md` and `skills/*/skill.md`
2. Executable layer in `scripts/` and shell helpers
3. Validation layer in `tests/`

The current issue is not one broken script. The issue is that these three layers no longer describe the same system.

## Alignment Strategy

Short-term strategy: align the docs and tests to the current executable scripts first.

Reason:
- The scripts in `scripts/` are the only concrete runtime surface today.
- Several phase APIs described in docs do not exist yet.
- Some tests validate simulated logic instead of the shipped scripts.

This means the immediate goal is not "implement the ideal architecture". The immediate goal is "make the repository truthful and runnable".

## Target Outcome

After alignment:

- `README.md` describes a workflow that actually exists
- router, state storage, planning, and tracking each have one canonical behavior
- tests verify real script behavior instead of internal mock logic
- phase docs stop presenting nonexistent APIs as if they were implemented
- a new contributor can identify the real entry points within a few minutes

## Workstreams

### 1. Canonical Runtime Baseline

Define the current executable baseline as:

- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/router.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/memory_ops.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/task_tracker.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/run_tracker.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/step_recorder.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/create_plan.sh`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/check_template.sh`

Actions:
- Add a "current runtime surface" section to `/Users/muyi/Downloads/dev/agentic-workflow/README.md`
- Make `/Users/muyi/Downloads/dev/agentic-workflow/SKILL.md` explicit about which parts are implemented and which parts are target design
- Make `/Users/muyi/Downloads/dev/agentic-workflow/scripts/README.md` the source of truth for script CLI usage

Acceptance criteria:
- Top-level docs identify the real entry points without requiring source inspection
- The same core script list is referenced consistently in root docs and script docs

### 2. Router Alignment

Current problem:
- Router docs describe a multi-layer semantic system
- The actual router is a keyword-based phase selector

Files to update:
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/router/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/SKILL.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/README.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/tests/run_phase_test.py`

Actions:
- Rewrite router documentation around actual supported behavior:
  - negative keyword filtering
  - forced phase keyword routing
  - ordered keyword matching
  - result-only shortcut if still supported by docs
- Remove or clearly mark unimplemented features such as:
  - preload detection
  - semantic interpretation layer
  - session-aware routing
  - explicit multi-stage route stack unless implemented
- Refactor tests to call the real router logic instead of duplicating routing rules locally

Acceptance criteria:
- Router docs and tests describe the same decision rules as the executable router
- A route example in docs can be reproduced by running the script directly

### 3. Session State And Memory Path Alignment

Current problem:
- Shared docs describe `~/.gstack/sessions/...`
- Actual tools write `SESSION-STATE.md` in the project

Files to update:
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/_shared/preamble.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/research/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/planning/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/executing/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/reviewing/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/complete/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/memory_ops.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/README.md`

Recommended short-term decision:
- Standardize docs on project-local files first
- Defer `~/.gstack` support until a configurable storage abstraction is introduced

Actions:
- Update docs to describe the project-local state files actually used by the scripts
- Audit all phase docs for stale references to `~/.gstack`
- If needed, add a short "future direction" note for configurable external session storage

Acceptance criteria:
- Docs mention one storage location model only
- Memory scripts and workflow docs no longer conflict on where session state lives

### 4. Phase API Truthfulness

Current problem:
- Multiple phase docs invoke APIs such as `phase_enter(...)`, `decision_record(...)`, `metric_record(...)`, and `error_record(...)`
- These APIs are not implemented in the repository

Files to update:
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/reviewing/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/complete/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/executing/skill.md`
- Any other phase doc referencing nonexistent telemetry helpers

Actions:
- Replace nonexistent API calls with one of:
  - plain-language process steps
  - references to actual scripts in `scripts/`
  - explicit "future implementation" notes
- Reserve function-call formatting for implemented commands only
- Mark `skills/_shared/telemetry.md` clearly as conceptual or deprecated if it is not active

Acceptance criteria:
- No phase doc presents nonexistent helper APIs as runnable capabilities
- Every command-like reference in docs maps to a file or implementation that exists

### 5. Execution Tracking Model Alignment

Current problem:
- Docs describe trajectory files under `trajectories/`
- Actual scripts persist run and step statistics in separate tracker files

Files to update:
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/executing/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/SKILL.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/README.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/tests/test_evaluation.py`
- Related tests for run tracking and phase recording

Recommended short-term decision:
- Treat `run_tracker.py` and `step_recorder.py` as the canonical implementation
- Move trajectory JSON to roadmap status unless it is actually implemented

Actions:
- Remove claims that per-task trajectory JSON already exists
- Document the current tracker outputs, file names, and intended usage
- Add tests around the real tracker outputs if missing

Acceptance criteria:
- Tracking documentation matches actual generated artifacts
- A user can run tracker scripts and observe the files described in docs

### 6. Planning Template Alignment

Current problem:
- Planning docs expect a canonical `task_plan.md`
- The shell generator creates dated plan files using an older structure

Files to update:
- `/Users/muyi/Downloads/dev/agentic-workflow/skills/planning/skill.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/create_plan.sh`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/check_template.sh`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/README.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/references/_deprecated_v4/task_plan.md`

Recommended short-term decision:
- Standardize on one canonical plan filename and one minimal schema

Actions:
- Decide whether the canonical output is:
  - `task_plan.md`, or
  - dated files generated per task
- Update the generator and docs together
- Fix template validation paths so the checker only references files that exist
- Explicitly mark deprecated templates as legacy reference material

Acceptance criteria:
- Plan generation and plan documentation describe the same filename and schema
- Template checks pass against files that actually exist in the repo

### 7. Test Realignment

Current problem:
- Some tests encode expected workflow behavior independently
- Some runner scripts are simulation-heavy and do not validate the true implementation

Files to update:
- `/Users/muyi/Downloads/dev/agentic-workflow/tests/run_phase_test.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/tests/run_subagent_test.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/tests/run_test.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/tests/run_full_test.py`
- `/Users/muyi/Downloads/dev/agentic-workflow/tests/TEST_ANALYSIS.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/tests/TEST_REPORT.md`

Actions:
- Split tests into three categories:
  - unit tests for script behavior
  - integration tests for real workflow chains
  - documentation/spec conformance tests
- Remove or relabel simulation-heavy scripts so they are not mistaken for runtime validation
- Prefer importing real code paths over reproducing expected logic in test files

Acceptance criteria:
- Test names and reports distinguish simulated evaluation from real implementation checks
- At least one integration path verifies actual router-to-state or router-to-tracker behavior

### 8. Documentation Entry-Point Cleanup

Current problem:
- New readers can easily mistake `src/` for the main runtime
- Root docs mix benchmark claims, roadmap claims, and current behavior

Files to update:
- `/Users/muyi/Downloads/dev/agentic-workflow/README.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/README_CN.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/scripts/README.md`
- `/Users/muyi/Downloads/dev/agentic-workflow/agents/README.md`

Actions:
- Add a "What this repo actually contains" section
- Separate "implemented now" from "design target / benchmark / historical notes"
- Explain that `src/` contains examples or auxiliary code, not the workflow runtime
- Add a minimal quickstart using real scripts only

Acceptance criteria:
- A new contributor can identify the workflow runtime without reading source code
- README quickstart commands work as documented

## Recommended Execution Order

1. Canonical runtime baseline
2. Router alignment
3. Session state and memory path alignment
4. Test realignment for router and trackers
5. Planning template alignment
6. Phase API truthfulness cleanup
7. Documentation entry-point cleanup

## Deliverables

### Deliverable A: Truthful Docs Pass

Scope:
- Root docs
- router docs
- shared preamble
- scripts README

Goal:
- Stop overstating capabilities

### Deliverable B: Runtime/Test Alignment Pass

Scope:
- router tests
- tracker tests
- plan generator and template check

Goal:
- Ensure tests validate the shipped scripts

### Deliverable C: Optional Runtime Expansion

Scope:
- only after A and B are complete

Goal:
- Implement missing design features intentionally instead of implying they already exist

## Non-Goals

- Building the full ideal orchestration runtime in one pass
- Implementing semantic routing before test and doc truthfulness are fixed
- Expanding telemetry APIs before deciding the canonical tracking model
- Preserving every historical v4/v5 claim as current behavior

## Definition Of Done

- All top-level workflow docs reflect current executable behavior
- All command examples in docs map to existing scripts and valid CLI arguments
- Tests no longer duplicate core runtime rules in isolation
- No phase doc implies that nonexistent helper APIs are available
- The repository exposes one clear baseline workflow for contributors
