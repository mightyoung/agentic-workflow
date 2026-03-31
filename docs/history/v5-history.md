# v5.x History

This directory contains historical information about agentic-workflow versions.

## v5.7 (2026-03-24)

### New Features

- **EXPLORING Phase**: Socratic deep exploration using questioning to uncover hidden assumptions
- **Trajectory Persistence**: Added `./trajectories/` directory for execution trajectory logging (basic implementation)

### v5.7.1 Privacy Assessment (2026-03-25)

## v5.6 (2026-03-22)

### Parallel Execution (Default Enabled)

> Default parallel-first mode: Independent tasks automatically execute in parallel for maximum throughput.

| Band | Phase | Parallel Strategy |
|------|-------|------------------|
| Band 0 | ROUTER | Sequential (entry point) |
| Band 1 | RESEARCH \|\| THINKING | Parallel |
| Band 2 | PLANNING | Sequential |
| Band 3 | EXECUTING | Sequential |
| Band 4 | REVIEWING \|\| DEBUGGING | Partial parallel |
| Band 5 | COMPLETE | Sequential |

### Multi-Level Search Fallback

| Priority | Provider | Status |
|----------|----------|--------|
| 1 | tavily | Primary |
| 2 | websearch | MCP fallback |
| 3 | baidu-search | Final fallback |

## v5.5 (2026-03-22)

### Result-only Subagent Spawning

For tasks requiring only results, skip all PHASE FLOW and directly spawn specialized Subagent.

| Path | Time | Token Reduction |
|------|------|----------------|
| Result-only | 15% | 70% |
| Fast Path | 40% | 40% |
| Standard Path | 100% | 0% |

### Subagent Definitions (12)

- researcher, planner, coder, reviewer, debugger
- security_expert, performance_expert
- frontend_developer, backend_architect
- devops_automator, database_optimizer, technical_writer

## v5.4 (2026-03-22)

### WITH vs WITHOUT Skill Benchmark

| Metric | WITHOUT Skill | WITH Skill | Difference |
|--------|-------------|------------|------------|
| Token Consumption | Baseline | +38-100% | More expensive |
| Code Quality | 5-65/100 | 8.5-93/100 | 30-70% better |
| Test Coverage | 0-60% | 85%+ | Overwhelming advantage |
| TDD First-pass Rate | 60-70% | 100% | 40% better |

## v4.13 (Earlier)

### YAGNI Check

> Don't implement features that aren't needed yet.

### Frequent Commit Rules

Commit after every meaningful independent unit of work.

## v5.5.1 Multi-Dimensional Benchmark

### Decision Matrix

| Scenario | Recommendation | Reason |
|----------|---------------|--------|
| Classic Algorithm | No Skill | +38% tokens, no benefit |
| Simple CRUD | No Skill | +100% tokens, slower |
| Complex System | Use Skill | Quality + TDD + Review |
| Bug Debugging | Use Skill | 5-step systematic |
