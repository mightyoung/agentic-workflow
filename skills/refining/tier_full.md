<!-- tier: ~45% full methodology + commands -->

# REFINING - Full Methodology

## Triggering REFINING

### Active Triggers
- User: "让我们迭代一下", "改进一下", "优化一下", "精炼一下"
- Explicit command: `/refining` or `/iterate`

### Passive Triggers
- REVIEWING phase: "这个实现有问题，我们需要修复"
- EXECUTING phase: "遇到障碍，无法继续"
- PLANNING phase: "方案之间有冲突"

### Auto-Triggers
- Test failures detected
- Code review flags P0/P1 issues
- Consistency checks fail

## Problem Categories Reference

| Category | Description | Examples |
|----------|-------------|----------|
| `consistency` | Internal contradictions | Outline conflicts, setting inconsistencies |
| `completeness` | Missing edge case handling | Boundary conditions not covered |
| `feasibility` | Technical impossibility | Implementation blocked by constraints |
| `performance` | Speed/resource issues | Slow algorithms, memory bloat |
| `quality` | Standards violations | Bad code, missing docs |
| `alignment` | User expectation mismatch | Feature doesn't match spec |

## DISCOVER — Complete Checklist

```markdown
## Discovery Checklist

### Consistency Check
- [ ] Architecture internally self-consistent?
- [ ] Assumptions don't contradict?
- [ ] Naming conventions uniform?
- [ ] Data flows logical?

### Completeness Check
- [ ] All edge cases handled?
- [ ] Error cases covered?
- [ ] Boundary conditions tested?
- [ ] State transitions complete?

### Feasibility Check
- [ ] Technology choices viable?
- [ ] Dependencies available?
- [ ] Timeline realistic?
- [ ] Team skills adequate?

### Performance Check
- [ ] Algorithms optimal?
- [ ] Database queries indexed?
- [ ] Memory leaks possible?
- [ ] Scaling concerns addressed?

### Quality Check
- [ ] Code standards met?
- [ ] Test coverage adequate?
- [ ] Documentation complete?
- [ ] Security review passed?

### Alignment Check
- [ ] Matches user requirements?
- [ ] Meets success criteria?
- [ ] MVP scope correct?
- [ ] User feedback positive?
```

## ANALYZE — 5-Why Template

```markdown
## Problem Analysis: [ISSUE-ID]

**Problem Statement**: [What's wrong]

**5-Why Analysis**:
- Why1: [First answer]
- Why2: [Follow on Why1]
- Why3: [Follow on Why2]
- Why4: [Follow on Why3]
- Why5: [Follow on Why4]

**Root Cause Identified**: [The underlying pattern]

**Impact Scope**:
- Affected files: [list]
- Affected functions: [list]
- User impact: [scenario]
- Rollback risk: [medium/high/critical]

**Solution Options**:
| Option | Approach | Pros | Cons | Effort |
|--------|----------|------|------|--------|
| A | [strategy] | [+] | [-] | high |
| B | [strategy] | [+] | [-] | medium |

**Recommendation**: [Option] because [reason]
```

## FIX — Execution Process

```bash
# 1. Create fix branch
git checkout -b fix/ISSUE-001

# 2. Execute fix (example for code)
# [Apply changes based on chosen solution]

# 3. Update tests
# [Modify test cases to cover fix]

# 4. Update documentation
# [Sync any docs that reference changed behavior]

# 5. Verify locally
npm test
npm run lint

# 6. Commit with detailed message
git commit -m "fix: resolve ISSUE-001 - [description]"
```

## VERIFY — Testing & Confirmation

**Verification checklist per fix**:
```markdown
## Verification: ISSUE-001

- [ ] **Problem resolved**: Original issue no longer exists
  - How verified: [test/manual check]
- [ ] **No regressions**: Related features still work
  - Tests run: [list test files]
  - Manual checks: [list scenarios]
- [ ] **Documentation updated**: Related docs synced
  - Files updated: [list]
- [ ] **Code quality**: Standards met
  - Lint passes: Yes/No
  - Test coverage: X%
- [ ] **User confirmation**: User confirms fix acceptable (if applicable)
  - User feedback: [quote or note]

**Status**: PASS / FAIL
```

## Loop Termination Protocol

### When to Stop Iterating

```
IF all_p0_p1_fixed AND all_verified THEN
    Status: DONE
    Proceed to next phase
ELSE IF max_iterations_reached(problem_severity) THEN
    IF problem_severity == P0_CRITICAL THEN
        Escalate to user
    ELSE
        Record as technical_debt
        Continue to next phase
    END
END
```

### Max Iterations Per Severity

| Severity | Max Attempts | If Exceeded |
|----------|-------------|------------|
| P0_CRITICAL | 5 | Escalate to user |
| P1_HIGH | 3 | Log as debt, continue |
| P2_MEDIUM | 2 | Log as debt, continue |
| P3_LOW | 1 | Defer to backlog |

## Integration Points

### From REVIEWING
```
REVIEWING [found problems] → REFINING(DISCOVER)
→ [ANALYZE/FIX/VERIFY loop]
→ VERIFY [confirms fix]
→ Back to REVIEWING or next phase
```

### From EXECUTING
```
EXECUTING [hit obstacle] → REFINING(ANALYZE)
→ [diagnose + fix]
→ Return to EXECUTING [continue]
```

### From PLANNING
```
PLANNING [conflict found] → REFINING(DISCOVER)
→ [resolve conflict]
→ Back to PLANNING [continue]
```

## Output Files Generated

| File | Purpose | Location |
|------|---------|----------|
| `refining_report.md` | Complete feedback loop record | Project root |
| `issues.md` | Problem tracking list | Project root |

## Example: Fixing a Consistency Issue

```
DISCOVER:
- Found: API endpoint returns different error format than spec
- Severity: P1_HIGH (breaks clients)

ANALYZE:
- Root cause: Developer refactored error handling but missed one endpoint
- Affected: 3 endpoints total; 2 already fixed, 1 remaining
- Solution: Standardize error format across all endpoints

FIX:
- Update remaining endpoint error handler
- Add test for error format consistency
- Update API documentation
- Commit: "fix: standardize error response format for all endpoints"

VERIFY:
- Run full API test suite → PASS
- Manual spot-check 3 endpoints → all return same format
- Check documentation → updated
- Status: PASS → proceed to next phase
```
