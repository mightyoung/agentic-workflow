# Protected Zones for Self-Improvement
# Part of docs/self_improvement_program.md implementation.
# Version: 1.0

## Zone A: Protected Core (Never touch without explicit justification)

These files form the stable foundation. Changes here require:
- Explicit justification
- Full validation bundle
- One hypothesis per run
- Rollback if degraded

Files:
- `scripts/workflow_engine.py` - Phase orchestration, state transitions
- `scripts/unified_state.py` - Single source of truth schema
- `scripts/state_schema.py` - State data model
- `scripts/quality_gate.py` - Quality enforcement
- `scripts/safe_io.py` - Atomic write / file lock primitives
- `scripts/trajectory_logger.py` - Trajectory persistence
- `scripts/router.py` - Entry routing
- `scripts/task_decomposer.py` - Task decomposition
- `scripts/task_tracker.py` - Task state tracking
- `scripts/memory_ops.py` - Session state operations
- `scripts/search_adapter.py` - Web search integration
- `scripts/state_schema.py` - Core data model
- `SKILL.md` - Skill definition
- `README.md` - Root documentation

## Zone B: Guided Mutable Surface (Preferred for improvements)

These are the preferred files for self-improvement:
- Routing heuristics refinements
- Plan quality improvements
- Review/research output quality
- State prompts and instructions
- Documentation truthfulness

Files:
- `skills/*/skill.md` - Phase skill definitions
- `scripts/README.md` - Scripts documentation
- `docs/roadmap/roadmap.md` - Roadmap planning

## Zone C: Experimental Surface (Safe to iterate)

Files:
- `scripts/experimental/*` - All experimental modules
- `docs/experimental/*` - Experimental documentation
- `tests/bench_*` - Benchmark tests
- `tests/run_*.py` - Historical test runners

## Self-Improvement Rules

1. **Baseline first**: Run `.self-improvement/baseline_check.sh` before any mutation
2. **One hypothesis**: Limit to one improvement idea per run
3. **Zone discipline**: Prefer Zone B before Zone A
4. **Validation bundle**: Run full checks after changes
5. **Ledger recording**: Record hypothesis, files, result in `.self-improvement/results.tsv`
6. **Hard gates fail-fast**: If core tests regress, rollback immediately
7. **No unbounded loops**: Set a stop condition before starting
